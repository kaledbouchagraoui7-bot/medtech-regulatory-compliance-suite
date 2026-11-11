#!/usr/bin/env python3
"""
legal_terms.py — Automated Terms of Service, Liability Disclaimers & GDPR Privacy Module
=========================================================================================

Generates customized legal notices, Word (.docx) disclaimer sections, Excel README legal rows,
standalone TERMS_OF_SERVICE_AND_DISCLAIMER.txt bundles, and turnkey static HTML pages
(`terms.html`, `privacy.html`) for GitHub Pages / Cloudflare Pages / Netlify hosting.

Designed for French B2B technical compliance automation (micro-entreprise ready, art. 293 B CGI)
operating strictly on passive public endpoints and public scientific registries.
"""

from __future__ import annotations

import html
import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

TERMS_VERSION = "2026.1"
DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent / "client_ops_config.json"

DEFAULT_CONFIG: dict[str, Any] = {
    "provider": {
        "brand_name": "Sentinel Regulatory & Technical Operations",
        "operator_name": "Kaled Bouchagraoui",
        "legal_status": "Pre-commercial technical studio (complimentary EUR 0 previews require no invoicing; paid contracts formalized strictly via legal-representative authorization under French Civil Code Art. 388-2 & 389 / authorized billing entity)",
        "siret": "PENDING_LEGAL_ENTITY_AUTH",
        "jurisdiction_city": "Strasbourg, France",
        "governing_law": "Laws of France",
        "vat_notice": "TVA non applicable, art. 293 B du CGI",
        "website_url": "https://kaledbouchagraoui7-bot.github.io/medtech-regulatory-compliance-suite/",
        "contact_email": "kaledbouchagraoui7@gmail.com",
        "terms_url": "https://kaledbouchagraoui7-bot.github.io/medtech-regulatory-compliance-suite/terms.html",
        "cgv_url": "https://kaledbouchagraoui7-bot.github.io/medtech-regulatory-compliance-suite/cgv.html",
        "privacy_url": "https://kaledbouchagraoui7-bot.github.io/medtech-regulatory-compliance-suite/privacy.html",
    },
    "payment": {
        "invoicing_platform": "Tiime",
        "stripe_mode": "payment_links_no_code",
        "stripe_payment_links": {
            "sentinel_compliance": "",
            "pms_openfda_psur": "",
            "clinical_lit_prisma": "",
            "unified_dossier": "",
            "ra_command_center": "",
        },
        "bank_transfer": {
            "account_holder": "Kaled Bouchagraoui",
            "iban": "IBAN_PENDING_TIIME_OR_BANK",
            "bic": "BIC_PENDING",
        },
        "payment_terms": "Complimentary 1-page diagnostic previews are EUR 0.00. Paid scopes require written confirmation and authorized legal-representative billing structure prior to invoice/Stripe collection.",
    },
    "operations": {
        "intake_form_url": "",
        "delivery_portal_base_url": "",
        "default_turnaround_hours": 48,
        "included_verification_rescan_days": 14,
    },
}


def load_provider_config(config_path: str | Path | None = None) -> dict[str, Any]:
    """Load `client_ops_config.json` safely, merging defaults if keys are omitted."""
    cfg = deepcopy(DEFAULT_CONFIG)
    p = Path(config_path) if config_path else DEFAULT_CONFIG_PATH
    if p.exists():
        try:
            loaded = json.loads(p.read_text(encoding="utf-8"))
            for section in ("provider", "payment", "operations"):
                if isinstance(loaded.get(section), dict):
                    cfg[section].update(loaded[section])
            if isinstance(loaded.get("payment", {}).get("stripe_payment_links"), dict):
                cfg["payment"]["stripe_payment_links"].update(
                    loaded["payment"]["stripe_payment_links"]
                )
            if isinstance(loaded.get("payment", {}).get("bank_transfer"), dict):
                cfg["payment"]["bank_transfer"].update(loaded["payment"]["bank_transfer"])
        except Exception:
            pass
    return cfg


