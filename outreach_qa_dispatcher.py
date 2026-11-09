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
    for banned in BANNED_UNPROFESSIONAL_TERMS:
        if re.search(rf"\b{re.escape(banned)}\b", lower_body) if banned.isalpha() else (banned in lower_body):
            issues.append(f"Banned phrase or 'free' offer detected: '{banned}'")

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

    # If slightly over 150 words, tighten non-essential modifiers first while preserving the GitHub system ref and question
    wc = count_words(body)
    if wc > max_words:
        trim_map = [
            (" and includes a post-deployment verification re-scan once your team applies the changes", ""),
            (" and includes a post-deployment verification re-scan", ""),
            (" with zero intrusive traffic", ""),
            (" (scorecard and system spec PDF attached, code at github.com/kaledbouchagraoui7-bot/medtech-regulatory-compliance-suite)", " (scorecard & system PDF attached, GitHub: medtech-regulatory-compliance-suite)"),
            ("Would you like me to send over the scope to get started?", "Shall I send the scope?"),
            ("Soll ich Ihnen den Projektvorschlag zusenden?", "Soll ich das Angebot senden?"),
            ("Souhaitez-vous mettre cela en place cette semaine ?", "Puis-je envoyer l'offre ?"),
            ("the full Word and 4-sheet Excel audit dossier, ", "the Word/Excel audit dossier, "),
            ("das vollständige Word- und Excel-Auditpaket, ", "das Word/Excel-Auditpaket, "),
            ("le rapport complet Word et Excel, ", "le dossier Word/Excel, "),
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
    is_medtech_cro = sector in ("cro_reg", "medtech_cer")
    if c == "UK":
        return "£380" if is_medtech_cro else "£300"
    if c == "US":
        return "$450" if is_medtech_cro else "$380"
    if c == "CA":
        return "CAD 540" if is_medtech_cro else "CAD 460"
    if c == "AU":
        return "AUD 580" if is_medtech_cro else "AUD 490"
    if c == "CH":
        return "450 CHF" if is_medtech_cro else "350 CHF"
    if c == "SG":
        return "SGD 520" if is_medtech_cro else "SGD 440"
    return "EUR 420" if is_medtech_cro else "EUR 350"


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
        subj = f"Technisches Audit & Bewertungssystem für {domain} ({score}/100)"
        body = (
            f"Guten Tag liebes {company_name} Team,\n\n"
            f"{rev_line} Ich habe {domain} mit meinem passiven 25-Kontrollen-System Sentinel "
            f"(Scorecard & System-PDF im Anhang, GitHub: medtech-regulatory-compliance-suite) geprüft, "
            f"wobei Ihre Seite aktuell {score}/100 Punkte erreicht.\n\n"
            f"Konkret fielen diese Punkte auf: {tech_joined}. {prob_line}\n\n"
            f"Für ein fixes Honorar von {price} liefere ich das vollständige Word- und Excel-Auditpaket, "
            f"direkt einfügbare DNS- und Server-Konfigurationen für {domain} sowie den Kontroll-Scan nach der Umsetzung. "
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
        subj = f"Évaluation technique de {domain} ({score}/100) & système d'audit joint"
        body = (
            f"Bonjour l'équipe {company_name},\n\n"
            f"{rev_line} J'ai évalué {domain} avec mon système passif à 25 contrôles Sentinel "
            f"(scorecard PNG et PDF du système joints, GitHub : medtech-regulatory-compliance-suite), "
            f"où votre site obtient {score}/100.\n\n"
            f"L'analyse relève notamment : {tech_joined}. {prob_line}\n\n"
            f"Pour un forfait fixe de {price}, je fournis le rapport complet Word et Excel, les "
            f"configurations DNS et serveur prêtes à déployer pour {domain}, ainsi que la contre-visite de validation. "
            f"Souhaitez-vous mettre cela en place cette semaine ?\n\n"
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
    subj = f"Technical evaluation of {domain} ({score}/100) + system spec attached"
    body = (
        f"Hello {company_name} team,\n\n"
        f"{rev_line} I evaluated {domain} using my passive 25-control Sentinel system "
        f"(scorecard and system spec PDF attached, code at github.com/kaledbouchagraoui7-bot/medtech-regulatory-compliance-suite), "
        f"where your site scored {score}/100.\n\n"
        f"Specifically, the scan flagged that {tech_joined}. {prob_line}\n\n"
        f"For a flat fee of {price}, I deliver the full Word and 4-sheet Excel audit dossier, copy-paste DNS and "
        f"HTTP header configs for {domain}, plus a post-deployment verification scan. "
        f"Would you like me to send over the scope to get started?\n\n"
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


def process_dispatch_queue(
    manifest_csv: Path,
    out_dir: Path,
    dispatch_mode: str = "draft",
    provider: str = "outlook",
    from_email: str = "",
    threshold_pct: float = 15.0,
    max_send_per_run: int = 40,
    confirm_send: bool = False,
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
