#!/usr/bin/env python3
"""
outreach_qa_dispatcher.py — Deliverability-Shielded 85–125 Word B2B Email Generator,
Single-Pass Humanizer, Smoking-Gun Gate, Hygiene Verifier & Multi-Attachment Dispatcher
========================================================================================

Key Capabilities
----------------
1. Tailored 85–125 Word B2B Emails:
   - Strictly enforces 85 to 125 words (`85 <= word_count <= 125`) with <15% AI detector score.
   - Prepends a crisp receptionist-routing ask when targeting generic mailboxes (`info@`, `contact@`, etc.).
   - Leads immediately with exact numerical scan evidence + concrete operational problem solved.
   - Includes transparent fixed B2B pricing (EUR 350 / USD 380 / GBP 300 / CHF 350 / AUD 550 / CAD 520)
     and omits any `-bot.github.io` URL unless a clean custom domain is configured.
2. Deliverability Shield & Smoking-Gun Trigger Gates:
   - Verifies email syntax, corporate domain matching, non-disposable/non-webmail rules,
     and live DoH MX records (rejecting RFC 7505 Null MX `0 .` and parked/sinkhole MXs).
   - Evaluates severity-based Smoking-Gun triggers across Tracks 1, 2, and 3.
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
    "kaledbouchagraoui7-bot",
]

FREE_WEBMAIL_DOMAINS = {
    "gmail.com", "googlemail.com", "yahoo.com", "yahoo.fr", "yahoo.co.uk",
    "hotmail.com", "hotmail.fr", "hotmail.co.uk", "outlook.com", "outlook.fr",
    "live.com", "live.fr", "msn.com", "icloud.com", "me.com", "mac.com",
    "proton.me", "protonmail.com", "pm.me", "aol.com", "gmx.com", "gmx.de",
    "gmx.ch", "web.de", "t-online.de", "orange.fr", "wanadoo.fr", "free.fr",
    "sfr.fr", "laposte.net", "mail.ru", "yandex.com", "qq.com", "163.com",
}

DISPOSABLE_EMAIL_DOMAINS = {
    "mailinator.com", "guerrillamail.com", "guerrillamail.org", "temp-mail.org",
    "10minutemail.com", "yopmail.com", "yopmail.fr", "trashmail.com",
    "sharklasers.com", "getnada.com", "dispostable.com", "tempmail.com",
    "throwawaymail.com", "maildrop.cc", "fakeinbox.com", "mintemail.com",
    "moakt.com", "tempr.email", "discard.email",
}

PARKED_OR_SINKHOLE_MX_KEYWORDS = (
    "sedoparking", "parkingcrew", "bodis.com", "hugedomains", "dan.com",
    "afternic", "undeveloped.com", "parklogic", "above.com", "cashparking",
    "domainmarket", "nullmx", "blackhole", "localhost", "sinkhole", "invalid",
)

RECEPTIONIST_GENERIC_PREFIXES = {
    "info", "contact", "office", "accueil", "reception", "hello", "bonjour",
    "team", "mail", "general", "enquiries", "enquiry", "inquiries", "inquiry",
    "admin", "support", "service", "cs", "scs", "rsp", "letschat", "clients",
    "client", "secretariat", "cabinet", "kontakt", "kanzlei", "desk",
    "frontdesk", "post", "mailroom", "customerservice", "clientservice",
}

FUNCTIONAL_OWNER_PREFIXES = {
    "regulatory", "ra", "quality", "qa", "qara", "compliance", "dpo", "privacy",
    "security", "secops", "clinical", "clinicaltrials", "medinfo",
    "pharmacovigilance", "pv", "pms", "psur", "vigilance", "legal", "juridique",
    "counsel", "ip", "patents", "partners", "direction", "ceo", "founder",
    "cto", "ciso",
}

_SYSTEM_ROLE_BLACKLIST_PREFIXES = (
    "noreply", "no-reply", "donotreply", "do-not-reply", "mailer-daemon",
    "postmaster", "bounce", "bounces", "unsubscribe",
)

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
# 1C. Deliverability Shield (Email/MX Hygiene) & Smoking-Gun Trigger Gate
# ---------------------------------------------------------------------------

def classify_recipient_mailbox(email_addr: str) -> str:
    """Classify mailbox into 'receptionist_generic', 'functional_owner', or 'named_direct'."""
    em = (email_addr or "").strip().lower()
    if "@" not in em:
        return "receptionist_generic"
    local = em.split("@", 1)[0]
    tokens = [t for t in re.split(r"[._+-]+", local) if t]
    if local in FUNCTIONAL_OWNER_PREFIXES or any(t in FUNCTIONAL_OWNER_PREFIXES for t in tokens):
        return "functional_owner"
    if (
        local in RECEPTIONIST_GENERIC_PREFIXES
        or any(t in RECEPTIONIST_GENERIC_PREFIXES for t in tokens)
        or local in ("paris", "london", "zurich", "geneva", "mir")
    ):
        return "receptionist_generic"
    return "named_direct"


def parse_mx_answer_record(raw_data: str) -> tuple[int | None, str]:
    """Parse a DoH MX answer data string such as '10 aspmx.l.google.com.' or '0 .'."""
    txt = str(raw_data or "").strip().strip('"')
    parts = txt.split()
    if len(parts) >= 2 and parts[0].isdigit():
        prio = int(parts[0])
        exch = parts[1].strip().rstrip(".").lower() if parts[1].strip() != "." else "."
        return prio, exch
    exch = txt.rstrip(".").lower() if txt != "." else "."
    return None, exch


def is_valid_mx_exchange(exchange: str, priority: int | None = None) -> tuple[bool, str]:
    """Validate an MX exchange target, rejecting Null MX (0 .), placeholders, and parked/sinkhole hosts."""
    ex = (exchange or "").strip().lower()
    if not ex or ex == "." or (priority == 0 and ex in ("", ".")):
        return False, "NULL_MX_REJECTED"
    if "." not in ex or len(ex) < 4:
        return False, f"INVALID_MX_HOST:{ex}"
    for kw in PARKED_OR_SINKHOLE_MX_KEYWORDS:
        if kw in ex:
            return False, f"PARKED_OR_SINKHOLE_MX:{kw}"
    return True, "OK"


def query_mx_records_doh(domain: str, timeout: float = 5.0) -> list[tuple[int, str]]:
    """Query public DNS MX records via Google DoH (`resolve.dns.google`) with Cloudflare fallback."""
    dom = (domain or "").strip().lower().rstrip(".")
    if not dom or "." not in dom:
        return []
    endpoints = [
        ("https://resolve.dns.google/resolve", {"name": dom, "type": "MX"}),
        ("https://cloudflare-dns.com/dns-query", {"name": dom, "type": "MX"}),
    ]
    headers = {
        "Accept": "application/dns-json",
        "User-Agent": "Sentinel-Compliance-Deliverability-Check/1.0",
    }
    for url, params in endpoints:
        try:
            r = requests.get(url, params=params, headers=headers, timeout=timeout)
            if r.status_code != 200:
                continue
            data = r.json() or {}
            status = data.get("Status", 0)
            answers = data.get("Answer") or []
            parsed: list[tuple[int, str]] = []
            for ans in answers:
                if ans.get("type") not in (None, 15):
                    continue
                prio, exch = parse_mx_answer_record(str(ans.get("data", "")))
                parsed.append((0 if prio is None else prio, exch))
            if parsed or status == 0:
                return sorted(parsed, key=lambda x: x[0])
        except Exception:
            continue
    return []


def _shares_corporate_brand(em_dom: str, tgt_dom: str) -> bool:
    """Return True if two distinct corporate domains share a clear company brand stem or prefix."""
    a = em_dom.lower().strip(".")
    b = tgt_dom.lower().strip(".")
    if a == b or a.endswith("." + b) or b.endswith("." + a):
        return True
    a_head = a.split(".", 1)[0]
    b_head = b.split(".", 1)[0]
    generic = {
        "labs", "lab", "clinic", "clinics", "health", "medical", "medtech",
        "pharma", "bio", "biotech", "group", "global", "diag", "diagnostics",
        "cabinet", "sante", "legal", "law", "cpa", "cpas", "advisors",
    }
    a_tokens = [p for p in re.split(r"[^a-z0-9]+", a_head) if len(p) >= 4 and p not in generic]
    b_tokens = [p for p in re.split(r"[^a-z0-9]+", b_head) if len(p) >= 4 and p not in generic]
    a_flat = re.sub(r"[^a-z0-9]", "", a_head)
    b_flat = re.sub(r"[^a-z0-9]", "", b_head)
    if any(tok in b_flat for tok in a_tokens) or any(tok in a_flat for tok in b_tokens):
        return True
    # Common brand prefix >= 5 chars
    plen = 0
    for c1, c2 in zip(a_flat, b_flat):
        if c1 == c2:
            plen += 1
        else:
            break
    if plen >= 5:
        return True
    # Established acronym / short-stem sister pair (e.g. mscr.in <-> msclinical.com)
    if len(a_flat) >= 2 and len(b_flat) >= 2:
        shorter, longer = (a_flat, b_flat) if len(a_flat) <= len(b_flat) else (b_flat, a_flat)
        if 3 <= len(shorter) <= 5 and shorter[:2] == longer[:2] and len(set(shorter) & set(longer)) >= 3:
            return True
    return False


def verify_email_and_domain_hygiene(
    email_addr: str,
    target_domain: str = "",
    check_mx: bool = True,
    allow_verified_webmail: bool = False,
) -> tuple[bool, str, dict[str, Any]]:
    """
    Zero-cost pre-send email & domain hygiene gate:
      - Syntax validation & role blacklist (`noreply`, `mailer-daemon`, etc.)
      - Disposable & parked domain rejection
      - Free webmail rejection (`gmail.com`, `yahoo.com`, etc.) unless `allow_verified_webmail=True`
      - Corporate domain-match verification against `target_domain` (exact or verified sister domain)
      - Google DoH MX verification rejecting missing MX, RFC 7505 Null MX (`0 .`), and parked/sinkhole MXs
    """
    em = (email_addr or "").strip().lower()
    mailbox_class = classify_recipient_mailbox(em)
    meta: dict[str, Any] = {
        "email": em,
        "target_domain": (target_domain or "").strip().lower(),
        "mailbox_class": mailbox_class,
        "domain_match": "unknown",
        "mx_hosts": [],
    }
    if not re.fullmatch(r"[a-z0-9._%+-]{1,64}@[a-z0-9.-]+\.[a-z]{2,15}", em) or ".." in em:
        return False, f"INVALID_EMAIL_SYNTAX:{em}", meta

    local, em_dom = em.split("@", 1)
    if any(local == p or local.startswith(p + ".") or local.startswith(p + "-") for p in _SYSTEM_ROLE_BLACKLIST_PREFIXES):
        return False, f"SYSTEM_NO_REPLY_MAILBOX:{local}", meta

    if em_dom in DISPOSABLE_EMAIL_DOMAINS:
        return False, f"BLOCKED_DISPOSABLE_DOMAIN:{em_dom}", meta

    if any(tok in em_dom for tok in ("example.", "yourdomain", "domain.", "sedoparking", "hugedomains", "afternic", "parklogic")):
        return False, f"BLOCKED_PARKED_DOMAIN:{em_dom}", meta

    if em_dom in FREE_WEBMAIL_DOMAINS and not allow_verified_webmail:
        return False, f"BLOCKED_FREE_WEBMAIL:{em_dom}", meta

    tgt = (target_domain or "").strip().lower().removeprefix("www.")
    if tgt:
        if em_dom == tgt or em_dom.endswith("." + tgt):
            meta["domain_match"] = "exact"
        elif _shares_corporate_brand(em_dom, tgt):
            meta["domain_match"] = "sister_domain"
        else:
            return False, f"OFF_DOMAIN_MISMATCH:{em_dom}!={tgt}", meta

    if check_mx:
        mx_list = query_mx_records_doh(em_dom)
        if not mx_list:
            return False, f"NO_MX_RECORDS:{em_dom}", meta
        valid_hosts: list[str] = []
        last_err = f"NO_VALID_MX:{em_dom}"
        for prio, exch in mx_list:
            ok_mx, mx_reason = is_valid_mx_exchange(exch, priority=prio)
            if ok_mx:
                valid_hosts.append(f"{prio} {exch}")
            else:
                last_err = mx_reason
        if not valid_hosts:
            return False, last_err, meta
        meta["mx_hosts"] = valid_hosts

    return True, "OK", meta


def count_recent_24h_sent_breakdown(
    ledger_csv: Path | None,
    master_csv: Path | None = None,
    hours: float = 24.0,
    now_utc: dt.datetime | None = None,
) -> dict[str, int]:
    """
    Count outbound sends over the rolling 24h window broken down into `primary` vs `followup`,
    deduplicating shared events logged in both `sent_ledger.csv` and `outreach_master_status.csv`.
    """
    ref_now = now_utc or dt.datetime.now(dt.timezone.utc)
    cutoff = ref_now - dt.timedelta(hours=hours)

    def _parse_ts(raw: str) -> dt.datetime | None:
        s = (raw or "").strip()
        if not s:
            return None
        try:
            d = dt.datetime.fromisoformat(s.replace("Z", "+00:00"))
            if d.tzinfo is None:
                d = d.replace(tzinfo=dt.timezone.utc)
            return d.astimezone(dt.timezone.utc)
        except Exception:
            return None

    followup_keys: set[tuple[str, str]] = set()
    ledger_rows: list[dict[str, str]] = []
    if ledger_csv and ledger_csv.is_file():
        with open(ledger_csv, "r", encoding="utf-8", errors="ignore", newline="") as f:
            for row in csv.DictReader(f):
                ts = _parse_ts(row.get("timestamp_utc") or row.get("timestamp") or "")
                if ts and ts >= cutoff:
                    ledger_rows.append(row)

    master_followups = 0
    master_primaries = 0
    master_ids: set[str] = set()
    if master_csv and master_csv.is_file():
        with open(master_csv, "r", encoding="utf-8", errors="ignore", newline="") as f:
            for row in csv.DictReader(f):
                ts = _parse_ts(row.get("Timestamp_UTC") or row.get("timestamp_utc") or "")
                if not ts or ts < cutoff:
                    continue
                batch = (row.get("Wave") or row.get("batch") or "").strip()
                dom = (row.get("Domain") or row.get("domain") or "").strip().lower()
                em = (row.get("To_Email") or row.get("to_email") or "").strip().lower()
                gid = (row.get("Gmail_ID") or row.get("gmail_message_id") or "").strip()
                if gid:
                    master_ids.add(gid)
                if batch.startswith("FollowUp"):
                    master_followups += 1
                    if dom or em:
                        followup_keys.add((dom, em))
                else:
                    master_primaries += 1

    if ledger_rows:
        fu_cnt = 0
        prim_cnt = 0
        for r in ledger_rows:
            dom = (r.get("domain") or "").strip().lower()
            em = (r.get("to_email") or r.get("email") or "").strip().lower()
            note = (r.get("send_type") or r.get("batch") or "").strip().lower()
            if "followup" in note or (dom, em) in followup_keys:
                fu_cnt += 1
            else:
                prim_cnt += 1
        fu_cnt = max(fu_cnt, master_followups)
        total = max(len(ledger_rows), fu_cnt + prim_cnt)
        return {"total": total, "primary": max(0, total - fu_cnt), "followup": fu_cnt}

    return {"total": master_primaries + master_followups, "primary": master_primaries, "followup": master_followups}


_GENERIC_MAUDE_PROBLEM_MARKERS = (
    "adverse event without identified",
    "no known device problem",
    "device problem monitoring",
    "appropriate term / code not available",
    "unknown",
    "insufficient information",
)

_REGULATED_HIGH_STAKES_SECTORS = {
    "HealthTech", "healthtech", "Legal/IP", "law_ip", "MedTech OEM", "MedTech RA",
    "Boutique RA", "medtech_cer", "Diagnostics", "diagnostics_lab", "Clinical Genomics",
    "Biotech / CRO", "cro_reg", "CDMO / Pharma", "Veterinary Pharma",
}


def extract_audit_trigger_metrics(
    track: str,
    payload: dict[str, Any],
    sector: str = "",
) -> dict[str, Any]:
    """Normalize track evidence JSON metrics deterministically across Tracks 1, 2, and 3."""
    tk = (track or "sentinel_compliance").strip()
    if tk == "pms_openfda_psur":
        ms = payload.get("maude_summary") or {}
        tot = int(ms.get("total_events_analyzed") or 0)
        ev_c = ms.get("event_type_counts") or {}
        probs = ms.get("top_device_problems") or []
        top_prob = str(probs[0].get("problem", "")).strip() if probs else ""
        recalls = payload.get("recalls_and_510k") or []
        trials = payload.get("clinical_trials") or []
        spikes = list(ms.get("signal_spikes") or [])
        monthly = ms.get("monthly_trend") or []
        if not spikes and len(monthly) > 3:
            try:
                pms_dir = Path(__file__).resolve().parent.parent / "pms-clinicaltrials-openfda-monitor"
                if str(pms_dir) not in sys.path:
                    sys.path.insert(0, str(pms_dir))
                import pms_monitor
                spikes = pms_monitor.compute_maude_signal_spikes(monthly, z_threshold=1.8)
            except Exception:
                spikes = []
        max_z = max((float(s.get("z_score", 0.0) or 0.0) for s in spikes), default=0.0)
        return {
            "total_events": tot,
            "malfunctions": int(ev_c.get("Malfunction", 0) or 0),
            "injuries": int(ev_c.get("Injury", 0) or 0),
            "deaths": int(ev_c.get("Death", 0) or 0),
            "top_problem": top_prob,
            "recalls_510k": len(recalls),
            "clinical_trials": len(trials),
            "spike_count": len(spikes),
            "max_z_score": round(max_z, 2),
        }

    if tk == "clinical_lit_prisma":
        pv = payload.get("prisma_verified") or {}
        cs = payload.get("curate_stats") or {}
        id_raw = int(pv.get("total_identified") or cs.get("identified_raw") or payload.get("identified_raw") or 0)
        dups = int(pv.get("duplicates_removed") or cs.get("duplicates_removed") or 0)
        exc = (
            int(pv.get("excluded_at_screening", 0) or 0) + int(pv.get("excluded_at_full_text", 0) or 0)
            or int(cs.get("excluded_missing_content", 0) or 0) + int(cs.get("excluded_prior_to_window", 0) or 0) + int(cs.get("excluded_beyond_cap", 0) or 0)
        )
        inc = int(pv.get("studies_included") or cs.get("included_final") or payload.get("included_final") or 0)
        filtered = dups + exc
        # Deterministic workload heuristic: 0.18h screening/abstract + 0.10h dedupe/exclusion logging + 0.35h Table 1 & Vancouver synthesis
        est_hours_saved = round(max(1.5, id_raw * 0.18 + filtered * 0.10 + inc * 0.35), 1)
        return {
            "identified_raw": id_raw,
            "duplicates_removed": dups,
            "excluded_cnt": exc,
            "filtered_out": filtered,
            "included_final": inc,
            "est_hours_saved": est_hours_saved,
        }

    # Track 1: Sentinel compliance
    findings = {f.get("id", ""): f for f in (payload.get("findings") or []) if f.get("id")}
    spf_diag = payload.get("spf_diagnostics") or {}
    cmp_diag = payload.get("cmp_diagnostics") or {}
    eml01 = findings.get("EML-01", {})
    eml02 = findings.get("EML-02", {})
    eml04 = findings.get("EML-04", {})
    prv01 = findings.get("PRV-01", {})
    prv02 = findings.get("PRV-02", {})
    sec02 = findings.get("SEC-02", {})
    sec09 = findings.get("SEC-09", {})

    spf_lookups = spf_diag.get("total_lookups")
    if spf_lookups is None:
        m_spf = re.search(r"(\d+)\s*/\s*10\s*DNS\s*lookups|triggers\s*(\d+)\s*DNS\s*lookups", str(eml02.get("evidence", "")), re.I)
        if m_spf:
            spf_lookups = int(m_spf.group(1) or m_spf.group(2))

    return {
        "overall_score": int(payload.get("overall_score", 0) or 0),
        "fail_count": int(payload.get("fail_count") if payload.get("fail_count") is not None else sum(1 for f in findings.values() if f.get("status") == "FAIL")),
        "warn_count": int(payload.get("warn_count") if payload.get("warn_count") is not None else sum(1 for f in findings.values() if f.get("status") == "WARN")),
        "pass_count": int(payload.get("pass_count") if payload.get("pass_count") is not None else sum(1 for f in findings.values() if f.get("status") == "PASS")),
        "spf_status": eml02.get("status", ""),
        "spf_lookups": spf_lookups,
        "spf_exceeds": bool(spf_diag.get("exceeds_limit")) or ("exceeding 10" in str(eml02.get("title", "") + " " + eml02.get("evidence", "")).lower()),
        "dmarc_status": eml01.get("status", ""),
        "dmarc_p_none": "p=none" in str(eml01.get("evidence", "")).lower() or eml01.get("status") == "WARN",
        "caa_missing": eml04.get("status") != "PASS",
        "hsts_missing": sec02.get("status") == "FAIL",
        "fonts_leak": prv01.get("status") == "FAIL",
        "tracker_leak": prv02.get("status") in ("WARN", "FAIL"),
        "cmp_has_reject": bool(cmp_diag.get("has_reject_copy_in_html", False)),
        "security_txt_missing": sec09.get("status") != "PASS",
        "sector": sector,
    }


def evaluate_smoking_gun_trigger(
    track: str,
    payload: dict[str, Any],
    sector: str = "",
) -> tuple[bool, str, dict[str, Any]]:
    """
    High-Severity Trigger ('Smoking Gun') Lead Gate across Tracks 1, 2, and 3.
    Rejects mild/low-urgency targets and accepts only verifiable, high-urgency pain signals.
    """
    tk = (track or "sentinel_compliance").strip()
    m = extract_audit_trigger_metrics(tk, payload, sector=sector)

    if tk == "pms_openfda_psur":
        prob_low = (m["top_problem"] or "").lower()
        concrete_problem = bool(prob_low) and not any(g in prob_low for g in _GENERIC_MAUDE_PROBLEM_MARKERS)
        if m["total_events"] >= 20 and concrete_problem:
            return True, f"MAUDE_{m['total_events']}_EVENTS_CONCRETE_PROBLEM", m
        if m["max_z_score"] >= 1.8 and m["spike_count"] >= 1:
            return True, f"MAUDE_TREND_SPIKE_Z{m['max_z_score']}", m
        if m["clinical_trials"] >= 2 and (m["total_events"] >= 10 or m["recalls_510k"] >= 1):
            return True, f"ACTIVE_TRIALS_{m['clinical_trials']}_PLUS_FDA_SIGNALS", m
        return False, f"PMS_LOW_SIGNAL_NO_TRIGGER:{m['total_events']}", m

    if tk == "clinical_lit_prisma":
        if m["identified_raw"] >= 12 and m["included_final"] >= 5 and m["filtered_out"] >= 2:
            return True, f"PRISMA_{m['identified_raw']}TO{m['included_final']}_SAVES_{m['est_hours_saved']}H", m
        return False, f"LIT_LOW_SIGNAL_NO_TRIGGER:{m['identified_raw']}/{m['included_final']}/filt={m['filtered_out']}", m

    # Track 1: Sentinel compliance
    if m["overall_score"] > 75:
        return False, f"MILD_SCORE_{m['overall_score']}", m

    triggers: list[str] = []
    if (
        m["spf_status"] == "FAIL"
        or m["spf_exceeds"]
        or (m["spf_lookups"] is not None and int(m["spf_lookups"]) >= 9)
        or (m["spf_status"] == "WARN")
    ):
        triggers.append("SPF_PERMERROR_OR_BROKEN")
    if m["dmarc_status"] == "FAIL" or (m["dmarc_p_none"] and (m["caa_missing"] or m["hsts_missing"])):
        triggers.append("DMARC_UNENFORCED_WITH_CAA_OR_HSTS_GAP")
    if m["fonts_leak"] or (m["tracker_leak"] and not m["cmp_has_reject"]):
        triggers.append("PRECONSENT_LEAK_NO_REJECT_SYMMETRY")
    if m["security_txt_missing"] and m["fail_count"] >= 1 and (sector or "").strip() in _REGULATED_HIGH_STAKES_SECTORS:
        triggers.append("REGULATED_MISSING_SECURITY_TXT_PLUS_FAILS")

    if not triggers:
        return False, f"NO_SMOKING_GUN_HEADERS_ONLY:{m['overall_score']}", m
    m["triggers"] = triggers
    return True, triggers[0], m


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
# 3. Strict 85–125 Word Professionalism Gate & Single-Pass Humanizer
# ---------------------------------------------------------------------------

def count_words(text: str) -> int:
    return len(text.split())


def verify_professionalism(
    subject: str,
    body: str,
    to_email: str,
    required_domain: str | None = None,
    min_words: int = 85,
    max_words: int = 125,
    require_price: bool = True,
) -> tuple[bool, list[str]]:
    """Enforce strict 85–125 word count, real B2B pricing, zero 'for free' or '-bot' URLs, domain alignment, and opt-out."""
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
    """Single-pass high-impact humanizer removing stiff AI phrases while keeping a single routing em-dash."""
    out = text
    for pat, repl in HIGH_IMPACT_HUMANIZER_REPLACEMENTS:
        out = re.sub(pat, repl, out)

    # Preserve up to one crisp routing em-dash (e.g., 'Hello — could you...'), strip excess em-dash chains
    if out.count("—") > 1:
        out = out.replace(" — ", ", ").replace("—", ", ")
    out = re.sub(r"[ \t]{2,}", " ", out)
    out = re.sub(r"\n{3,}", "\n\n", out)
    return out.strip()


def calibrate_word_count(body: str, lang: str = "en", min_words: int = 85, max_words: int = 125) -> str:
    """
    Fine-tune word count after single-pass humanization so the final email lands strictly
    inside [min_words, max_words] (85–125 words) without cutting sentences abruptly.
    """
    wc = count_words(body)
    if min_words <= wc <= max_words:
        return body

    # If slightly under min_words, insert a natural methodology/deliverable detail before the closing opt-out
    if wc < min_words:
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

    # If over max_words, tighten non-essential modifiers first while preserving metrics and routing
    wc = count_words(body)
    if wc > max_words:
        trim_map = [
            (" and includes a post-deployment verification re-scan once your team applies the changes", ""),
            (" and includes a post-deployment verification re-scan", ""),
            (" with zero intrusive traffic", ""),
            (" using my passive 25-control Sentinel evaluation system", " across 25 passive checks"),
            (" (scorecard and evaluation system PDF attached)", " (scorecard & guide attached)"),
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
            ("the full Word/Excel audit plus ready-to-paste DNS and server headers", "the Word/Excel dossier and turnkey DNS/server headers"),
            ("we use our automated IT fix files to simplify this and deliver ", "I deliver "),
            ("for a flat fee of ", "for "),
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
            ("Specifically, the scan flagged that ", "Scan findings: "),
            ("Konkret fielen diese Punkte auf: ", "Befunde: "),
            ("L'analyse relève notamment : ", "Constats : "),
            ("If this is not a priority right now, simply reply 'no' and I will not follow up.", "If not relevant, reply 'no' and I won't follow up."),
            ("Si ce n'est pas pertinent, un simple « non » suffit et je ne relancerai pas.", "Un simple « non » suffit si ce n'est pas pertinent."),
            ("Falls kein Bedarf besteht, genügt ein kurzes «Nein», dann schreibe ich nicht erneut.", "Bei Nichtinteresse genügt ein kurzes «Nein», ohne Nachfassen."),
            ("consistently ", ""),
            ("evaluated ", "checked "),
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
    min_words: int = 85,
    max_words: int = 125,
    require_price: bool = True,
) -> dict[str, Any]:
    """
    Run a single high-impact humanizer pass (`max_passes=1` default), calibrate word count
    to 85–125 words, and verify professionalism + detector score.
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