def _track_scope_description(track: str) -> str:
    t = (track or "general").strip().lower()
    if t in ("sentinel", "sentinel_compliance"):
        return (
            "Passive external observation of publicly broadcast DNS (TXT/MX/CAA via DNS-over-HTTPS), "
            "TLS certificate metadata, and a single standard HTTPS GET request identical to an ordinary web "
            "browser visit. Strictly excludes port scanning, brute-forcing, credential testing, or intrusive probing."
        )
    if t in ("pms", "pms_openfda_psur"):
        return (
            "Automated retrieval and structuring of public U.S. FDA OpenFDA (MAUDE, 510(k), Recalls) and "
            "NLM ClinicalTrials.gov REST API v2 records into EU MDR Art. 83-86 / MDCG 2022-21 PSUR draft deliverables."
        )
    if t in ("prisma", "clinical_lit_prisma", "biostats"):
        return (
            "Automated PRISMA 2020 clinical literature deduplication, arithmetic reconciliation, reference extraction, "
            "biostatistical baseline Table 1 calculation, and public NCBI RefSeq transcript QC under ALCOA+ rules."
        )
    if t in ("ra_command_center", "unified", "unified_dossier"):
        return (
            "Combined passive external domain security/privacy posture review, automated PRISMA 2020 clinical "
            "evidence compilation, PMS safety trend formatting, and deterministic RA submission gatekeeper linting."
        )
    return (
        "Automated technical compliance posture review, public registry data compilation, and regulatory "
        "documentation formatting across Sentinel, OpenFDA/ClinicalTrials PMS, PRISMA 2020, and RA workflows."
    )


def get_legal_clauses(track: str = "general", cfg: dict[str, Any] | None = None) -> list[tuple[str, str]]:
    """Return canonical Terms of Service & Liability Disclaimer clauses for the specified track."""
    c = cfg or load_provider_config()
    prov = c["provider"]
    pay = c["payment"]
    provider_line = f"{prov['brand_name']} ({prov['operator_name']}, {prov['jurisdiction_city']})"
    raw_siret = prov["siret"]
    siret_txt = (
        raw_siret
        if raw_siret not in ("PENDING_INSEE_SIRET", "PENDING_LEGAL_ENTITY_AUTH")
        else "Authorized billing entity / SIRET confirmed prior to paid invoicing"
    )

    return [
        (
            "Provider & Commercial Entity Status",
            f"Prepared by {provider_line}. Status: {prov['legal_status']} (SIRET: {siret_txt}; {prov['vat_notice']}). "
            f"Contact: {prov['contact_email']} | Terms Version: {TERMS_VERSION}.",
        ),
        (
            "1. Scope & Strictly Passive / Public Data Boundary",
            f"{_track_scope_description(track)} All security checks remain strictly passive under Swiss Criminal Code "
            "Art. 143bis and EU cybersecurity norms, and no patient-identifiable data (PHI/PII) is ingested during automated public-registry runs.",
        ),
        (
            "2. No Legal, Medical, Regulatory Approval, or Certified Pen-Test Advice",
            "All scores, Word dossiers, Excel workbooks, PRISMA tables, PSUR drafts, statutory gatekeeper alerts, and sample "
            "server/DNS configuration snippets are provided strictly as automated engineering and documentation preparation aids. "
            "They do NOT constitute formal legal advice (Rechtsberatung / conseil juridique), clinical medical advice, a binding GDPR/nFADP "
            "adequacy opinion, or an accredited penetration-test certification. All regulatory deliverables must be independently reviewed "
            "and signed off by the Client's qualified Regulatory Affairs Specialist, PRRC (EU MDR Art. 15), DPO, or legal counsel prior to submission.",
        ),
        (
            "3. Zero Fabrication Integrity & Public Source Accuracy",
            "Software outputs reflect third-party public endpoints (DNS, HTTP headers, OpenFDA CC0, NLM ClinicalTrials.gov v2, "
            "Europe PMC / NCBI PubMed) or Client-supplied files at the exact capture timestamp. Missing DOIs or conclusions are never "
            "invented and are highlighted yellow (#FFF2CC) for manual QA verification. Third-party registries can update after capture.",
        ),
        (
            "4. Client Authorization & Deployment Responsibility",
            "By commissioning a paid deliverable or providing internal datasets/URLs, the Client represents that it holds full legal "
            "authority over the target domain or dataset. Where optional Nginx, Cloudflare, Apache, or DNS records are included, "
            "the Client's IT administrator is solely responsible for staging, testing, and backing up live production configurations before deployment.",
        ),
        (
            "5. Limitation of Liability & No Guarantee of Agency Clearance",
            "To the maximum extent permitted by applicable French law, deliverables are provided 'as is' at the point-in-time capture without warranty "
            "of uninterrupted regulatory approval by any Notified Body, FDA, EMA, MHRA, Swissmedic, or CNIL. The Provider shall not be liable for "
            "indirect, incidental, lost-profit, business-interruption, or regulatory-fine damages. Provider's total cumulative liability "
            "for any claim arising out of an engagement is strictly capped at the total fees actually paid by the Client for that specific engagement "
            "(EUR 0 / zero liability for complimentary 1-page pre-engagement evaluation previews).",
        ),
        (
            "6. Invoicing, Payment & Intellectual Property License",
            f"{pay['payment_terms']} Upon receipt of full cleared payment via {pay['invoicing_platform']} / Stripe / SEPA, the Client "
            "receives a perpetual, non-exclusive internal business license to use, modify, and file the generated reports and configuration outputs. "
            "Underlying automation software and source code remain the exclusive intellectual property of the Provider.",
        ),
        (
            "7. Governing Law & Dispute Resolution",
            f"These Terms are governed by the {prov['governing_law']}. In the event of any dispute arising out of commercial deliverables, "
            f"the parties agree to seek amicable resolution first, failing which competent courts within the jurisdiction of {prov['jurisdiction_city']} "
            "shall have jurisdiction to the extent permitted by law.",
        ),
    ]


