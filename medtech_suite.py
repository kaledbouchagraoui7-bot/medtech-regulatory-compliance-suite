#!/usr/bin/env python3
"""
medtech_suite.py — Unified MedTech, CRO & Digital Health Regulatory Compliance Suite
====================================================================================

Combines two high-margin regulatory & technical automation engines into one platform:
  1. Engine A (Digital Compliance & Security Auditor — `sentinel_scanner.py`):
     Passive 25-control audit across Swiss nFADP / EU GDPR Web Privacy, RFC 7489 DMARC/SPF
     Anti-Spoofing, HTTP/TLS Edge Hardening (EU MDR Annex I GSPR 17.2 IT Security), and
     European Accessibility Act (EAA / WCAG 2.1 AA).
  2. Engine B (Clinical Literature & PRISMA 2020 Evidence Generator — `pilot_package_generator.py`):
     Automated EU MDR Annex XIV / MEDDEV 2.7/1 Rev 4 Clinical Evaluation Report (CER) &
     Post-Market Clinical Follow-up (PMCF) literature screening deliverable generator
     (Landscape Word Vancouver Evidence Table, 4-sheet filterable Excel workbook, and
     300-DPI PRISMA 2020 Flow Diagram with strict mathematical conservation checks).

Modes of Operation
------------------
  1. `audit-domain`:
       Run the 25-control passive domain compliance & security audit on one or more domains.
  2. `clinical-prisma`:
       Generate the PRISMA 2020 Clinical Evidence Package from `records.csv` and `config.json`.
  3. `unified-dossier`:
       Run BOTH engines in a single command for a target MedTech / Digital Health / CRO company
       and package:
         - `00_Unified_Executive_Brief.docx` (Executive summary linking Digital Security + Clinical QA)
         - `01_Digital_Compliance_Audit/` (.docx, 4-sheet .xlsx, 300-DPI Scorecard .png/.pdf, configs)
         - `02_Clinical_PRISMA_Pilot/` (.docx Vancouver table, 4-sheet .xlsx, 300-DPI PRISMA .png/.pdf)
         - `<company_slug>_unified_medtech_dossier.zip`
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
import zipfile
from pathlib import Path
from typing import Any

from docx import Document
from docx.enum.section import WD_ORIENT
from docx.shared import Inches, Pt, RGBColor

from pilot_package_generator import build_pilot_package
from sentinel_scanner import (
    build_domain_audit_package,
    generate_excel_audit_workbook,
    generate_visual_scorecard,
    generate_word_audit_report,
    write_remediation_configs,
)


def generate_unified_executive_brief(
    out_docx: Path,
    audit_data: dict[str, Any],
    prisma_counts: dict[str, Any],
    config_data: dict[str, Any],
) -> None:
    """Create a unified executive cover briefing (.docx) combining Digital Posture + Clinical PRISMA."""
    doc = Document()
    style = doc.styles["Normal"]
    style.font.name = "Calibri"
    style.font.size = Pt(10.5)

    section = doc.sections[0]
    section.orientation = WD_ORIENT.LANDSCAPE
    section.page_width = Inches(11.69)
    section.page_height = Inches(8.27)
    section.top_margin = Inches(0.65)
    section.bottom_margin = Inches(0.65)
    section.left_margin = Inches(0.65)
    section.right_margin = Inches(0.65)

    # Header Title
    p_title = doc.add_paragraph()
    r_title = p_title.add_run(
        f"UNIFIED MEDTECH & CRO COMPLIANCE DOSSIER — {audit_data['domain'].upper()}"
    )
    r_title.font.name = "Calibri"
    r_title.font.size = Pt(16)
    r_title.font.bold = True
    r_title.font.color.rgb = RGBColor(0x11, 0x2A, 0x46)

    p_sub = doc.add_paragraph()
    r_sub = p_sub.add_run(
        "Part I: External Digital Privacy & Security Posture (Swiss nFADP / GDPR / DMARC / EU MDR Annex I GSPR 17.2)\n"
        "Part II: Automated Clinical Literature Traceability & PRISMA 2020 Synthesis (EU MDR Annex XIV / MEDDEV 2.7/1 Rev 4)"
    )
    r_sub.font.bold = True
    r_sub.font.size = Pt(10)
    r_sub.font.color.rgb = RGBColor(0x33, 0x41, 0x55)

    # Part I Summary
    h1 = doc.add_paragraph()
    r_h1 = h1.add_run(
        f"1. External Digital Privacy, Anti-Spoofing & Security Audit ({audit_data['domain']})"
    )
    r_h1.font.bold = True
    r_h1.font.size = Pt(13)
    r_h1.font.color.rgb = RGBColor(0x11, 0x2A, 0x46)

    p_b1 = doc.add_paragraph()
    p_b1.add_run(
        f"• Audited URL: {audit_data['final_url']}  |  Timestamp: {audit_data['scanned_at']}\n"
        f"• Overall Compliance Score: {audit_data['overall_score']}/100 (Grade {audit_data['grade']}) — "
        f"PASS: {audit_data['pass_count']}, WARN: {audit_data['warn_count']}, FAIL: {audit_data['fail_count']} across 25 controls.\n"
        "• Included Deliverables in Folder 01_Digital_Compliance_Audit/:\n"
        "   - 300-DPI Executive Scorecard (.png & .pdf)\n"
        "   - Landscape Technical Audit & Remediation Report (.docx)\n"
        "   - 4-Sheet Filterable Findings & Remediation Roadmap (.xlsx)\n"
        "   - Ready-to-Paste DNS (DMARC/CAA) & Web Server Security Header Configs (remediation_configs/)"
    )

    # Part II Summary
    h2 = doc.add_paragraph()
    r_h2 = h2.add_run(
        f"2. Clinical Literature & PRISMA 2020 Evidence Pilot ({config_data.get('project_title', 'CER Pilot')})"
    )
    r_h2.font.bold = True
    r_h2.font.size = Pt(13)
    r_h2.font.color.rgb = RGBColor(0x11, 0x2A, 0x46)

    p_b2 = doc.add_paragraph()
    p_b2.add_run(
        f"• Target Indication: {config_data.get('indication', 'N/A')}\n"
        f"• PRISMA 2020 Accounting: {prisma_counts['total_identified']} Identified -> "
        f"{prisma_counts['duplicates_removed']} Duplicates Removed -> "
        f"{prisma_counts['records_screened']} Screened ({prisma_counts['excluded_at_screening']} Excluded) -> "
        f"{prisma_counts['reports_assessed_full_text']} Full-Text Assessed ({prisma_counts['excluded_at_full_text']} Excluded) -> "
        f"{prisma_counts['studies_included']} Studies Included.\n"
        "• Included Deliverables in Folder 02_Clinical_PRISMA_Pilot/:\n"
        "   - Landscape Word Clinical Evidence Table (.docx) formatted in Vancouver style\n"
        "   - 4-Sheet Filterable Excel Workbook (.xlsx) with clickable DOI links & yellow QA flags\n"
        "   - 300-DPI Print-Ready PRISMA 2020 Flow Diagram (.png & .pdf)"
    )

    doc.save(str(out_docx))


def build_unified_medtech_dossier(
    target_domain: str,
    records_csv: str | Path,
    config_json: str | Path,
    base_out: str | Path = "output",
    offline_audit_override: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Run both Engine A (Domain Audit) and Engine B (PRISMA Clinical Pilot) into one combined bundle."""
    base_out_path = Path(base_out)
    base_out_path.mkdir(parents=True, exist_ok=True)

    # 1. Run or load Domain Compliance Audit
    if offline_audit_override is not None:
        audit_data = offline_audit_override
        slug = re.sub(r"[^a-z0-9]+", "_", audit_data["domain"].lower()).strip("_")
    else:
        dom_res = build_domain_audit_package(target_domain, base_out=base_out_path / "_tmp_dom")
        audit_data = dom_res["audit"]
        slug = re.sub(r"[^a-z0-9]+", "_", audit_data["domain"].lower()).strip("_")

    dossier_dir = base_out_path / f"{slug}_unified_medtech_dossier"
    if dossier_dir.exists():
        shutil.rmtree(dossier_dir)
    dossier_dir.mkdir(parents=True, exist_ok=True)

    # Populate 01_Digital_Compliance_Audit
    dir_01 = dossier_dir / "01_Digital_Compliance_Audit"
    dir_01.mkdir(parents=True, exist_ok=True)
    generate_visual_scorecard(
        audit_data,
        dir_01 / f"{slug}_scorecard.png",
        dir_01 / f"{slug}_scorecard.pdf",
    )
    generate_word_audit_report(audit_data, dir_01 / f"{slug}_executive_audit.docx")
    generate_excel_audit_workbook(audit_data, dir_01 / f"{slug}_technical_findings.xlsx")
    write_remediation_configs(audit_data, dir_01 / "remediation_configs")

    # Clean up temporary domain output if used
    tmp_dom = base_out_path / "_tmp_dom"
    if tmp_dom.exists():
        shutil.rmtree(tmp_dom, ignore_errors=True)

    # 2. Run Clinical PRISMA 2020 Pilot Package Generator
    tmp_prisma = base_out_path / "_tmp_prisma"
    prisma_res = build_pilot_package(records_csv, config_json, base_output_dir=tmp_prisma)
    dir_02 = dossier_dir / "02_Clinical_PRISMA_Pilot"
    shutil.copytree(prisma_res["package_dir"], dir_02)
    shutil.rmtree(tmp_prisma, ignore_errors=True)

    # 3. Generate Unified Executive Brief (.docx)
    import json
    cfg_data = json.loads(Path(config_json).read_text(encoding="utf-8"))
    brief_docx = dossier_dir / "00_Unified_Executive_Brief.docx"
    generate_unified_executive_brief(
        brief_docx,
        audit_data=audit_data,
        prisma_counts=prisma_res["prisma"],
        config_data=cfg_data,
    )

    # 4. Zip the entire Unified MedTech Dossier
    zip_path = base_out_path / f"{slug}_unified_medtech_dossier.zip"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for file_p in sorted(dossier_dir.rglob("*")):
            if file_p.is_file():
                rel = file_p.relative_to(dossier_dir.parent)
                zf.write(file_p, arcname=str(rel))

    return {
        "dossier_dir": dossier_dir,
        "zip_path": zip_path,
        "brief_docx": brief_docx,
        "digital_dir": dir_01,
        "clinical_dir": dir_02,
        "domain_score": audit_data["overall_score"],
        "domain_grade": audit_data["grade"],
        "studies_included": prisma_res["prisma"]["studies_included"],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Unified MedTech, CRO & Digital Health Regulatory Compliance Suite."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # Subcommand 1: audit-domain
    p_dom = sub.add_parser("audit-domain", help="Run 25-control passive domain compliance & security audit")
    p_dom.add_argument("domains", nargs="+", help="One or more domains/URLs to audit")
    p_dom.add_argument("--output-dir", default="output", help="Output directory")

    # Subcommand 2: clinical-prisma
    p_clin = sub.add_parser("clinical-prisma", help="Build PRISMA 2020 clinical literature evidence package")
    p_clin.add_argument("--records", default="records.csv", help="Path to records.csv")
    p_clin.add_argument("--config", default="config.json", help="Path to config.json")
    p_clin.add_argument("--output-dir", default="output", help="Output directory")

    # Subcommand 3: unified-dossier
    p_uni = sub.add_parser(
        "unified-dossier",
        help="Run BOTH Digital Domain Audit + Clinical PRISMA 2020 Pilot into a single MedTech/CRO Dossier",
    )
    p_uni.add_argument("domain", help="Target company domain (e.g. decomplix.com or rcts.fr)")
    p_uni.add_argument("--records", default="records.csv", help="Path to screened records.csv")
    p_uni.add_argument("--config", default="config.json", help="Path to clinical search config.json")
    p_uni.add_argument("--output-dir", default="output", help="Output directory")

    args = parser.parse_args(argv)

    if args.command == "audit-domain":
        for d in args.domains:
            res = build_domain_audit_package(d, args.output_dir)
            a = res["audit"]
            print(
                f"[audit-domain] {a['domain']}: {a['overall_score']}/100 (Grade {a['grade']}) -> {res['zip']}"
            )
    elif args.command == "clinical-prisma":
        res = build_pilot_package(args.records, args.config, args.output_dir)
        print(f"[clinical-prisma] Package ready -> {res['zip']}")
    elif args.command == "unified-dossier":
        res = build_unified_medtech_dossier(
            args.domain, args.records, args.config, args.output_dir
        )
        print(
            f"[unified-dossier] {args.domain}: Digital Score={res['domain_score']}/100 ({res['domain_grade']}) | "
            f"Clinical Studies Included={res['studies_included']} -> {res['zip_path']}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