def load_custom_domain_display() -> str:
    """
    Return the user's configured custom domain (without scheme) for outreach/briefing copy,
    or empty string when only the default `-bot.github.io` host is active.
    """
    cfg_path = Path(__file__).resolve().parent / "client_ops_config.json"
    if not cfg_path.is_file():
        return ""
    try:
        cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
        prov = cfg.get("provider", {})
        dom = (prov.get("custom_domain") or "").strip().rstrip("/")
        if not dom:
            w = (prov.get("website_url") or "").strip()
            if w and "kaledbouchagraoui7-bot" not in w.lower():
                dom = re.sub(r"^https?://", "", w).rstrip("/")
        if dom and "kaledbouchagraoui7-bot" not in dom.lower():
            return dom
    except Exception:
        pass
    return ""


def receptionist_routing_line(
    to_email: str,
    company_name: str = "",
    lang: str = "en",
    sector: str = "",
) -> str:
    """
    Return a crisp 1-line receptionist-routing ask when sending to generic inboxes
    (`info@`, `contact@`, `accueil@`, `hello@`, etc.), or '' for functional/named owners.
    """
    if classify_recipient_mailbox(to_email) != "receptionist_generic":
        return ""
    lg = (lang or "en").strip().lower()
    comp = (company_name or "").strip()
    at_comp_fr = f" chez {comp}" if comp else ""
    at_comp_en = f" at {comp}" if comp else ""
    at_comp_de = f" bei {comp}" if comp else ""
    is_life_sci = any(
        k in (sector or "").lower()
        for k in ("medtech", "biotech", "cro", "diag", "pharma", "genom", "health", "dermo", "nutra", "vet", "ra")
    )

    if lg == "fr":
        role = "responsable Qualité/Réglementaire ou DPO" if is_life_sci else "responsable conformité, juridique ou DPO"
        return f"Bonjour — pourriez-vous transmettre ces éléments à votre {role}{at_comp_fr} ?"
    if lg == "de":
        role = "die Leitung Qualität/Regulatory oder Datenschutz" if is_life_sci else "die Leitung Compliance, Recht oder Datenschutz"
        return f"Guten Tag — könnten Sie diese Übersicht bitte an {role}{at_comp_de} weiterleiten?"
    role = "regulatory affairs, QA, or IT security" if is_life_sci else "compliance, legal, or IT security"
    return f"Hello — could you forward this brief to whoever oversees {role}{at_comp_en}?"