def get_privacy_clauses(cfg: dict[str, Any] | None = None) -> list[tuple[str, str]]:
    """Return structured GDPR / Swiss nFADP Privacy Policy clauses for B2B outreach & client delivery."""
    c = cfg or load_provider_config()
    prov = c["provider"]
    return [
        (
            "Data Controller",
            f"{prov['brand_name']} ({prov['operator_name']}), operating from {prov['jurisdiction_city']}. Privacy & erasure contact: {prov['contact_email']}.",
        ),
        (
            "Data Processed & Lawful Basis (EU GDPR Art. 6)",
            "For B2B technical outreach and contracted service delivery, we process only business contact details published on corporate websites "
            "(role/company email, company domain), client-supplied billing details required for statutory Tiime/French invoicing (GDPR Art. 6(1)(b)/(c)), "
            "and strictly passive public DNS/TLS/HTTP response metadata or public scientific database records under legitimate business interest (GDPR Art. 6(1)(f) & CNIL B2B guidelines).",
        ),
        (
            "Zero Patient / Special-Category Health Data",
            "Automated surveillance workflows query public aggregated endpoints (OpenFDA, ClinicalTrials.gov, PubMed/Europe PMC) or synthetic datasets. "
            "Clients must not transmit identifiable Protected Health Information (PHI) unless covered by a separate written Data Processing Addendum (DPA).",
        ),
        (
            "Sub-Processors & Retention",
            "Business correspondence and invoices use encrypted cloud mail/accounting providers (Gmail/Zoho, Tiime, Stripe when enabled) under EU/standard contractual safeguards. "
            "Deliverables are retained during active engagement and statutory accounting periods (10 years for French invoices; immediate deletion upon request for evaluation previews).",
        ),
        (
            "Data Subject Rights & Immediate Opt-Out",
            f"Under EU GDPR Arts. 15-22 and Swiss nFADP, recipients may request access, rectification, or permanent suppression at any time by replying 'no' or emailing {prov['contact_email']}.",
        ),
    ]


