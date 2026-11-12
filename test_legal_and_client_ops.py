#!/usr/bin/env python3
"""
Unit & Integration Tests for Automated Legal Disclaimers (`legal_terms.py`)
and Zero-Cost Client Onboarding, Multi-Track Delivery & QA Engine (`client_ops_automation.py`).
"""

from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

import openpyxl
from docx import Document
from openpyxl.styles import Alignment, Border, Font, Side

from client_ops_automation import (
    _curated_to_pilot_csv,
    create_engagement,
    resolve_payment_block,
    run_delivery_for_engagement,
    stage_delivery,
    stage_onboarding,
    stage_positive_reply_onboarding,
    verify_delivery_package,
)
from legal_terms import (
    TERMS_VERSION,
    append_terms_section_docx,
    append_terms_to_readme_xlsx,
    build_legal_web_pages,
    get_legal_clauses,
    get_privacy_clauses,
    load_provider_config,
    render_terms_txt,
    set_custom_domain,
)


class TestLegalAndClientOps(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = Path(tempfile.mkdtemp(prefix="client_ops_test_"))
        self.repo_dir = Path(__file__).resolve().parent
        self.eng_json = self.temp_dir / "engagements.json"
        self.staged_dir = self.temp_dir / "staged_replies"
        self.pms_sample = json.loads(
            (self.repo_dir.parent / "pms-clinicaltrials-openfda-monitor" / "sample_pms_input.json").read_text(
                encoding="utf-8"
            )
        )
        self.synthetic_audit = {
            "domain": "medtech-client.ch",
            "final_url": "https://www.medtech-client.ch/",
            "scanned_at": "2026-11-11 20:00 UTC (Synthetic Test)",
            "response_time_ms": 95,
            "overall_score": 58,
            "grade": "D",
            "pass_count": 3,
            "warn_count": 1,
            "fail_count": 1,
            "total_checks": 5,
            "pillar_scores": {
                "1. Email & Anti-Spoofing (DMARC/SPF)": {"score": 40, "pass": 1, "warn": 0, "fail": 1, "total": 2},
                "2. Swiss nFADP & GDPR Web Privacy": {"score": 100, "pass": 1, "warn": 0, "fail": 0, "total": 1},
                "3. Edge & Transport Security (HTTP/TLS)": {"score": 50, "pass": 0, "warn": 1, "fail": 0, "total": 1},
                "4. Accessibility (EAA / WCAG 2.1 AA)": {"score": 100, "pass": 1, "warn": 0, "fail": 0, "total": 1},
            },
            "findings": [
                {
                    "id": "EML-01",
                    "pillar": "1. Email & Anti-Spoofing (DMARC/SPF)",
                    "title": "DMARC Anti-Spoofing Record & Policy",
                    "status": "FAIL",
                    "severity": "CRITICAL",
                    "weight": 12,
                    "evidence": "Missing _dmarc TXT record.",
                    "impact": "Domain spoofing risk.",
                    "remediation": 'Publish _dmarc.medtech-client.ch TXT "v=DMARC1; p=quarantine;"',
                    "regulation": "RFC 7489 / nFADP Art. 8",
                },
                {
                    "id": "SEC-02",
                    "pillar": "3. Edge & Transport Security (HTTP/TLS)",
                    "title": "HTTP Strict-Transport-Security (HSTS)",
                    "status": "WARN",
                    "severity": "MEDIUM",
                    "weight": 5,
                    "evidence": "HSTS max-age shorter than 1 year.",
                    "impact": "Downgrade exposure.",
                    "remediation": "Set Strict-Transport-Security: max-age=31536000; includeSubDomains",
                    "regulation": "RFC 6797",
                },
                {
                    "id": "PRV-04",
                    "pillar": "2. Swiss nFADP & GDPR Web Privacy",
                    "title": "Privacy Policy Link",
                    "status": "PASS",
                    "severity": "HIGH",
                    "weight": 6,
                    "evidence": "Found /privacy link on homepage.",
                    "impact": "Transparent GDPR/nFADP disclosure.",
                    "remediation": "None",
                    "regulation": "GDPR Art. 13 / nFADP Art. 19",
                },
            ],
        }

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_legal_terms_rendering_and_web_bundle(self) -> None:
        cfg = load_provider_config(self.repo_dir / "client_ops_config.json")
        clauses = get_legal_clauses("sentinel_compliance", cfg)
        privacy = get_privacy_clauses(cfg)
        self.assertGreaterEqual(len(clauses), 7)
        self.assertGreaterEqual(len(privacy), 4)

        txt = render_terms_txt("pms_openfda_psur", cfg)
        self.assertIn(TERMS_VERSION, txt)
        self.assertIn("293 B", txt)
        self.assertIn("capped at the total fees actually paid", txt)

        # Word injection must NOT add extra tables
        doc = Document()
        doc.add_paragraph("Report Body")
        append_terms_section_docx(doc, track="clinical_lit_prisma", cfg=cfg)
        self.assertEqual(len(doc.tables), 0)
        full_doc = "\n".join(p.text for p in doc.paragraphs).lower()
        self.assertIn("terms of service", full_doc)
        self.assertIn("liability", full_doc)

        # Excel injection appends rows cleanly inside existing README sheet
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "README"
        ws.append(["Field", "Description"])
        thin = Side(border_style="thin", color="CBD5E1")
        append_terms_to_readme_xlsx(
            ws,
            Border(left=thin, right=thin, top=thin, bottom=thin),
            Font(name="Calibri", size=10, bold=True),
            Font(name="Calibri", size=10),
            Alignment(wrap_text=True, vertical="top"),
            track="sentinel_compliance",
            cfg=cfg,
        )
        self.assertEqual(wb.sheetnames, ["README"])
        self.assertGreater(ws.max_row, 5)

        # Static HTML deployment bundle (Storefront + EN Terms + FR CGV + Privacy + SEO + Samples + Security Headers)
        site_dir = self.temp_dir / "site"
        assets = build_legal_web_pages(site_dir, cfg)
        for key in (
            "index_html",
            "terms_html",
            "cgv_html",
            "privacy_html",
            "terms_txt",
            "headers",
            "nojekyll",
            "robots_txt",
            "security_txt",
            "nfadp_audit_html",
            "eu_mdr_psur_html",
            "prisma_2020_html",
            "sitemap_xml",
            "samples_dir",
        ):
            self.assertIn(key, assets)
            self.assertTrue(assets[key].exists(), f"Missing generated web asset: {key}")

        html_txt = assets["terms_html"].read_text(encoding="utf-8")
        self.assertIn("Terms of Service &amp; Liability Disclaimer", html_txt)
        self.assertIn("privacy.html", html_txt)
        self.assertIn("cgv.html", html_txt)

        cgv_txt = assets["cgv_html"].read_text(encoding="utf-8")
        self.assertIn("Conditions Générales de Vente", cgv_txt)
        self.assertIn("388-2", cgv_txt)
        self.assertIn("293 B", cgv_txt)
        self.assertNotIn("where micro/franchise applies", cgv_txt)

        idx_txt = assets["index_html"].read_text(encoding="utf-8")
        self.assertIn("<h1", idx_txt)
        self.assertIn("PRISMA 2020", idx_txt)
        self.assertIn("OpenFDA MAUDE", idx_txt)
        self.assertIn('id="specimen-inspector"', idx_txt)
        self.assertIn('id="live-check"', idx_txt)
        self.assertIn("runDnsPrecheck()", idx_txt)
        self.assertIn("runFdaPrecheck()", idx_txt)
        self.assertIn("runEpmcPrecheck()", idx_txt)
        self.assertIn("openGmailWebCompose()", idx_txt)
        self.assertIn("copyScopeBrief()", idx_txt)
        self.assertIn("samples/sentinel_swiss_sme_sample.zip", idx_txt)
        self.assertIn("samples/prisma_glp1_clinical_sample.zip", idx_txt)
        self.assertIn("nfadp-audit.html", idx_txt)
        self.assertIn("selectSpecimenTab('t1')", idx_txt)
        self.assertIn('id="spec-panel-t4"', idx_txt)
        self.assertIn("ALCOA_PROVENANCE_MANIFEST.json", idx_txt)
        self.assertIn("04_eCTD_N_Count_Linter", idx_txt)
        self.assertIn("localStorage", idx_txt)
        self.assertIn("sentinel_lang", idx_txt)
        self.assertIn("data-ph-fr", idx_txt)
        self.assertIn("device_report_product_code", idx_txt)
        self.assertIn("sentinel_avatar_github.png", idx_txt)
        self.assertIn("selectIntakeMode", idx_txt)
        self.assertIn('id="f-mode"', idx_txt)
        self.assertIn("Design Partner Pilot", idx_txt)
        self.assertNotIn("fonts.googleapis.com", idx_txt)
        self.assertNotIn("GenevaOS", idx_txt)
        self.assertNotIn("`.docx`", idx_txt)
        # Ensure CSS color whitepaper note wasn't leaked into visible client prose
        body_html = idx_txt.split("</style>", 1)[-1]
        self.assertNotIn("#FFF2CC", body_html)
        for seo_key in ("nfadp_audit_html", "eu_mdr_psur_html", "prisma_2020_html"):
            self.assertNotIn("#FFF2CC", assets[seo_key].read_text(encoding="utf-8"))
        self.assertNotIn("#FFF2CC", assets["terms_txt"].read_text(encoding="utf-8"))

        hdr_txt = assets["headers"].read_text(encoding="utf-8")
        self.assertIn("https://dns.google https://api.fda.gov https://www.ebi.ac.uk", hdr_txt)
        robots_txt = assets["robots_txt"].read_text(encoding="utf-8")
        self.assertIn("Sitemap:", robots_txt)
        sitemap_txt = assets["sitemap_xml"].read_text(encoding="utf-8")
        self.assertIn("nfadp-audit.html", sitemap_txt)
        self.assertIn("eu-mdr-psur.html", sitemap_txt)
        self.assertIn("prisma-2020.html", sitemap_txt)

    def test_client_ops_lifecycle_sentinel_and_safety_gates(self) -> None:
        cfg_file = self.temp_dir / "client_ops_config.json"
        custom_cfg = load_provider_config(self.repo_dir / "client_ops_config.json")
        custom_cfg["payment"]["stripe_payment_links"]["sentinel_compliance"] = "https://buy.stripe.com/test_sentinel"
        cfg_file.write_text(json.dumps(custom_cfg, indent=2), encoding="utf-8")

        eng = create_engagement(
            company="Helvetia MedTech AG",
            domain="https://www.medtech-client.ch/about",
            contact_email="qa@medtech-client.ch",
            track="sentinel",
            country="CH",
            sector="MedTech OEM",
            engagements_json=self.eng_json,
            workspace_dir=self.temp_dir,
        )
        eid = eng["engagement_id"]
        self.assertEqual(eng["domain"], "medtech-client.ch")
        self.assertEqual(eng["track"], "sentinel_compliance")
        self.assertTrue((self.temp_dir / "engagements.csv").exists())

        # Unconfirmed send must raise ValueError
        with self.assertRaises(ValueError):
            stage_onboarding(eid, engagements_json=self.eng_json, config_path=cfg_file, send_email=True, confirm_send=False)

        gmail_calls: list[list[str]] = []

        def _fake_gmail(args: list[str]) -> str:
            gmail_calls.append(args)
            return '{"id": "draft_123"}'

        with mock.patch("client_ops_automation._run_gmail_cli", side_effect=_fake_gmail):
            onb = stage_onboarding(
                eid,
                engagements_json=self.eng_json,
                config_path=cfg_file,
                create_gmail_draft=True,
                send_email=False,
            )

        self.assertEqual(onb["engagement"]["status"], "ONBOARDING_DRAFTED")
        self.assertTrue(Path(onb["draft_path"]).exists())
        self.assertTrue(Path(onb["terms_path"]).exists())
        self.assertIn("https://buy.stripe.com/test_sentinel", Path(onb["draft_path"]).read_text(encoding="utf-8"))
        self.assertEqual(gmail_calls[0][:2], ["mutate", "create-draft"])

        # Run full Sentinel delivery offline
        deliv = run_delivery_for_engagement(
            eid,
            engagements_json=self.eng_json,
            offline_audit_override=self.synthetic_audit,
        )
        self.assertTrue(deliv["qa"]["passed"], f"QA failed: {deliv['qa']}")
        self.assertTrue(Path(deliv["zip_path"]).exists())
        self.assertTrue(Path(deliv["manifest_path"]).exists())
        self.assertTrue(Path(deliv["checklist_path"]).exists())

        # Check SHA-256 provenance integrity & ZIP contents
        manifest = json.loads(Path(deliv["manifest_path"]).read_text(encoding="utf-8"))
        deliv_dir = Path(eng["workspace_dir"]) / "deliverables"
        self.assertGreaterEqual(len(manifest["artifacts"]), 6)
        for art in manifest["artifacts"]:
            fpath = deliv_dir / art["relative_path"]
            self.assertTrue(fpath.exists())
            actual_sha = hashlib.sha256(fpath.read_bytes()).hexdigest()
            self.assertEqual(actual_sha, art["sha256"])

        with zipfile.ZipFile(deliv["zip_path"], "r") as zf:
            znames = zf.namelist()
            self.assertTrue(any(n.endswith("TERMS_OF_SERVICE_AND_DISCLAIMER.txt") for n in znames))
            self.assertTrue(any(n.endswith("ALCOA_PROVENANCE_MANIFEST.json") for n in znames))
            self.assertTrue(any(n.endswith("QA_SIGNOFF_CHECKLIST.md") for n in znames))

        # Delivery send gate check
        with self.assertRaises(ValueError):
            stage_delivery(eid, engagements_json=self.eng_json, config_path=cfg_file, send_email=True, confirm_send=False)

        with mock.patch("client_ops_automation._run_gmail_cli", side_effect=_fake_gmail):
            dstage = stage_delivery(
                eid,
                engagements_json=self.eng_json,
                config_path=cfg_file,
                create_gmail_draft=True,
                send_email=False,
            )
        self.assertEqual(dstage["engagement"]["status"], "DELIVERY_DRAFTED")
        self.assertEqual(gmail_calls[1][:2], ["mutate", "create-draft"])
        self.assertIn("--file", gmail_calls[1])

    def test_all_tracks_qa_and_inbox_positive_reply_hook(self) -> None:
        # 1. PMS Track
        e_pms = create_engagement(
            company="Alpine Valves GmbH",
            domain="alpine-valves.de",
            contact_email="ra@alpine-valves.de",
            track="pms",
            engagements_json=self.eng_json,
            workspace_dir=self.temp_dir,
        )
        r_pms = run_delivery_for_engagement(
            e_pms["engagement_id"],
            engagements_json=self.eng_json,
            pms_data_override=self.pms_sample,
        )
        self.assertTrue(r_pms["qa"]["passed"], r_pms["qa"])

        # 2. PRISMA Track
        e_pr = create_engagement(
            company="EuroCRO Trials",
            domain="eurocro-demo.fr",
            contact_email="biostats@eurocro-demo.fr",
            track="prisma",
            engagements_json=self.eng_json,
            workspace_dir=self.temp_dir,
        )
        r_pr = run_delivery_for_engagement(e_pr["engagement_id"], engagements_json=self.eng_json)
        self.assertTrue(r_pr["qa"]["passed"], r_pr["qa"])

        # 3. RA Command Center Track
        e_ra = create_engagement(
            company="Nordic Regulatory",
            domain="nordic-ra.se",
            contact_email="dir@nordic-ra.se",
            track="ra",
            engagements_json=self.eng_json,
            workspace_dir=self.temp_dir,
        )
        r_ra = run_delivery_for_engagement(e_ra["engagement_id"], engagements_json=self.eng_json)
        self.assertTrue(r_ra["qa"]["passed"], r_ra["qa"])

        # 4. Unified Dossier Track
        e_uni = create_engagement(
            company="Romandie HealthTech",
            domain="medtech-client.ch",
            contact_email="cto@medtech-client.ch",
            track="unified",
            engagements_json=self.eng_json,
            workspace_dir=self.temp_dir,
        )
        r_uni = run_delivery_for_engagement(
            e_uni["engagement_id"],
            engagements_json=self.eng_json,
            offline_audit_override=self.synthetic_audit,
        )
        self.assertTrue(r_uni["qa"]["passed"], r_uni["qa"])
        # Confirm verify_delivery_package fails cleanly when deliverables dir is empty
        empty_qa = verify_delivery_package(self.temp_dir / "empty_dir", "sentinel_compliance")
        self.assertFalse(empty_qa["passed"])

        # 5. EuropePMC -> PRISMA schema bridge
        out_csv = self.temp_dir / "epmc_bridge.csv"
        out_cfg = self.temp_dir / "epmc_cfg.json"
        _curated_to_pilot_csv(
            normalized_records=[
                {
                    "pmid": "12345678",
                    "title": "Transcatheter Valve Safety Cohort",
                    "authors": "Smith J, Lee K",
                    "pub_year": "2025",
                    "journal": "Eur Heart J",
                    "doi": "10.1000/test.1",
                    "pub_type": "Prospective Cohort",
                    "key_takeaway": "Low 30-day complication rate.",
                    "screening_stage": "included",
                },
                {
                    "pmid": "87654321",
                    "title": "Preclinical Bench Note",
                    "authors": "Doe A",
                    "pub_year": "2024",
                    "journal": "Bench Med",
                    "doi": "",
                    "pub_type": "Preclinical",
                    "screening_stage": "full_text_assessed",
                    "exclusion_reason": "",
                },
            ],
            out_csv=out_csv,
            epmc_query='"valve" AND "safety"',
            title="Bridge Test",
            indication="Aortic Stenosis",
            duplicates_removed=2,
            out_cfg=out_cfg,
        )
        self.assertTrue(out_csv.exists())
        self.assertIn("Did not meet eligibility window/content threshold", out_csv.read_text(encoding="utf-8"))

        # 6. Positive reply inbox watcher hook (non-sending)
        hook_eng_json = self.temp_dir / "inbox_engagements.json"
        staged = stage_positive_reply_onboarding(
            domain="swiss-med-demo.ch",
            sender_email="qa.lead@swiss-med-demo.ch",
            fresh_text="Yes, sounds good! Please share your invoice details and Terms so we can proceed.",
            company="Swiss Med Demo SA",
            country="CH",
            sector="MedTech",
            track="pms_openfda_psur",
            fee_label="EUR 650",
            staged_replies_dir=self.staged_dir,
            engagements_json=hook_eng_json,
        )
        self.assertEqual(staged["reply_intent"], "POSITIVE_BUY_OR_SCOPE_INTENT")
        self.assertTrue(Path(staged["draft_onboarding_path"]).exists())
        self.assertTrue(Path(staged["terms_path"]).exists())
        draft_txt = Path(staged["draft_onboarding_path"]).read_text(encoding="utf-8")
        self.assertIn("EUR 650", draft_txt)
        self.assertIn("TERMS_OF_SERVICE_AND_DISCLAIMER.txt", draft_txt)

    def test_custom_domain_binding_and_design_partner_pilot_mode(self) -> None:
        cfg_file = self.temp_dir / "client_ops_config.json"
        base_cfg = load_provider_config(self.repo_dir / "client_ops_config.json")
        cfg_file.write_text(json.dumps(base_cfg, indent=2), encoding="utf-8")

        updated_cfg = set_custom_domain("sentinel-regulatory.eu", config_path=cfg_file)
        prov = updated_cfg["provider"]
        self.assertEqual(prov["custom_domain"], "sentinel-regulatory.eu")
        self.assertEqual(prov["website_url"], "https://sentinel-regulatory.eu/")
        self.assertEqual(prov["terms_url"], "https://sentinel-regulatory.eu/terms.html")
        self.assertEqual(prov["cgv_url"], "https://sentinel-regulatory.eu/cgv.html")
        self.assertEqual(prov["privacy_url"], "https://sentinel-regulatory.eu/privacy.html")

        site_custom = self.temp_dir / "site_custom"
        assets = build_legal_web_pages(site_custom, updated_cfg)
        self.assertIn("https://sentinel-regulatory.eu/", assets["index_html"].read_text(encoding="utf-8"))
        self.assertIn("https://sentinel-regulatory.eu/nfadp-audit.html", assets["sitemap_xml"].read_text(encoding="utf-8"))

        reset_cfg = set_custom_domain("", config_path=cfg_file)
        self.assertEqual(reset_cfg["provider"]["custom_domain"], "")
        self.assertIn("github.io", reset_cfg["provider"]["website_url"])

        pilot_eng = create_engagement(
            company="Pilot Biotech SAS",
            domain="pilot-biotech.fr",
            contact_email="qa@pilot-biotech.fr",
            track="pms",
            country="FR",
            sector="Biotech / CRO",
            engagement_mode="design_partner_pilot",
            engagements_json=self.eng_json,
            workspace_dir=self.temp_dir,
        )
        self.assertEqual(pilot_eng["engagement_mode"], "design_partner_pilot")
        self.assertEqual(pilot_eng["fee_label"], "EUR 0.00 (Design Partner Pilot)")
        pblock = resolve_payment_block("pms_openfda_psur", pilot_eng["fee_label"], updated_cfg, engagement_mode="design_partner_pilot")
        self.assertIn("Zero-Cost Design Partner Pilot", pblock)
        self.assertIn("Reciprocity Request", pblock)
        onb = stage_onboarding(
            pilot_eng["engagement_id"],
            engagements_json=self.eng_json,
            config_path=cfg_file,
            create_gmail_draft=False,
            send_email=False,
        )
        onb_txt = Path(onb["draft_path"]).read_text(encoding="utf-8")
        self.assertIn("Design Partner Pilot", onb_txt)
        self.assertNotIn("Stripe Payment Link", onb_txt)


if __name__ == "__main__":
    unittest.main()
