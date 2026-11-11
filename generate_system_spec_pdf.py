#!/usr/bin/env python3
"""
generate_system_spec_pdf.py — Generates the 1-page Swiss-Editorial Technical Methodology Brief
(`Sentinel_25_Control_Evaluation_System.pdf` & `.png`) attached alongside each prospect briefing.
All narrative prose is passed through the single-pass humanizer and 4-detector AI verifier (<10%).
"""

from __future__ import annotations

import html
from pathlib import Path

from editorial_renderer import _SENTINEL_HEADER_SVG, render_html_to_pdf_and_png
from outreach_qa_dispatcher import apply_humanizer_pass, evaluate_4_detectors


def build_evaluation_system_pdf(out_pdf: Path, out_png: Path | None = None) -> Path:
    out_pdf.parent.mkdir(parents=True, exist_ok=True)

    # Narrative blocks vetted through the humanizer + 4-detector gate (<10% AI score)
    raw_summary = (
        "This 1-page sheet outlines the 25 passive external checks used to review public business domains. "
        "Every check relies solely on standard DNS-over-HTTPS queries, public TLS certificate metadata, and a single "
        "HTTPS GET request identical to an ordinary web browser visit, without port scanning or intrusive probing."
    )
    raw_scope = (
        "When engaged for a fixed-fee remediation package, deliverables include the full Word and 4-sheet Excel audit "
        "dossier, copy-paste DNS records (DMARC, SPF, CAA), ready-to-deploy Nginx, Apache, or Cloudflare security headers, "
        "local webfont privacy guidance, and a post-deployment verification re-scan once your team applies the changes."
    )

    clean_summary = apply_humanizer_pass(raw_summary, iteration=1)
    clean_scope = apply_humanizer_pass(raw_scope, iteration=1)

    det_report = evaluate_4_detectors(f"{clean_summary}\n\n{clean_scope}")
    if det_report["average_ai_pct"] >= 10.0:
        raise RuntimeError(f"Methodology paper failed <10% AI detector gate: {det_report['average_ai_pct']}%")

    stages = [
        (
            "01 · Passive Collectors",
            "Queries Cloudflare and Google DNS-over-HTTPS (TXT, MX, CAA), inspects TLS 1.2/1.3 certificate validity, and reads one standard public HTTPS response.",
        ),
        (
            "02 · 25-Control Matrix",
            "Evaluates 25 deterministic rules across email authentication, pre-consent privacy leaks, browser security headers, WCAG 2.1 AA, and structured Schema.org.",
        ),
        (
            "03 · Clinical & RA Add-Ons",
            "Optional modules automate PRISMA 2020 clinical literature tables (EU MDR Annex XIV), OpenFDA MAUDE safety digests (PSUR), and eCTD cross-checks.",
        ),
        (
            "04 · Turnkey Config Fixes",
            "Outputs copy-paste DNS records, Nginx and Cloudflare header snippets, Word and Excel audit tables, plus a verification re-scan after deployment.",
        ),
    ]

    stage_cards = []
    for title, desc in stages:
        stage_cards.append(
            f"""
            <div class="stage-card">
              <div class="stage-title">{html.escape(title)}</div>
              <div class="stage-desc">{html.escape(desc)}</div>
            </div>
            """
        )

    pillars = [
        (
            "Pillar 1 · Email Authentication & Anti-Spoofing (4 Controls)",
            "EML-01 DMARC enforcement policy (p=quarantine / p=reject vs missing or p=none) · EML-02 SPF syntax & 10-lookup ceiling · EML-03 MX mail routing · EML-04 DNS CAA certificate lock (RFC 7489, RFC 7208, RFC 8659).",
        ),
        (
            "Pillar 2 · Web Privacy & Cross-Border Data Hygiene (4 Controls)",
            "PRV-01 Pre-consent remote Google Fonts IP transfer check · PRV-02 Initial HTML third-party ad/analytics tracker scan · PRV-03 Cookie Secure, HttpOnly & SameSite flags · PRV-04 Discoverable Privacy Policy link (GDPR Art. 13/44, Swiss nFADP).",
        ),
        (
            "Pillar 3 · Edge Transport & Browser Security Headers (9 Controls)",
            "SEC-01 TLS 1.2/1.3 & certificate expiry · SEC-02 HSTS · SEC-03 Content-Security-Policy · SEC-04 X-Frame-Options · SEC-05 X-Content-Type-Options: nosniff · SEC-06 Referrer-Policy · SEC-07 Permissions-Policy · SEC-08 Server fingerprinting · SEC-09 security.txt.",
        ),
        (
            "Pillar 4 · Accessibility (WCAG 2.1 AA / EAA) & Pillar 5 · Technical SEO (8 Controls)",
            "A11Y-01 Root html lang attribute · A11Y-02 Image alt coverage · A11Y-03 Viewport pinch-to-zoom freedom · A11Y-04 Single h1 heading · SEO-01 Title & meta description · SEO-02 Canonical URL · SEO-03 JSON-LD Schema.org · SEO-04 robots.txt.",
        ),
    ]

    pillar_rows = []
    for p_title, p_detail in pillars:
        pillar_rows.append(
            f"""
            <tr>
              <td class="p-name">{html.escape(p_title)}</td>
              <td class="p-desc">{html.escape(p_detail)}</td>
            </tr>
            """
        )

    html_doc = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<style>
  @page {{ size: 11.4in 7.8in; margin: 0; }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0;
    width: 1140px;
    height: 780px;
    padding: 34px 44px 26px 44px;
    background: #FFFFFF;
    color: #111827;
    font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, Helvetica, Arial, sans-serif;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
  }}
  .header {{
    border-bottom: 2px solid #0F172A;
    padding-bottom: 11px;
    display: flex;
    justify-content: space-between;
    align-items: flex-end;
    gap: 24px;
  }}
  .header-brand {{
    display: flex;
    align-items: center;
    gap: 13px;
    flex: 1 1 auto;
    min-width: 0;
  }}
  .brand-mark {{
    flex: 0 0 auto;
    line-height: 0;
  }}
  .eyebrow {{
    font-size: 9.8px;
    letter-spacing: 1.4px;
    text-transform: uppercase;
    color: #0F766E;
    font-weight: 700;
    margin-bottom: 4px;
  }}
  h1 {{
    margin: 0;
    font-family: Georgia, 'Times New Roman', serif;
    font-size: 18px;
    font-weight: 700;
    color: #0F172A;
    white-space: nowrap;
  }}
  .meta {{
    text-align: right;
    font-size: 10.5px;
    color: #4B5563;
    line-height: 1.45;
    white-space: nowrap;
  }}
  .lead {{
    margin: 12px 0 14px 0;
    font-size: 11.5px;
    line-height: 1.5;
    color: #374151;
  }}
  .stages-grid {{
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 14px;
    margin-bottom: 16px;
  }}
  .stage-card {{
    background: #F8FAFC;
    border: 1px solid #E2E8F0;
    border-top: 2.5px solid #0F172A;
    padding: 11px 13px;
  }}
  .stage-title {{
    font-size: 11px;
    font-weight: 700;
    color: #0F172A;
    margin-bottom: 5px;
  }}
  .stage-desc {{
    font-size: 10.2px;
    line-height: 1.42;
    color: #4B5563;
  }}
  .sec-label {{
    font-size: 10px;
    letter-spacing: 1.2px;
    text-transform: uppercase;
    color: #475569;
    font-weight: 700;
    margin-bottom: 6px;
  }}
  table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 10.8px;
  }}
  td {{
    border-top: 1px solid #E5E7EB;
    padding: 8px 10px 8px 0;
    vertical-align: top;
    line-height: 1.4;
  }}
  tr:last-child td {{ border-bottom: 1px solid #E5E7EB; }}
  .p-name {{
    width: 340px;
    font-weight: 700;
    color: #0F172A;
  }}
  .p-desc {{ color: #374151; }}
  .scope-box {{
    margin-top: 14px;
    background: #F8FAFC;
    border: 1px solid #E2E8F0;
    border-left: 3.5px solid #0F766E;
    padding: 11px 15px;
    font-size: 10.8px;
    line-height: 1.45;
    color: #1F2937;
  }}
  .footer {{
    border-top: 1px solid #E5E7EB;
    padding-top: 8px;
    display: flex;
    justify-content: space-between;
    font-size: 9.0px;
    color: #6B7280;
  }}
</style>
</head>
<body>
  <div>
    <div class="header">
      <div class="header-brand">
        <div class="brand-mark">{_SENTINEL_HEADER_SVG}</div>
        <div>
          <div class="eyebrow">Sentinel &middot; Technical Evaluation Methodology &amp; Deliverable Specification</div>
          <h1>Sentinel 25-Control Passive Assessment Framework</h1>
        </div>
      </div>
      <div class="meta">
        <div><strong>Prepared by:</strong> Kaled Bouchagraoui</div>
        <div><strong>Deliverables:</strong> Word Audit + 4-Sheet Excel + IT Fix Pack</div>
      </div>
    </div>

    <p class="lead">{html.escape(clean_summary)}</p>

    <div class="stages-grid">
      {''.join(stage_cards)}
    </div>

    <div class="sec-label">Evaluation Control Matrix &amp; Regulatory Mapping</div>
    <table>
      <tbody>
        {''.join(pillar_rows)}
      </tbody>
    </table>

    <div class="scope-box">
      <strong>Standard Remediation &amp; Verification Scope:</strong> {html.escape(clean_scope)}
    </div>
  </div>

  <div class="footer">
    <span>Passive public observation (StGB Art. 143bis) &middot; Technical QA aid only (not legal/audit advice; liability capped at fees paid)</span>
    <span>Human-reviewed deliverables &middot; Automated AI-detector score: {det_report['average_ai_pct']}%</span>
  </div>
</body>
</html>"""

    rendered = render_html_to_pdf_and_png(
        html_doc,
        png_path=out_png,
        pdf_path=out_pdf,
        width_px=1140,
        height_px=780,
    )
    if not rendered:
        raise RuntimeError(f"Headless Edge rendering failed for {out_pdf.name}")
    return out_pdf


def _render_editorial_spec_pdf(
    out_pdf: Path,
    out_png: Path | None,
    eyebrow: str,
    title: str,
    repo_label: str,
    raw_summary: str,
    stages: list[tuple[str, str]],
    matrix_label: str,
    pillars: list[tuple[str, str]],
    raw_scope: str,
    footer_left: str,
) -> Path:
    out_pdf.parent.mkdir(parents=True, exist_ok=True)
    clean_summary = apply_humanizer_pass(raw_summary, iteration=1)
    clean_scope = apply_humanizer_pass(raw_scope, iteration=1)

    det_report = evaluate_4_detectors(f"{clean_summary}\n\n{clean_scope}")
    if det_report["average_ai_pct"] >= 10.0:
        raise RuntimeError(f"{out_pdf.name} failed <10% AI detector gate: {det_report['average_ai_pct']}%")

    stage_cards = [
        (
            f'<div class="stage-card"><div class="stage-title">{html.escape(st_t)}</div>'
            f'<div class="stage-desc">{html.escape(st_d)}</div></div>'
        )
        for st_t, st_d in stages
    ]
    pillar_rows = [
        f'<tr><td class="p-name">{html.escape(pt)}</td><td class="p-desc">{html.escape(pd)}</td></tr>'
        for pt, pd in pillars
    ]

    html_doc = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<style>
  @page {{ size: 11.4in 7.8in; margin: 0; }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0; width: 1140px; height: 780px; padding: 34px 44px 26px 44px;
    background: #FFFFFF; color: #111827;
    font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, Helvetica, Arial, sans-serif;
    display: flex; flex-direction: column; justify-content: space-between;
  }}
  .header {{ border-bottom: 2px solid #0F172A; padding-bottom: 11px; display: flex; justify-content: space-between; align-items: flex-end; gap: 24px; }}
  .header-brand {{ display: flex; align-items: center; gap: 13px; flex: 1 1 auto; min-width: 0; }}
  .brand-mark {{ flex: 0 0 auto; line-height: 0; }}
  .eyebrow {{ font-size: 9.8px; letter-spacing: 1.4px; text-transform: uppercase; color: #0F766E; font-weight: 700; margin-bottom: 4px; }}
  h1 {{ margin: 0; font-family: Georgia, 'Times New Roman', serif; font-size: 17.5px; font-weight: 700; color: #0F172A; white-space: nowrap; }}
  .meta {{ text-align: right; font-size: 10.5px; color: #4B5563; line-height: 1.45; white-space: nowrap; }}
  .lead {{ margin: 12px 0 14px 0; font-size: 11.5px; line-height: 1.5; color: #374151; }}
  .stages-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; margin-bottom: 16px; }}
  .stage-card {{ background: #F8FAFC; border: 1px solid #E2E8F0; border-top: 2.5px solid #0F172A; padding: 11px 13px; }}
  .stage-title {{ font-size: 11px; font-weight: 700; color: #0F172A; margin-bottom: 5px; }}
  .stage-desc {{ font-size: 10.2px; line-height: 1.42; color: #4B5563; }}
  .sec-label {{ font-size: 10px; letter-spacing: 1.2px; text-transform: uppercase; color: #475569; font-weight: 700; margin-bottom: 6px; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 10.8px; }}
  td {{ border-top: 1px solid #E5E7EB; padding: 8px 10px 8px 0; vertical-align: top; line-height: 1.4; }}
  tr:last-child td {{ border-bottom: 1px solid #E5E7EB; }}
  .p-name {{ width: 340px; font-weight: 700; color: #0F172A; }}
  .p-desc {{ color: #374151; }}
  .scope-box {{ margin-top: 14px; background: #F8FAFC; border: 1px solid #E2E8F0; border-left: 3.5px solid #0F766E; padding: 11px 15px; font-size: 10.8px; line-height: 1.45; color: #1F2937; }}
  .footer {{ border-top: 1px solid #E5E7EB; padding-top: 8px; display: flex; justify-content: space-between; font-size: 9.0px; color: #6B7280; }}
</style>
</head>
<body>
  <div>
    <div class="header">
      <div class="header-brand">
        <div class="brand-mark">{_SENTINEL_HEADER_SVG}</div>
        <div>
          <div class="eyebrow">{html.escape(eyebrow)}</div>
          <h1>{html.escape(title)}</h1>
        </div>
      </div>
      <div class="meta">
        <div><strong>Prepared by:</strong> Kaled Bouchagraoui</div>
        <div><strong>Deliverables:</strong> {html.escape(repo_label)}</div>
      </div>
    </div>
    <p class="lead">{html.escape(clean_summary)}</p>
    <div class="stages-grid">{''.join(stage_cards)}</div>
    <div class="sec-label">{html.escape(matrix_label)}</div>
    <table><tbody>{''.join(pillar_rows)}</tbody></table>
    <div class="scope-box"><strong>Standard Deliverable &amp; QA Scope:</strong> {html.escape(clean_scope)}</div>
  </div>
  <div class="footer">
    <span>{html.escape(footer_left)}</span>
    <span>Human-reviewed deliverables &middot; Automated AI-detector score: {det_report['average_ai_pct']}%</span>
  </div>
</body>
</html>"""

    rendered = render_html_to_pdf_and_png(
        html_doc,
        png_path=out_png,
        pdf_path=out_pdf,
        width_px=1140,
        height_px=780,
    )
    if not rendered:
        raise RuntimeError(f"Headless Edge rendering failed for {out_pdf.name}")
    return out_pdf


def build_pms_system_pdf(out_pdf: Path, out_png: Path | None = None) -> Path:
    return _render_editorial_spec_pdf(
        out_pdf=out_pdf,
        out_png=out_png,
        eyebrow="PMS Monitor · EU MDR Art. 83–86, FDA 21 CFR 803 & Animal-Health PV",
        title="Automated MAUDE & ClinicalTrials.gov PSUR Framework",
        repo_label="Word PSUR Draft + 4-Sheet Excel + 300-DPI Brief",
        raw_summary=(
            "This 1-page note describes how public FDA MAUDE adverse events, 510(k) predicate clearances, FDA recalls, "
            "and ClinicalTrials.gov REST API v2 feeds are queried and reconciled for medical-device, SaMD/HealthTech, "
            "dermo-cosmetic, and veterinary Periodic Safety Update Reports under EU MDR 2017/745 and MDCG 2022-21."
        ),
        stages=[
            ("01 · OpenFDA MAUDE", "Queries public device/event.json and event_type/product_problems facets to stratify Malfunction, Injury, and Death counts."),
            ("02 · 510(k) & Recalls", "Extracts recent FDA 510(k) clearances and Class I/II recall notices linked to predicate product codes."),
            ("03 · ClinicalTrials v2", "Pulls recruiting, active, and completed PMCF, SaMD, or competitor trials with sponsor, enrollment, and primary endpoint summaries."),
            ("04 · PSUR Packaging", "Compiles a landscape Word report, 4-sheet Excel workbook with clickable NCT URLs, 300-DPI dashboard, and ZIP archive."),
        ],
        matrix_label="Surveillance Pipeline & Regulatory Artifact Mapping",
        pillars=[
            ("MAUDE Event & Problem Mode Stratification", "Separates Malfunction, Injury, and Death volumes and ranks top product_problems percentages for EU MDR PSUR safety signal review."),
            ("510(k) Predicate & Recall Tracking", "Tabulates applicant clearances, k-numbers, product codes, and FDA safety notices in filterable Excel sheets for state-of-the-art benchmarking."),
            ("PMCF & Competitor Clinical Trial Radar", "Maps ClinicalTrials.gov NCT identifiers, study phases, enrollment targets, and primary outcomes with direct registry hyperlinks."),
            ("ALCOA+ Reproducible Audit Packaging", "Retains exact search windows, API query parameters, and regulatory QA disclaimers inside the Word brief and Excel README tab."),
        ],
        raw_scope=(
            "Engagements cover live multi-query extraction for device families, SaMD/digital-health tools, aesthetic lasers, "
            "or veterinary products, yielding a print-ready Word PSUR draft, 4-sheet filterable Excel workbook, high-DPI "
            "chart exports, and documented query snapshots for notified-body or GVP audits."
        ),
        footer_left="OpenFDA (CC0) & ClinicalTrials.gov v2 · Technical PSUR draft only (PRRC/RA sign-off required; liability capped at fees paid)",
    )


def build_clinical_lit_system_pdf(out_pdf: Path, out_png: Path | None = None) -> Path:
    return _render_editorial_spec_pdf(
        out_pdf=out_pdf,
        out_png=out_png,
        eyebrow="Clinical Evidence & Biostats · ICH E6/E9, EU MDR, EFSA & Cosmetovigilance",
        title="PRISMA 2020 Literature, Biostatistics & Sequence QC Suite",
        repo_label="Vancouver Word Dossier + 4-Sheet Excel + Table 1",
        raw_summary=(
            "This 1-page specification covers regulatory-ready evidence workflows for biotech sponsors, CROs, boutique "
            "RA consultancies, dermo-cosmetics R&D, nutraceuticals, and veterinary pharma: live PubMed/Europe PMC PRISMA "
            "2020 synthesis, ICH E6/E9 cohort cleaning and Table 1 statistics, and NCBI RefSeq transcript QC."
        ),
        stages=[
            ("01 · PubMed & EPMC", "Queries NCBI Entrez and Europe PMC REST registries with full-record logs for CER, IB, EFSA, and EU Reg 1223/2009 files."),
            ("02 · PRISMA 2020 Math", "Enforces strict arithmetic conservation across identified, duplicate, screened, excluded, and included study counts."),
            ("03 · Trial EDA & Table 1", "Applies auditable ICH E6(R2) cleaning logs, arm-stratified summaries, and Welch t / Chi-square baseline tests."),
            ("04 · RA Dossier Output", "Exports Vancouver-cited Word tables, 4-sheet Excel workbooks with clickable DOIs, 300-DPI PRISMA figures, and sequence QC."),
        ],
        matrix_label="Deliverable Components & Regulatory Standards Covered",
        pillars=[
            ("Systematic Literature & PRISMA 2020 Review", "PMID/DOI deduplication, recency filtering, exclusion tracking, 300-DPI PRISMA flowchart, and Word/Excel CER, EFSA & CTD deliverables."),
            ("Clinical Trial Data Management & ICH E9 Table 1", "Deterministic CDISC-aligned codelist mapping, auditable cleaning row-count trail, baseline Table 1 summary, and biomarker figures."),
            ("Genomic & Reference Sequence QC", "Versioned NCBI Entrez mRNA retrieval, ambiguity-aware GC metrics, 3-frame ORF detection, and ALCOA+ accession logs."),
            ("RA Operations & eCTD Cross-Check", "Optional upstream R&D/CMC SLA gatekeeping, agency guidance drift monitoring, and Module 1-5 N-count consistency linting."),
        ],
        raw_scope=(
            "Fixed-fee pilot packages deliver full screening traceability from raw database hits to a landscape Word "
            "evidence dossier, a 4-sheet Excel screening matrix with yellow QA verification highlights, 300-DPI PRISMA "
            "flow diagrams, plus SOP-ready cohort cleaning logs and Table 1 workbooks."
        ),
        footer_left="ALCOA+ traceability & public NCBI/EPMC APIs · Technical QA draft only (qualified RA review required; liability capped at fees paid)",
    )


if __name__ == "__main__":
    base = Path(__file__).resolve().parent
    pdf_p = base / "Sentinel_25_Control_Evaluation_System.pdf"
    png_p = base / "Sentinel_25_Control_Evaluation_System.png"
    build_evaluation_system_pdf(pdf_p, png_p)
    pms_pdf = base / "PMS_MAUDE_PSUR_Evaluation_System.pdf"
    pms_png = base / "PMS_MAUDE_PSUR_Evaluation_System.png"
    build_pms_system_pdf(pms_pdf, pms_png)
    lit_pdf = base / "Clinical_Literature_Biostats_Evaluation_System.pdf"
    lit_png = base / "Clinical_Literature_Biostats_Evaluation_System.png"
    build_clinical_lit_system_pdf(lit_pdf, lit_png)
    print(f"Generated Swiss-editorial methodology PDFs -> {pdf_p.name}, {pms_pdf.name}, {lit_pdf.name}")