def append_terms_section_docx(
    doc: Any,
    track: str = "general",
    cfg: dict[str, Any] | None = None,
) -> None:
    """
    Append Terms of Service, Scope Boundary & Liability Disclaimer as paragraphs (NO extra tables)
    so existing unit tests asserting exact `len(doc.tables)` and page footers remain 100% untouched.
    """
    from docx.shared import Pt, RGBColor

    clauses = get_legal_clauses(track=track, cfg=cfg)

    p_hdr = doc.add_paragraph()
    p_hdr.paragraph_format.space_before = Pt(12)
    p_hdr.paragraph_format.space_after = Pt(4)
    r_hdr = p_hdr.add_run(f"TERMS OF SERVICE, PASSIVE SCOPE & LIABILITY DISCLAIMER (v{TERMS_VERSION})")
    r_hdr.font.name = "Calibri"
    r_hdr.font.size = Pt(10.5)
    r_hdr.font.bold = True
    r_hdr.font.color.rgb = RGBColor(0x0F, 0x17, 0x2A)

    for title, text in clauses:
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(1)
        p.paragraph_format.space_after = Pt(2)
        p.paragraph_format.line_spacing = 1.05
        rt = p.add_run(f"{title}: ")
        rt.font.name = "Calibri"
        rt.font.size = Pt(8.5)
        rt.font.bold = True
        rt.font.color.rgb = RGBColor(0x1E, 0x29, 0x3B)

        rb = p.add_run(text)
        rb.font.name = "Calibri"
        rb.font.size = Pt(8.5)
        rb.font.color.rgb = RGBColor(0x47, 0x55, 0x69)


def append_terms_to_readme_xlsx(
    ws_readme: Any,
    border: Any,
    bold_font: Any,
    body_font: Any,
    wrap_top: Any,
    track: str = "general",
    cfg: dict[str, Any] | None = None,
) -> None:
    """Append structured Terms of Service & Liability rows directly inside the existing README sheet."""
    for title, text in get_legal_clauses(track=track, cfg=cfg):
        ws_readme.append([f"Legal: {title}", text])
        rn = ws_readme.max_row
        c1 = ws_readme.cell(row=rn, column=1)
        c2 = ws_readme.cell(row=rn, column=2)
        c1.font = bold_font
        c1.border = border
        c1.alignment = wrap_top
        c2.font = body_font
        c2.border = border
        c2.alignment = wrap_top


def render_terms_txt(track: str = "general", cfg: dict[str, Any] | None = None) -> str:
    """Render standalone plain-text Terms of Service + Liability Disclaimer + Privacy summary."""
    c = cfg or load_provider_config()
    prov = c["provider"]
    lines = [
        "=" * 78,
        f"  {prov['brand_name'].upper()} — TERMS OF SERVICE & LIABILITY DISCLAIMER",
        f"  Version {TERMS_VERSION} | Track: {track} | Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        "=" * 78,
        "",
    ]
    for title, body in get_legal_clauses(track=track, cfg=c):
        lines.append(title)
        lines.append("-" * len(title))
        lines.append(body)
        lines.append("")
    lines.extend([
        "=" * 78,
        "  GDPR & SWISS nFADP PRIVACY NOTICE SUMMARY",
        "=" * 78,
        "",
    ])
    for title, body in get_privacy_clauses(cfg=c):
        lines.append(f"- {title}: {body}")
    lines.append("")
    return "\n".join(lines)


