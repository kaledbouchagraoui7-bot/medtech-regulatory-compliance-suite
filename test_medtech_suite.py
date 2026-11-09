#!/usr/bin/env python3
"""
Unit & Integration Tests for Unified MedTech, CRO & Digital Health Regulatory Compliance Suite.
Tests:
  1. Engine A (Digital Domain Compliance & Security Auditor - 4-sheet Excel, Word, 300-DPI PNG/PDF)
  2. Engine B (Clinical Literature PRISMA 2020 Pilot Package Generator - Word, 4-sheet Excel, 300-DPI PRISMA PNG/PDF)
  3. Combined Orchestrator (`build_unified_medtech_dossier` - `00_Unified_Executive_Brief.docx` + both folders + `.zip`)
"""

import shutil
import tempfile
import unittest
import zipfile
from pathlib import Path

import openpyxl
from docx import Document

from medtech_suite import build_unified_medtech_dossier


class TestUnifiedMedTechSuite(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = Path(tempfile.mkdtemp(prefix="medtech_suite_test_"))
        self.repo_dir = Path(__file__).resolve().parent
        self.records_csv = self.repo_dir / "records.csv"
        self.config_json = self.repo_dir / "config.json"

        self.synthetic_audit = {
            "domain": "healthtech-demo.ch",
            "final_url": "https://www.healthtech-demo.ch/",
            "scanned_at": "2026-03-02 18:00 UTC (Fictional Demo Sample)",
            "response_time_ms": 124,
            "overall_score": 52,
            "grade": "D",
            "pass_count": 13,
            "warn_count": 4,
            "fail_count": 8,
            "total_checks": 25,
            "pillar_scores": {
                "1. Email & Anti-Spoofing (DMARC/SPF)": {"score": 47, "pass": 2, "warn": 1, "fail": 1, "total": 4},
                "2. Swiss nFADP & GDPR Web Privacy": {"score": 51, "pass": 2, "warn": 0, "fail": 2, "total": 4},
                "3. Edge & Transport Security (HTTP/TLS)": {"score": 28, "pass": 2, "warn": 2, "fail": 5, "total": 9},
                "4. Accessibility (EAA / WCAG 2.1 AA)": {"score": 100, "pass": 4, "warn": 0, "fail": 0, "total": 4},
                "5. Technical SEO & AI Discoverability": {"score": 100, "pass": 4, "warn": 0, "fail": 0, "total": 4},
            },
            "findings": [
                {
                    "id": "EML-01",
                    "pillar": "1. Email & Anti-Spoofing (DMARC/SPF)",
                    "title": "DMARC Anti-Spoofing Record & Policy",
                    "status": "FAIL",
                    "severity": "CRITICAL",
                    "weight": 12,
                    "evidence": "No _dmarc.healthtech-demo.ch TXT record found in public DNS.",
                    "impact": "External attackers can spoof emails from @healthtech-demo.ch.",
                    "remediation": 'Publish _dmarc.healthtech-demo.ch TXT record: "v=DMARC1; p=quarantine;"',
                    "regulation": "RFC 7489 / Swiss nFADP Art. 8",
                },
                {
                    "id": "PRV-01",
                    "pillar": "2. Swiss nFADP & GDPR Web Privacy",
                    "title": "Remote Google Fonts IP Leak (Schrems II / nFADP)",
                    "status": "FAIL",
                    "severity": "HIGH",
                    "weight": 8,
                    "evidence": "Page HTML loads fonts directly from fonts.googleapis.com on initial load.",
                    "impact": "Transmits visitor IP to US servers before consent.",
                    "remediation": "Self-host WOFF2 fonts locally.",
                    "regulation": "Swiss nFADP Art. 6 & 16 / EU GDPR Art. 44",
                },
                {
                    "id": "SEC-02",
                    "pillar": "3. Edge & Transport Security (HTTP/TLS)",
                    "title": "HTTP Strict-Transport-Security (HSTS)",
                    "status": "FAIL",
                    "severity": "HIGH",
                    "weight": 7,
                    "evidence": "Missing 'Strict-Transport-Security' response header.",
                    "impact": "Vulnerable to SSL-stripping on public networks.",
                    "remediation": "Add Strict-Transport-Security: max-age=31536000; includeSubDomains",
                    "regulation": "RFC 6797 / EU MDR Annex I GSPR 17.2",
                },
            ],
        }

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_build_unified_medtech_dossier_creates_combined_deliverables(self) -> None:
        res = build_unified_medtech_dossier(
            target_domain="healthtech-demo.ch",
            records_csv=self.records_csv,
            config_json=self.config_json,
            base_out=self.temp_dir,
            offline_audit_override=self.synthetic_audit,
        )

        self.assertTrue(res["brief_docx"].exists(), "Unified executive brief .docx must exist")
        self.assertTrue(res["zip_path"].exists(), "Unified .zip dossier must exist")

        # Check Part I (Digital Compliance Audit)
        d01 = res["digital_dir"]
        self.assertTrue((d01 / "healthtech_demo_ch_scorecard.png").exists())
        self.assertTrue((d01 / "healthtech_demo_ch_executive_audit.docx").exists())
        wb_dig = openpyxl.load_workbook(str(d01 / "healthtech_demo_ch_technical_findings.xlsx"))
        self.assertEqual(
            wb_dig.sheetnames,
            ["Findings_Matrix", "Pillar_Summary", "Remediation_Roadmap", "README"],
        )

        # Check Part II (Clinical PRISMA 2020 Pilot)
        d02 = res["clinical_dir"]
        self.assertTrue(any(d02.glob("*_evidence_table.docx")))
        self.assertTrue(any(d02.glob("*_literature_workbook.xlsx")))
        self.assertTrue((d02 / "prisma_flow_diagram.png").exists())
        self.assertTrue((d02 / "prisma_flow_diagram.pdf").exists())

        # Check Unified Brief content
        doc = Document(str(res["brief_docx"]))
        full_text = "\n".join(p.text for p in doc.paragraphs)
        self.assertIn("UNIFIED MEDTECH & CRO COMPLIANCE DOSSIER", full_text)
        self.assertIn("52/100", full_text)


if __name__ == "__main__":
    unittest.main()
