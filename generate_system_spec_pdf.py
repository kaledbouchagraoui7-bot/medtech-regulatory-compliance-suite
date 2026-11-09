#!/usr/bin/env python3
"""
generate_system_spec_pdf.py — Generates the 1-page visual technical specification PDF
(`Sentinel_25_Control_Evaluation_System.pdf`) documenting the passive 25-control
evaluation engine attached alongside each prospect's domain scorecard.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch


def build_evaluation_system_pdf(out_pdf: Path, out_png: Path | None = None) -> Path:
    out_pdf.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(11.0, 8.5), dpi=300)
    fig.patch.set_facecolor("#FFFFFF")
    ax.set_facecolor("#FFFFFF")
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis("off")

    # Header Banner
    banner = FancyBboxPatch(
        (2, 86), 96, 11.5,
        boxstyle="round,pad=0.6,rounding_size=1.2",
        facecolor="#0F172A", edgecolor="#1E293B", linewidth=1.5,
    )
    ax.add_patch(banner)
    ax.text(
        4.5, 93.8,
        "SENTINEL 25-CONTROL PASSIVE EVALUATION SYSTEM — TECHNICAL ARCHITECTURE",
        fontsize=12.5, fontweight="bold", color="#FFFFFF", family="sans-serif",
    )
    ax.text(
        4.5, 90.2,
        "100% Non-Intrusive External OSINT & Regulatory Compliance Engine (DNS-over-HTTPS + TLS + HTTP Header + DOM Inspection)",
        fontsize=8.6, color="#94A3B8", family="sans-serif",
    )
    ax.text(
        4.5, 87.3,
        "Open-Source Code & Methodology: https://github.com/kaledbouchagraoui7-bot/medtech-regulatory-compliance-suite  |  Author: Kaled Bouchagraoui",
        fontsize=8.0, color="#38BDF8", fontweight="bold", family="sans-serif",
    )

    # 4-Step Pipeline Architecture Row
    steps = [
        ("STAGE 1: PASSIVE COLLECTORS", "#EFF6FF", "#1D4ED8",
         "• Cloudflare/Google DoH (TXT/MX/CAA)\n• TLS 1.2/1.3 X.509 Handshake Check\n• Single Standard HTTPS GET Request\n• Zero port-scanning or active probing"),
        ("STAGE 2: 25-CONTROL ENGINE", "#F0FDF4", "#15803D",
         "• Weighted 100-Point Scoring Matrix\n• 5 Regulatory & Security Pillars\n• Automated Evidence Extraction\n• False-Positive Header Normalization"),
        ("STAGE 3: CLINICAL & PMS ADD-ON", "#FEF3C7", "#B45309",
         "• PRISMA 2020 Literature Synthesizer\n• OpenFDA MAUDE + ClinicalTrials.gov\n• EU MDR Annex XIV / CER / PSUR Tables\n• Mathematical Conservation Checks"),
        ("STAGE 4: TURNKEY DELIVERABLES", "#F5F3FF", "#6D28D9",
         "• 300-DPI Visual Scorecard (PNG/PDF)\n• Landscape Executive Audit (.docx)\n• 4-Sheet Filterable Matrix (.xlsx)\n• Drop-in Nginx/Cloudflare/DNS Configs"),
    ]
    x_positions = [2, 26.5, 51, 75.5]
    for (title, bg, fg, desc), x0 in zip(steps, x_positions):
        box = FancyBboxPatch(
            (x0, 68.5), 22.5, 15.0,
            boxstyle="round,pad=0.4,rounding_size=1.0",
            facecolor=bg, edgecolor=fg, linewidth=1.2,
        )
        ax.add_patch(box)
        ax.text(x0 + 1.2, 81.2, title, fontsize=8.0, fontweight="bold", color=fg)
        ax.text(x0 + 1.2, 70.0, desc, fontsize=7.2, color="#1E293B", linespacing=1.38, verticalalignment="bottom")

    # 5 Pillars Matrix Section Title
    ax.text(
        2.5, 64.8,
        "COMPLETE 25-CONTROL EVALUATION MATRIX & INTERNATIONAL REGULATORY MAPPING",
        fontsize=10.0, fontweight="bold", color="#0F172A",
    )

    pillars = [
        (
            "Pillar 1: Email Anti-Spoofing & Deliverability (Weight: 26 pts)",
            "#1E3A8A",
            [
                "EML-01 (12 pt): DMARC Record & Enforcement Policy (p=quarantine / p=reject vs missing or p=none) — RFC 7489 / Gmail & Yahoo Bulk Sender Rule",
                "EML-02 (8 pt):  SPF (Sender Policy Framework) Syntax & Lookup Ceiling (<=10 lookups, -all / ~all) — RFC 7208",
                "EML-03 (3 pt):  Inbound Mail Exchange (MX) Redundancy & Routing Integrity — RFC 5321",
                "EML-04 (3 pt):  DNS CAA (Certificate Authority Authorization) Restriction — RFC 8659",
            ],
        ),
        (
            "Pillar 2: Web Privacy, Cross-Border Data & Consent Hygiene (Weight: 25 pts)",
            "#0F766E",
            [
                "PRV-01 (8 pt):  Remote Google Fonts IP Leak Detection (fonts.googleapis.com / fonts.gstatic.com pre-consent transfer) — GDPR Art. 44 / Swiss nFADP",
                "PRV-02 (7 pt):  Initial HTML Third-Party Advertising & Behavioral Tracker Inspection (GTM, GA, Meta, Hotjar, HubSpot) — ePrivacy / UK GDPR / CCPA",
                "PRV-03 (5 pt):  Pre-Consent Cookie Hygiene & Security Flags (Secure, HttpOnly, SameSite attributes on initial response) — OWASP / GDPR Art. 25",
                "PRV-04 (5 pt):  Discoverable Privacy Notice / Data Protection Policy Link on Landing Page — GDPR Art. 13 / Swiss nFADP Art. 19 / HIPAA",
            ],
        ),
        (
            "Pillar 3: Edge, Transport & Application Hardening (Weight: 27 pts)",
            "#991B1B",
            [
                "SEC-01 (8 pt):  TLS 1.2/1.3 Encryption Protocol & X.509 Certificate Validity Horizon — OWASP Transport Layer Protection / EU MDR GSPR 17.2",
                "SEC-02 (7 pt):  HTTP Strict-Transport-Security (HSTS max-age >= 15768000) — RFC 6797  |  SEC-03 (7 pt): Content-Security-Policy (CSP XSS Defense)",
                "SEC-04 (5 pt):  Clickjacking Protection (X-Frame-Options / frame-ancestors)  |  SEC-05 (4 pt): MIME-Sniffing Lock (X-Content-Type-Options: nosniff)",
                "SEC-06..09:     Referrer-Policy, Permissions-Policy (Camera/Mic/Geo Lockdown), Server Version Suppression & RFC 9116 /.well-known/security.txt",
            ],
        ),
        (
            "Pillar 4: Accessibility (WCAG 2.1 AA / EAA / ADA) & Pillar 5: Technical Discoverability (Weight: 22 pts)",
            "#4338CA",
            [
                "ACC-01..04:     HTML <html lang> declaration, Image alt-text coverage (>=90%), Form input <label>/aria-label binding, and Viewport zoom-lock check",
                "SEO-01..04:     robots.txt availability, XML Sitemap declaration, Canonical URL normalization, and JSON-LD Schema.org structured metadata",
            ],
        ),
    ]

    y_top = 62.5
    for p_title, p_color, bullets in pillars:
        h = 3.2 + len(bullets) * 2.55
        y_bottom = y_top - h
        p_box = FancyBboxPatch(
            (2, y_bottom), 96, h - 0.5,
            boxstyle="round,pad=0.3,rounding_size=0.8",
            facecolor="#F8FAFC", edgecolor="#CBD5E1", linewidth=1.0,
        )
        ax.add_patch(p_box)
        ax.text(3.2, y_top - 2.3, p_title, fontsize=8.3, fontweight="bold", color=p_color)
        cy = y_top - 4.7
        for b in bullets:
            ax.text(3.8, cy, f"• {b}", fontsize=7.15, color="#1E293B", family="sans-serif")
            cy -= 2.45
        y_top = y_bottom - 0.8

    # Footer Box: Standard Fixed-Fee B2B Remediation Package
    footer = FancyBboxPatch(
        (2, 2.2), 96, 8.2,
        boxstyle="round,pad=0.4,rounding_size=0.9",
        facecolor="#F1F5F9", edgecolor="#64748B", linewidth=1.1,
    )
    ax.add_patch(footer)
    ax.text(
        3.5, 8.1,
        "TURNKEY REMEDIATION & VERIFICATION DELIVERABLES (FIXED B2B FEE: EUR 350 / USD 380 / GBP 300 / CHF 350)",
        fontsize=8.4, fontweight="bold", color="#0F172A",
    )
    ax.text(
        3.5, 5.4,
        "1. Full Landscape Executive Word Audit (.docx) & 4-Sheet Filterable Technical Matrix (.xlsx) mapped to every failing and warning control.\n"
        "2. Ready-to-deploy DNS TXT records (DMARC/SPF/CAA), Nginx/Apache/Cloudflare HTTP security header snippets, and local webfont privacy fixes.\n"
        "3. Post-deployment re-verification scan & updated 300-DPI compliance certificate once your IT/web team applies the snippets.",
        fontsize=7.2, color="#334155", linespacing=1.35, verticalalignment="center",
    )

    fig.savefig(str(out_pdf), format="pdf", dpi=300, bbox_inches="tight")
    if out_png:
        fig.savefig(str(out_png), format="png", dpi=300, bbox_inches="tight")
    plt.close(fig)
    return out_pdf


if __name__ == "__main__":
    dest = Path(r"C:\Users\KALED.BOUCHAGRAOUI\.gemini\antigravity\scratch\medtech-regulatory-compliance-suite\Sentinel_25_Control_Evaluation_System.pdf")
    build_evaluation_system_pdf(dest, dest.with_suffix(".png"))
    print(f"Generated: {dest}")
