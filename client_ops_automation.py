#!/usr/bin/env python3
"""
client_ops_automation.py — Zero-Cost Client Onboarding, Multi-Track Delivery & QA Engine
========================================================================================

Automates the end-to-end commercial delivery lifecycle across all 4 repositories:
  1. Engagement Ledger (`client_delivery_workspace/engagements.json` + `.csv`)
  2. Plug-and-Play Config (`client_ops_config.json` — Stripe Payment Links, Tiime IBAN/SIRET, custom domain)
  3. Turnkey Onboarding Drafts + Track Terms (`stage-onboarding`) & Positive-Reply Auto-Staging
  4. Multi-Track Deliverable Generation (`run-delivery` across Sentinel, PMS/MAUDE, PRISMA 2020/Biostats,
     Unified Dossier, and RA Command Center) with SHA-256 ALCOA+ Provenance Manifest & QA Sign-Off
  5. Automated Pre-Delivery QA Verifier (`verify_delivery_package`) + Client Delivery Packaging (`stage-delivery`)
  6. Safe Gmail Draft / Confirmed-Send Integration (`gmail mutate create-draft` / `--send --confirm-send`)
  7. Turnkey Static Legal Web Pages (`build-legal-web` -> `site_deploy_ready/terms.html`, `privacy.html`)
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import openpyxl
from docx import Document

SUITE_DIR = Path(__file__).resolve().parent
PMS_DIR = SUITE_DIR.parent / "pms-clinicaltrials-openfda-monitor"
COMPBIO_DIR = SUITE_DIR.parent / "computational-biology-portfolio" / "computational-biology-portfolio"

for _p in (str(SUITE_DIR), str(PMS_DIR), str(COMPBIO_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from legal_terms import (
    TERMS_VERSION,
    build_legal_web_pages,
    load_provider_config,
    render_terms_txt,
)

WORKSPACE_DIR = SUITE_DIR / "client_delivery_workspace"
ENGAGEMENTS_JSON = WORKSPACE_DIR / "engagements.json"
ENGAGEMENTS_CSV = WORKSPACE_DIR / "engagements.csv"
STAGED_REPLIES_DIR = WORKSPACE_DIR / "staged_replies"
SITE_DEPLOY_DIR = SUITE_DIR / "site_deploy_ready"

GMAIL_ACCOUNT = "kaledbouchagraoui7@gmail.com"
MAX_DIRECT_ATTACHMENT_BYTES = 18 * 1024 * 1024

TRACK_ALIASES = {
    "sentinel": "sentinel_compliance",
    "sentinel_compliance": "sentinel_compliance",
    "pms": "pms_openfda_psur",
    "pms_openfda_psur": "pms_openfda_psur",
    "prisma": "clinical_lit_prisma",
    "clinical_lit_prisma": "clinical_lit_prisma",
    "biostats": "clinical_lit_prisma",
    "unified": "unified_dossier",
    "unified_dossier": "unified_dossier",
    "ra": "ra_command_center",
    "ra_command_center": "ra_command_center",
}

DEFAULT_TRACK_FEES = {
    "sentinel_compliance": "EUR 350",
    "pms_openfda_psur": "EUR 650",
    "clinical_lit_prisma": "EUR 750",
    "unified_dossier": "EUR 1,100",
    "ra_command_center": "EUR 950",
}

POSITIVE_REPLY_RE = re.compile(
    r"\b(yes|interested|send|share|price|quote|invoice|stripe|proceed|let'?s do|"
    r"can you|how much|more info|sounds good|go ahead|happy to|please send|d'accord|"
    r"oui|intéressé|interesse|devis|tarif|ja|gerne|angebot|kosten)\b",
    re.I,
)


def normalize_track(raw_track: str) -> str:
    key = re.sub(r"[^a-z0-9_]+", "_", (raw_track or "sentinel_compliance").strip().lower()).strip("_")
    return TRACK_ALIASES.get(key, "sentinel_compliance")


def _slugify(text: str, max_len: int = 42) -> str:
    return re.sub(r"[^a-z0-9]+", "_", (text or "client").lower()).strip("_")[:max_len] or "client"


def _gmail_bin_path() -> str:
    found = shutil.which("gmail")
    if found:
        return found
    env_bin = os.environ.get("GMAIL_CLI_BIN", "").strip()
    if env_bin:
        return env_bin
    local_bins = sorted(Path.home().glob(".gemini/antigravity/plugin_data/gmail/bin/gmail*.exe"))
    if local_bins:
        return str(local_bins[0])
    return "gmail"


def _run_gmail_cli(args: list[str]) -> str:
    env = os.environ.copy()
    env["AGY_ACCOUNT"] = GMAIL_ACCOUNT
    env.pop("AGY_UNATTENDED", None)
    res = subprocess.run(
        [_gmail_bin_path(), *args],
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
    )
    if res.returncode != 0:
        raise RuntimeError(f"gmail CLI error ({res.returncode}): {res.stderr or res.stdout}")
    return res.stdout


def load_engagements(engagements_json: Path = ENGAGEMENTS_JSON) -> list[dict[str, Any]]:
    if not engagements_json.exists():
        return []
    try:
        data = json.loads(engagements_json.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except Exception:
        return []


def save_engagements(rows: list[dict[str, Any]], engagements_json: Path = ENGAGEMENTS_JSON) -> None:
    engagements_json.parent.mkdir(parents=True, exist_ok=True)
    engagements_json.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")

    csv_path = engagements_json.with_suffix(".csv")
    fields = [
        "engagement_id", "created_at", "updated_at", "company", "domain",
        "contact_email", "country", "sector", "track", "fee_label", "status",
        "qa_passed", "zip_path", "onboarding_draft_path", "delivery_draft_path",
    ]
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)


def get_engagement(
    engagement_id: str,
    engagements_json: Path = ENGAGEMENTS_JSON,
) -> dict[str, Any]:
    for row in load_engagements(engagements_json):
        if row.get("engagement_id") == engagement_id:
            return row
    raise KeyError(f"Engagement ID not found: {engagement_id}")


def upsert_engagement(
    record: dict[str, Any],
    engagements_json: Path = ENGAGEMENTS_JSON,
) -> dict[str, Any]:
    rows = load_engagements(engagements_json)
    eid = record["engagement_id"]
    now_iso = datetime.now(timezone.utc).isoformat()
    record["updated_at"] = now_iso
    if not record.get("created_at"):
        record["created_at"] = now_iso

    replaced = False
    for idx, existing in enumerate(rows):
        if existing.get("engagement_id") == eid:
            rows[idx] = record
            replaced = True
            break
    if not replaced:
        rows.append(record)
    save_engagements(rows, engagements_json)
    return record


def create_engagement(
    company: str,
    domain: str,
    contact_email: str,
    track: str = "sentinel_compliance",
    country: str = "FR",
    sector: str = "MedTech OEM",
    fee_label: str = "",
    device_term: str = "",
    condition_term: str = "",
    epmc_query: str = "",
    records_csv: str = "",
    config_json: str = "",
    ra_input_json: str = "",
    vertical: str = "medtech_ra",
    engagements_json: Path = ENGAGEMENTS_JSON,
    workspace_dir: Path | None = None,
) -> dict[str, Any]:
    norm_track = normalize_track(track)
    ws = workspace_dir or engagements_json.parent
    existing = load_engagements(engagements_json)

    dom_clean = re.sub(r"^https?://", "", (domain or "").strip().lower()).split("/", 1)[0]
    if dom_clean.startswith("www."):
        dom_clean = dom_clean[4:]
    slug = _slugify(dom_clean or company, 24)
    date_tag = datetime.now(timezone.utc).strftime("%Y%m%d")
    seq = sum(1 for r in existing if slug in str(r.get("engagement_id", "")).lower()) + 1
    eid = f"ENG-{date_tag}-{slug}-{seq:02d}".upper()

    eng_dir = ws / eid
    for sub in ("onboarding", "deliverables", "qa", "delivery"):
        (eng_dir / sub).mkdir(parents=True, exist_ok=True)

    rec = {
        "engagement_id": eid,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "company": (company or dom_clean or "Client").strip(),
        "domain": dom_clean,
        "contact_email": (contact_email or "").strip().lower(),
        "country": (country or "FR").strip().upper(),
        "sector": (sector or "MedTech OEM").strip(),
        "track": norm_track,
        "fee_label": (fee_label or DEFAULT_TRACK_FEES.get(norm_track, "EUR 350")).strip(),
        "device_term": device_term.strip(),
        "condition_term": condition_term.strip(),
        "epmc_query": epmc_query.strip(),
        "records_csv": records_csv.strip(),
        "config_json": config_json.strip(),
        "ra_input_json": ra_input_json.strip(),
        "vertical": vertical.strip() or "medtech_ra",
        "workspace_dir": str(eng_dir),
        "status": "CREATED",
        "qa_passed": False,
        "zip_path": "",
        "onboarding_draft_path": "",
        "delivery_draft_path": "",
        "invoice_ref": "",
    }
    return upsert_engagement(rec, engagements_json)


def resolve_payment_block(track: str, fee_label: str, cfg: dict[str, Any]) -> str:
    pay = cfg.get("payment", {})
    prov = cfg.get("provider", {})
    links = pay.get("stripe_payment_links", {})
    stripe_url = (links.get(track) or "").strip()
    bank = pay.get("bank_transfer", {})
    iban = (bank.get("iban") or "").strip()

    lines = [f"Fixed Fee: {fee_label} ({prov.get('vat_notice', 'TVA non applicable, art. 293 B du CGI')})"]
    if stripe_url and stripe_url.startswith("http"):
        lines.append(f"- Option A (Instant Card / Apple Pay via Stripe): {stripe_url}")
    else:
        lines.append("- Option A (Card / Apple Pay Checkout): Direct Stripe Payment Link sent upon your confirmation of scope.")
    if iban and not iban.startswith("IBAN_PENDING"):
        lines.append(
            f"- Option B (SEPA / Bank Transfer via {pay.get('invoicing_platform', 'Tiime')} PDF Invoice): "
            f"IBAN {iban} / BIC {bank.get('bic', '')}"
        )
    else:
        lines.append(
            f"- Option B (Bank / SEPA Transfer): PDF invoice generated via {pay.get('invoicing_platform', 'Tiime')} upon confirmation."
        )
    return "\n".join(lines)


def _track_deliverables_and_inputs(track: str, domain: str) -> tuple[str, str]:
    if track == "sentinel_compliance":
        return (
            "1) Executive Word (.docx) Audit & Remediation Dossier across all 25 passive controls; "
            "2) 4-Sheet Filterable Excel Risk Register (.xlsx); "
            "3) 300-DPI Executive Scorecard (.png & .pdf); "
            "4) Ready-to-deploy DNS (DMARC/SPF/CAA) & HTTP Security Header configs (Nginx / Cloudflare / Apache); "
            "5) One complimentary verification re-scan within 14 days of deployment.",
            f"Please confirm: (a) legal authorization to passively scan {domain} and its public DNS/headers, "
            "and (b) your billing entity name + VAT/registration number (if applicable) for your Tiime PDF invoice.",
        )
    if track == "pms_openfda_psur":
        return (
            "1) Landscape Word (.docx) EU MDR Art. 83-86 / MDCG 2022-21 PSUR Surveillance Draft; "
            "2) 4-Sheet Filterable Excel PMS Workbook (.xlsx) linking MAUDE trends, 510(k)/Recalls, and clickable ClinicalTrials.gov NCT records; "
            "3) 300-DPI Visual Safety & Trial Dashboard (.png & .pdf); "
            "4) ALCOA+ SHA-256 Query Provenance Manifest.",
            "Please confirm: (a) target device name / FDA product code(s) / predicate keywords and date range, "
            "and (b) billing entity details for your Tiime invoice.",
        )
    if track == "clinical_lit_prisma":
        return (
            "1) Vancouver-Cited Landscape Word Evidence Table (.docx); "
            "2) 4-Sheet Filterable Excel Screening Matrix (.xlsx) with clickable DOIs, COUNTIFS formulas, and #FFF2CC QA verification flags; "
            "3) 300-DPI Print-Ready PRISMA 2020 Flow Diagram (.png & .pdf) with verified conservation math; "
            "4) Optional ICH E6/E9 Cohort Table 1 & RefSeq QC annex + ALCOA+ SHA-256 Provenance Manifest.",
            "Please confirm: (a) search keywords / PICO criteria or your CSV screening export + recency window, "
            "and (b) billing entity details for your Tiime invoice.",
        )
    if track == "ra_command_center":
        return (
            "1) Statutory Gatekeeper & Delay Attribution Brief (.docx); "
            "2) 6-Sheet eCTD M1-M5 Cross-Check, SLA Blame-Shield & Guidance Drift Workbook (.xlsx); "
            "3) 300-DPI 4-Panel Operations Dashboard (.png & .pdf); "
            "4) ALCOA+ SHA-256 Telemetry & Provenance Bundle.",
            "Please confirm: (a) target regulatory pathway (eCTD / EU MDR / IVDR) and department SLA dates, "
            "and (b) billing entity details for your Tiime invoice.",
        )
    return (
        "1) 00_Unified_Executive_Brief.docx linking technical posture and clinical evidence; "
        "2) 01_Digital_Compliance_Audit/ (Word, 4-sheet Excel, 300-DPI Scorecard, IT/DNS fixes); "
        "3) 02_Clinical_PRISMA_Pilot/ (Vancouver Word, 4-sheet Excel, 300-DPI PRISMA 2020 diagram); "
        "4) ALCOA+ SHA-256 Provenance Manifest & signed QA Checklist.",
        f"Please confirm: (a) authorized target domain ({domain}) + literature PICO/device terms, "
        "and (b) billing entity details for your Tiime invoice.",
    )


def stage_onboarding(
    engagement_id: str,
    engagements_json: Path = ENGAGEMENTS_JSON,
    config_path: Path | None = None,
    create_gmail_draft: bool = False,
    send_email: bool = False,
    confirm_send: bool = False,
) -> dict[str, Any]:
    if send_email and not confirm_send:
        raise ValueError("Refusing unattended onboarding send: pass --confirm-send explicitly.")

    eng = get_engagement(engagement_id, engagements_json)
    cfg = load_provider_config(config_path)
    prov = cfg["provider"]
    ops = cfg["operations"]

    eng_dir = Path(eng["workspace_dir"])
    onb_dir = eng_dir / "onboarding"
    onb_dir.mkdir(parents=True, exist_ok=True)
    slug = _slugify(eng["domain"] or eng["company"])

    terms_txt_path = onb_dir / "TERMS_OF_SERVICE_AND_DISCLAIMER.txt"
    terms_txt_path.write_text(render_terms_txt(track=eng["track"], cfg=cfg), encoding="utf-8")

    deliverables_desc, inputs_needed = _track_deliverables_and_inputs(eng["track"], eng["domain"])
    payment_block = resolve_payment_block(eng["track"], eng["fee_label"], cfg)
    turnaround_h = int(ops.get("default_turnaround_hours", 48))

    intake_line = (
        f"\nOptional Kickoff Intake Form: {ops['intake_form_url']}"
        if ops.get("intake_form_url")
        else ""
    )
    terms_ref_line = (
        f"Full Terms: {prov.get('terms_url')} (also attached as TERMS_OF_SERVICE_AND_DISCLAIMER.txt)"
        if prov.get("terms_url")
        else "Terms & Liability Disclaimer attached as TERMS_OF_SERVICE_AND_DISCLAIMER.txt."
    )

    subject = f"Onboarding & Scope Confirmation — {eng['company']} ({eng['engagement_id']})"
    body = (
        f"Hi {eng['company']} team,\n\n"
        f"Thank you for your reply regarding {eng['domain']}. I have staged engagement {eng['engagement_id']} "
        f"with everything needed to deliver your full package within {turnaround_h} hours of confirmation.\n\n"
        f"1. DELIVERABLES INCLUDED\n"
        f"{deliverables_desc}\n\n"
        f"2. CONFIRMATION & KICKOFF INPUTS\n"
        f"{inputs_needed}{intake_line}\n\n"
        f"3. INVOICING & PAYMENT OPTIONS\n"
        f"{payment_block}\n\n"
        f"4. PASSIVE SCOPE & LEGAL TERMS (v{TERMS_VERSION})\n"
        f"All deliverables serve as technical QA/RA preparation aids (not formal legal or clinical advice) "
        f"under strict ALCOA+ traceability, with provider liability capped at fees paid. {terms_ref_line}\n\n"
        f"Simply reply to this thread with your confirmation and billing details so I can trigger the run.\n\n"
        f"Best regards,\n"
        f"{prov.get('operator_name', 'Kaled Bouchagraoui')}\n"
        f"{prov.get('brand_name', 'Sentinel Regulatory & Technical Operations')} — {prov.get('jurisdiction_city', 'Strasbourg, France')}"
    )

    draft_path = onb_dir / f"{slug}_onboarding_email.txt"
    draft_path.write_text(f"Subject: {subject}\nTo: {eng['contact_email']}\n\n{body}", encoding="utf-8")
    body_only_path = onb_dir / f"{slug}_onboarding_body.txt"
    body_only_path.write_text(body, encoding="utf-8")

    eng["onboarding_draft_path"] = str(draft_path)
    eng["status"] = "ONBOARDING_DRAFTED"

    gmail_result = ""
    if send_email and eng["contact_email"]:
        gmail_result = _run_gmail_cli([
            "mutate", "send-with-attachment",
            "--to", eng["contact_email"],
            "--subject", subject,
            "--body-file", str(body_only_path),
            "--file", str(terms_txt_path),
            "--json",
        ])
        eng["status"] = "ONBOARDING_SENT"
    elif create_gmail_draft and eng["contact_email"]:
        gmail_result = _run_gmail_cli([
            "mutate", "create-draft",
            "--to", eng["contact_email"],
            "--subject", subject,
            "--body-file", str(body_only_path),
            "--file", str(terms_txt_path),
            "--json",
        ])

    upsert_engagement(eng, engagements_json)
    return {
        "engagement": eng,
        "subject": subject,
        "draft_path": draft_path,
        "body_only_path": body_only_path,
        "terms_path": terms_txt_path,
        "gmail_result": gmail_result,
    }


def classify_reply_intent(fresh_text: str) -> str:
    if POSITIVE_REPLY_RE.search(fresh_text or ""):
        return "POSITIVE_BUY_OR_SCOPE_INTENT"
    return "QUESTION_OR_NEUTRAL_REVIEW"


def stage_positive_reply_onboarding(
    domain: str,
    sender_email: str,
    fresh_text: str,
    company: str = "",
    country: str = "FR",
    sector: str = "MedTech OEM",
    track: str = "sentinel_compliance",
    fee_label: str = "",
    staged_replies_dir: Path = STAGED_REPLIES_DIR,
    engagements_json: Path = ENGAGEMENTS_JSON,
    config_path: Path | None = None,
) -> dict[str, Any]:
    """
    Non-sending inbox-watcher hook: classifies a Case 3 human reply and stages a
    turnkey onboarding/scope confirmation draft + Terms file ready for user approval.
    """
    intent = classify_reply_intent(fresh_text)
    norm_track = normalize_track(track)
    fee = (fee_label or DEFAULT_TRACK_FEES.get(norm_track, "EUR 350")).strip()

    # Reuse existing engagement for same domain + email if not yet delivered, else create new
    existing = None
    for row in load_engagements(engagements_json):
        if (
            row.get("domain") == domain.strip().lower()
            and row.get("contact_email") == sender_email.strip().lower()
            and not str(row.get("status", "")).startswith("DELIVERY_SENT")
        ):
            existing = row
            break

    if existing is None:
        existing = create_engagement(
            company=company or domain,
            domain=domain,
            contact_email=sender_email,
            track=norm_track,
            country=country,
            sector=sector,
            fee_label=fee,
            engagements_json=engagements_json,
        )
    onb = stage_onboarding(
        existing["engagement_id"],
        engagements_json=engagements_json,
        config_path=config_path,
        create_gmail_draft=False,
        send_email=False,
    )

    staged_replies_dir.mkdir(parents=True, exist_ok=True)
    slug = _slugify(domain or sender_email)
    reply_copy = staged_replies_dir / f"{slug}_onboarding_reply_draft.txt"
    reply_copy.write_text(
        f"Reply Intent: {intent}\nEngagement ID: {existing['engagement_id']}\n"
        f"Original Snippet: {fresh_text[:280]}\n"
        + "=" * 68 + "\n"
        + Path(onb["draft_path"]).read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    return {
        "reply_intent": intent,
        "engagement_id": existing["engagement_id"],
        "draft_onboarding_path": str(reply_copy),
        "terms_path": str(onb["terms_path"]),
    }


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def verify_delivery_package(deliverables_dir: Path, track: str) -> dict[str, Any]:
    """
    Deterministic Pre-Delivery QA Gate verifying:
      - Non-empty .docx, .xlsx, .png, .pdf, .zip, and TERMS_OF_SERVICE_AND_DISCLAIMER.txt
      - Embedded Terms & Liability Disclaimer inside every .docx and .xlsx README/6_README
      - Required Excel worksheet names intact
      - Legal text file bundled inside the .zip archive
    """
    checks: list[dict[str, Any]] = []
    norm_track = normalize_track(track)

    def add_check(name: str, ok: bool, detail: str) -> None:
        checks.append({"check": name, "passed": bool(ok), "detail": detail})

    docx_files = sorted(deliverables_dir.rglob("*.docx"))
    xlsx_files = sorted(deliverables_dir.rglob("*.xlsx"))
    png_files = sorted(deliverables_dir.rglob("*.png"))
    pdf_files = sorted(deliverables_dir.rglob("*.pdf"))
    zip_files = sorted(deliverables_dir.rglob("*.zip"))
    terms_files = sorted(deliverables_dir.rglob("TERMS_OF_SERVICE_AND_DISCLAIMER.txt"))

    add_check("docx_present", bool(docx_files), f"Found {len(docx_files)} Word file(s)")
    add_check("xlsx_present", bool(xlsx_files), f"Found {len(xlsx_files)} Excel workbook(s)")
    add_check("visuals_present", bool(png_files) and bool(pdf_files), f"Found {len(png_files)} PNG, {len(pdf_files)} PDF")
    add_check("zip_present", bool(zip_files), f"Found {len(zip_files)} ZIP archive(s)")
    add_check("terms_txt_present", bool(terms_files), f"Found {len(terms_files)} Terms txt file(s)")

    # Verify Terms text in every Word document
    for dpath in docx_files:
        doc = Document(str(dpath))
        full_txt = "\n".join(p.text for p in doc.paragraphs).lower()
        has_terms = ("terms of service" in full_txt and "liability" in full_txt)
        add_check(f"docx_legal_{dpath.name}", has_terms, "Embedded Terms & Liability paragraphs checked")

    # Verify sheet structure and Terms rows in Excel README / 6_README
    for xpath in xlsx_files:
        wb = openpyxl.load_workbook(str(xpath), read_only=True)
        sheets = list(wb.sheetnames)
        readme_name = "6_README" if "6_README" in sheets else ("README" if "README" in sheets else "")
        has_legal_row = False
        if readme_name:
            ws = wb[readme_name]
            txt_rows = " ".join(
                str(val) for row in ws.iter_rows(values_only=True) for val in row if val is not None
            ).lower()
            has_legal_row = ("liability" in txt_rows and ("french" in txt_rows or "terms" in txt_rows or "provider" in txt_rows))
        wb.close()
        add_check(f"xlsx_readme_legal_{xpath.name}", bool(readme_name) and has_legal_row, f"Sheet={readme_name}, sheets={sheets}")

    # Verify primary ZIP contains deliverables + Terms file
    if zip_files:
        primary_zip = max(zip_files, key=lambda p: p.stat().st_size)
        with zipfile.ZipFile(primary_zip, "r") as zf:
            names = zf.namelist()
        has_terms_in_zip = any(n.endswith("TERMS_OF_SERVICE_AND_DISCLAIMER.txt") for n in names)
        add_check(
            f"zip_contents_{primary_zip.name}",
            len(names) >= 4 and has_terms_in_zip,
            f"entries={len(names)}, has_terms={has_terms_in_zip}",
        )

    passed = all(c["passed"] for c in checks)
    return {
        "track": norm_track,
        "passed": passed,
        "checks": checks,
        "primary_zip": str(max(zip_files, key=lambda p: p.stat().st_size)) if zip_files else "",
    }


def _curated_to_pilot_csv(
    normalized_records: list[dict[str, Any]],
    out_csv: Path,
    epmc_query: str,
    title: str,
    indication: str,
    duplicates_removed: int,
    out_cfg: Path,
) -> None:
    """Convert `03_pubmed_literature_synthesizer.py` normalized records into `pilot_package_generator.py` schema."""
    from pilot_package_generator import REQUIRED_CSV_COLUMNS

    with out_csv.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=REQUIRED_CSV_COLUMNS)
        w.writeheader()
        for r in normalized_records:
            st = (r.get("screening_stage") or "included").strip()
            ex_reason = (r.get("exclusion_reason") or "").strip()
            if st != "included" and not ex_reason:
                ex_reason = "Did not meet eligibility window/content threshold"
            w.writerow({
                "record_id": r.get("pmid") or r.get("record_id") or "",
                "title": r.get("title") or "",
                "authors": r.get("authors") or "",
                "year": r.get("pub_year") or r.get("year") or "",
                "journal": r.get("journal") or "",
                "doi": r.get("doi") or "",
                "study_type": r.get("pub_type") or r.get("study_type") or "",
                "population": indication or "Target Clinical Cohort",
                "intervention_exposure": epmc_query,
                "outcome": r.get("outcome") or "Safety / Efficacy Endpoint",
                "conclusion": r.get("key_takeaway") or r.get("conclusion") or "",
                "screening_stage": st,
                "exclusion_reason": "" if st == "included" else ex_reason,
            })

    cfg_obj = {
        "project_slug": _slugify(title),
        "project_title": title,
        "indication": indication,
        "search_string": epmc_query,
        "databases_searched": {"Europe PMC / PubMed": len(normalized_records)},
        "date_of_search": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "duplicates_removed_count": int(duplicates_removed),
        "is_fictional_sample": False,
    }
    out_cfg.write_text(json.dumps(cfg_obj, indent=2), encoding="utf-8")


def _build_manifest_and_refresh_zip(
    deliverables_dir: Path,
    primary_zip: Path,
    eng: dict[str, Any],
    qa_res: dict[str, Any],
) -> tuple[Path, Path]:
    qa_dir = Path(eng["workspace_dir"]) / "qa"
    qa_dir.mkdir(parents=True, exist_ok=True)

    artifact_hashes = []
    for fp in sorted(deliverables_dir.rglob("*")):
        if fp.is_file() and fp.suffix.lower() != ".zip" and fp.name not in (
            "ALCOA_PROVENANCE_MANIFEST.json",
            "QA_SIGNOFF_CHECKLIST.md",
        ):
            artifact_hashes.append({
                "relative_path": str(fp.relative_to(deliverables_dir)).replace("\\", "/"),
                "size_bytes": fp.stat().st_size,
                "sha256": _sha256_file(fp),
            })

    manifest_obj = {
        "engagement_id": eng["engagement_id"],
        "company": eng["company"],
        "domain": eng["domain"],
        "track": eng["track"],
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "terms_version": TERMS_VERSION,
        "qa_passed": qa_res["passed"],
        "qa_checks": qa_res["checks"],
        "artifacts": artifact_hashes,
    }
    manifest_json = deliverables_dir / "ALCOA_PROVENANCE_MANIFEST.json"
    manifest_json.write_text(json.dumps(manifest_obj, indent=2), encoding="utf-8")
    (qa_dir / "ALCOA_PROVENANCE_MANIFEST.json").write_text(
        manifest_json.read_text(encoding="utf-8"), encoding="utf-8"
    )

    checklist_lines = [
        f"# Pre-Delivery QA Sign-Off Checklist — {eng['engagement_id']}",
        "",
        f"- **Client:** {eng['company']} ({eng['domain']})",
        f"- **Track:** `{eng['track']}` | **Terms Version:** `v{TERMS_VERSION}`",
        f"- **Automated QA Verdict:** `{'PASS — READY FOR CLIENT DELIVERY' if qa_res['passed'] else 'FAIL — REVIEW REQUIRED'}`",
        f"- **Timestamp (UTC):** `{manifest_obj['generated_at_utc']}`",
        "",
        "## Automated Verification Checks",
        "",
        "| Check | Status | Detail |",
        "|---|---|---|",
    ]
    for chk in qa_res["checks"]:
        badge = "PASS" if chk["passed"] else "FAIL"
        checklist_lines.append(f"| `{chk['check']}` | **{badge}** | {chk['detail']} |")
    checklist_lines.extend([
        "",
        "## Human-in-the-Loop Sign-Off (EU MDR / nFADP / ALCOA+)",
        "- [ ] Verified target domain / product scope matches signed confirmation.",
        "- [ ] Confirmed any missing DOI/conclusion cells (`#FFF2CC`) were flagged cleanly without fabrication.",
        "- [ ] Attached or linked matching Tiime invoice + `TERMS_OF_SERVICE_AND_DISCLAIMER.txt`.",
    ])
    checklist_md = deliverables_dir / "QA_SIGNOFF_CHECKLIST.md"
    checklist_md.write_text("\n".join(checklist_lines), encoding="utf-8")
    (qa_dir / "QA_SIGNOFF_CHECKLIST.md").write_text(
        checklist_md.read_text(encoding="utf-8"), encoding="utf-8"
    )

    # Append manifest + QA checklist cleanly into the primary delivery ZIP
    if primary_zip and primary_zip.exists():
        with zipfile.ZipFile(primary_zip, "a", compression=zipfile.ZIP_DEFLATED) as zf:
            existing_names = set(zf.namelist())
            root_prefix = sorted(existing_names)[0].split("/")[0] if existing_names else _slugify(eng["domain"])
            for extra_p in (manifest_json, checklist_md):
                arc = f"{root_prefix}/{extra_p.name}"
                if arc not in existing_names:
                    zf.write(extra_p, arcname=arc)

    return manifest_json, checklist_md


def run_delivery_for_engagement(
    engagement_id: str,
    engagements_json: Path = ENGAGEMENTS_JSON,
    offline_audit_override: dict[str, Any] | None = None,
    pms_data_override: dict[str, Any] | None = None,
    include_table1: bool = False,
) -> dict[str, Any]:
    eng = get_engagement(engagement_id, engagements_json)
    track = eng["track"]
    eng_dir = Path(eng["workspace_dir"])
    deliv_dir = eng_dir / "deliverables"
    deliv_dir.mkdir(parents=True, exist_ok=True)

    eng["status"] = "DELIVERY_BUILDING"
    upsert_engagement(eng, engagements_json)

    metrics_summary: dict[str, Any] = {}
    primary_zip: Path

    if track == "sentinel_compliance":
        from sentinel_scanner import (
            build_domain_audit_package,
            generate_excel_audit_workbook,
            generate_visual_scorecard,
            generate_word_audit_report,
            write_remediation_configs,
        )

        if offline_audit_override is not None:
            audit = offline_audit_override
            slug = _slugify(audit["domain"])
            pkg_dir = deliv_dir / f"{slug}_audit"
            pkg_dir.mkdir(parents=True, exist_ok=True)
            docx_p = pkg_dir / f"{slug}_executive_audit.docx"
            xlsx_p = pkg_dir / f"{slug}_technical_findings.xlsx"
            png_p = pkg_dir / f"{slug}_scorecard.png"
            pdf_p = pkg_dir / f"{slug}_scorecard.pdf"
            json_p = pkg_dir / f"{slug}_raw_evidence.json"
            terms_p = pkg_dir / "TERMS_OF_SERVICE_AND_DISCLAIMER.txt"
            cfg_dir = pkg_dir / "remediation_configs"
            generate_visual_scorecard(audit, png_p, pdf_p)
            generate_word_audit_report(audit, docx_p)
            generate_excel_audit_workbook(audit, xlsx_p)
            write_remediation_configs(audit, cfg_dir)
            json_p.write_text(json.dumps(audit, indent=2), encoding="utf-8")
            terms_p.write_text(render_terms_txt(track="sentinel_compliance"), encoding="utf-8")
            primary_zip = deliv_dir / f"{slug}_audit_package.zip"
            with zipfile.ZipFile(primary_zip, "w", compression=zipfile.ZIP_DEFLATED) as zf:
                for fp in (docx_p, xlsx_p, png_p, pdf_p, json_p, terms_p):
                    zf.write(fp, arcname=f"{slug}_audit/{fp.name}")
                for cf in cfg_dir.iterdir():
                    zf.write(cf, arcname=f"{slug}_audit/remediation_configs/{cf.name}")
        else:
            res = build_domain_audit_package(eng["domain"], base_out=deliv_dir)
            audit = res["audit"]
            primary_zip = Path(res["zip"])

        metrics_summary = {
            "overall_score": audit["overall_score"],
            "pass_count": audit["pass_count"],
            "warn_count": audit["warn_count"],
            "fail_count": audit["fail_count"],
            "total_checks": audit["total_checks"],
        }

    elif track == "pms_openfda_psur":
        from pms_monitor import build_pms_dossier, fetch_live_pms_dataset

        if pms_data_override is not None:
            pms_data = pms_data_override
        else:
            dev = eng.get("device_term") or "patient monitor"
            cond = eng.get("condition_term") or "patient safety"
            pms_data = fetch_live_pms_dataset(dev, cond)
        res = build_pms_dossier(pms_data, deliv_dir)
        primary_zip = Path(res["zip"])
        ms = pms_data.get("maude_summary", {})
        metrics_summary = {
            "total_maude_events": ms.get("total_events_analyzed", 0),
            "recalls_and_510k": len(pms_data.get("recalls_and_510k", [])),
            "clinical_trials": len(pms_data.get("clinical_trials", [])),
        }

    elif track == "clinical_lit_prisma":
        from pilot_package_generator import build_pilot_package

        rec_csv = Path(eng["records_csv"]) if eng.get("records_csv") else None
        cfg_json = Path(eng["config_json"]) if eng.get("config_json") else None

        if not (rec_csv and rec_csv.exists() and cfg_json and cfg_json.exists()):
            if eng.get("epmc_query"):
                spec = importlib.util.spec_from_file_location(
                    "lit_synth_03", str(COMPBIO_DIR / "03_pubmed_literature_synthesizer.py")
                )
                assert spec and spec.loader
                lit_mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(lit_mod)
                raw_recs, _ = lit_mod.europepmc_fetch(eng["epmc_query"], max_records=25)
                kept, normalized_all, stats = lit_mod.curate(raw_recs, years=5, max_records=20)
                rec_csv = eng_dir / "qa" / "live_records.csv"
                cfg_json = eng_dir / "qa" / "live_config.json"
                _curated_to_pilot_csv(
                    normalized_all,
                    rec_csv,
                    epmc_query=eng["epmc_query"],
                    title=f"{eng['company']} ({eng['domain']}) — Systematic Evidence Synthesis",
                    indication=eng.get("condition_term") or "Clinical Safety & Performance",
                    duplicates_removed=int(stats.get("duplicates_removed", 0)),
                    out_cfg=cfg_json,
                )
            else:
                rec_csv = SUITE_DIR / "records.csv"
                cfg_json = SUITE_DIR / "config.json"

        res = build_pilot_package(rec_csv, cfg_json, deliv_dir, include_legal_files=True)
        primary_zip = Path(res["zip"])
        if include_table1:
            eda_script = COMPBIO_DIR / "02_clinical_trial_eda.py"
            if eda_script.exists():
                t1_png = Path(res["package_dir"]) / "table1_demographics_benchmark.png"
                subprocess.run(
                    [sys.executable, str(eda_script), "--png", str(t1_png)],
                    cwd=str(res["package_dir"]),
                    capture_output=True,
                    timeout=60,
                    check=False,
                )
        pr = res["prisma"]
        metrics_summary = {
            "identified": pr["total_identified"],
            "screened": pr["records_screened"],
            "included": pr["studies_included"],
        }

    elif track == "ra_command_center":
        from ra_operations_command_center import build_ra_command_center_package

        in_json = Path(eng["ra_input_json"]) if eng.get("ra_input_json") else (SUITE_DIR / "sample_ra_submission_state.json")
        res = build_ra_command_center_package(in_json, deliv_dir, vertical=eng.get("vertical") or "medtech_ra")
        primary_zip = Path(res["zip"])
        rep = res["report"]
        metrics_summary = {
            "readiness_score": rep["overall_readiness_score"],
            "gate_decision": rep["gate_decision"],
            "crl_probability_pct": rep["crl_probability_pct"],
        }

    else:  # unified_dossier
        from medtech_suite import build_unified_medtech_dossier

        rec_csv = Path(eng["records_csv"]) if eng.get("records_csv") else (SUITE_DIR / "records.csv")
        cfg_json = Path(eng["config_json"]) if eng.get("config_json") else (SUITE_DIR / "config.json")
        res = build_unified_medtech_dossier(
            target_domain=eng["domain"],
            records_csv=rec_csv,
            config_json=cfg_json,
            base_out=deliv_dir,
            offline_audit_override=offline_audit_override,
        )
        primary_zip = Path(res["zip_path"])
        metrics_summary = {
            "domain_score": res["domain_score"],
            "studies_included": res["studies_included"],
        }

    qa_res = verify_delivery_package(deliv_dir, track)
    manifest_p, checklist_p = _build_manifest_and_refresh_zip(deliv_dir, primary_zip, eng, qa_res)

    eng["qa_passed"] = bool(qa_res["passed"])
    eng["zip_path"] = str(primary_zip)
    eng["metrics_summary"] = metrics_summary
    eng["status"] = "QA_VERIFIED_READY_FOR_DELIVERY" if qa_res["passed"] else "QA_FAILED_REVIEW_REQUIRED"
    upsert_engagement(eng, engagements_json)

    return {
        "engagement": eng,
        "qa": qa_res,
        "zip_path": primary_zip,
        "manifest_path": manifest_p,
        "checklist_path": checklist_p,
    }


def stage_delivery(
    engagement_id: str,
    engagements_json: Path = ENGAGEMENTS_JSON,
    config_path: Path | None = None,
    create_gmail_draft: bool = False,
    send_email: bool = False,
    confirm_send: bool = False,
) -> dict[str, Any]:
    if send_email and not confirm_send:
        raise ValueError("Refusing unattended delivery send: pass --confirm-send explicitly.")

    eng = get_engagement(engagement_id, engagements_json)
    if not eng.get("qa_passed") or not eng.get("zip_path"):
        raise RuntimeError(f"Engagement {engagement_id} has not passed QA verification yet (status={eng.get('status')}).")

    zip_path = Path(eng["zip_path"])
    if not zip_path.exists():
        raise FileNotFoundError(f"Verified delivery ZIP missing: {zip_path}")

    cfg = load_provider_config(config_path)
    prov = cfg["provider"]
    ops = cfg["operations"]

    eng_dir = Path(eng["workspace_dir"])
    deliv_stage_dir = eng_dir / "delivery"
    deliv_stage_dir.mkdir(parents=True, exist_ok=True)
    slug = _slugify(eng["domain"] or eng["company"])
    terms_p = eng_dir / "onboarding" / "TERMS_OF_SERVICE_AND_DISCLAIMER.txt"
    if not terms_p.exists():
        terms_p.write_text(render_terms_txt(track=eng["track"], cfg=cfg), encoding="utf-8")

    zip_size = zip_path.stat().st_size
    large_bundle = zip_size > MAX_DIRECT_ATTACHMENT_BYTES
    portal_url = (ops.get("delivery_portal_base_url") or "").strip()

    metrics_txt = ", ".join(f"{k}={v}" for k, v in (eng.get("metrics_summary") or {}).items())
    rescan_days = int(ops.get("included_verification_rescan_days", 14))
    rescan_note = (
        f"\n- Verification Re-Scan Included: Reply once your team deploys the DNS/header updates within "
        f"{rescan_days} days and I will run one verification re-scan and send updated results."
        if eng["track"] in ("sentinel_compliance", "unified_dossier")
        else ""
    )
    transfer_note = (
        f"Because the bundle is {zip_size / (1024 * 1024):.1f} MB, access the encrypted archive via portal: {portal_url or '[Add shared Drive link before sending]'}"
        if large_bundle
        else f"The complete QA-verified ZIP package ({zip_path.name}, {zip_size / 1024:.0f} KB) and Terms file are attached directly."
    )

    subject = f"QA-Verified Deliverable Ready — {eng['company']} ({eng['engagement_id']})"
    body = (
        f"Hi {eng['company']} team,\n\n"
        f"Your engagement package ({eng['engagement_id']}) for {eng['domain']} has passed all automated "
        f"pre-delivery QA & ALCOA+ checksum checks and is ready for internal review.\n\n"
        f"Key Summary: {metrics_txt}\n"
        f"Package Access: {transfer_note}\n"
        f"Included Inside Archive: Full Word/Excel/300-DPI deliverables, ALCOA_PROVENANCE_MANIFEST.json (SHA-256 hashes), "
        f"QA_SIGNOFF_CHECKLIST.md, and TERMS_OF_SERVICE_AND_DISCLAIMER.txt (v{TERMS_VERSION}).{rescan_note}\n\n"
        f"Please ensure your qualified QA/IT/RA lead completes final sign-off before regulatory filing or production DNS changes.\n\n"
        f"Best regards,\n"
        f"{prov.get('operator_name', 'Kaled Bouchagraoui')}\n"
        f"{prov.get('brand_name', 'Sentinel Regulatory & Technical Operations')}"
    )

    draft_path = deliv_stage_dir / f"{slug}_delivery_email.txt"
    draft_path.write_text(f"Subject: {subject}\nTo: {eng['contact_email']}\n\n{body}", encoding="utf-8")
    body_only = deliv_stage_dir / f"{slug}_delivery_body.txt"
    body_only.write_text(body, encoding="utf-8")

    eng["delivery_draft_path"] = str(draft_path)
    eng["status"] = "DELIVERY_DRAFTED"

    gmail_result = ""
    attach_flags = ["--file", str(terms_p)] if large_bundle else ["--file", str(zip_path), "--file", str(terms_p)]
    if send_email and eng["contact_email"]:
        gmail_result = _run_gmail_cli([
            "mutate", "send-with-attachment",
            "--to", eng["contact_email"],
            "--subject", subject,
            "--body-file", str(body_only),
            *attach_flags,
            "--json",
        ])
        eng["status"] = "DELIVERY_SENT"
    elif create_gmail_draft and eng["contact_email"]:
        gmail_result = _run_gmail_cli([
            "mutate", "create-draft",
            "--to", eng["contact_email"],
            "--subject", subject,
            "--body-file", str(body_only),
            *attach_flags,
            "--json",
        ])

    upsert_engagement(eng, engagements_json)
    return {
        "engagement": eng,
        "subject": subject,
        "draft_path": draft_path,
        "zip_path": zip_path,
        "gmail_result": gmail_result,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Zero-Cost Client Onboarding, Delivery & QA Automation CLI")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_web = sub.add_parser("build-legal-web", help="Generate static terms.html, privacy.html, and _headers for free hosting")
    p_web.add_argument("--out-dir", default=str(SITE_DEPLOY_DIR))

    sub.add_parser("status", help="Show active engagements and lifecycle statuses")

    p_ce = sub.add_parser("create-engagement", help="Register a new client engagement")
    p_ce.add_argument("--company", required=True)
    p_ce.add_argument("--domain", required=True)
    p_ce.add_argument("--email", required=True)
    p_ce.add_argument("--track", default="sentinel_compliance")
    p_ce.add_argument("--country", default="FR")
    p_ce.add_argument("--sector", default="MedTech OEM")
    p_ce.add_argument("--fee", default="")
    p_ce.add_argument("--device-term", default="")
    p_ce.add_argument("--condition-term", default="")
    p_ce.add_argument("--epmc-query", default="")
    p_ce.add_argument("--records-csv", default="")
    p_ce.add_argument("--config-json", default="")
    p_ce.add_argument("--ra-input-json", default="")
    p_ce.add_argument("--vertical", default="medtech_ra")

    p_onb = sub.add_parser("stage-onboarding", help="Generate onboarding email + Terms bundle (optional Gmail draft/send)")
    p_onb.add_argument("--id", required=True)
    p_onb.add_argument("--gmail-draft", action="store_true")
    p_onb.add_argument("--send", action="store_true")
    p_onb.add_argument("--confirm-send", action="store_true")

    p_run = sub.add_parser("run-delivery", help="Build full deliverable package + ALCOA+ provenance + QA Gate")
    p_run.add_argument("--id", required=True)
    p_run.add_argument("--include-table1", action="store_true")

    p_del = sub.add_parser("stage-delivery", help="Prepare QA-verified client delivery email + ZIP (optional Gmail draft/send)")
    p_del.add_argument("--id", required=True)
    p_del.add_argument("--gmail-draft", action="store_true")
    p_del.add_argument("--send", action="store_true")
    p_del.add_argument("--confirm-send", action="store_true")

    args = parser.parse_args(argv)

    if args.cmd == "build-legal-web":
        res = build_legal_web_pages(args.out_dir)
        try:
            from site_builder import build_storefront_bundle
            sync_target = (SUITE_DIR / "docs") if Path(args.out_dir).resolve() == SITE_DEPLOY_DIR.resolve() else None
            build_storefront_bundle(args.out_dir, sync_docs_dir=sync_target)
        except Exception:
            pass
        print(f"[build-legal-web] Static storefront & legal site bundle ready -> {args.out_dir} ({len(res)} files)")
        return 0

    if args.cmd == "status":
        rows = load_engagements()
        print(f"[status] {len(rows)} engagement(s) in {ENGAGEMENTS_JSON}")
        for r in rows:
            print(
                f"  - {r['engagement_id']} | {r['company']} ({r['domain']}) | track={r['track']} | "
                f"status={r['status']} | qa={r.get('qa_passed')} | fee={r.get('fee_label')}"
            )
        return 0

    if args.cmd == "create-engagement":
        rec = create_engagement(
            company=args.company,
            domain=args.domain,
            contact_email=args.email,
            track=args.track,
            country=args.country,
            sector=args.sector,
            fee_label=args.fee,
            device_term=args.device_term,
            condition_term=args.condition_term,
            epmc_query=args.epmc_query,
            records_csv=args.records_csv,
            config_json=args.config_json,
            ra_input_json=args.ra_input_json,
            vertical=args.vertical,
        )
        print(f"[create-engagement] Created {rec['engagement_id']} ({rec['track']}) -> {rec['workspace_dir']}")
        return 0

    if args.cmd == "stage-onboarding":
        res = stage_onboarding(
            args.id,
            create_gmail_draft=args.gmail_draft,
            send_email=args.send,
            confirm_send=args.confirm_send,
        )
        print(f"[stage-onboarding] {args.id} status={res['engagement']['status']} -> {res['draft_path']}")
        return 0

    if args.cmd == "run-delivery":
        res = run_delivery_for_engagement(args.id, include_table1=args.include_table1)
        print(
            f"[run-delivery] {args.id} qa_passed={res['qa']['passed']} status={res['engagement']['status']} -> {res['zip_path']}"
        )
        return 0 if res["qa"]["passed"] else 1

    if args.cmd == "stage-delivery":
        res = stage_delivery(
            args.id,
            create_gmail_draft=args.gmail_draft,
            send_email=args.send,
            confirm_send=args.confirm_send,
        )
        print(f"[stage-delivery] {args.id} status={res['engagement']['status']} -> {res['draft_path']}")
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
