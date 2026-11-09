#!/usr/bin/env python3
"""Generate a synthetic Unified MedTech & CRO Compliance Dossier in examples/ for public repository showcase."""

from pathlib import Path
from medtech_suite import build_unified_medtech_dossier


def main() -> None:
    repo_dir = Path(__file__).resolve().parent
    examples_dir = repo_dir / "examples"
    examples_dir.mkdir(parents=True, exist_ok=True)

    synthetic_audit = {
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

    res = build_unified_medtech_dossier(
        target_domain="healthtech-demo.ch",
        records_csv=repo_dir / "records.csv",
        config_json=repo_dir / "config.json",
        base_out=examples_dir,
        offline_audit_override=synthetic_audit,
    )
    print(f"Generated unified demo dossier -> {res['zip_path']}")


if __name__ == "__main__":
    main()