def _render_editorial_legal_html(
    page_title: str,
    eyebrow: str,
    intro: str,
    sections: list[tuple[str, str]],
    cfg: dict[str, Any],
    other_link_href: str,
    other_link_label: str,
) -> str:
    prov = cfg["provider"]
    cards = []
    for title, body in sections:
        cards.append(
            f"""
            <section class="clause">
              <h2>{html.escape(title)}</h2>
              <p>{html.escape(body)}</p>
            </section>
            """
        )

    footer_links = (
        f'<a href="index.html">Storefront (EN/FR)</a> &middot; '
        f'<a href="terms.html">Terms (EN)</a> &middot; '
        f'<a href="cgv.html">CGV (FR)</a> &middot; '
        f'<a href="privacy.html">Privacy</a> &middot; '
        f'<a href="mailto:{html.escape(prov["contact_email"])}">{html.escape(prov["contact_email"])}</a>'
    )
    html_lang = "fr" if "cgv" in page_title.lower() else "en"
    provider_label = "Prestataire :" if html_lang == "fr" else "Provider:"
    version_label = "Version :" if html_lang == "fr" else "Version:"
    return f"""<!doctype html>
<html lang="{html_lang}">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{html.escape(page_title)} — {html.escape(prov['brand_name'])}</title>
  <meta name="description" content="{html.escape(page_title)} for {html.escape(prov['brand_name'])} technical compliance and regulatory data deliverables." />
  <style>
    :root {{
      --navy: #0F172A;
      --teal: #0F766E;
      --border: #E2E8F0;
      --bg: #F8FAFC;
      --text: #1E293B;
      --muted: #475569;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      padding: 40px 20px;
      background: var(--bg);
      color: var(--text);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      line-height: 1.6;
    }}
    main {{
      max-width: 860px;
      margin: 0 auto;
      background: #FFFFFF;
      border: 1px solid var(--border);
      border-top: 4px solid var(--navy);
      padding: 40px 44px;
    }}
    header {{
      border-bottom: 1.5px solid var(--navy);
      padding-bottom: 18px;
      margin-bottom: 24px;
      display: flex;
      justify-content: space-between;
      align-items: flex-end;
      flex-wrap: wrap;
      gap: 16px;
    }}
    .eyebrow {{
      font-size: 11px;
      font-weight: 700;
      letter-spacing: 1.4px;
      text-transform: uppercase;
      color: var(--teal);
      margin-bottom: 6px;
    }}
    h1 {{
      margin: 0;
      font-family: Georgia, "Times New Roman", serif;
      font-size: 26px;
      color: var(--navy);
    }}
    .meta {{
      font-size: 13px;
      color: var(--muted);
      text-align: right;
    }}
    .intro {{
      background: var(--bg);
      border-left: 3.5px solid var(--teal);
      padding: 14px 18px;
      font-size: 14.5px;
      margin-bottom: 26px;
    }}
    .clause {{
      padding: 14px 0;
      border-bottom: 1px solid var(--border);
    }}
    .clause:last-of-type {{ border-bottom: none; }}
    h2 {{
      margin: 0 0 6px 0;
      font-size: 16px;
      color: var(--navy);
    }}
    p {{
      margin: 0;
      font-size: 14.5px;
      color: var(--text);
    }}
    footer {{
      margin-top: 28px;
      padding-top: 16px;
      border-top: 1px solid var(--border);
      font-size: 13px;
      color: var(--muted);
      display: flex;
      justify-content: space-between;
      flex-wrap: wrap;
      gap: 12px;
    }}
    a {{ color: var(--teal); text-decoration: none; font-weight: 600; }}
    a:hover {{ text-decoration: underline; }}
    @media (max-width: 640px) {{
      main {{ padding: 26px 20px; }}
      .meta {{ text-align: left; }}
    }}
  </style>
</head>
<body>
  <main>
    <header>
      <div>
        <div class="eyebrow">{html.escape(eyebrow)}</div>
        <h1>{html.escape(page_title)}</h1>
      </div>
      <div class="meta">
        <div><strong>{version_label}</strong> {TERMS_VERSION}</div>
        <div><strong>{provider_label}</strong> {html.escape(prov['operator_name'])} &middot; {html.escape(prov['jurisdiction_city'])}</div>
      </div>
    </header>
    <div class="intro">{html.escape(intro)}</div>
    {''.join(cards)}
    <footer>
      <span>&copy; {datetime.now(timezone.utc).year} {html.escape(prov['brand_name'])} &middot; {html.escape(prov['vat_notice'])}</span>
      <span>{footer_links}</span>
    </footer>
  </main>
</body>
</html>
"""


