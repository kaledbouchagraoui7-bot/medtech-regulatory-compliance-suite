#!/usr/bin/env python3
"""
outreach_qa_dispatcher.py — Automated B2B Email QA Gate, Multi-Signal AI Detector,
Iterative Humanizer & Outlook (.eml) / Dual-Provider SMTP Dispatcher
==================================================================================

Workflow
--------
1. Draft Generation (or Text Ingestion):
   Generates concise EN/DE/FR B2B briefing drafts directly from verified domain audit JSON
   (`*_raw_evidence.json`) or accepts custom text files.
2. Iterative Humanizer -> Professionalism Check -> 4-Detector Verification Loop:
   - Detector 1 (D1): LLM Cliché, Transition & Punctuation Signature Detector (EN/DE/FR)
   - Detector 2 (D2): Sentence Length Burstiness & Cadence Uniformity Analyzer
   - Detector 3 (D3): Syntactic Formulaicity & Passive/Nominalization Ratio Analyzer
   - Detector 4 (D4): Cold-Outreach Boilerplate & Sales-Template Fingerprint Detector
   *(Optional: Also supports documented GPTZero / Sapling REST APIs when API keys exist in env.)*
   Rewrites iteratively (up to `max_passes`) whenever Average AI Score >= 10.0%, and enforces
   a strict Professionalism Gate (word budget, zero sales clichés, domain fact alignment,
   technical keyword preservation, and Swiss UWG / GDPR 1-line opt-out check).
3. Safe Dispatch (Dual Support: Outlook .eml Drafts + Throttled Outlook/Gmail/Custom SMTP):
   - Default `--dispatch draft`: Writes RFC 5322 `.eml` files with `X-Unsent: 1` and the
     `.png` scorecard pre-attached so Windows Outlook (Classic or New Outlook) opens the
     ready-to-click draft cleanly, respecting Swiss UWG Art. 3(1)(o) manual 1-to-1 review.
   - Optional `--dispatch smtp --confirm-send`: Sends via authenticated Outlook Office365,
     Gmail, or custom SMTP using `.env` credentials with deduplication ledger tracking
     (`sent_ledger.csv`), strict daily batch limits, and human-paced intervals.
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


# ---------------------------------------------------------------------------
# 1. Blacklists & Linguistic Signals (EN / DE / FR)
# ---------------------------------------------------------------------------

AI_CLICHE_PATTERNS: list[tuple[str, float]] = [
    # English LLM markers
    (r"\bin today'?s (?:rapidly evolving|fast-paced|digital|modern) (?:landscape|world|era)\b", 22.0),
    (r"\bi hope this email finds you (?:well|in good spirits)\b", 22.0),
    (r"\bi am writing to (?:express|reach out|share)\b", 14.0),
    (r"\b(?:delighted|thrilled|excited|pleased) to (?:share|introduce|offer|present)\b", 16.0),
    (r"\b(?:leverage|utilize|harness|revolutionize|streamline|synergy|paradigm|holistic)\b", 15.0),
    (r"\b(?:cutting-edge|state-of-the-art|game-changing|seamless|robust|comprehensive|paramount)\b", 13.0),
    (r"\b(?:furthermore|moreover|additionally|consequently|nevertheless)\b", 11.0),
    (r"\bit is (?:worth noting|important to highlight|crucial to recognize) that\b", 18.0),
    (r"\b(?:delve|testament|tapestry|underscore|pivotal)\b", 18.0),
    (r"\bplease do not hesitate to\b", 14.0),
    (r"\bin conclusion\b", 12.0),
    # German LLM / stiff boilerplate markers
    (r"\bin der heutigen (?:digitalen|schnelllebigen) welt\b", 20.0),
    (r"\bich hoffe, diese e-mail erreicht sie wohlbehalten\b", 22.0),
    (r"\bdarüber hinaus\b", 11.0),
    (r"\b(?:nahtlos|ganzheitlich|maßgeschneidert|umfassend|revolutionieren)\b", 13.0),
    (r"\bzögern sie nicht, mich zu kontaktieren\b", 14.0),
    # French LLM / stiff boilerplate markers
    (r"\bdans un monde en constante évolution\b", 20.0),
    (r"\bj'espère que ce message vous trouve\b", 22.0),
    (r"\b(?:par ailleurs|de plus|en outre|néanmoins)\b", 10.0),
    (r"\b(?:holistique|révolutionner|solution clé en main|synergie)\b", 14.0),
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
    "guarantee",
    "guaranteed",
    "garanti",
    "garantiert",
    "100% compliant",
    "act now",
    "!!!",
    "free money",
]

# Safe humanizing phrase substitutions (preserves Swiss/EU formal courtesy & technical acronyms)
HUMANIZER_REPLACEMENTS: list[tuple[str, str]] = [
    (r"(?i)I hope this email finds you well[\.,]?\s*", ""),
    (r"(?i)J'espère que ce message vous trouve en bonne santé[\.,]?\s*", ""),
    (r"(?i)Ich hoffe, diese E-Mail erreicht Sie wohlbehalten[\.,]?\s*", ""),
    (r"(?i)\bin today'?s (?:rapidly evolving|fast-paced|digital|modern) (?:landscape|world|era),?\s*", ""),
    (r"(?i)\bdelighted to\b", "happy to"),
    (r"(?i)\bthrilled to\b", "ready to"),
    (r"(?i)\bleverage\b", "use"),
    (r"(?i)\butilize\b", "use"),
    (r"(?i)\bstreamline\b", "simplify"),
    (r"(?i)\bcomprehensive\b", "full"),
    (r"(?i)\brobust\b", "solid"),
    (r"(?i)\bcutting-edge\b", "automated"),
    (r"(?i)\bseamlessly\b", "cleanly"),
    (r"(?i)\bparamount\b", "essential"),
    (r"(?i)\bFurthermore,\s*", "Also, "),
    (r"(?i)\bMoreover,\s*", "Also, "),
    (r"(?i)\bAdditionally,\s*", ""),
    (r"(?i)\bPlease do not hesitate to reach out\.?", "Let me know if useful."),
    (r"(?i)\bschedule a brief \d+-minute (?:discovery )?call\b", "reply to this email"),
    (r"(?i)\bhop on a quick call\b", "reply here"),
    (r"(?i)\bDarüber hinaus\s+", "Zudem "),
    (r"(?i)\bPar ailleurs,\s*", "Également, "),
    (r"(?i)\bDe plus,\s*", ""),
    (r"(?i)\bin order to\b", "to"),
    (r"(?i)\bdue to the fact that\b", "because"),
]


# ---------------------------------------------------------------------------
# 2. Four Independent Local AI-Detection Signals + Optional Official APIs
# ---------------------------------------------------------------------------

def split_sentences(text: str) -> list[str]:
    """Split text into non-trivial sentences while ignoring email/domain dots."""
    body_lines = [ln.strip() for ln in text.strip().splitlines() if ln.strip()]
    # Skip greeting/sign-off one-word lines when computing structural cadence
    joined = " ".join(body_lines)
    # Protect domain dots like domain.ch or fonts.googleapis.com from splitting
    protected = re.sub(r"([a-zA-Z0-9_-])\.([a-zA-Z]{2,})", r"\1<DOT>\2", joined)
    raw_parts = re.split(r"(?<=[.!?])\s+", protected)
    sentences = []
    for p in raw_parts:
        restored = p.replace("<DOT>", ".").strip()
        if len(restored.split()) >= 3:
            sentences.append(restored)
    return sentences


def detector_1_cliche_signatures(text: str) -> tuple[float, list[str]]:
    """D1: LLM cliché, formal connector & em-dash overload probability (0–100)."""
    score = 0.0
    hits: list[str] = []
    for pat, weight in AI_CLICHE_PATTERNS:
        found = re.findall(pat, text, flags=re.I)
        if found:
            score += weight * min(len(found), 2)
            hits.append(f"cliché:{found[0]}")

    em_dashes = text.count("—") + text.count("--")
    if em_dashes > 2:
        score += (em_dashes - 2) * 8.0
        hits.append(f"excess_dashes:{em_dashes}")

    return min(100.0, round(score, 1)), hits


def detector_2_burstiness_cadence(text: str) -> tuple[float, list[str]]:
    """D2: Measures sentence-length burstiness (Coefficient of Variation & mean sentence size)."""
    sents = split_sentences(text)
    if len(sents) < 3:
        return 4.0, []

    lengths = [len(s.split()) for s in sents]
    mean_len = statistics.mean(lengths)
    stdev_len = statistics.pstdev(lengths)
    cv = stdev_len / max(mean_len, 1.0)

    score = 0.0
    hits: list[str] = []
    # LLMs typically produce 16–24 word sentences with low burstiness (cv < 0.25)
    if mean_len > 17.5:
        score += min(40.0, (mean_len - 17.5) * 4.5)
        hits.append(f"long_mean_sent:{mean_len:.1f}w")
    # Realistic baseline gradient for natural burstiness vs uniformity
    if cv < 0.28 and len(sents) >= 4:
        score += min(45.0, (0.28 - cv) * 180.0)
        hits.append(f"low_burstiness_cv:{cv:.2f}")
    elif cv < 0.42:
        score += round((0.42 - cv) * 28.0, 1)

    if len(lengths) >= 4 and max(lengths) - min(lengths) <= 4:
        score += 20.0
        hits.append("uniform_sentence_lengths")

    return min(100.0, round(score, 1)), hits


def detector_3_syntactic_formulaicity(text: str) -> tuple[float, list[str]]:
    """D3: Passive / nominalization density & robotic starter repetition."""
    words = re.findall(r"\b[a-zA-Zäöüàéèêîôûç]+\b", text.lower())
    n_words = max(len(words), 1)
    score = 0.0
    hits: list[str] = []

    # High density of abstract Latinate/nominalized suffixes signals robotic corporate prose
    abstract_suffixes = re.findall(r"\b\w+(?:tion|ment|ity|ness|keit|ung|schaft|ité|ement)\b", text.lower())
    abs_ratio = len(abstract_suffixes) / n_words
    if abs_ratio > 0.14:
        score += min(45.0, (abs_ratio - 0.14) * 320.0)
        hits.append(f"high_nominalization:{abs_ratio:.2f}")
    elif abs_ratio > 0.03:
        score += round((abs_ratio - 0.03) * 55.0, 1)

    # Repetitive sentence starters (e.g., "I ...", "I ...", "We ...", "We ...")
    sents = split_sentences(text)
    if len(sents) >= 4:
        starters = [s.split()[0].lower() for s in sents]
        most_common_cnt = max(starters.count(st) for st in set(starters))
        if most_common_cnt >= max(3, int(math.ceil(len(sents) * 0.55))):
            score += 22.0
            hits.append("repetitive_sentence_starters")

    # Excessive word bloat for cold email (>140 words pushes robotic/essay style)
    if n_words > 145:
        score += min(35.0, (n_words - 145) * 0.8)
        hits.append(f"verbose:{n_words}w")

    return min(100.0, round(score, 1)), hits


def detector_4_outreach_boilerplate(text: str) -> tuple[float, list[str]]:
    """D4: Cold-email template & sales-pitch cliché detector."""
    score = 0.0
    hits: list[str] = []
    for pat, weight in SALES_SPAM_PATTERNS:
        found = re.findall(pat, text, flags=re.I)
        if found:
            score += weight
            hits.append(f"spam_cta:{found[0]}")

    # Check if opening uses overly stiff generic greeting
    first_line = text.strip().splitlines()[0] if text.strip() else ""
    if re.search(r"^(?:Dear Sir/Madam|To Whom It May Concern|Sehr geehrte Damen und Herren|Madame, Monsieur,)", first_line, re.I):
        score += 14.0
        hits.append("generic_greeting")

    return min(100.0, round(score, 1)), hits


def query_optional_external_detectors(text: str) -> list[tuple[str, float]]:
    """
    If official API keys are configured in environment variables (`GPTZERO_API_KEY`,
    `SAPLING_API_KEY`), query those documented APIs cleanly without bypassing any limits.
    """
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
                    prob_pct = round(float(docs[0]["completely_generated_prob"]) * 100.0, 1)
                    ext_scores.append(("GPTZero_API", prob_pct))
        except Exception:
            pass

    sapling_key = os.environ.get("SAPLING_API_KEY", "").strip()
    if sapling_key:
        try:
            r = requests.post(
                "https://api.sapling.ai/api/v1/aidetect",
                json={"key": sapling_key, "text": text},
                timeout=10,
            )
            if r.status_code == 200 and "score" in r.json():
                prob_pct = round(float(r.json()["score"]) * 100.0, 1)
                ext_scores.append(("Sapling_API", prob_pct))
        except Exception:
            pass

    return ext_scores


def evaluate_4_detectors(text: str) -> dict[str, Any]:
    """Run all 4 independent detectors (+ optional official APIs) and compute ensemble average."""
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
    ext = query_optional_external_detectors(text)
    for k, v in ext:
        scores[k] = v

    avg_score = round(sum(scores.values()) / len(scores), 2)
    return {
        "average_ai_pct": avg_score,
        "scores": scores,
        "flags": h1 + h2 + h3 + h4,
        "external_apis_used": [k for k, _ in ext],
    }


# ---------------------------------------------------------------------------
# 3. Professionalism Gate & Iterative Humanizer Loop
# ---------------------------------------------------------------------------

def verify_professionalism(
    subject: str,
    body: str,
    to_email: str,
    required_domain: str | None = None,
) -> tuple[bool, list[str]]:
    """Check Swiss/EU B2B professionalism, integrity, opt-out compliance & accuracy."""
    issues: list[str] = []
    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", to_email.strip()):
        issues.append(f"Invalid recipient email: '{to_email}'")
    if len(subject.strip()) < 8 or len(subject.strip()) > 110:
        issues.append("Subject must be between 8 and 110 characters.")

    word_count = len(body.split())
    if word_count < 35:
        issues.append(f"Body too short ({word_count} words).")
    if word_count > 165:
        issues.append(f"Body exceeds 165-word cold-email professionalism ceiling ({word_count} words).")

    lower_body = body.lower()
    for banned in BANNED_UNPROFESSIONAL_TERMS:
        if banned in lower_body:
            issues.append(f"Unprofessional / risky claim detected: '{banned}'")

    if required_domain and required_domain.lower() not in lower_body and required_domain.lower() not in subject.lower():
        issues.append(f"Target domain '{required_domain}' missing from briefing text.")

    # Require transparent 1-line opt-out / no-pressure closing for Swiss UWG / GDPR B2B hygiene
    has_opt_out = bool(re.search(
        r"(kein interesse|kein bedarf|nicht erneut|keine nachfragen|abmelden|nicht mehr|"
        r"pas pertinent|ne relancerai pas|ne pas|stop|not relevant|opt out|no follow)",
        lower_body,
    ))
    if not has_opt_out:
        issues.append("Missing concise opt-out / no-follow-up courtesy line.")

    return len(issues) == 0, issues


def apply_humanizer_pass(text: str, iteration: int, detector_flags: list[str]) -> str:
    """
    Apply targeted, meaning-preserving humanization rewrites without corrupting technical
    acronyms (DMARC, SPF, nFADP, revDSG, HSTS, CSP, EU MDR, PRISMA) or domain names.
    """
    out = text

    # Pass edits: replace robotic boilerplate phrases
    for pat, repl in HUMANIZER_REPLACEMENTS:
        out = re.sub(pat, repl, out)

    # Normalize excessive em-dashes and double spaces
    out = out.replace(" — ", ", ").replace("—", ", ")
    out = re.sub(r"[ \t]{2,}", " ", out)
    out = re.sub(r"\n{3,}", "\n\n", out)

    # On iteration >= 2, break long compound sentences for natural burstiness
    if iteration >= 2 or any("long_mean_sent" in f or "low_burstiness" in f for f in detector_flags):
        lines = out.splitlines()
        new_lines = []
        for ln in lines:
            if len(ln.split()) > 22 and not ln.strip().startswith(("1.", "2.", "3.", "-", "•")):
                # Split on '; ' or ', which ' cleanly
                ln = ln.replace("; ", ". ").replace(", which ", ". That ")
            new_lines.append(ln)
        out = "\n".join(new_lines)

    # On iteration >= 3, tighten verbose filler sentences
    if iteration >= 3 or any("verbose" in f for f in detector_flags):
        lines = out.splitlines()
        trimmed = [ln for ln in lines if not re.match(r"^(Also,\s*$|Zudem\s*$|Également,\s*$)", ln.strip())]
        out = "\n".join(trimmed)

    return out.strip()


def run_qa_humanizer_loop(
    subject: str,
    body: str,
    to_email: str,
    required_domain: str | None = None,
    threshold_pct: float = 10.0,
    max_passes: int = 5,
) -> dict[str, Any]:
    """
    Iteratively humanize -> check professionalism -> run 4 detectors until
    `average_ai_pct < threshold_pct` and professionalism passes.
    """
    current_body = body.strip()
    history: list[dict[str, Any]] = []

    for attempt in range(1, max_passes + 1):
        det = evaluate_4_detectors(current_body)
        prof_ok, prof_issues = verify_professionalism(subject, current_body, to_email, required_domain)

        history.append({
            "pass": attempt,
            "average_ai_pct": det["average_ai_pct"],
            "scores": det["scores"],
            "flags": det["flags"],
            "professionalism_ok": prof_ok,
            "professionalism_issues": prof_issues,
        })

        if det["average_ai_pct"] < threshold_pct and prof_ok:
            return {
                "approved": True,
                "passes_used": attempt,
                "final_subject": subject.strip(),
                "final_body": current_body,
                "final_average_ai_pct": det["average_ai_pct"],
                "detector_scores": det["scores"],
                "professionalism_ok": True,
                "professionalism_issues": [],
                "history": history,
            }

        if attempt < max_passes:
            current_body = apply_humanizer_pass(current_body, attempt + 1, det["flags"])

    # Final evaluation after last pass
    final_det = evaluate_4_detectors(current_body)
    final_prof_ok, final_prof_issues = verify_professionalism(subject, current_body, to_email, required_domain)
    approved = (final_det["average_ai_pct"] < threshold_pct) and final_prof_ok

    return {
        "approved": approved,
        "passes_used": max_passes,
        "final_subject": subject.strip(),
        "final_body": current_body,
        "final_average_ai_pct": final_det["average_ai_pct"],
        "detector_scores": final_det["scores"],
        "professionalism_ok": final_prof_ok,
        "professionalism_issues": final_prof_issues,
        "history": history,
    }


# ---------------------------------------------------------------------------
# 4. Data-Grounded Briefing Generator (EN / DE / FR from Raw JSON Evidence)
# ---------------------------------------------------------------------------

def build_evidence_email(audit: dict[str, Any], company_name: str, to_email: str, lang: str = "de") -> tuple[str, str]:
    """Generate a concise, factual briefing email from real failing controls in `*_raw_evidence.json`."""
    domain = audit["domain"]
    score = audit["overall_score"]
    gaps = [f for f in audit["findings"] if f["status"] == "FAIL"]
    top_ids = {g["id"] for g in gaps}

    bullets: list[str] = []
    if lang == "de":
        if "EML-01" in top_ids:
            bullets.append(f"1. Kein _dmarc.{domain} DNS-Eintrag: Dritte können E-Mails im Namen Ihrer Domain fälschen.")
        if "PRV-01" in top_ids:
            bullets.append("2. Remote Google Fonts (revDSG): Besucher-IPs gehen vor Einwilligung an fonts.googleapis.com (USA).")
        if "PRV-03" in top_ids:
            bullets.append("2. Cookie-Flags: Initiale Cookies setzen noch nicht alle Secure/HttpOnly/SameSite-Attribute.")
        if "SEC-02" in top_ids or "SEC-03" in top_ids:
            bullets.append(f"{len(bullets)+1}. Fehlende Security-Header: HSTS, Content-Security-Policy oder X-Frame-Options fehlen.")
        if not bullets and gaps:
            for g in gaps[:2]:
                bullets.append(f"{len(bullets)+1}. {g['title']}: {g['evidence']}")

        subj = f"Kurzer Technik-Hinweis zu {domain} (DMARC & Security)"
        body = (
            f"Guten Tag liebes {company_name} Team,\n\n"
            f"beim passiven Check Ihrer öffentlichen Domain {domain} (Score {score}/100, Grafik anbei) fielen diese Punkte auf:\n\n"
            + "\n".join(bullets[:3])
            + f"\n\nDie fertigen Korrektur-Snippets (DNS + Header) und der Word/Excel-Bericht für {domain} liegen bereit. "
            "Soll ich sie Ihnen kostenlos für Ihre IT mailen?\n\n"
            "Falls kein Bedarf besteht, genügt ein kurzes «Nein», dann schreibe ich nicht erneut.\n\n"
            "Freundliche Grüsse\nKaled Bouchagraoui"
        )
        return subj, body

    if lang == "fr":
        if "EML-01" in top_ids:
            bullets.append(f"1. Absence d'enregistrement DNS _dmarc.{domain} : risque d'usurpation d'e-mails.")
        if "PRV-01" in top_ids:
            bullets.append("2. Polices Google Fonts distantes : transfert d'IP visiteurs vers les USA dès le chargement.")
        if "PRV-03" in top_ids:
            bullets.append("2. Sécurité cookies : drapeaux Secure/HttpOnly/SameSite incomplets au chargement.")
        if "SEC-02" in top_ids or "SEC-03" in top_ids:
            bullets.append(f"{len(bullets)+1}. En-têtes HTTP absents : HSTS, CSP ou X-Frame-Options manquants.")
        if not bullets and gaps:
            for g in gaps[:2]:
                bullets.append(f"{len(bullets)+1}. {g['title']} : {g['evidence']}")

        subj = f"Note technique {domain} : DMARC & sécurité web"
        body = (
            f"Bonjour l'équipe {company_name},\n\n"
            f"Un contrôle passif public de {domain} (score {score}/100, fiche ci-jointe) montre ces points :\n\n"
            + "\n".join(bullets[:3])
            + "\n\nLe rapport Word/Excel et les fichiers de correction prêts à copier pour votre IT sont déjà générés. "
            "Voulez-vous que je vous les envoie gratuitement ?\n\n"
            "Si ce n'est pas pertinent pour votre équipe, un simple « non » suffit et je ne relancerai pas.\n\n"
            "Cordialement,\nKaled Bouchagraoui"
        )
        return subj, body

    # English fallback
    if "EML-01" in top_ids:
        bullets.append(f"1. Missing _dmarc.{domain} DNS policy: domain is open to email spoofing.")
    else:
        bullets.append(f"1. DMARC enforcement check: {next((f['evidence'] for f in audit['findings'] if f['id']=='EML-01'), 'Needs enforcement review')}")
    if "PRV-01" in top_ids:
        bullets.append("2. Remote Google Fonts leak: visitor IPs are sent to fonts.googleapis.com prior to consent.")
    if "SEC-02" in top_ids or "SEC-03" in top_ids:
        bullets.append(f"{len(bullets)+1}. Missing edge headers: HSTS, Content-Security-Policy, or X-Frame-Options are absent.")

    subj = f"Quick technical note on {domain} (score {score}/100)"
    body = (
        f"Hello {company_name} team,\n\n"
        f"A passive external check of {domain} (score {score}/100, scorecard attached) flagged three quick fixes:\n\n"
        + "\n".join(bullets[:3])
        + f"\n\nI already generated the Word/Excel audit and drop-in config fixes for {domain}. "
        "Want me to reply with those files free for your IT team?\n\n"
        "If not relevant right now, just reply 'no' and I will not follow up.\n\n"
        "Best regards,\nKaled Bouchagraoui"
    )
    return subj, body


# ---------------------------------------------------------------------------
# 5. Dual Dispatch Engine: Outlook Unsent `.eml` Drafts + Throttled SMTP
# ---------------------------------------------------------------------------

def build_email_message(
    from_email: str,
    to_email: str,
    subject: str,
    body: str,
    attachment_path: Path | None = None,
    unsent_draft: bool = True,
) -> EmailMessage:
    msg = EmailMessage()
    if from_email:
        msg["From"] = from_email
    msg["To"] = to_email
    msg["Subject"] = subject
    msg["Date"] = email.utils.formatdate(localtime=True)
    if unsent_draft:
        # Standard Microsoft Outlook / Thunderbird flag opening `.eml` directly in Compose mode
        msg["X-Unsent"] = "1"
    msg.set_content(body, subtype="plain", charset="utf-8")

    if attachment_path and attachment_path.is_file():
        raw_bytes = attachment_path.read_bytes()
        subtype = attachment_path.suffix.lstrip(".").lower() or "octet-stream"
        maintype = "image" if subtype in ("png", "jpg", "jpeg") else "application"
        msg.add_attachment(
            raw_bytes,
            maintype=maintype,
            subtype=subtype,
            filename=attachment_path.name,
        )
    return msg


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
    dispatch_mode: str = "draft",  # draft | smtp
    provider: str = "outlook",     # outlook | gmail | custom
    from_email: str = "",
    threshold_pct: float = 10.0,
    max_send_per_run: int = 10,
    confirm_send: bool = False,
) -> dict[str, Any]:
    """Run QA Gate + Humanizer Loop on every lead in `manifest_csv`, write Outlook drafts or send via SMTP."""
    out_dir.mkdir(parents=True, exist_ok=True)
    drafts_dir = out_dir / "outlook_drafts_eml"
    drafts_dir.mkdir(parents=True, exist_ok=True)
    for old_eml in drafts_dir.glob("*.eml"):
        old_eml.unlink()
    seen_eml_paths: set[Path] = set()
    ledger_path = out_dir / "sent_ledger.csv"
    qa_report_csv = out_dir / "qa_detector_report.csv"

    already_sent: set[str] = set()
    if ledger_path.exists():
        with open(ledger_path, "r", encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                already_sent.add(row.get("to_email", "").strip().lower())

    rows = []
    with open(manifest_csv, "r", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))

    qa_results: list[dict[str, Any]] = []
    approved_queue: list[tuple[dict[str, str], dict[str, Any], EmailMessage, Path | None]] = []

    for row in rows:
        domain = row["domain"].strip()
        company = row["company_name"].strip()
        to_email = row["to_email"].strip()
        lang = row.get("lang", "de").strip().lower()
        evidence_json = Path(row["evidence_json_path"].strip())
        attachment = Path(row["attachment_path"].strip()) if row.get("attachment_path") else None

        audit = json.loads(evidence_json.read_text(encoding="utf-8"))
        raw_subj, raw_body = build_evidence_email(audit, company, to_email, lang=lang)

        qa = run_qa_humanizer_loop(
            subject=raw_subj,
            body=raw_body,
            to_email=to_email,
            required_domain=domain,
            threshold_pct=threshold_pct,
            max_passes=5,
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
            "avg_ai_pct": qa["final_average_ai_pct"],
            "d1_cliche": qa["detector_scores"]["D1_Cliche_Signatures"],
            "d2_burstiness": qa["detector_scores"]["D2_Burstiness_Cadence"],
            "d3_syntactic": qa["detector_scores"]["D3_Syntactic_Formulaicity"],
            "d4_boilerplate": qa["detector_scores"]["D4_Outreach_Boilerplate"],
            "passes_used": qa["passes_used"],
            "professionalism_ok": qa["professionalism_ok"],
            "professionalism_issues": "; ".join(qa["professionalism_issues"]),
            "eml_draft": str(eml_path) if qa["approved"] else "",
        })

        if qa["approved"]:
            msg_draft = build_email_message(
                from_email=from_email,
                to_email=to_email,
                subject=qa["final_subject"],
                body=qa["final_body"],
                attachment_path=attachment,
                unsent_draft=True,
            )
            eml_path.write_bytes(bytes(msg_draft))
            approved_queue.append((row, qa, msg_draft, attachment))

    # Save QA CSV report
    if qa_results:
        with open(qa_report_csv, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(qa_results[0].keys()))
            writer.writeheader()
            writer.writerows(qa_results)

    sent_count = 0
    if dispatch_mode == "smtp":
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
            for idx, (row, qa, _draft, att_p) in enumerate(approved_queue):
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
                    attachment_path=att_p if (att_p is not None and att_p.is_file()) else None,
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
    parser = argparse.ArgumentParser(
        description="Automated Email QA Gate, 4-Detector Ensemble, Humanizer & Outlook (.eml) / SMTP Dispatcher."
    )
    parser.add_argument("--manifest", required=True, help="CSV manifest (domain,company_name,to_email,lang,evidence_json_path,attachment_path)")
    parser.add_argument("--output-dir", default="outreach_queue", help="Output folder for .eml drafts & QA CSV report")
    parser.add_argument("--dispatch", choices=["draft", "smtp"], default="draft", help="'draft' writes Outlook .eml files; 'smtp' sends live emails")
    parser.add_argument("--provider", choices=["outlook", "gmail", "custom"], default="outlook", help="SMTP provider profile")
    parser.add_argument("--from-email", default="", help="Sender email address")
    parser.add_argument("--threshold", type=float, default=10.0, help="Max allowed average AI detector % (default: 10.0)")
    parser.add_argument("--max-send", type=int, default=10, help="Safety cap per SMTP run (default: 10)")
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
            f"  - {r['domain']:28s} | {r['status']} | AvgAI={r['avg_ai_pct']:4.1f}% "
            f"(D1={r['d1_cliche']} D2={r['d2_burstiness']} D3={r['d3_syntactic']} D4={r['d4_boilerplate']}) "
            f"| Passes={r['passes_used']}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