# ---------------------------------------------------------------------------
# 4. Tailored 85–125 Word Briefing Builder (Specific Findings + Routing + Price)
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
        return "£390" if is_premium else "£340"
    if c == "US":
        return "$450" if is_premium else "$380"
    if c == "CA":
        return "CAD 520" if is_premium else "CAD 440"
    if c == "AU":
        return "AUD 580" if is_premium else "AUD 490"
    if c == "CH":
        return "CHF 450" if is_premium else "CHF 350"
    if c == "SG":
        return "SGD 520" if is_premium else "SGD 440"
    return "EUR 420" if is_premium else "EUR 350"


def summarize_technical_gaps(audit: dict[str, Any], lang: str = "en") -> list[str]:
    domain = audit["domain"]
    fails = {f["id"]: f for f in audit["findings"] if f["status"] == "FAIL"}
    warns = {f["id"]: f for f in audit["findings"] if f["status"] == "WARN"}
    m = extract_audit_trigger_metrics("sentinel_compliance", audit)
    spf_n = m.get("spf_lookups")

    points: list[str] = []
    if lang == "de":
        if "EML-01" in fails:
            points.append(f"kein aktiver _dmarc.{domain} DNS-Schutz")
        elif "EML-01" in warns:
            points.append(f"_dmarc.{domain} nur auf p=none")
        if "EML-02" in fails:
            points.append(f"SPF fehlerhaft oder >10 Lookups ({spf_n}/10)" if spf_n else "fehlendes/permissives SPF")
        elif spf_n is not None and int(spf_n) >= 9:
            points.append(f"SPF-Limit fast erreicht ({spf_n}/10 Lookups)")
        if "PRV-01" in fails:
            points.append("externe Google Fonts vor Einwilligung")
        elif "PRV-02" in warns or "PRV-02" in fails:
            points.append("Tracker-Skripte vor Einwilligung ohne Ablehnen-Button")
        elif "PRV-03" in fails:
            points.append("Cookies ohne Secure/HttpOnly/SameSite")
        if "SEC-02" in fails or "SEC-03" in fails:
            points.append("fehlende HSTS/CSP-Header")
        if not points:
            points.append("fehlende HTTP-Security-Header und DNS-CAA")
        return points[:3]

    if lang == "fr":
        if "EML-01" in fails:
            points.append(f"aucun DNS _dmarc.{domain} actif")
        elif "EML-01" in warns:
            points.append(f"_dmarc.{domain} en p=none sans blocage")
        if "EML-02" in fails:
            points.append(f"SPF >10 requêtes DNS ({spf_n}/10)" if spf_n else "SPF absent ou permissif")
        elif spf_n is not None and int(spf_n) >= 9:
            points.append(f"SPF proche du plafond ({spf_n}/10 requêtes DNS)")
        if "PRV-01" in fails:
            points.append("Google Fonts distants avant consentement")
        elif "PRV-02" in warns or "PRV-02" in fails:
            points.append("traceurs chargés avant consentement sans refus 1-clic")
        elif "PRV-03" in fails:
            points.append("cookies sans Secure/HttpOnly/SameSite")
        if "SEC-02" in fails or "SEC-03" in fails:
            points.append("en-têtes HSTS et CSP absents")
        if not points:
            points.append("en-têtes HTTP et restriction DNS CAA absents")
        return points[:3]

    # English
    if "EML-01" in fails:
        points.append(f"missing _dmarc.{domain} enforcement")
    elif "EML-01" in warns:
        points.append(f"_dmarc.{domain} stuck at p=none")
    if "EML-02" in fails:
        points.append(f"SPF exceeding 10-lookup limit ({spf_n}/10)" if spf_n else "missing/permissive SPF record")
    elif spf_n is not None and int(spf_n) >= 9:
        points.append(f"SPF lookup budget near limit ({spf_n}/10 lookups)")
    if "PRV-01" in fails:
        points.append("remote Google Fonts IP leak before consent")
    elif "PRV-02" in warns or "PRV-02" in fails:
        points.append("pre-consent analytics scripts without Reject symmetry")
    elif "PRV-03" in fails:
        points.append("cookies missing Secure/HttpOnly/SameSite flags")
    if "SEC-02" in fails or "SEC-03" in fails:
        points.append("missing HSTS and CSP headers")
    if not points:
        points.append("missing HTTP security headers and DNS CAA")
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
    Generate a personalized 85–125 word email combining:
      1. Automatic 1-line receptionist routing ask for generic mailboxes (`info@`, `contact@`, etc.)
      2. Immediate Sentence-1 numerical scan findings (`score/100`, fail count, SPF/DMARC/font metrics)
      3. Concrete operational problem solved (`problem_solved`) + attached PNG scorecard & guide PDF
      4. Clear fixed price (`price_str`), no `-bot` URLs unless custom domain set, and polite opt-out
    """
    domain = audit["domain"]
    score = int(audit["overall_score"])
    m = extract_audit_trigger_metrics("sentinel_compliance", audit, sector=sector)
    fail_cnt = m["fail_count"]
    total_chk = int(audit.get("total_checks") or len(audit.get("findings") or []) or 25)
    price = price_str.strip() or default_price_for_country(country, sector)
    tech_points = summarize_technical_gaps(audit, lang=lang)
    tech_joined = "; ".join(tech_points[:2])
    route_line = receptionist_routing_line(to_email, company_name=company_name, lang=lang, sector=sector)
    custom_dom = load_custom_domain_display()

    if lang == "de":
        opening = route_line or f"Guten Tag {company_name}-Team,"
        prob_line = problem_solved.strip() or (
            "Diese Korrekturen stoppen E-Mail-Spoofing sowie unnötige DSGVO-/revDSG-Treffer."
        )
        site_line = f"\nReferenzen & AGB: https://{custom_dom}\n" if custom_dom else "\n"
        subj = f"1-Seiten-Risikovorschau für {domain} ({score}/100)"
        body = (
            f"{opening}\n\n"
            f"Ein passiver 25-Kontrollen-Scan von {domain} ergab {score}/100 Punkte ({fail_cnt} Fehler): "
            f"{tech_joined}. {prob_line}\n\n"
            f"Anbei die 1-Seiten-Risikovorschau (PNG) und der System-Leitfaden (PDF). Für {price} pauschal "
            f"liefere ich Word-Bericht, Excel-Register, IT-Korrekturdateien und Kontroll-Scan.{site_line}"
            f"Soll ich den Projektumfang senden?\n\n"
            f"Falls kein Bedarf besteht, genügt ein kurzes «Nein».\n\n"
            f"Freundliche Grüsse,\nKaled Bouchagraoui"
        )
        return subj, calibrate_word_count(body, lang="de", min_words=85, max_words=125)

    if lang == "fr":
        opening = route_line or f"Bonjour l'équipe {company_name},"
        prob_line = problem_solved.strip() or (
            "Corriger ces points protège vos courriels contre le spam et ferme ces écarts RGPD avant tout audit."
        )
        site_line = f"\nExemples & CGV : https://{custom_dom}\n" if custom_dom else "\n"
        subj = f"Aperçu risques {domain} ({score}/100, {fail_cnt} écarts)"
        body = (
            f"{opening}\n\n"
            f"Un relevé passif sur {total_chk} contrôles place {domain} à {score}/100 ({fail_cnt} échecs) : "
            f"{tech_joined}. {prob_line}\n\n"
            f"La fiche 1 page (PNG) et la méthode (PDF) sont jointes. Pour {price} fixe, je livre le dossier "
            f"Word/Excel, les correctifs IT prêts à poser pour {domain} et l'attestation re-vérifiée.{site_line}"
            f"Puis-je envoyer le périmètre ?\n\n"
            f"Si ce n'est pas pertinent, un simple « non » suffit.\n\n"
            f"Cordialement,\nKaled Bouchagraoui"
        )
        return subj, calibrate_word_count(body, lang="fr", min_words=85, max_words=125)

    # English
    opening = route_line or f"Hello {company_name} team,"
    prob_line = problem_solved.strip() or (
        "Closing these prevents outbound spam-folder filtering and removes avoidable GDPR/vendor-audit flags."
    )
    site_line = f"\nPortfolio & terms: https://{custom_dom}\n" if custom_dom else "\n"
    subj = f"{domain} compliance scan: {score}/100 ({fail_cnt} failed checks)"
    body = (
        f"{opening}\n\n"
        f"A passive {total_chk}-control scan on {domain} scored {score}/100 ({fail_cnt} failed checks): "
        f"{tech_joined}. {prob_line}\n\n"
        f"Your 1-page visual scorecard (PNG) and evaluation guide (PDF) are attached. For {price} flat, "
        f"I deliver the Word audit, 4-sheet Excel risk register, turnkey IT fix files, and verification "
        f"re-scan.{site_line}Should I send over the scope?\n\n"
        f"If this is not a priority right now, reply 'no' and I won't follow up.\n\n"
        f"Best regards,\nKaled Bouchagraoui"
    )
    return subj, calibrate_word_count(body, lang="en", min_words=85, max_words=125)


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


def is_email_suppressed(
    email_addr: str,
    domain: str,
    sup_domains: dict[str, str],
    sup_emails: dict[str, str],
) -> tuple[bool, str]:
    """Return `(is_suppressed, reason)` matching either exact email or suppressed corporate domain."""
    em = (email_addr or "").strip().lower()
    dom = (domain or "").strip().lower()
    if em and em in sup_emails:
        return True, sup_emails[em]
    if dom and dom in sup_domains:
        return True, sup_domains[dom]
    return False, ""


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
    check_mx: bool = False,
) -> dict[str, Any]:
    """Run deliverability hygiene check, single-pass humanizer, and strict 85–125w QA gate on `manifest_csv`."""
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

        hyg_ok, hyg_reason, _hyg_meta = verify_email_and_domain_hygiene(
            to_email,
            target_domain=domain,
            check_mx=check_mx,
            allow_verified_webmail=False,
        )
        if not hyg_ok:
            qa_results.append({
                "domain": domain,
                "to_email": to_email,
                "lang": lang,
                "status": "BLOCKED_HYGIENE",
                "word_count": 0,
                "avg_ai_pct": 0.0,
                "d1_cliche": 0.0,
                "d2_burstiness": 0.0,
                "d3_syntactic": 0.0,
                "d4_boilerplate": 0.0,
                "passes_used": 0,
                "professionalism_ok": False,
                "professionalism_issues": f"Hygiene reject: {hyg_reason}",
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
            min_words=85,
            max_words=125,
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
        description="Personalized 85–125 Word B2B Email Generator, Single-Pass Humanizer & Dispatcher."
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
    parser.add_argument("--check-mx", action="store_true", help="Verify live MX records via DNS-over-HTTPS (default enabled automatically for --dispatch smtp)")
    parser.add_argument("--skip-mx", action="store_true", help="Skip live DNS MX lookups during SMTP dispatch")
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
        check_mx=(not args.skip_mx) and (args.check_mx or args.dispatch == "smtp"),
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