def get_cgv_fr_clauses(cfg: dict[str, Any] | None = None) -> list[tuple[str, str]]:
    """Return French B2B Conditions Générales de Vente (CGV) & Avertissement Réglementaire clauses."""
    c = cfg or load_provider_config()
    prov = c["provider"]
    return [
        (
            "1. Identité, Statut Juridique & Capacité Contractuelle",
            f"Les présentes Conditions Générales de Vente (CGV) régissent les prestations techniques automatisées proposées sous l'enseigne {prov['brand_name']} ({prov['jurisdiction_city']}, contact : {prov['contact_email']}). Les aperçus diagnostiques gratuits d'une page (0 EUR) constituent des démonstrations techniques sans engagement ni facturation. Toute commande payante est soumise à la validation écrite d'une structure de facturation dûment habilitée (société unipersonnelle autorisée ou co-signature du représentant légal conformément aux articles 388-2 et 389 du Code civil).",
        ),
        (
            "2. Périmètre Strictement Passif & Données Publiques",
            "Les contrôles Sentinel s'effectuent exclusivement par observation externe passive (requêtes DNS-over-HTTPS TXT/MX/CAA, métadonnées TLS et requête HTTPS GET standard équivalente à un navigateur), dans le strict respect du Code pénal suisse (art. 143bis) et du droit européen. Aucun scan intrusif ni aucune donnée patient (PHI/PII) ne sont traités.",
        ),
        (
            "3. Absence de Conseil Juridique, Médical ou Audit Certifié",
            "Les scores, rapports Word (.docx), matrices Excel (.xlsx), diagrammes PRISMA 2020, synthèses PSUR/MAUDE et configurations types (Nginx, Cloudflare, DNS) sont fournis exclusivement comme supports techniques d'ingénierie documentaire. Ils ne constituent ni un conseil juridique, ni un avis médical, ni une certification d'audit ou test d'intrusion. Toute soumission réglementaire ou mise en production doit être validée et signée par le responsable AQ/AR, la PRRC (Règlement UE MDR 2017/745 art. 15), le DPO ou l'administrateur système du Client.",
        ),
        (
            "4. Intégrité ALCOA+ & Zéro Fabrication",
            "Les données proviennent directement d'APIs publiques (OpenFDA CC0, ClinicalTrials.gov v2, Europe PMC / NCBI PubMed) ou de fichiers fournis par le Client à l'instant T. Les champs absents ne sont jamais inventés et sont signalés en surbrillance jaune (#FFF2CC) pour vérification manuelle.",
        ),
        (
            "5. Limitation de Responsabilité",
            "Dans toute la mesure permise par la loi française, la responsabilité cumulée du Prestataire au titre d'un livrable payant est strictement plafonnée au montant total hors taxes effectivement encaissé pour la mission concernée (responsabilité nulle / 0 EUR pour les aperçus diagnostiques gracieux). Le Prestataire ne garantit aucune décision d'homologation d'organisme notifié, FDA, ANSM, Swissmedic ou CNIL.",
        ),
        (
            "6. Facturation, TVA & Propriété Intellectuelle",
            f"Les missions payantes font l'objet d'un devis validé et d'une facture conforme (Tiime / virement SEPA / Stripe ; {prov['vat_notice']} le cas échéant). Après paiement intégral, le Client acquiert une licence interne non exclusive d'utilisation et d'adaptation des rapports générés ; le code source et les moteurs d'automatisation restent la propriété exclusive du Prestataire.",
        ),
        (
            "7. Droit Applicable & Juridiction Compétente",
            f"Les présentes CGV sont soumises au droit français. À défaut d'accord amiable préalable, tout litige commercial relève des juridictions compétentes de {prov['jurisdiction_city']}.",
        ),
    ]


def render_cgv_fr_html(cfg: dict[str, Any] | None = None) -> str:
    """Render static Swiss-editorial French CGV & Legal Notice HTML page (`cgv.html`)."""
    c = cfg or load_provider_config()
    return _render_editorial_legal_html(
        page_title="Conditions Générales de Vente & Avertissement (CGV)",
        eyebrow="Sentinel Regulatory & Technical Operations · Mentions & CGV (FR)",
        intro=(
            "Ces CGV encadrent les aperçus techniques gracieux (0 EUR) et les livrables forfaitaires B2B "
            "d'audit de posture numérique (nFADP / RGPD / DMARC), veille OpenFDA MAUDE / PSUR, synthèse clinique PRISMA 2020 et contrôle eCTD."
        ),
        sections=get_cgv_fr_clauses(cfg=c),
        cfg=c,
        other_link_href="terms.html",
        other_link_label="English Terms · Privacy · Home",
    )


