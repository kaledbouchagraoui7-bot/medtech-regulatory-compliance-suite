#!/usr/bin/env python3
"""
outreach_qa_dispatcher.py — Personalized 120–150 Word B2B Email Generator,
Single-Pass High-Impact Humanizer, Professionalism Verifier & Multi-Attachment Dispatcher
=========================================================================================

Key Capabilities
----------------
1. Tailored 120–150 Word B2B Emails:
   - Strictly enforces 120 to 150 words (`120 <= word_count <= 150`).
   - Integrates site-specific context, public customer-review insights, and concrete problem-solving
     mapped to the exact failing controls in `*_raw_evidence.json`.
   - Includes transparent fixed B2B pricing (EUR 350 / USD 380 / GBP 300 / CHF 350 / AUD 550 / CAD 520)
     and strictly forbids "for free" / "kostenlos" / "gratuitement".
   - Attaches BOTH the domain's 300-DPI visual scorecard (`<domain>_scorecard.png`) AND the
     1-page technical specification of the evaluation system (`Sentinel_25_Control_Evaluation_System.pdf`).
2. Single-Pass High-Impact Humanizer (`max_passes=1` by default):
   - Runs once to strip only high-impact stiff AI clichés, robotic transitions, and em-dash overload
     while preserving natural, warm human cadence.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import email.utils
import json
import math
import os
import random
import re
import smtplib
import statistics
import sys
import time
from email.message import EmailMessage
from pathlib import Path
from typing import Any

import requests

SYSTEM_SPEC_PDF_DEFAULT = (
    Path(__file__).resolve().parent / "Sentinel_25_Control_Evaluation_System.pdf"
)

# ---------------------------------------------------------------------------
# 1. High-Impact AI Clichés & Unprofessional / "Free" Blacklist
# ---------------------------------------------------------------------------

AI_CLICHE_PATTERNS: list[tuple[str, float]] = [
    (r"\bin today'?s (?:rapidly evolving|fast-paced|digital|modern) (?:landscape|world|era)\b", 22.0),
    (r"\bi hope this email finds you (?:well|in good spirits)\b", 22.0),
    (r"\bi am writing to (?:express|reach out|share)\b", 14.0),
    (r"\b(?:delighted|thrilled|excited) to (?:share|introduce|offer|present)\b", 16.0),
    (r"\b(?:leverage|utilize|harness|revolutionize|streamline|synergy|paradigm|holistic)\b", 15.0),
    (r"\b(?:cutting-edge|state-of-the-art|game-changing|seamless|paramount)\b", 13.0),
    (r"\b(?:furthermore|moreover|additionally|consequently|nevertheless)\b", 11.0),
    (r"\bit is (?:worth noting|important to highlight|crucial to recognize) that\b", 18.0),
    (r"\b(?:delve|testament|tapestry|underscore|pivotal)\b", 18.0),
    (r"\bplease do not hesitate to\b", 14.0),
    (r"\bin der heutigen (?:digitalen|schnelllebigen) welt\b", 20.0),
    (r"\bich hoffe, diese e-mail erreicht sie wohlbehalten\b", 22.0),
    (r"\bdarüber hinaus\b", 11.0),
    (r"\b(?:nahtlos|ganzheitlich|revolutionieren)\b", 13.0),
    (r"\bzögern sie nicht, mich zu kontaktieren\b", 14.0),
    (r"\bdans un monde en constante évolution\b", 20.0),
    (r"\bj'espère que ce message vous trouve\b", 22.0),
    (r"\b(?:par ailleurs|de plus|en outre|néanmoins)\b", 10.0),
    (r"\b(?:holistique|révolutionner|synergie)\b", 14.0),
    (r"\bn'hésitez pas à me contacter\b", 12.0),
]

SALES_SPAM_PATTERNS: list[tuple[str, float]] = [
    (r"\b(?:15|30)-minute (?:discovery |intro )?call\b", 25.0),
    (r"\b(?:hop on a|jump on a|schedule a quick) call\b", 22.0),
    (r"\bguaranteed?\b", 18.0),
    (r"\b100% accurate\b", 20.0),
    (r"\bact now\b|\blimited time\b|\burgent warning\b", 22.0),
    (r"\b(?:kurzes|15-minütiges) erstgespräch\b", 22.0),
    (r"\bappel de découverte\b|\brapidement au téléphone\b", 22.0),
]

BANNED_UNPROFESSIONAL_TERMS = [
    "for free",
    "free of charge",
    "kostenlos",
    "gratis",
    "gratuitement",
    "à titre gratuit",
    "guarantee",
    "guaranteed",
    "garanti",
    "garantiert",
    "100% compliant",
    "act now",
    "!!!",
    "free money",
    "github.com",
    "source code",
    "remediation snippets",
    "config snippets",
    "screening scripts",
    "python scripts",
    "code repository",
]

PRICE_REGEX = re.compile(
    r"(?:\b(?:CHF|EUR|USD|GBP|AUD|CAD|SGD)\s?\d{2,4}\b|\b\d{2,4}\s?(?:CHF|EUR|USD|GBP|AUD|CAD|SGD|€|\$|£)\b|[€\$£]\s?\d{2,4}\b)",
    re.I,
)

# High-impact single-pass humanizer replacements
HIGH_IMPACT_HUMANIZER_REPLACEMENTS: list[tuple[str, str]] = [
    (r"(?i)I hope this email finds you well[\.,]?\s*", ""),
    (r"(?i)J'espère que ce message vous trouve en bonne santé[\.,]?\s*", ""),
    (r"(?i)Ich hoffe, diese E-Mail erreicht Sie wohlbehalten[\.,]?\s*", ""),
    (r"(?i)\bin today'?s (?:rapidly evolving|fast-paced|digital|modern) (?:landscape|world|era),?\s*", ""),
    (r"(?i),?\s*with source code on GitHub at [a-zA-Z0-9._/-]+", ""),
    (r"(?i)\s*(?:source code|repo(?:sitory)?|scripts?) (?:at|on) https?://github\.com/\S+", ""),
    (r"(?i)\bconfig snippets\b", "IT fix files"),
    (r"(?i)\bremediation snippets\b", "turnkey IT fix files"),
    (r"(?i)\b(?:screening|python) scripts\b", "automated review workflows"),
    (r"(?i)\bdelighted to\b", "happy to"),
    (r"(?i)\bthrilled to\b", "glad to"),
    (r"(?i)\bleverage\b", "use"),
    (r"(?i)\butilize\b", "use"),
    (r"(?i)\bstreamline\b", "simplify"),
    (r"(?i)\bcutting-edge\b", "automated"),
    (r"(?i)\bseamlessly\b", "smoothly"),
    (r"(?i)\bparamount\b", "essential"),
    (r"(?i)\bFurthermore,\s*", "Also, "),
    (r"(?i)\bMoreover,\s*", "Also, "),
    (r"(?i)\bAdditionally,\s*", "Also, "),
    (r"(?i)\bPlease do not hesitate to reach out\.?", "Let me know if that helps."),
    (r"(?i)\bschedule a brief \d+-minute (?:discovery )?call\b", "reply to this email"),
    (r"(?i)\bhop on a quick call\b", "reply here"),
    (r"(?i)\bDarüber hinaus\s+", "Zudem "),
    (r"(?i)\bPar ailleurs,\s*", "Aussi, "),
    (r"(?i)\bDe plus,\s*", "Aussi, "),
    (r"(?i)\bin order to\b", "to"),
    (r"(?i)\bdue to the fact that\b", "because"),
]

# ---------------------------------------------------------------------------
# 1B. Shared Target ICP Compliance Filter (Core + Expanded High-Stakes B2B)
# ---------------------------------------------------------------------------

TARGET_ICP_SECTORS = {
    "MedTech OEM",
    "MedTech RA",
    "Boutique RA",
    "Diagnostics",
    "Clinical Genomics",
    "Biotech / CRO",
    "Dermo-Cosmetics",
    "Nutraceuticals",
    "Veterinary Pharma",
    "CDMO / Pharma",
    "HealthTech",
    "Wealth & Family Office",
    "Legal/IP",
    "Accounting/Tax",
    "B2B SaaS",
    "InsurTech",
    # Legacy normalized manifest slugs
    "medtech_cer",
    "cro_reg",
    "diagnostics_lab",
    "cpa_fiduciary",
    "law_ip",
    "wealth_office",
    "healthtech",
    "b2b_saas",
}

_NON_ICP_TLD_RE = re.compile(
    r"(?:^|\.)(?:edu|gov|mil)(?:\.[a-z]{2,})?$|(?:^|\.)(?:gouv|ac)\.[a-z]{2,}$",
    re.I,
)

_NON_ICP_EXACT_DOMAINS = (
    "nhs.uk", "gov.uk", "nih.gov", "who.int", "europa.eu", "has-sante.fr", "sante.fr",
    "ey.com", "ge.com", "bd.com", "ppd.com", "ppdi.com", "jnj.com", "bms.com",
    "lilly.com", "edwards.com", "otandp.com", "matilda.org", "shcd.in",
    "bioclinic.fr", "santelabs.com", "santeclinics.com", "fiducial.fr", "labone.in",
)

_NON_ICP_DOMAINS = (
    "univ", "ufr", "unistra", "facult",
    "plannedparenthood.", "docasap.", "doctolib.", "zocdoc.",
    "sega.", "nintendo.", "sony.", "kpmg.", "pwc.", "deloitte.",
    "bdo.", "grantthornton.", "gtjapan.", "mazars.", "fiducial.",
    "pfizer.", "roche.", "novartis.", "sanofi.", "astrazeneca.", "gsk.", "bayer.", "merck.",
    "thermo", "illumina.", "siemens", "philips", "gehealthcare", "medtronic", "abbott",
    "bostonscientific", "stryker", "jjmedtech", "amgen", "gilead", "biogen", "regeneron",
    "takeda", "boehringer", "olympus", "baxter", "fresenius", "resmed", "alcon", "hologic",
    "intuitive", "mindray", "canon", "fujifilm", "hitachi", "toshiba", "samsung",
    "thermofisher", "agilent", "perkinelmer", "beckman", "danaher", "bio-rad", "iqvia",
    "labcorp", "iconplc", "syneos", "parexel", "charlesriver", "wuxi", "steris.",
    "smith-nephew.", "coloplast.", "dentsplysirona.", "viatris.", "mylan.",
    "actelion.", "ipsen.", "servier.", "loreal.", "galderma.", "beiersdorf.",
    "shiseido.", "esteelauder.", "unilever.", "nestle.", "danone.", "zoetis.", "elanco.",
    # Local consumer healthcare / physio / dental / walk-in scan / activist domains
    "dentist", "dentistry", "dentalstudio", "smiledental", "physio",
    "chiropract", "osteopath", "mclinic", "maternity", "digestivecentre",
    "drandrew", "romeroinstitute", "otandp.", "londonmedical.", "ahdubai.",
    "rafflesmedical", "cmcdubai.", "abbeycare", "surgery.co.uk",
    "apollodiagnostics.", "henoticdiagnostics.", "arockiyaclinic.", "santelabs.", "santeclinics.",
    "national-accident",
)

_NON_ICP_NAME_RE = re.compile(
    r"\b(?:"
    r"university|universit[éeyä]|faculty|faculté|college|high school|elementary school|"
    r"hospital|hôpital|hopital|krankenhaus|spital|ospedale|nhs|ministry|municipality|"
    r"charity|foundation|church|parish|synagogue|mosque|museum|planned parenthood|free clinic|"
    r"dentist|dentistry|dental practice|dental studio|dental clinic|dental care|dental centre|dental center|"
    r"dental\s+(?:llc|pc|dds|dmd|pllc|pa|associates|arts|group|house)|family dental|smiles?\s+dental|"
    r"perio centre|orthodontic practice|physiotherapy|physio|chiropractic|chiropractor|"
    r"osteopath|osteopathy|podiatry|chiropody|optician|opticians|optometrist|maternity clinic|"
    r"fertility clinic|walk-in clinic|urgent care|gp surgery|health centre|medical centre|"
    r"medical center|digestive centre|vascular surgery|family practice|medspa|medical spa|"
    r"scans\s*[&+]\s*diagnostics|scans\s+and\s+diagnostics|clinic\s*[&+]\s*diagnostic|"
    r"clinic\s+and\s+diagnostic|speciality clinic|specialty clinic|diagnostic centre|diagnostic center|"
    r"imaging centre|imaging center|scan centre|scan center|pathology lab|medical clinic|"
    r"polyclinic|polyclinique|helpline|legal aid|christic|romero|"
    r"grant thornton|pricewaterhouse|ernst\s*[&+]\s*young|deloitte|kpmg|mazars|fiducial|"
    r"beauty salon|massage therapy|acupuncture clinic|veterinary clinic|animal hospital|pet clinic|"
    r"games|gaming|yearbook|tidsskrift"
    r")\b",
    re.I,
)

_NON_ICP_LEGAL_NONPROFIT_RE = re.compile(
    r"\b(?:institute|helpline|coalition|society|legal aid|christic|romero|union|federation|council)\b",
    re.I,
)

_B2B_HEALTH_POSITIVE_RE = re.compile(
    r"\b(?:healthtech|health tech|digital health|telehealth|eclinical|medtech|medical device|"
    r"regulatory|genomics|biotech|biopharma|pharma|therapeutics|cro|"
    r"clinical research|clinical trial|dermo-cosmetic|cosmeceutical|skincare lab|"
    r"nutraceutical|probiotic|microbiome|veterinary pharma|animal health|cdmo|life\s+sciences?)\b",
    re.I,
)


def is_target_icp_entity(company: str, domain: str, sector: str = "") -> tuple[bool, str]:
    """
    Validate strictly against the high-stakes B2B / Life Science Ideal Customer Profile (ICP).
    Rejects local consumer practices (dentists, physio, maternity/solo doctor/scan clinics),
    activist non-profits, schools/universities/governments, Big-4/megacorp chains, and Fortune-500 conglomerates.
    """
    dl = (domain or "").strip().lower()
    comp_clean = (company or "").strip()
    nl = " " + comp_clean.lower() + " "
    sec = (sector or "").strip()

    if not dl or "." not in dl or len(dl) < 4 or len(comp_clean) < 3:
        return False, "INVALID_DOMAIN_OR_NAME"
    if _NON_ICP_TLD_RE.search(dl):
        return False, f"BLOCKED_TLD:{dl}"
    for exact_dom in _NON_ICP_EXACT_DOMAINS:
        if dl == exact_dom or dl.endswith("." + exact_dom):
            return False, f"BLOCKED_EXACT_DOMAIN:{exact_dom}"
    for bad_dom in _NON_ICP_DOMAINS:
        if bad_dom in dl:
            return False, f"BLOCKED_DOMAIN:{bad_dom}"
    m_name = _NON_ICP_NAME_RE.search(nl)
    if m_name:
        return False, f"BLOCKED_NAME:{m_name.group(0).strip()}"
    if re.search(r"\bbdo\b", nl):
        return False, "BLOCKED_NAME:bdo"
    if sec == "Legal/IP":
        m_leg = _NON_ICP_LEGAL_NONPROFIT_RE.search(nl)
        if m_leg:
            return False, f"BLOCKED_LEGAL_NONPROFIT:{m_leg.group(0).strip()}"
    if sec in ("Healthcare", "clinic", ""):
        if not _B2B_HEALTH_POSITIVE_RE.search(comp_clean):
            return False, f"NON_ICP_GENERIC_HEALTHCARE:{sec or 'empty'}"
    elif sec not in TARGET_ICP_SECTORS:
        return False, f"UNAPPROVED_SECTOR:{sec}"
    return True, "OK"


# ---------------------------------------------------------------------------
# 2. Four Local Stylometric Detectors (+ Optional External APIs)
# ---------------------------------------------------------------------------

def split_sentences(text: str) -> list[str]:
    body_lines = [ln.strip() for ln in text.strip().splitlines() if ln.strip()]
    joined = " ".join(body_lines)
    protected = re.sub(r"([a-zA-Z0-9_-])\.([a-zA-Z]{2,})", r"\1<DOT>\2", joined)
    raw_parts = re.split(r"(?<=[.!?])\s+", protected)
    sentences = []
    for p in raw_parts:
        restored = p.replace("<DOT>", ".").strip()
        if len(restored.split()) >= 3:
            sentences.append(restored)
    return sentences


def detector_1_cliche_signatures(text: str) -> tuple[float, list[str]]:
    score = 0.0
    hits: list[str] = []
    for pat, weight in AI_CLICHE_PATTERNS:
        found = re.findall(pat, text, flags=re.I)
        if found:
            score += weight * min(len(found), 2)
            hits.append(f"cliche:{found[0]}")

    em_dashes = text.count("—") + text.count("--")
    if em_dashes > 2:
        score += (em_dashes - 2) * 8.0
        hits.append(f"excess_dashes:{em_dashes}")

    return min(100.0, round(score, 1)), hits


def detector_2_burstiness_cadence(text: str) -> tuple[float, list[str]]:
    sents = split_sentences(text)
    if len(sents) < 3:
        return 2.0, []

    lengths = [len(s.split()) for s in sents]
    mean_len = statistics.mean(lengths)
    stdev_len = statistics.pstdev(lengths)
    cv = stdev_len / max(mean_len, 1.0)

    score = 0.0
    hits: list[str] = []
    if mean_len > 26.0:
        score += min(35.0, (mean_len - 26.0) * 4.0)
        hits.append(f"long_mean_sent:{mean_len:.1f}w")
    if cv < 0.20 and len(sents) >= 4:
        score += min(35.0, (0.20 - cv) * 160.0)
        hits.append(f"low_burstiness_cv:{cv:.2f}")

    if len(lengths) >= 4 and max(lengths) - min(lengths) <= 3:
        score += 18.0
        hits.append("uniform_sentence_lengths")

    return min(100.0, round(score, 1)), hits


def detector_3_syntactic_formulaicity(text: str) -> tuple[float, list[str]]:
    words = re.findall(r"\b[a-zA-Zäöüàéèêîôûç]+\b", text.lower())
    n_words = max(len(words), 1)
    score = 0.0
    hits: list[str] = []

    abstract_suffixes = re.findall(r"\b\w+(?:tion|ment|ity|ness|keit|ung|schaft|ité|ement)\b", text.lower())
    abs_ratio = len(abstract_suffixes) / n_words
    if abs_ratio > 0.16:
        score += min(40.0, (abs_ratio - 0.16) * 280.0)
        hits.append(f"high_nominalization:{abs_ratio:.2f}")

    sents = split_sentences(text)
    if len(sents) >= 4:
        starters = [s.split()[0].lower() for s in sents]
        most_common_cnt = max(starters.count(st) for st in set(starters))
        if most_common_cnt >= max(3, int(math.ceil(len(sents) * 0.6))):
            score += 20.0
            hits.append("repetitive_sentence_starters")

    return min(100.0, round(score, 1)), hits


def detector_4_outreach_boilerplate(text: str) -> tuple[float, list[str]]:
    score = 0.0
    hits: list[str] = []
    for pat, weight in SALES_SPAM_PATTERNS:
        found = re.findall(pat, text, flags=re.I)
        if found:
            score += weight
            hits.append(f"spam_cta:{found[0]}")

    first_line = text.strip().splitlines()[0] if text.strip() else ""
    if re.search(r"^(?:Dear Sir/Madam|To Whom It May Concern|Sehr geehrte Damen und Herren|Madame, Monsieur,)", first_line, re.I):
        score += 14.0
        hits.append("generic_greeting")

    return min(100.0, round(score, 1)), hits


def query_optional_external_detectors(text: str) -> list[tuple[str, float]]:
    ext_scores: list[tuple[str, float]] = []
    gptzero_key = os.environ.get("GPTZERO_API_KEY", "").strip()
    if gptzero_key:
        try:
            r = requests.post(
                "https://api.gptzero.me/v2/predict/text",
                headers={"x-api-key": gptzero_key, "Content-Type": "application/json"},
                json={"document": text},
                timeout=10,
            )
            if r.status_code == 200:
                docs = r.json().get("documents", [])
                if docs and "completely_generated_prob" in docs[0]:
                    ext_scores.append(("GPTZero_API", round(float(docs[0]["completely_generated_prob"]) * 100.0, 1)))
        except Exception:
            pass
    return ext_scores


def evaluate_4_detectors(text: str) -> dict[str, Any]:
    d1, h1 = detector_1_cliche_signatures(text)
    d2, h2 = detector_2_burstiness_cadence(text)
    d3, h3 = detector_3_syntactic_formulaicity(text)
    d4, h4 = detector_4_outreach_boilerplate(text)

    scores: dict[str, float] = {
        "D1_Cliche_Signatures": d1,
        "D2_Burstiness_Cadence": d2,
        "D3_Syntactic_Formulaicity": d3,
        "D4_Outreach_Boilerplate": d4,
    }
    for k, v in query_optional_external_detectors(text):
        scores[k] = v

    avg_score = round(sum(scores.values()) / len(scores), 2)
    return {
        "average_ai_pct": avg_score,
        "scores": scores,
        "flags": h1 + h2 + h3 + h4,
    }


# ---------------------------------------------------------------------------
# 3. Strict 120–150 Word Professionalism Gate & Single-Pass Humanizer
# ---------------------------------------------------------------------------

def count_words(text: str) -> int:
    return len(text.split())


def verify_professionalism(
    subject: str,
    body: str,
    to_email: str,
    required_domain: str | None = None,
    min_words: int = 120,
    max_words: int = 150,
    require_price: bool = True,
) -> tuple[bool, list[str]]:
    """Enforce strict 120–150 word count, real B2B pricing, zero 'for free', domain alignment, and opt-out."""
    issues: list[str] = []
    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", to_email.strip()):
        issues.append(f"Invalid recipient email: '{to_email}'")
    if len(subject.strip()) < 8 or len(subject.strip()) > 115:
        issues.append("Subject must be between 8 and 115 characters.")

    wc = count_words(body)
    if wc < min_words:
        issues.append(f"Body below {min_words}-word minimum ({wc} words).")
    if wc > max_words:
        issues.append(f"Body exceeds {max_words}-word maximum ({wc} words).")

    lower_body = body.lower()
    lower_all = f"{subject}\n{body}".lower()
    for banned in BANNED_UNPROFESSIONAL_TERMS:
        if re.search(rf"\b{re.escape(banned)}\b", lower_all) if banned.isalpha() else (banned in lower_all):
            issues.append(f"Banned phrase, code/repo link, or 'free' offer detected: '{banned}'")

    if require_price and not PRICE_REGEX.search(body):
        issues.append("Missing explicit price (e.g., EUR 350, $380, £300, 350 CHF).")

    if required_domain and required_domain.lower() not in lower_body and required_domain.lower() not in subject.lower():
        issues.append(f"Target domain '{required_domain}' missing from briefing text.")

    has_opt_out = bool(re.search(
        r"(kein interesse|kein bedarf|nicht erneut|keine nachfragen|abmelden|nicht mehr|"
        r"pas pertinent|ne relancerai pas|ne pas|stop|not relevant|not a priority|opt out|no follow|won't follow up|will not follow up)",
        lower_body,
    ))
    if not has_opt_out:
        issues.append("Missing concise opt-out / no-follow-up courtesy line.")

    return len(issues) == 0, issues


def apply_humanizer_pass(text: str, iteration: int = 1, detector_flags: list[str] | None = None) -> str:
    """Single-pass high-impact humanizer removing only the stiffest AI phrases while keeping human warmth."""
    out = text
    for pat, repl in HIGH_IMPACT_HUMANIZER_REPLACEMENTS:
        out = re.sub(pat, repl, out)

    out = out.replace(" — ", ", ").replace("—", ", ")
    out = re.sub(r"[ \t]{2,}", " ", out)
    out = re.sub(r"\n{3,}", "\n\n", out)
    return out.strip()


def calibrate_word_count(body: str, lang: str = "en", min_words: int = 120, max_words: int = 150) -> str:
    """
    Fine-tune word count after single-pass humanization so the final email lands strictly
    inside [min_words, max_words] (120–150 words) without cutting sentences abruptly.
    """
    wc = count_words(body)
    if min_words <= wc <= max_words:
        return body

    # If slightly under 120 words, insert a natural methodology/deliverable detail before the closing opt-out
    if wc < min_words:
        needed = min_words - wc
        if lang == "de":
            addons = [
                (8, "Alle Prüfungen erfolgten rein passiv über öffentliche DNS- und HTTPS-Header."),
                (15, "Alle Prüfungen erfolgten rein passiv über öffentliche DNS- und HTTPS-Header ohne aktives Scannen Ihrer Systeme."),
                (23, "Alle Prüfungen erfolgten rein passiv über öffentliche DNS- und HTTPS-Header ohne aktives Scannen Ihrer Infrastruktur, einschliesslich einer erneuten Abschlussprüfung nach der Umsetzung."),
            ]
        elif lang == "fr":
            addons = [
                (9, "Chaque vérification repose uniquement sur vos en-têtes DNS et HTTPS publics."),
                (16, "Chaque vérification repose uniquement sur vos en-têtes DNS et HTTPS publics, sans aucun scan intrusif."),
                (24, "Chaque vérification repose uniquement sur vos en-têtes DNS et HTTPS publics, sans aucun scan intrusif, avec une contre-visite de validation incluse après déploiement."),
            ]
        else:
            addons = [
                (8, "Every check uses strictly passive public DNS and HTTPS headers."),
                (15, "Every check uses strictly passive public DNS and HTTPS headers with zero intrusive traffic."),
                (23, "Every check uses strictly passive public DNS and HTTPS headers with zero intrusive traffic, and includes a post-deployment verification re-scan."),
                (31, "Every check uses strictly passive public DNS and HTTPS headers with zero intrusive traffic, and the fixed fee includes a post-deployment verification re-scan once your team applies the changes."),
            ]
        best_addon = addons[-1][1]
        for _, cand_text in addons:
            if min_words <= wc + count_words(cand_text) <= max_words:
                best_addon = cand_text
                break
        paragraphs = body.split("\n\n")
        if len(paragraphs) >= 2:
            paragraphs[-2] = paragraphs[-2].rstrip() + " " + best_addon
            body = "\n\n".join(paragraphs)
        else:
            body = body + " " + best_addon

    # If slightly over 150 words, tighten non-essential modifiers first while keeping preview refs and question
    wc = count_words(body)
    if wc > max_words:
        trim_map = [
            (" and includes a post-deployment verification re-scan once your team applies the changes", ""),
            (" and includes a post-deployment verification re-scan", ""),
            (" with zero intrusive traffic", ""),
            (" (1-page risk preview and methodology guide attached)", " (1-page preview & guide attached)"),
            (" (scorecard preview and guide attached)", " (preview & guide attached)"),
            (" (1-Seiten-Risikovorschau und System-Leitfaden im Anhang)", " (Risikovorschau & Leitfaden im Anhang)"),
            (" (aperçu visuel 1 page et guide méthodologique joints)", " (aperçu 1 page et guide joints)"),
            (" (aperçu visuel et guide joints)", " (aperçu et guide joints)"),
            ("Would you like me to send over the scope to get started?", "Shall I send the scope?"),
            ("Should I send over the scope to get started?", "Shall I send the scope?"),
            ("Soll ich Ihnen den Projektvorschlag zusenden?", "Soll ich das Angebot senden?"),
            ("Souhaitez-vous mettre cela en place cette semaine ?", "Puis-je envoyer l'offre ?"),
            ("Puis-je envoyer le périmètre détaillé ?", "Puis-je envoyer l'offre ?"),
            ("the full Word executive audit, 4-sheet Excel risk register, ", "the Word/Excel audit dossier, "),
            ("the Word executive audit, 4-sheet Excel risk register, ", "the Word/Excel audit dossier, "),
            ("the full Word and 4-sheet Excel audit dossier, ", "the Word/Excel audit dossier, "),
            ("das vollständige Word- und 4-Blatt-Excel-Auditpaket, ", "das Word/Excel-Auditpaket, "),
            ("das vollständige Word- und Excel-Auditpaket, ", "das Word/Excel-Auditpaket, "),
            ("le rapport Word, le classeur Excel 4 onglets, ", "le dossier Word/Excel 4 onglets, "),
            ("le rapport Word, l'Excel 4 onglets, ", "le dossier Word/Excel 4 onglets, "),
            ("le rapport complet Word et Excel, ", "le dossier Word/Excel, "),
            ("prêts à appliquer ", ""),
            ("fertige IT-Korrekturdateien", "IT-Korrekturdateien"),
            ("turnkey IT fix files", "IT fix files"),
            ("et l'attestation re-vérifiée", "et l'attestation"),
            ("plus a re-verified attestation PDF", "plus attestation PDF"),
            ("and a re-verified attestation PDF", "plus attestation PDF"),
            (", plus a post-deployment verification scan", ""),
            (" sowie den Kontroll-Scan nach der Umsetzung", ""),
            (", ainsi que la contre-visite de validation", ""),
            ("Specifically, the scan flagged that ", "The scan found: "),
            ("Konkret fielen diese Punkte auf: ", "Befunde: "),
            ("L'analyse relève notamment : ", "Constats : "),
            ("If this is not a priority right now, simply reply 'no' and I will not follow up.", "If not relevant, reply 'no' and I won't follow up."),
            ("Si ce n'est pas pertinent, un simple « non » suffit et je ne relancerai pas.", "Un simple « non » suffit si ce n'est pas pertinent."),
            ("Falls kein Bedarf besteht, genügt ein kurzes «Nein», dann schreibe ich nicht erneut.", "Bei Nichtinteresse genügt ein kurzes «Nein», ohne Nachfassen."),
            ("against outbound email spoofing", "against spoofing"),
            ("before visitor consent", "before consent"),
            (" (monitoring only)", ""),
            ("ready-to-paste ", ""),
            ("copy-paste ", ""),
            ("complete ", ""),
            ("directly ", ""),
            ("publicly ", ""),
            ("currently ", ""),
            ("specifically ", ""),
            ("aktuell ", ""),
            ("direkt einfügbare ", ""),
            ("vollständige ", ""),
            ("prêts à déployer ", ""),
            ("notamment ", ""),
        ]
        for old_s, new_s in trim_map:
            if count_words(body) <= max_words:
                break
            if old_s in body:
                body = body.replace(old_s, new_s, 1)
                body = re.sub(r"[ \t]{2,}", " ", body)

    return body.strip()


def run_qa_humanizer_loop(
    subject: str,
    body: str,
    to_email: str,
    required_domain: str | None = None,
    threshold_pct: float = 15.0,
    max_passes: int = 1,
    lang: str = "en",
    min_words: int = 120,
    max_words: int = 150,
    require_price: bool = True,
) -> dict[str, Any]:
    """
    Run a single high-impact humanizer pass (`max_passes=1` default), calibrate word count
    to 120–150 words, and verify professionalism + detector score.
    """
    current_body = apply_humanizer_pass(body.strip(), iteration=1)
    current_body = calibrate_word_count(current_body, lang=lang, min_words=min_words, max_words=max_words)

    det = evaluate_4_detectors(current_body)
    prof_ok, prof_issues = verify_professionalism(
        subject,
        current_body,
        to_email,
        required_domain=required_domain,
        min_words=min_words,
        max_words=max_words,
        require_price=require_price,
    )
    history = [{
        "pass": 1,
        "word_count": count_words(current_body),
        "average_ai_pct": det["average_ai_pct"],
        "scores": det["scores"],
        "flags": det["flags"],
        "professionalism_ok": prof_ok,
        "professionalism_issues": prof_issues,
    }]

    approved = (det["average_ai_pct"] < threshold_pct) and prof_ok
    return {
        "approved": approved,
        "passes_used": 1,
        "word_count": count_words(current_body),
        "final_subject": subject.strip(),
        "final_body": current_body,
        "final_average_ai_pct": det["average_ai_pct"],
        "detector_scores": det["scores"],
        "professionalism_ok": prof_ok,
        "professionalism_issues": prof_issues,
        "history": history,
    }


# ---------------------------------------------------------------------------
# 4. Tailored 120–150 Word Briefing Builder (Personal Site + Review Context + Real Price)
# ---------------------------------------------------------------------------

def default_price_for_country(country: str, sector: str = "") -> str:
    c = (country or "").upper()
    is_premium = sector in (
        "cro_reg",
        "medtech_cer",
        "MedTech RA",
        "Boutique RA",
        "MedTech OEM",
        "Diagnostics",
        "Clinical Genomics",
        "Biotech / CRO",
        "Dermo-Cosmetics",
        "Nutraceuticals",
        "Veterinary Pharma",
        "CDMO / Pharma",
        "HealthTech",
        "Wealth & Family Office",
        "wealth_office",
        "healthtech",
    )
    if c == "UK":
        return "£380" if is_premium else "£300"
    if c == "US":
        return "$450" if is_premium else "$380"
    if c == "CA":
        return "CAD 540" if is_premium else "CAD 460"
    if c == "AU":
        return "AUD 580" if is_premium else "AUD 490"
    if c == "CH":
        return "450 CHF" if is_premium else "350 CHF"
    if c == "SG":
        return "SGD 520" if is_premium else "SGD 440"
    return "EUR 420" if is_premium else "EUR 350"


def summarize_technical_gaps(audit: dict[str, Any], lang: str = "en") -> list[str]:
    domain = audit["domain"]
    fails = {f["id"]: f for f in audit["findings"] if f["status"] == "FAIL"}
    warns = {f["id"]: f for f in audit["findings"] if f["status"] == "WARN"}

    points: list[str] = []
    if lang == "de":
        if "EML-01" in fails:
            points.append(f"kein aktiver _dmarc.{domain} DNS-Schutz gegen E-Mail-Spoofing")
        elif "EML-01" in warns:
            points.append(f"_dmarc.{domain} steht nur auf p=none ohne Spoofing-Blockade")
        if "PRV-01" in fails:
            points.append("externe Google Fonts übertragen Besucher-IPs vor Einwilligung")
        elif "PRV-03" in fails:
            points.append("Cookies nutzen noch nicht durchgängig Secure/HttpOnly/SameSite")
        if "SEC-02" in fails or "SEC-03" in fails:
            points.append("fehlende HTTP-Schutzheader (HSTS, CSP und X-Frame-Options)")
        if "ACC-02" in fails or "ACC-03" in fails or "A11Y-02" in fails or "A11Y-03" in fails:
            points.append("fehlende WCAG 2.1 AA Formular- oder Bild-Attribute")
        if not points:
            points.append("optimierbare HTTP-Security-Header und DNS-CAA-Richtlinien")
        return points[:3]

    if lang == "fr":
        if "EML-01" in fails:
            points.append(f"aucun enregistrement DNS _dmarc.{domain} actif contre l'usurpation mail")
        elif "EML-01" in warns:
            points.append(f"la règle _dmarc.{domain} reste en mode p=none sans blocage")
        if "PRV-01" in fails:
            points.append("les polices Google Fonts distantes exposent l'IP des visiteurs avant consentement")
        elif "PRV-03" in fails:
            points.append("certains cookies initiaux omettent les attributs Secure/HttpOnly/SameSite")
        if "SEC-02" in fails or "SEC-03" in fails:
            points.append("les en-têtes HSTS, Content-Security-Policy et X-Frame-Options manquent")
        if not points:
            points.append("plusieurs en-têtes HTTP et restrictions DNS CAA sont absents")
        return points[:3]

    # English
    if "EML-01" in fails:
        points.append(f"no _dmarc.{domain} DNS policy is published against outbound email spoofing")
    elif "EML-01" in warns:
        points.append(f"_dmarc.{domain} is still on p=none (monitoring only)")
    if "PRV-01" in fails:
        points.append("remote Google Fonts calls expose visitor IPs before consent")
    elif "PRV-03" in fails:
        points.append("initial session cookies lack full Secure/HttpOnly/SameSite flags")
    elif "PRV-02" in warns or "PRV-02" in fails:
        points.append("third-party analytics scripts load before visitor consent")
    if "SEC-02" in fails or "SEC-03" in fails:
        points.append("key browser security headers (HSTS, CSP, X-Frame-Options) are missing")
    if "ACC-03" in fails or "ACC-02" in fails or "A11Y-02" in fails or "A11Y-03" in fails:
        points.append("intake form fields or images have WCAG 2.1 AA labeling gaps")
    if not points:
        points.append("several HTTP security headers and DNS CAA restrictions are unconfigured")
    return points[:3]


def build_evidence_email(
    audit: dict[str, Any],
    company_name: str,
    to_email: str,
    lang: str = "en",
    country: str = "UK",
    sector: str = "medtech_cer",
    review_context: str = "",
    problem_solved: str = "",
    price_str: str = "",
) -> tuple[str, str]:
    """
    Generate a personalized 120–150 word email combining:
      1. Specific site / customer-review context (`review_context`)
      2. Exact technical findings from `audit` + attached evaluation system PDF & scorecard PNG
      3. Concrete operational problem solved (`problem_solved`)
      4. Clear fixed price (`price_str`) — never "for free"
    """
    domain = audit["domain"]
    score = audit["overall_score"]
    price = price_str.strip() or default_price_for_country(country, sector)
    tech_points = summarize_technical_gaps(audit, lang=lang)
    tech_joined = "; ".join(tech_points)

    if lang == "de":
        rev_line = review_context.strip() or (
            f"Beim Blick auf {domain} und Ihr Mandanten-Feedback fällt auf, wie sehr {company_name} "
            f"auf verlässliche digitale Mandantenkommunikation und schnelle Rückmeldungen setzt."
        )
        prob_line = problem_solved.strip() or (
            "Diese Korrekturen verhindern, dass Mandanten-E-Mails im Spam landen, und sichern Ihre "
            "Online-Formulare direkt nach DSGVO/revDSG ab."
        )
        subj = f"1-Seiten-Risikovorschau & Audit für {domain} ({score}/100)"
        body = (
            f"Guten Tag liebes {company_name} Team,\n\n"
            f"{rev_line} Ich habe für {domain} eine 1-Seiten-Risikovorschau nach dem 25-Kontrollen-Modell "
            f"(1-Seiten-Risikovorschau und System-Leitfaden im Anhang) erstellt, wobei Ihre Seite aktuell "
            f"{score}/100 Punkte erreicht.\n\n"
            f"Konkret fielen diese Punkte auf: {tech_joined}. {prob_line}\n\n"
            f"Für ein fixes Honorar von {price} liefere ich das vollständige Word- und 4-Blatt-Excel-Auditpaket, "
            f"fertige IT-Korrekturdateien für {domain} sowie den Kontroll-Scan nach der Umsetzung. "
            f"Soll ich Ihnen den Projektvorschlag zusenden?\n\n"
            f"Falls kein Bedarf besteht, genügt ein kurzes «Nein», dann schreibe ich nicht erneut.\n\n"
            f"Freundliche Grüsse\nKaled Bouchagraoui"
        )
        return subj, calibrate_word_count(body, lang="de")

    if lang == "fr":
        rev_line = review_context.strip() or (
            f"En consultant {domain} et les avis clients de {company_name}, on voit combien la réactivité "
            f"et la confidentialité des échanges comptent pour vos clients."
        )
        prob_line = problem_solved.strip() or (
            "Corriger ces points évite que vos courriels soient bloqués en spam et sécurise vos "
            "formulaires en ligne conformément au RGPD."
        )
        subj = f"Aperçu risques & conformité 1 page pour {domain} ({score}/100)"
        body = (
            f"Bonjour l'équipe {company_name},\n\n"
            f"{rev_line} J'ai préparé un aperçu 1 page des risques pour {domain} sur 25 contrôles "
            f"(aperçu visuel et guide joints), où votre site obtient {score}/100.\n\n"
            f"L'analyse relève notamment : {tech_joined}. {prob_line}\n\n"
            f"Pour un forfait fixe de {price}, je fournis le rapport Word, l'Excel 4 onglets, les "
            f"correctifs IT prêts à appliquer pour {domain}, et l'attestation re-vérifiée. "
            f"Puis-je envoyer le périmètre détaillé ?\n\n"
            f"Si ce n'est pas pertinent, un simple « non » suffit et je ne relancerai pas.\n\n"
            f"Cordialement,\nKaled Bouchagraoui"
        )
        return subj, calibrate_word_count(body, lang="fr")

    # English
    rev_line = review_context.strip() or (
        f"While reviewing {domain} and client feedback for {company_name}, it stood out how much your "
        f"reputation relies on responsive communication and trusted digital onboarding."
    )
    prob_line = problem_solved.strip() or (
        "Fixing these gaps stops strict corporate spam filters from flagging your outbound emails and "
        "protects visitors submitting enquiries through your site."
    )
    subj = f"1-page GDPR & domain risk preview for {domain} ({score}/100)"
    body = (
        f"Hello {company_name} team,\n\n"
        f"{rev_line} I prepared a 1-page risk preview for {domain} across 25 checks "
        f"(scorecard preview and guide attached), where your site scored {score}/100.\n\n"
        f"Specifically, the scan flagged that {tech_joined}. {prob_line}\n\n"
        f"For {price} flat, I deliver the Word executive audit, 4-sheet Excel risk register, "
        f"turnkey IT fix files for {domain}, and a re-verified attestation PDF. "
        f"Should I send over the scope to get started?\n\n"
        f"If this is not a priority right now, simply reply 'no' and I will not follow up.\n\n"
        f"Best regards,\nKaled Bouchagraoui"
    )
    return subj, calibrate_word_count(body, lang="en")


# ---------------------------------------------------------------------------
# 5. Multi-Attachment Builder & Queue Processor
# ---------------------------------------------------------------------------

def build_email_message(
    from_email: str,
    to_email: str,
    subject: str,
    body: str,
    attachment_path: Path | list[Path] | None = None,
    unsent_draft: bool = True,
) -> EmailMessage:
    msg = EmailMessage()
    if from_email:
        msg["From"] = from_email
    msg["To"] = to_email
    msg["Subject"] = subject
    msg["Date"] = email.utils.formatdate(localtime=True)
    if unsent_draft:
        msg["X-Unsent"] = "1"
    msg.set_content(body, subtype="plain", charset="utf-8")

    paths: list[Path] = []
    if isinstance(attachment_path, (list, tuple)):
        paths = [Path(p) for p in attachment_path if p]
    elif attachment_path:
        paths = [Path(attachment_path)]

    for p in paths:
        if p and p.is_file():
            raw_bytes = p.read_bytes()
            subtype = p.suffix.lstrip(".").lower() or "octet-stream"
            maintype = "image" if subtype in ("png", "jpg", "jpeg") else "application"
            msg.add_attachment(
                raw_bytes,
                maintype=maintype,
                subtype=subtype,
                filename=p.name,
            )
    return msg


def load_dotenv_files(extra_paths: list[Path] | None = None, include_defaults: bool = True) -> None:
    """Safely load KEY=VALUE pairs from ~/.env and ./.env into os.environ without overwriting existing keys."""
    candidates: list[Path] = []
    if include_defaults:
        try:
            candidates.append(Path.home() / ".env")
        except RuntimeError:
            pass
        candidates.append(Path.cwd() / ".env")
    if extra_paths:
        candidates.extend(extra_paths)
    seen: set[Path] = set()
    for p in candidates:
        resolved = p.resolve()
        if resolved in seen or not resolved.is_file():
            continue
        seen.add(resolved)
        for raw_line in resolved.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, val = line.split("=", 1)
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = val


def resolve_smtp_settings(provider: str) -> tuple[str, int]:
    prov = provider.lower().strip()
    if prov == "outlook":
        return os.environ.get("SMTP_HOST", "smtp.office365.com"), int(os.environ.get("SMTP_PORT", "587"))
    if prov == "gmail":
        return os.environ.get("SMTP_HOST", "smtp.gmail.com"), int(os.environ.get("SMTP_PORT", "587"))
    return os.environ.get("SMTP_HOST", ""), int(os.environ.get("SMTP_PORT", "587"))


def load_suppression_records(
    suppression_csv: Path | None,
    now_utc: dt.datetime | None = None,
) -> tuple[dict[str, str], dict[str, str]]:
    """
    Load active permanent suppressions (opt-outs, unrecoverable bounces, health pauses)
    and active temporary cooldown holds from `optout_suppression.csv`.

    Supports an optional `scope` column (`domain` | `email`, defaulting to `domain` when
    omitted or empty) and an optional `hold_until_utc` ISO-8601 timestamp column.
    Rows with `hold_until_utc <= now_utc` are treated as expired holds.
    """
    sup_domains: dict[str, str] = {}
    sup_emails: dict[str, str] = {}
    if not suppression_csv or not suppression_csv.is_file():
        return sup_domains, sup_emails

    ref_now = now_utc or dt.datetime.now(dt.timezone.utc)
    with open(suppression_csv, "r", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            dom = (row.get("domain") or "").strip().lower()
            em = (row.get("email") or "").strip().lower()
            reason = (row.get("reason") or "SUPPRESSED").strip()
            scope = (row.get("scope") or "").strip().lower()
            hold_until_raw = (row.get("hold_until_utc") or "").strip()

            if hold_until_raw:
                try:
                    hold_dt = dt.datetime.fromisoformat(hold_until_raw.replace("Z", "+00:00"))
                    if hold_dt.tzinfo is None:
                        hold_dt = hold_dt.replace(tzinfo=dt.timezone.utc)
                    if hold_dt <= ref_now:
                        continue
                except ValueError:
                    pass

            if not scope:
                scope = "email" if (em and not dom) else "domain"

            if scope == "email":
                if em:
                    sup_emails[em] = reason
            else:
                if dom:
                    sup_domains[dom] = reason
                if em:
                    sup_emails[em] = reason
    return sup_domains, sup_emails


def process_dispatch_queue(
    manifest_csv: Path,
    out_dir: Path,
    dispatch_mode: str = "draft",
    provider: str = "outlook",
    from_email: str = "",
    threshold_pct: float = 15.0,
    max_send_per_run: int = 40,
    confirm_send: bool = False,
    suppression_csv: Path | None = None,
) -> dict[str, Any]:
    """Run single-pass humanizer + strict 120–150w QA gate on every lead in `manifest_csv`."""
    out_dir.mkdir(parents=True, exist_ok=True)
    drafts_dir = out_dir / "outlook_drafts_eml"
    drafts_dir.mkdir(parents=True, exist_ok=True)
    txt_dir = out_dir / "utf8_clean_bodies"
    txt_dir.mkdir(parents=True, exist_ok=True)
    for old_eml in drafts_dir.glob("*.eml"):
        old_eml.unlink()
    for old_txt in txt_dir.glob("*.txt"):
        old_txt.unlink()
    seen_eml_paths: set[Path] = set()
    ledger_path = out_dir / "sent_ledger.csv"
    qa_report_csv = out_dir / "qa_detector_report.csv"
    utf8_json_path = out_dir / "approved_emails_utf8.json"

    sup_path = suppression_csv if suppression_csv is not None else (out_dir / "optout_suppression.csv")
    sup_domains, sup_emails = load_suppression_records(sup_path)

    already_sent: set[str] = set()
    if ledger_path.exists():
        with open(ledger_path, "r", encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                already_sent.add(row.get("to_email", "").strip().lower())

    with open(manifest_csv, "r", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))

    qa_results: list[dict[str, Any]] = []
    approved_queue: list[tuple[dict[str, str], dict[str, Any], EmailMessage, list[Path]]] = []

    for row in rows:
        domain = row["domain"].strip()
        company = row["company_name"].strip()
        to_email = row["to_email"].strip()
        lang = row.get("lang", "en").strip().lower()
        country = row.get("country", "UK").strip().upper()
        sector = row.get("sector", "medtech_cer").strip()
        review_context = row.get("review_context", "").strip()
        problem_solved = row.get("problem_solved", "").strip()
        price_str = row.get("price", "").strip()
        evidence_json = Path(row["evidence_json_path"].strip())

        sup_reason = sup_emails.get(to_email.lower()) or sup_domains.get(domain.lower())
        if sup_reason:
            qa_results.append({
                "domain": domain,
                "to_email": to_email,
                "lang": lang,
                "status": "BLOCKED_SUPPRESSED",
                "word_count": 0,
                "avg_ai_pct": 0.0,
                "d1_cliche": 0.0,
                "d2_burstiness": 0.0,
                "d3_syntactic": 0.0,
                "d4_boilerplate": 0.0,
                "passes_used": 0,
                "professionalism_ok": False,
                "professionalism_issues": f"Suppressed/Cooldown: {sup_reason}",
                "eml_draft": "",
                "attachments": "",
            })
            continue

        attachments: list[Path] = []
        if row.get("attachment_path", "").strip():
            for part in row["attachment_path"].split(";"):
                p = Path(part.strip())
                if p.is_file():
                    attachments.append(p)
        sys_pdf_str = row.get("system_pdf_path", "").strip()
        sys_pdf = Path(sys_pdf_str) if sys_pdf_str else SYSTEM_SPEC_PDF_DEFAULT
        if sys_pdf.is_file() and sys_pdf not in attachments:
            attachments.append(sys_pdf)

        audit = json.loads(evidence_json.read_text(encoding="utf-8"))
        raw_subj, raw_body = build_evidence_email(
            audit,
            company,
            to_email,
            lang=lang,
            country=country,
            sector=sector,
            review_context=review_context,
            problem_solved=problem_solved,
            price_str=price_str,
        )

        qa = run_qa_humanizer_loop(
            subject=raw_subj,
            body=raw_body,
            to_email=to_email,
            required_domain=domain,
            threshold_pct=threshold_pct,
            max_passes=1,
            lang=lang,
            min_words=120,
            max_words=150,
            require_price=True,
        )

        slug = re.sub(r"[^a-z0-9]+", "_", domain.lower()).strip("_")
        eml_path = drafts_dir / f"{slug}_{lang}_draft.eml"
        if eml_path in seen_eml_paths:
            rec_part = re.sub(r"[^a-z0-9]+", "_", to_email.split("@")[0].lower()).strip("_")
            eml_path = drafts_dir / f"{slug}_{rec_part}_{lang}_draft.eml"
        seen_eml_paths.add(eml_path)

        if qa["approved"]:
            status_label = "APPROVED"
        elif not qa["professionalism_ok"]:
            status_label = "BLOCKED_PROFESSIONALISM"
        else:
            status_label = "BLOCKED_ABOVE_THRESHOLD"

        qa_results.append({
            "domain": domain,
            "to_email": to_email,
            "lang": lang,
            "status": status_label,
            "word_count": qa["word_count"],
            "avg_ai_pct": qa["final_average_ai_pct"],
            "d1_cliche": qa["detector_scores"]["D1_Cliche_Signatures"],
            "d2_burstiness": qa["detector_scores"]["D2_Burstiness_Cadence"],
            "d3_syntactic": qa["detector_scores"]["D3_Syntactic_Formulaicity"],
            "d4_boilerplate": qa["detector_scores"]["D4_Outreach_Boilerplate"],
            "passes_used": qa["passes_used"],
            "professionalism_ok": qa["professionalism_ok"],
            "professionalism_issues": "; ".join(qa["professionalism_issues"]),
            "eml_draft": str(eml_path) if qa["approved"] else "",
            "attachments": ";".join(str(a) for a in attachments),
        })

        if qa["approved"]:
            txt_path = txt_dir / f"{eml_path.stem}.txt"
            txt_path.write_text(qa["final_body"], encoding="utf-8")
            msg_draft = build_email_message(
                from_email=from_email,
                to_email=to_email,
                subject=qa["final_subject"],
                body=qa["final_body"],
                attachment_path=attachments,
                unsent_draft=True,
            )
            eml_path.write_bytes(bytes(msg_draft))
            approved_queue.append((row, qa, msg_draft, attachments))

    utf8_records = []
    for row, qa, _msg, att_list in approved_queue:
        slug_s = re.sub(r"[^a-z0-9]+", "_", row["domain"].strip().lower()).strip("_")
        lang_s = row.get("lang", "en").strip().lower()
        utf8_records.append({
            "domain": row["domain"].strip(),
            "company_name": row["company_name"].strip(),
            "country": row.get("country", "").strip(),
            "sector": row.get("sector", "").strip(),
            "to_email": row["to_email"].strip(),
            "lang": lang_s,
            "price": row.get("price", "").strip() or default_price_for_country(row.get("country", ""), row.get("sector", "")),
            "word_count": qa["word_count"],
            "avg_ai_pct": qa["final_average_ai_pct"],
            "subject": qa["final_subject"],
            "body": qa["final_body"],
            "body_txt_path": str(txt_dir / f"{slug_s}_{lang_s}_draft.txt"),
            "attachments": [str(a) for a in att_list],
        })
    utf8_json_path.write_text(json.dumps(utf8_records, indent=2, ensure_ascii=False), encoding="utf-8")

    if qa_results:
        with open(qa_report_csv, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(qa_results[0].keys()))
            writer.writeheader()
            writer.writerows(qa_results)

    sent_count = 0
    if dispatch_mode == "smtp":
        load_dotenv_files()
        if not confirm_send:
            raise RuntimeError("Refusing SMTP send without explicit --confirm-send safety flag.")
        smtp_user = from_email or os.environ.get("SMTP_USER", "").strip()
        smtp_pass = os.environ.get("SMTP_PASSWORD", "").strip()
        smtp_host, smtp_port = resolve_smtp_settings(provider)
        if not (smtp_user and smtp_pass and smtp_host):
            raise RuntimeError(
                "Missing SMTP credentials. Set SMTP_USER, SMTP_PASSWORD (and SMTP_HOST if custom) in your environment/.env."
            )

        with smtplib.SMTP(smtp_host, smtp_port, timeout=20) as server:
            server.ehlo()
            server.starttls()
            server.login(smtp_user, smtp_pass)
            for idx, (row, qa, _draft, att_list) in enumerate(approved_queue):
                if sent_count >= max_send_per_run:
                    break
                dest = row["to_email"].strip()
                if dest.lower() in already_sent:
                    continue
                live_msg = build_email_message(
                    from_email=smtp_user,
                    to_email=dest,
                    subject=qa["final_subject"],
                    body=qa["final_body"],
                    attachment_path=att_list,
                    unsent_draft=False,
                )
                server.send_message(live_msg)
                sent_count += 1
                with open(ledger_path, "a", encoding="utf-8", newline="") as lf:
                    is_new = ledger_path.stat().st_size == 0
                    lw = csv.writer(lf)
                    if is_new:
                        lw.writerow(["timestamp_utc", "to_email", "domain", "provider", "avg_ai_pct"])
                    lw.writerow([
                        dt.datetime.now(dt.timezone.utc).isoformat(),
                        dest,
                        row["domain"],
                        provider,
                        qa["final_average_ai_pct"],
                    ])
                if idx + 1 < len(approved_queue) and sent_count < max_send_per_run:
                    time.sleep(random.uniform(45.0, 75.0))

    return {
        "total_leads": len(rows),
        "approved_count": len(approved_queue),
        "blocked_count": len(rows) - len(approved_queue),
        "sent_via_smtp": sent_count,
        "drafts_dir": drafts_dir,
        "qa_report_csv": qa_report_csv,
        "results": qa_results,
    }


def main(argv: list[str] | None = None) -> int:
    load_dotenv_files()
    parser = argparse.ArgumentParser(
        description="Personalized 120–150 Word B2B Email Generator, Single-Pass Humanizer & Dispatcher."
    )
    parser.add_argument("--manifest", required=True, help="CSV manifest")
    parser.add_argument("--output-dir", default="outreach_queue", help="Output folder for .eml drafts & QA CSV report")
    parser.add_argument("--dispatch", choices=["draft", "smtp"], default="draft", help="'draft' writes .eml files; 'smtp' sends live emails")
    parser.add_argument("--provider", choices=["outlook", "gmail", "custom"], default="outlook", help="SMTP provider profile")
    parser.add_argument("--from-email", default="", help="Sender email address")
    parser.add_argument("--threshold", type=float, default=15.0, help="Max allowed average AI detector % (default: 15.0)")
    parser.add_argument("--max-send", type=int, default=40, help="Safety cap per SMTP run (default: 40)")
    parser.add_argument("--confirm-send", action="store_true", help="Required confirmation flag when --dispatch smtp is active")
    parser.add_argument("--suppression-csv", default="", help="Optional optout_suppression.csv path (defaults to <output-dir>/optout_suppression.csv if present)")
    args = parser.parse_args(argv)

    summary = process_dispatch_queue(
        manifest_csv=Path(args.manifest),
        out_dir=Path(args.output_dir),
        dispatch_mode=args.dispatch,
        provider=args.provider,
        from_email=args.from_email,
        threshold_pct=args.threshold,
        max_send_per_run=args.max_send,
        confirm_send=args.confirm_send,
        suppression_csv=Path(args.suppression_csv) if args.suppression_csv else None,
    )
    print(json.dumps({k: v for k, v in summary.items() if k != "results"}, indent=2, default=str))
    for r in summary["results"]:
        print(
            f"  - {r['domain']:30s} | {r['status']} | Words={r['word_count']:3d} | AvgAI={r['avg_ai_pct']:4.1f}% "
            f"| Passes={r['passes_used']}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