def render_terms_html(cfg: dict[str, Any] | None = None) -> str:
    """Render static Swiss-editorial Terms of Service & Liability Disclaimer HTML page."""
    c = cfg or load_provider_config()
    return _render_editorial_legal_html(
        page_title="Terms of Service & Liability Disclaimer",
        eyebrow="Sentinel Regulatory & Technical Operations · Legal Terms",
        intro=(
            "These Terms govern all complimentary 1-page technical posture previews and paid fixed-fee "
            "automation deliverables across external web/email posture reviews, OpenFDA/ClinicalTrials PSUR packs, "
            "PRISMA 2020 systematic literature synthesis, and RA dossier linting."
        ),
        sections=get_legal_clauses(track="general", cfg=c),
        cfg=c,
        other_link_href="privacy.html",
        other_link_label="Privacy Notice (GDPR / nFADP)",
    )


def render_privacy_html(cfg: dict[str, Any] | None = None) -> str:
    """Render static Swiss-editorial GDPR / Swiss nFADP Privacy Policy HTML page."""
    c = cfg or load_provider_config()
    return _render_editorial_legal_html(
        page_title="Privacy Policy (EU GDPR & Swiss nFADP)",
        eyebrow="Sentinel Regulatory & Technical Operations · Data Protection",
        intro=(
            "We process only corporate contact data, statutory commercial invoicing details, and passive public "
            "technical/scientific endpoints. Zero sensitive patient health records are collected."
        ),
        sections=get_privacy_clauses(cfg=c),
        cfg=c,
        other_link_href="terms.html",
        other_link_label="Terms of Service & Disclaimer",
    )


def build_legal_web_pages(
    out_dir: str | Path,
    cfg: dict[str, Any] | None = None,
) -> dict[str, Path]:
    """Generate turnkey static storefront & legal web assets (`index.html`, `terms.html`, `cgv.html`, `privacy.html`, `.txt`, `_headers`) for free hosting."""
    c = cfg or load_provider_config()
    target_dir = Path(out_dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    terms_html = target_dir / "terms.html"
    cgv_html = target_dir / "cgv.html"
    privacy_html = target_dir / "privacy.html"
    terms_txt = target_dir / "TERMS_OF_SERVICE_AND_DISCLAIMER.txt"
    headers_file = target_dir / "_headers"
    nojekyll_file = target_dir / ".nojekyll"

    terms_html.write_text(render_terms_html(c), encoding="utf-8")
    cgv_html.write_text(render_cgv_fr_html(c), encoding="utf-8")
    privacy_html.write_text(render_privacy_html(c), encoding="utf-8")
    terms_txt.write_text(render_terms_txt(track="general", cfg=c), encoding="utf-8")
    nojekyll_file.write_text("", encoding="utf-8")
    headers_file.write_text(
        "/*\n"
        "  Strict-Transport-Security: max-age=31536000; includeSubDomains; preload\n"
        "  X-Content-Type-Options: nosniff\n"
        "  X-Frame-Options: SAMEORIGIN\n"
        "  Referrer-Policy: strict-origin-when-cross-origin\n"
        "  Permissions-Policy: camera=(), microphone=(), geolocation=()\n"
        "  Content-Security-Policy: default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; connect-src 'self' https://dns.google https://api.fda.gov https://www.ebi.ac.uk; base-uri 'self'; form-action 'self' https://tally.so https://mail.google.com mailto:;\n",
        encoding="utf-8",
    )

    out_map: dict[str, Path] = {
        "terms_html": terms_html,
        "cgv_html": cgv_html,
        "privacy_html": privacy_html,
        "terms_txt": terms_txt,
        "headers": headers_file,
        "nojekyll": nojekyll_file,
    }

    try:
        from site_builder import build_storefront_bundle
        storefront_assets = build_storefront_bundle(target_dir, cfg=c)
        out_map.update(storefront_assets)
    except ImportError:
        pass

    return out_map


if __name__ == "__main__":
    default_site_dir = Path(__file__).resolve().parent / "site_deploy_ready"
    res = build_legal_web_pages(default_site_dir)
    print(f"[legal_terms] Generated v{TERMS_VERSION} static legal pages -> {default_site_dir}")
    for k, p in res.items():
        print(f"  - {k}: {p}")
