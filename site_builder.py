#!/usr/bin/env python3
"""
site_builder.py — Zero-Cost Bilingual (EN/FR) Swiss-Editorial B2B Storefront Builder
===================================================================================

Generates a complete, static, zero-external-dependency storefront bundle (`index.html`,
`robots.txt`, `.well-known/security.txt`, and local self-hosted preview assets) for
GitHub Pages, Cloudflare Pages, or Netlify at EUR 0.00 cost.

Engineered to pass all 25 passive Sentinel controls (no remote Google Fonts IP leak,
full semantic HTML/WCAG 2.1 AA, JSON-LD Schema.org metadata, strict security headers).
"""

from __future__ import annotations

import html
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from legal_terms import TERMS_VERSION, load_provider_config

SUITE_DIR = Path(__file__).resolve().parent


def _specimen_inspector_css() -> str:
    """Return self-hosted CSS for the interactive 4-track deliverable previewer."""
    return """
    .specimen-inspector {
      background: var(--slate-bg);
      border: 1px solid var(--border);
      border-top: 4px solid var(--teal);
      border-radius: 6px;
      margin-bottom: 28px;
      overflow: hidden;
    }
    .spec-head-bar {
      padding: 16px 20px;
      background: #FFFFFF;
      border-bottom: 1px solid var(--border);
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 12px;
    }
    .spec-head-bar h3 {
      margin: 0;
      font-size: 17px;
      color: var(--navy);
    }
    .spec-badge-note {
      background: #FFF2CC;
      color: #713F12;
      border: 1px solid #FDE047;
      font-size: 12px;
      font-weight: 700;
      padding: 4px 10px;
      border-radius: 4px;
    }
    .spec-tabs {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      padding: 12px 20px;
      background: #F1F5F9;
      border-bottom: 1px solid var(--border);
    }
    .spec-tab {
      border: 1px solid var(--border);
      background: #FFFFFF;
      color: var(--navy-soft);
      font-family: inherit;
      font-size: 13px;
      font-weight: 700;
      padding: 8px 14px;
      border-radius: 5px;
      cursor: pointer;
    }
    .spec-tab:hover {
      border-color: var(--teal);
      color: var(--teal-dark);
    }
    .spec-tab.active, .spec-tab[aria-selected="true"] {
      background: var(--navy);
      border-color: var(--navy);
      color: #FFFFFF;
    }
    .spec-panel {
      display: none;
      padding: 20px;
      background: #FFFFFF;
    }
    .spec-panel.active {
      display: block;
    }
    .spec-meta {
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 10px;
      margin-bottom: 14px;
    }
    .spec-meta p {
      margin: 0;
      font-size: 13.5px;
      color: var(--muted);
    }
    .table-wrap {
      overflow-x: auto;
      border: 1px solid var(--border);
      border-radius: 5px;
      margin-bottom: 14px;
    }
    .spec-table {
      width: 100%;
      border-collapse: collapse;
      font-size: 13px;
      text-align: left;
      background: #FFFFFF;
    }
    .spec-table th {
      background: var(--navy);
      color: #FFFFFF;
      font-weight: 700;
      padding: 9px 12px;
      white-space: nowrap;
      border-right: 1px solid #334155;
    }
    .spec-table td {
      padding: 9px 12px;
      border-top: 1px solid var(--border);
      vertical-align: top;
      color: var(--navy);
    }
    .spec-table tr.qa-flag-row td {
      background: #FFF2CC;
      color: #713F12;
    }
    .badge-pass, .badge-warn, .badge-fail {
      display: inline-block;
      padding: 2px 7px;
      border-radius: 4px;
      font-size: 11.5px;
      font-weight: 700;
      white-space: nowrap;
    }
    .badge-pass { background: #ECFDF5; color: #065F46; border: 1px solid #A7F3D0; }
    .badge-warn { background: #FFFBEB; color: #92400E; border: 1px solid #FDE68A; }
    .badge-fail { background: #FEF2F2; color: #991B1B; border: 1px solid #FECACA; }
    .spec-snippet {
      background: #0F172A;
      color: #E2E8F0;
      border-radius: 5px;
      padding: 12px 14px;
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      font-size: 12.5px;
      line-height: 1.5;
      overflow-x: auto;
      margin: 0;
    }
    .spec-snippet-label {
      font-size: 12px;
      font-weight: 700;
      color: var(--navy-soft);
      margin: 0 0 6px 0;
    }
    .spec-actions {
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
      align-items: center;
    }
    .btn-sample-dl {
      display: inline-block;
      background: var(--ok-bg);
      color: var(--ok-fg);
      border: 1px solid #A7F3D0;
      padding: 8px 13px;
      border-radius: 5px;
      font-size: 13px;
      font-weight: 700;
      text-decoration: none;
    }
    .btn-sample-dl:hover {
      background: #D1FAE5;
      border-color: var(--teal);
    }
"""


def _live_check_css() -> str:
    """Return self-hosted CSS for the on-click client-side DNS / OpenFDA / Europe PMC pre-check and CH/FR strip."""
    return """
    .ch-fr-strip {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 18px;
      margin-top: 26px;
    }
    .jurisdiction-card {
      background: var(--slate-bg);
      border: 1px solid var(--border);
      border-left: 4px solid var(--navy);
      border-radius: 6px;
      padding: 16px 20px;
    }
    .jurisdiction-card.fr-accent {
      border-left-color: var(--teal);
    }
    .jurisdiction-card h3 {
      margin: 0 0 6px 0;
      font-size: 15.5px;
      color: var(--navy);
    }
    .jurisdiction-card p {
      margin: 0 0 8px 0;
      font-size: 13.5px;
      color: var(--muted);
    }
    .jurisdiction-links {
      font-size: 13px;
      font-weight: 600;
      color: var(--navy-soft);
    }
    .jurisdiction-links a {
      color: var(--teal);
      text-decoration: none;
    }
    .jurisdiction-links a:hover {
      text-decoration: underline;
    }
    .live-grid {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 20px;
    }
    .live-card {
      background: #FFFFFF;
      border: 1px solid var(--border);
      border-top: 3.5px solid var(--navy);
      border-radius: 6px;
      padding: 20px;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      gap: 12px;
    }
    .live-card h3 {
      margin: 0 0 6px 0;
      font-size: 16.5px;
      color: var(--navy);
    }
    .live-card p {
      margin: 0 0 10px 0;
      font-size: 13.5px;
      color: var(--muted);
    }
    .live-input-row {
      display: flex;
      gap: 8px;
      margin-bottom: 10px;
    }
    .live-input-row input {
      flex: 1;
      min-width: 0;
      padding: 9px 10px;
      border: 1px solid var(--border);
      border-radius: 5px;
      font-family: inherit;
      font-size: 13.5px;
      background: var(--slate-bg);
    }
    .live-result {
      background: var(--slate-bg);
      border: 1px solid var(--border);
      border-radius: 5px;
      padding: 10px 12px;
      font-size: 12.5px;
      color: var(--navy-soft);
      min-height: 76px;
      white-space: pre-wrap;
      word-break: break-word;
    }
    .live-result a {
      color: var(--teal);
      font-weight: 600;
      text-decoration: none;
    }
    .live-result a:hover {
      text-decoration: underline;
    }
    .intake-secondary-actions {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 10px;
      margin-top: 10px;
    }
    .intake-secondary-actions button {
      cursor: pointer;
      font-family: inherit;
      text-align: center;
    }
    @media (max-width: 860px) {
      .ch-fr-strip, .live-grid, .intake-secondary-actions { grid-template-columns: 1fr; }
    }
"""


def _storefront_core_js(intake_url_json: str, email_esc: str) -> str:
    """Return core zero-dependency UI & intake JavaScript without f-string brace conflicts."""
    template = """    function selectTrack(trackVal) {
      var sel = document.getElementById('f-track');
      if (sel) sel.value = trackVal;
      var comp = document.getElementById('f-company');
      if (comp) comp.focus();
    }
    function setLang(lang) {
      var isFr = (lang === 'fr');
      document.body.classList.toggle('is-fr', isFr);
      document.documentElement.lang = isFr ? 'fr' : 'en';
      var bEn = document.getElementById('btn-en');
      var bFr = document.getElementById('btn-fr');
      if (bEn) bEn.classList.toggle('active', !isFr);
      if (bFr) bFr.classList.toggle('active', isFr);
    }
    function selectSpecimenTab(tabKey) {
      var keys = ['t1', 't2', 't3', 't4'];
      for (var i = 0; i < keys.length; i++) {
        var k = keys[i];
        var btn = document.getElementById('spec-tab-' + k);
        var panel = document.getElementById('spec-panel-' + k);
        var active = (k === tabKey);
        if (btn) {
          btn.classList.toggle('active', active);
          btn.setAttribute('aria-selected', active ? 'true' : 'false');
        }
        if (panel) {
          panel.classList.toggle('active', active);
        }
      }
    }
    function buildIntakePayload() {
      var compEl = document.getElementById('f-company');
      var domEl = document.getElementById('f-domain');
      var trkEl = document.getElementById('f-track');
      var notesEl = document.getElementById('f-notes');
      var comp = (compEl && compEl.value.trim()) ? compEl.value.trim() : 'Organization';
      var dom = (domEl && domEl.value.trim()) ? domEl.value.trim() : 'N/A';
      var trk = trkEl ? trkEl.value : 'Track 01 - Sentinel 25-Control External Audit';
      var notes = (notesEl && notesEl.value.trim()) ? notesEl.value.trim() : 'N/A';
      var subj = 'Complimentary 1-Page Scope Preview - ' + comp + ' (' + trk + ')';
      var body =
        'Company: ' + comp + '\\n' +
        'Domain / Product Scope: ' + dom + '\\n' +
        'Module: ' + trk + '\\n' +
        'Notes: ' + notes + '\\n\\n' +
        'Please prepare a complimentary 1-page technical preview and fixed-scope confirmation under passive observation terms.';
      return { comp: comp, dom: dom, trk: trk, notes: notes, subj: subj, body: body };
    }
    function handleIntakeSubmit(ev) {
      ev.preventDefault();
      var p = buildIntakePayload();
      var intakeForm = __INTAKE_FORM_JSON__;
      if (intakeForm) {
        window.open(intakeForm, '_blank', 'noopener,noreferrer');
        return false;
      }
      window.location.href = 'mailto:__EMAIL_ESC__?subject=' + encodeURIComponent(p.subj) + '&body=' + encodeURIComponent(p.body);
      var fb = document.getElementById('form-feedback');
      if (fb) fb.textContent = 'Email composer opened with pre-filled scope (' + p.comp + '). Or email __EMAIL_ESC__ directly.';
      return false;
    }
    function openGmailWebCompose() {
      var p = buildIntakePayload();
      var gmailUrl = 'https://mail.google.com/mail/?view=cm&fs=1&to=' + encodeURIComponent('__EMAIL_ESC__') + '&su=' + encodeURIComponent(p.subj) + '&body=' + encodeURIComponent(p.body);
      window.open(gmailUrl, '_blank', 'noopener,noreferrer');
      var fb = document.getElementById('form-feedback');
      if (fb) fb.textContent = 'Opened pre-filled Gmail Web compose window for ' + p.comp + '.';
    }
    function copyScopeBrief() {
      var p = buildIntakePayload();
      var fullTxt = 'To: __EMAIL_ESC__\\nSubject: ' + p.subj + '\\n\\n' + p.body;
      var fb = document.getElementById('form-feedback');
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(fullTxt).then(function() {
          if (fb) fb.textContent = 'Copied full scope brief to clipboard (' + p.comp + ').';
        }, function() {
          if (fb) fb.textContent = 'Clipboard blocked; use the email button or send to __EMAIL_ESC__.';
        });
      } else {
        var ta = document.createElement('textarea');
        ta.value = fullTxt;
        ta.setAttribute('readonly', '');
        ta.style.position = 'fixed';
        ta.style.left = '-9999px';
        document.body.appendChild(ta);
        ta.select();
        try {
          document.execCommand('copy');
          if (fb) fb.textContent = 'Copied full scope brief to clipboard (' + p.comp + ').';
        } catch (e) {
          if (fb) fb.textContent = 'Copy unavailable in this browser; please send to __EMAIL_ESC__.';
        }
        document.body.removeChild(ta);
      }
    }
"""
    return template.replace("__INTAKE_FORM_JSON__", intake_url_json).replace("__EMAIL_ESC__", email_esc)


def _live_check_js() -> str:
    """Return strict on-click client-side pre-check JS (zero background requests on load; XSS-safe DOM nodes)."""
    return """    function setResultLines(el, lines) {
      if (!el) return;
      while (el.firstChild) el.removeChild(el.firstChild);
      for (var i = 0; i < lines.length; i++) {
        var item = lines[i];
        var div = document.createElement('div');
        div.style.marginBottom = '4px';
        if (typeof item === 'string') {
          div.textContent = item;
        } else if (item && item.label) {
          var strong = document.createElement('strong');
          strong.textContent = item.label + ': ';
          div.appendChild(strong);
          if (item.url && item.url.indexOf('https://') === 0) {
            var a = document.createElement('a');
            a.href = item.url;
            a.target = '_blank';
            a.rel = 'noopener noreferrer';
            a.textContent = item.text || item.url;
            div.appendChild(a);
          } else {
            var span = document.createElement('span');
            span.textContent = item.text || '';
            div.appendChild(span);
          }
        }
        el.appendChild(div);
      }
    }
    function prefillFromLiveCheck(trackVal, scopeVal, noteVal) {
      var sel = document.getElementById('f-track');
      var dom = document.getElementById('f-domain');
      var notes = document.getElementById('f-notes');
      if (sel) sel.value = trackVal;
      if (dom && scopeVal) dom.value = scopeVal;
      if (notes && noteVal) notes.value = noteVal;
      var intake = document.getElementById('intake');
      if (intake && intake.scrollIntoView) intake.scrollIntoView({ behavior: 'smooth' });
      var comp = document.getElementById('f-company');
      if (comp) comp.focus();
    }
    var lastLiveSummary = { dns: '', fda: '', epmc: '' };
    function countSpfLookups(spfTxt) {
      var tokens = spfTxt.toLowerCase().split(/\\s+/);
      var count = 0;
      for (var i = 0; i < tokens.length; i++) {
        var tok = tokens[i].replace(/^[+?~-]/, '');
        if (tok.indexOf('include:') === 0 || tok.indexOf('redirect=') === 0 || tok.indexOf('exists:') === 0) {
          count++;
        } else if (tok === 'a' || tok.indexOf('a:') === 0 || tok.indexOf('a/') === 0) {
          count++;
        } else if (tok === 'mx' || tok.indexOf('mx:') === 0 || tok.indexOf('mx/') === 0) {
          count++;
        } else if (tok === 'ptr' || tok.indexOf('ptr:') === 0) {
          count++;
        }
      }
      return count;
    }
    async function runDnsPrecheck() {
      var inp = document.getElementById('lc-domain-input');
      var out = document.getElementById('lc-dns-out');
      var raw = (inp ? inp.value : '').trim().toLowerCase().replace(/^https?:\\/\\//, '').replace(/\\/.*$/, '').replace(/^www\\./, '');
      if (!/^[a-z0-9.-]+\\.[a-z]{2,}$/.test(raw)) {
        setResultLines(out, ['Please enter a valid domain name (e.g. example-medtech.ch).']);
        return;
      }
      setResultLines(out, ['Querying public Google DoH TXT records for ' + raw + '...']);
      try {
        var qDmarc = fetch('https://dns.google/resolve?name=' + encodeURIComponent('_dmarc.' + raw) + '&type=TXT').then(function(r) { return r.json(); });
        var qRoot = fetch('https://dns.google/resolve?name=' + encodeURIComponent(raw) + '&type=TXT').then(function(r) { return r.json(); });
        var qSts = fetch('https://dns.google/resolve?name=' + encodeURIComponent('_mta-sts.' + raw) + '&type=TXT').then(function(r) { return r.json(); });
        var res = await Promise.all([qDmarc, qRoot, qSts]);
        var dmarcTxts = (res[0].Answer || []).map(function(a) { return String(a.data || '').replace(/^"|"$/g, ''); }).filter(function(t) { return /v=dmarc1/i.test(t); });
        var spfTxts = (res[1].Answer || []).map(function(a) { return String(a.data || '').replace(/^"|"$/g, ''); }).filter(function(t) { return /v=spf1/i.test(t); });
        var stsTxts = (res[2].Answer || []).map(function(a) { return String(a.data || '').replace(/^"|"$/g, ''); }).filter(function(t) { return /v=stsv1/i.test(t); });

        var dmarcLine = dmarcTxts.length ? dmarcTxts[0] : 'MISSING _dmarc TXT record (spoofing risk)';
        var spfStatus = 'MISSING v=spf1 TXT record';
        if (spfTxts.length) {
          var lookups = countSpfLookups(spfTxts[0]);
          spfStatus = 'Direct mechanisms ~' + lookups + '/10 RFC 7208 limit' + (lookups > 10 ? ' (OVER 10-LOOKUP CAP!)' : (lookups >= 8 ? ' (Near limit before nested includes)' : '')) + ' | ' + spfTxts[0].slice(0, 75);
        }
        var stsLine = stsTxts.length ? stsTxts[0] : 'Not published (optional RFC 8461 MTA-STS hardening)';
        lastLiveSummary.dns = 'DNS Pre-Check (' + raw + '): DMARC=' + dmarcLine + '; SPF=' + spfStatus + '; MTA-STS=' + stsLine;
        setResultLines(out, [
          { label: 'Domain', text: raw },
          { label: 'DMARC', text: dmarcLine },
          { label: 'SPF', text: spfStatus },
          { label: 'MTA-STS', text: stsLine }
        ]);
      } catch (err) {
        setResultLines(out, ['Public DNS DoH check failed cleanly (' + (err && err.message ? err.message : 'network blocked') + '). Request a full Sentinel server-side audit below.']);
      }
    }
    async function runFdaPrecheck() {
      var inp = document.getElementById('lc-fda-input');
      var out = document.getElementById('lc-fda-out');
      var qRaw = (inp ? inp.value : '').trim();
      if (!qRaw || qRaw.length < 2) {
        setResultLines(out, ['Enter a medical device keyword or FDA product code (e.g. insulin pump).']);
        return;
      }
      setResultLines(out, ['Querying public OpenFDA MAUDE database for "' + qRaw + '"...']);
      try {
        var cleanTerm = qRaw.replace(/["\\\\]/g, ' ').trim();
        var url = 'https://api.fda.gov/device/event.json?search=' + encodeURIComponent('"' + cleanTerm + '"') + '&count=event_type.exact';
        var r = await fetch(url);
        if (!r.ok) {
          setResultLines(out, ['OpenFDA returned HTTP ' + r.status + ' for "' + cleanTerm + '" (no matching MAUDE events or broader term needed).']);
          return;
        }
        var js = await r.json();
        var rows = js.results || [];
        var total = 0;
        var breakdown = [];
        for (var i = 0; i < rows.length; i++) {
          total += Number(rows[i].count || 0);
          breakdown.push(String(rows[i].term || 'Other') + ': ' + Number(rows[i].count || 0).toLocaleString());
        }
        lastLiveSummary.fda = 'OpenFDA MAUDE Pre-Check (' + cleanTerm + '): ' + total.toLocaleString() + ' total indexed events (' + breakdown.join(', ') + ')';
        setResultLines(out, [
          { label: 'Query', text: cleanTerm },
          { label: 'Indexed MAUDE Events', text: total.toLocaleString() },
          { label: 'Severity Split', text: breakdown.length ? breakdown.join(' | ') : 'No event_type breakdown available' }
        ]);
      } catch (err) {
        setResultLines(out, ['OpenFDA request could not complete (' + (err && err.message ? err.message : 'network error') + ').']);
      }
    }
    async function runEpmcPrecheck() {
      var inp = document.getElementById('lc-epmc-input');
      var out = document.getElementById('lc-epmc-out');
      var qRaw = (inp ? inp.value : '').trim();
      if (!qRaw || qRaw.length < 2) {
        setResultLines(out, ['Enter clinical/PICO terms (e.g. GLP-1 renal outcomes).']);
        return;
      }
      setResultLines(out, ['Querying Europe PMC REST API for "' + qRaw + '"...']);
      try {
        var url = 'https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=' + encodeURIComponent(qRaw) + '&resultType=lite&format=json&pageSize=3';
        var r = await fetch(url);
        if (!r.ok) {
          setResultLines(out, ['Europe PMC returned HTTP ' + r.status + '.']);
          return;
        }
        var js = await r.json();
        var hitCount = Number(js.hitCount || 0);
        var list = (js.resultList && js.resultList.result) ? js.resultList.result : [];
        var lines = [{ label: 'Matching Records', text: hitCount.toLocaleString() + ' indexed articles/preprints' }];
        for (var i = 0; i < Math.min(3, list.length); i++) {
          var item = list[i];
          var pmid = item.pmid ? String(item.pmid) : '';
          var yr = item.pubYear ? String(item.pubYear) : '';
          var ttl = (item.title || 'Untitled').slice(0, 82);
          var artUrl = pmid ? ('https://pubmed.ncbi.nlm.nih.gov/' + encodeURIComponent(pmid) + '/') : '';
          lines.push({ label: '[' + (yr || 'n.d.') + ']', text: ttl + (pmid ? ' (PMID ' + pmid + ')' : ''), url: artUrl });
        }
        lastLiveSummary.epmc = 'Europe PMC Pre-Check (' + qRaw + '): ' + hitCount.toLocaleString() + ' matching records found.';
        setResultLines(out, lines);
      } catch (err) {
        setResultLines(out, ['Europe PMC request could not complete (' + (err && err.message ? err.message : 'network error') + ').']);
      }
    }
"""



def render_specimen_inspector_html() -> str:
    """Render accessible, zero-dependency interactive specimen preview panels across all 4 tracks."""
    return """        <div class="specimen-inspector" id="specimen-inspector">
          <div class="spec-head-bar">
            <div>
              <h3>
                <span class="lang-en">Interactive Deliverable Inspector (Word, Excel &amp; Turnkey Config Structure)</span>
                <span class="lang-fr">Inspecteur Interactif des Livrables (Structure Excel, Word &amp; Correctifs)</span>
              </h3>
            </div>
            <span class="spec-badge-note">
              <span class="lang-en">Illustrative Structure &middot; Redacted Specimen Layout (#FFF2CC = Manual QA Flag)</span>
              <span class="lang-fr">Structure Illustrative Anonymis&eacute;e (#FFF2CC = Contr&ocirc;le Qualit&eacute; Manuel)</span>
            </span>
          </div>

          <div class="spec-tabs" role="tablist" aria-label="Deliverable Specimen Modules">
            <button id="spec-tab-t1" class="spec-tab active" type="button" role="tab" aria-selected="true" aria-controls="spec-panel-t1" onclick="selectSpecimenTab('t1')">
              <span class="lang-en">Track 01 &middot; Sentinel Excel + Fix Snippet</span>
              <span class="lang-fr">Module 01 &middot; Matrice Sentinel + Correctif</span>
            </button>
            <button id="spec-tab-t2" class="spec-tab" type="button" role="tab" aria-selected="false" aria-controls="spec-panel-t2" onclick="selectSpecimenTab('t2')">
              <span class="lang-en">Track 02 &middot; OpenFDA MAUDE &amp; PSUR</span>
              <span class="lang-fr">Module 02 &middot; Registre MAUDE &amp; PSUR</span>
            </button>
            <button id="spec-tab-t3" class="spec-tab" type="button" role="tab" aria-selected="false" aria-controls="spec-panel-t3" onclick="selectSpecimenTab('t3')">
              <span class="lang-en">Track 03 &middot; PRISMA 2020 + ICH E9 Table 1</span>
              <span class="lang-fr">Module 03 &middot; PRISMA 2020 + Table 1 ICH E9</span>
            </button>
            <button id="spec-tab-t4" class="spec-tab" type="button" role="tab" aria-selected="false" aria-controls="spec-panel-t4" onclick="selectSpecimenTab('t4')">
              <span class="lang-en">Track 04 &middot; eCTD Linter &amp; ALCOA+ SHA-256</span>
              <span class="lang-fr">Module 04 &middot; Linter eCTD &amp; Manifeste ALCOA+</span>
            </button>
          </div>

          <div id="spec-panel-t1" class="spec-panel active" role="tabpanel" aria-labelledby="spec-tab-t1">
            <div class="spec-meta">
              <p>
                <span class="lang-en"><strong>Sample Workbook Sheet:</strong> <code>02_Executive_Risk_Matrix</code> (DMARC, SPF &gt;10 PermError Check, MTA-STS, CMP Symmetry &amp; Nginx/Cloudflare Fix Pack).</span>
                <span class="lang-fr"><strong>Onglet Excel Exemple :</strong> <code>02_Executive_Risk_Matrix</code> (DMARC, plafond 10 requ&ecirc;tes SPF, MTA-STS, banniere cookies &amp; correctifs DNS/Nginx).</span>
              </p>
              <div class="spec-actions">
                <a class="btn-sample-dl" href="samples/sentinel_swiss_sme_sample.zip" download>
                  <span class="lang-en">&#8595; Download Sample ZIP (Word + Excel + Fix Pack)</span>
                  <span class="lang-fr">&#8595; T&eacute;l&eacute;charger l'Exemple ZIP (Word + Excel + Correctifs)</span>
                </a>
                <a class="btn-outline" href="#intake" onclick="selectTrack('Track 01 - Sentinel 25-Control External Audit');">
                  <span class="lang-en">Request 1-Page Audit on Your Domain</span>
                  <span class="lang-fr">Demander cet Audit sur Votre Domaine</span>
                </a>
              </div>
            </div>
            <div class="table-wrap">
              <table class="spec-table">
                <thead>
                  <tr>
                    <th>Control ID</th>
                    <th><span class="lang-en">Pillar &amp; Check</span><span class="lang-fr">Pilier &amp; Contr&ocirc;le</span></th>
                    <th>Status</th>
                    <th><span class="lang-en">Observed Evidence (Specimen)</span><span class="lang-fr">Preuve Observ&eacute;e (Sp&eacute;cimen)</span></th>
                    <th><span class="lang-en">Deliverable Action</span><span class="lang-fr">Action Pr&ecirc;te au D&eacute;ploiement</span></th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td><code>EML-01</code></td>
                    <td>DMARC Anti-Spoofing Policy</td>
                    <td><span class="badge-fail">FAIL</span></td>
                    <td><code>_dmarc.example-medtech.ch</code> missing or <code>p=none</code></td>
                    <td>Step-up DNS TXT progression: <code>p=none</code> &rarr; <code>p=quarantine</code> &rarr; <code>p=reject</code></td>
                  </tr>
                  <tr>
                    <td><code>EML-02</code></td>
                    <td>SPF &amp; RFC 7208 10-Lookup Cap</td>
                    <td><span class="badge-fail">FAIL</span></td>
                    <td>11 recursive DNS lookups detected (&gt;10 PermError risk)</td>
                    <td>Consolidate/flatten <code>include:</code> directives down to &le;8 lookups</td>
                  </tr>
                  <tr>
                    <td><code>PRV-02</code></td>
                    <td>CMP Reject Symmetry &amp; US Fonts</td>
                    <td><span class="badge-warn">WARN</span></td>
                    <td>Cookie notice lacks first-layer Reject / Necessary-Only button</td>
                    <td>Add symmetric Reject button &amp; self-host WOFF2 fonts locally</td>
                  </tr>
                  <tr class="qa-flag-row">
                    <td><code>SEC-01</code></td>
                    <td>HTTP Strict-Transport-Security &amp; CSP</td>
                    <td><span class="badge-warn">QA CHECK</span></td>
                    <td>HSTS present; legacy wildcard subdomain policy flagged (<code>#FFF2CC</code>)</td>
                    <td>Confirm legacy portal TLS readiness with IT prior to <code>preload</code></td>
                  </tr>
                  <tr>
                    <td><code>SEC-09</code></td>
                    <td>Vulnerability Disclosure (<code>security.txt</code>)</td>
                    <td><span class="badge-pass">PASS</span></td>
                    <td>RFC 9116 file verified at <code>/.well-known/security.txt</code></td>
                    <td>Retain annual expiration renewal reminder in QMS log</td>
                  </tr>
                </tbody>
              </table>
            </div>
            <p class="spec-snippet-label">
              <span class="lang-en">Included Copy-Paste Remediation Excerpt (<code>04_Fixes_Nginx_Cloudflare.conf</code>):</span>
              <span class="lang-fr">Extrait de Correctif Pr&ecirc;t &agrave; D&eacute;ployer Inclus (<code>04_Fixes_Nginx_Cloudflare.conf</code>) :</span>
            </p>
            <pre class="spec-snippet">_dmarc.example-medtech.ch. 300 IN TXT "v=DMARC1; p=quarantine; rua=mailto:dmarc@example-medtech.ch; adkim=s; aspf=s;"
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
add_header X-Content-Type-Options "nosniff" always;</pre>
          </div>

          <div id="spec-panel-t2" class="spec-panel" role="tabpanel" aria-labelledby="spec-tab-t2">
            <div class="spec-meta">
              <p>
                <span class="lang-en"><strong>Sample PSUR Sheets:</strong> <code>MAUDE_Adverse_Events</code> (with Monthly Z-Score Signal Spike Alerts) + <code>ClinicalTrials_Landscape</code> under EU MDR Art. 83&ndash;86 &amp; MDCG 2022-21.</span>
                <span class="lang-fr"><strong>Onglets PSUR Exemples :</strong> <code>MAUDE_Adverse_Events</code> (avec d&eacute;tection statistique Z-score de pics mensuels) + <code>ClinicalTrials_Landscape</code> (UE MDR Art. 83&ndash;86 &amp; MDCG 2022-21).</span>
              </p>
              <div class="spec-actions">
                <a class="btn-sample-dl" href="samples/pms_cgm_class_iib_sample.zip" download>
                  <span class="lang-en">&#8595; Download PSUR Sample ZIP (Word + Excel + Spike Alert)</span>
                  <span class="lang-fr">&#8595; T&eacute;l&eacute;charger Exemple PSUR ZIP (Word + Excel + Alertes)</span>
                </a>
                <a class="btn-outline" href="#intake" onclick="selectTrack('Track 02 - OpenFDA MAUDE & PSUR Surveillance');">
                  <span class="lang-en">Request 1-Page PSUR Preview</span>
                  <span class="lang-fr">Demander un Aper&ccedil;u PSUR (1 Page)</span>
                </a>
              </div>
            </div>
            <div class="table-wrap">
              <table class="spec-table">
                <thead>
                  <tr>
                    <th>PSUR Section</th>
                    <th><span class="lang-en">Source API Endpoint</span><span class="lang-fr">Source API Publique</span></th>
                    <th><span class="lang-en">Structured Fields Exported</span><span class="lang-fr">Champs Structur&eacute;s Export&eacute;s</span></th>
                    <th>QA Rule</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td>MAUDE Severity &amp; Spike Radar</td>
                    <td><code>api.fda.gov/device/event</code></td>
                    <td>Malfunction / Injury / Death split, IMDRF terms &amp; Z-score monthly spike alerts (<code>Z &ge; 2.0</code>)</td>
                    <td><span class="badge-pass">AUTO-COUNTED</span></td>
                  </tr>
                  <tr>
                    <td>Predicate &amp; Recall Log</td>
                    <td><code>device/510k</code> &amp; <code>recall</code></td>
                    <td>K-number decision dates, Class I/II/III status &amp; open remediation summaries</td>
                    <td><span class="badge-pass">TRACEABLE</span></td>
                  </tr>
                  <tr>
                    <td>PMCF Clinical Registry</td>
                    <td><code>clinicaltrials.gov/api/v2</code></td>
                    <td>Humanized study status, enrollment, Sponsor, clickable <code>NCTId</code> hyperlink</td>
                    <td><span class="badge-pass">VERIFIED URL</span></td>
                  </tr>
                  <tr class="qa-flag-row">
                    <td>Blank Narrative / Code</td>
                    <td>Unmapped FDA event record</td>
                    <td>Missing manufacturer narrative or unknown device code (<code>#FFF2CC</code>)</td>
                    <td><span class="badge-warn">NO GUESSWORK</span></td>
                  </tr>
                </tbody>
              </table>
            </div>
            <p class="spec-snippet-label">
              <span class="lang-en">PSUR Governance Output Layout:</span>
              <span class="lang-fr">Format de Livrable PSUR &amp; Tra&ccedil;abilit&eacute; :</span>
            </p>
            <pre class="spec-snippet">Landscape Word Dossier (.docx): Executive Benefit-Risk Summary + MDCG 2022-21 Monthly Spike Narrative
Filterable Excel (.xlsx):        4 Sheets (MAUDE Events + Spike Alerts, Recalls/510k, ClinicalTrials v2, README)
High-Res Visual (.png + .pdf):   300-DPI Multi-Panel Post-Market Safety &amp; Trial Timeline Dashboard</pre>
          </div>

          <div id="spec-panel-t3" class="spec-panel" role="tabpanel" aria-labelledby="spec-tab-t3">
            <div class="spec-meta">
              <p>
                <span class="lang-en"><strong>Sample Literature &amp; Cohort Dossier:</strong> Conserved PRISMA 2020 flow equation, Vancouver Word citations, RoB 2 / NOS framework summary, and ready-to-import <code>.ris</code> / <code>.bib</code> files.</span>
                <span class="lang-fr"><strong>Dossier Clinique &amp; Biostats Exemple :</strong> &Eacute;quation PRISMA 2020 conserv&eacute;e, citations Vancouver Word, synth&egrave;se RoB 2 / NOS et exports <code>.ris</code> / <code>.bib</code>.</span>
              </p>
              <div class="spec-actions">
                <a class="btn-sample-dl" href="samples/prisma_glp1_clinical_sample.zip" download>
                  <span class="lang-en">&#8595; Download PRISMA Sample ZIP (Word + Excel + .ris + .bib)</span>
                  <span class="lang-fr">&#8595; T&eacute;l&eacute;charger Exemple PRISMA ZIP (Word + Excel + .ris/.bib)</span>
                </a>
                <a class="btn-outline" href="#intake" onclick="selectTrack('Track 03 - PRISMA 2020 Clinical Evidence & Table 1');">
                  <span class="lang-en">Request 1-Page PRISMA Preview</span>
                  <span class="lang-fr">Demander un Aper&ccedil;u PRISMA (1 Page)</span>
                </a>
              </div>
            </div>
            <div class="table-wrap">
              <table class="spec-table">
                <thead>
                  <tr>
                    <th>PRISMA / Biostat Block</th>
                    <th><span class="lang-en">Verification Formula</span><span class="lang-fr">R&egrave;gle de V&eacute;rification</span></th>
                    <th><span class="lang-en">Excel / Word Presentation</span><span class="lang-fr">Restitution Excel / Word</span></th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td>Dual-Source Screening</td>
                    <td><code>N_identified - N_dup = N_screened</code></td>
                    <td>Strict integer conservation verified prior to rendering 300-DPI flow diagram</td>
                    <td><span class="badge-pass">CONSERVED</span></td>
                  </tr>
                  <tr>
                    <td>Vancouver Table + <code>.ris</code> / <code>.bib</code></td>
                    <td>Mandatory clickable <code>PMID</code> &amp; non-fabricated <code>DOI</code></td>
                    <td>Exports directly to Zotero / EndNote / BibTeX alongside Word &amp; Excel tables</td>
                    <td><span class="badge-pass">ZERO-FABRICATION</span></td>
                  </tr>
                  <tr>
                    <td>ICH E9 Table 1 + RoB Summary</td>
                    <td>Design-matched RoB 2 / NOS / JBI map</td>
                    <td>Shapiro-Wilk <code>Mean &plusmn; SD</code> vs. <code>Median [IQR]</code> + RoB appraisal framework table</td>
                    <td><span class="badge-pass">ICH E9 ALIGNED</span></td>
                  </tr>
                  <tr class="qa-flag-row">
                    <td>Missing Abstract / SD</td>
                    <td>Empty variance or missing full text</td>
                    <td>Cell preserved &amp; shaded <code>#FFF2CC</code> (never imputed silently)</td>
                    <td><span class="badge-warn">QA FLAGGED</span></td>
                  </tr>
                </tbody>
              </table>
            </div>
            <p class="spec-snippet-label">
              <span class="lang-en">Conserved Excel Audit Equation (Built into Sheet 1 Summary):</span>
              <span class="lang-fr">&Eacute;quation de Conservation Int&eacute;gr&eacute;e (Onglet 1 Synth&egrave;se Excel) :</span>
            </p>
            <pre class="spec-snippet">=COUNTIFS(Screening_Log!G:G,"Included") + COUNTIFS(Screening_Log!G:G,"Excluded*") = Records_Assessed</pre>
          </div>

          <div id="spec-panel-t4" class="spec-panel" role="tabpanel" aria-labelledby="spec-tab-t4">
            <div class="spec-meta">
              <p>
                <span class="lang-en"><strong>Sample RA Command Center:</strong> 6-sheet eCTD M1&ndash;M5 Gatekeeper Linter + Upstream SLA Attribution + cryptographic SHA-256 ALCOA+ Manifest.</span>
                <span class="lang-fr"><strong>Centre de Commande AR :</strong> Linter eCTD M1&ndash;M5 &agrave; 6 onglets + Suivi SLA + Manifeste cryptographique ALCOA+ SHA-256.</span>
              </p>
              <div class="spec-actions">
                <a class="btn-sample-dl" href="samples/ra_ectd_command_sample.zip" download>
                  <span class="lang-en">&#8595; Download RA Command Sample ZIP (Word + 6-Sheet Excel)</span>
                  <span class="lang-fr">&#8595; T&eacute;l&eacute;charger Exemple Centre AR ZIP (Word + Excel 6 Onglets)</span>
                </a>
                <a class="btn-outline" href="#intake" onclick="selectTrack('Track 04 - Unified Dossier / eCTD RA Command');">
                  <span class="lang-en">Request Unified / eCTD Preview</span>
                  <span class="lang-fr">Demander un Aper&ccedil;u Pack Unifi&eacute;</span>
                </a>
              </div>
            </div>
            <div class="table-wrap">
              <table class="spec-table">
                <thead>
                  <tr>
                    <th>Gatekeeper Sheet / File</th>
                    <th><span class="lang-en">Cross-Check Logic</span><span class="lang-fr">Contr&ocirc;le Crois&eacute;</span></th>
                    <th><span class="lang-en">Sample Specimen Detection</span><span class="lang-fr">D&eacute;tection Exemple</span></th>
                    <th>Outcome</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td><code>02_Upstream_Blame_Shield</code></td>
                    <td>Target vs. actual handoff delta (days)</td>
                    <td>CMC stability tables delivered +9d post-freeze &rarr; attributes critical-path slip</td>
                    <td><span class="badge-warn">SLA LOGGED</span></td>
                  </tr>
                  <tr class="qa-flag-row">
                    <td><code>04_eCTD_N_Count_Linter</code></td>
                    <td>Module 2.7 vs. Module 5 table counts</td>
                    <td>Mismatch flagged for RA review before publishing sequence XML (<code>#FFF2CC</code>)</td>
                    <td><span class="badge-fail">BLOCK UNTIL FIXED</span></td>
                  </tr>
                  <tr>
                    <td><code>05_Agency_Drift_Radar</code></td>
                    <td>FDA / EMA / Swissmedic / MDCG tags</td>
                    <td>Direct statutory URLs mapped to active submission milestones</td>
                    <td><span class="badge-pass">MAPPED</span></td>
                  </tr>
                  <tr>
                    <td><code>ALCOA_PROVENANCE_MANIFEST.json</code></td>
                    <td>UTC timestamp + SHA-256 per file</td>
                    <td>Immutable cryptographic verification across Word, Excel, PNG, PDF &amp; ZIP</td>
                    <td><span class="badge-pass">ALCOA+ HASHED</span></td>
                  </tr>
                </tbody>
              </table>
            </div>
            <p class="spec-snippet-label">
              <span class="lang-en">Sample <code>ALCOA_PROVENANCE_MANIFEST.json</code> Verification Block:</span>
              <span class="lang-fr">Extrait du Manifeste Cryptographique <code>ALCOA_PROVENANCE_MANIFEST.json</code> :</span>
            </p>
            <pre class="spec-snippet">{
  "pipeline": "Sentinel Unified RA / Clinical Pack",
  "generated_utc": "2026-11-11T21:00:00+00:00",
  "verification_rule": "sha256_file_digest == manifest.artifacts[].sha256",
  "zero_fabrication_policy": "#FFF2CC highlighted for any incomplete primary-source record"
}</pre>
          </div>
        </div>"""



def render_live_check_section_html() -> str:
    """Render zero-background-traffic interactive client-side pre-check section (`#live-check`)."""
    return """    <section class="band" id="live-check" style="background:var(--slate-bg);">
      <div class="container">
        <div class="sec-head">
          <div class="eyebrow">
            <span class="lang-en">Interactive Public-API Pre-Check &middot; Zero Page-Load Requests</span>
            <span class="lang-fr">Pr&eacute;-Contr&ocirc;le Interactif Temps R&eacute;el &middot; Z&eacute;ro Requ&ecirc;te au Chargement</span>
          </div>
          <h2>
            <span class="lang-en">Test Your Domain, FDA Device Code, or Clinical Query Live</span>
            <span class="lang-fr">Testez en Direct Votre Domaine, Code Dispositif FDA ou Sujet Clinique</span>
          </h2>
          <p class="lang-en">Nothing is fetched until you click. Queries run directly from your browser to public Google DoH (<code>dns.google</code>), OpenFDA MAUDE (<code>api.fda.gov</code>), and Europe PMC (<code>ebi.ac.uk</code>).</p>
          <p class="lang-fr">Aucune requ&ecirc;te n'est envoy&eacute;e sans clic de votre part. Vos tests interrogent directement Google DoH (<code>dns.google</code>), OpenFDA MAUDE (<code>api.fda.gov</code>) et Europe PMC (<code>ebi.ac.uk</code>).</p>
        </div>

        <div class="live-grid">
          <article class="live-card">
            <div>
              <div class="offer-tag">Pre-Check 01 &middot; DNS / DMARC / SPF / MTA-STS</div>
              <h3>
                <span class="lang-en">Public Mail Spoofing &amp; SPF Lookup Cap</span>
                <span class="lang-fr">Contr&ocirc;le DMARC, Plafond 10 SPF &amp; MTA-STS</span>
              </h3>
              <p class="lang-en">Checks live <code>_dmarc</code>, <code>v=spf1</code> RFC 7208 10-lookup pressure, and <code>_mta-sts</code> TXT records via Google DoH.</p>
              <p class="lang-fr">V&eacute;rifie en direct vos champs <code>_dmarc</code>, le plafond 10 requ&ecirc;tes SPF (RFC 7208) et <code>_mta-sts</code> via Google DoH.</p>
              <div class="live-input-row">
                <input id="lc-domain-input" type="text" value="example-medtech.ch" placeholder="e.g. yourcompany.ch" aria-label="Domain to check via Google DoH" />
                <button type="button" class="btn-primary" onclick="runDnsPrecheck();">
                  <span class="lang-en">Check DNS</span><span class="lang-fr">Tester</span>
                </button>
              </div>
              <div id="lc-dns-out" class="live-result">Click "Check DNS" to query public DMARC / SPF / MTA-STS TXT records.</div>
            </div>
            <button type="button" class="btn-outline" onclick="prefillFromLiveCheck('Track 01 - Sentinel 25-Control External Audit', document.getElementById('lc-domain-input').value, lastLiveSummary.dns);">
              <span class="lang-en">Use Result in 1-Page Audit Form &rarr;</span>
              <span class="lang-fr">Envoyer vers le Formulaire Audit &rarr;</span>
            </button>
          </article>

          <article class="live-card">
            <div>
              <div class="offer-tag">Pre-Check 02 &middot; OpenFDA MAUDE Endpoint</div>
              <h3>
                <span class="lang-en">Live Medical Device MAUDE Stratification</span>
                <span class="lang-fr">Comptage Public OpenFDA MAUDE</span>
              </h3>
              <p class="lang-en">Queries official <code>api.fda.gov/device/event.json</code> for total indexed Malfunction, Injury, and Death counts.</p>
              <p class="lang-fr">Interroge l'API officielle <code>api.fda.gov/device/event.json</code> pour les r&eacute;partitions pannes, blessures et d&eacute;c&egrave;s.</p>
              <div class="live-input-row">
                <input id="lc-fda-input" type="text" value="insulin pump" placeholder="e.g. cardiac catheter" aria-label="Medical device term for OpenFDA MAUDE" />
                <button type="button" class="btn-primary" onclick="runFdaPrecheck();">
                  <span class="lang-en">Query FDA</span><span class="lang-fr">Tester</span>
                </button>
              </div>
              <div id="lc-fda-out" class="live-result">Click "Query FDA" to summarize public MAUDE event classifications.</div>
            </div>
            <button type="button" class="btn-outline" onclick="prefillFromLiveCheck('Track 02 - OpenFDA MAUDE & PSUR Surveillance', document.getElementById('lc-fda-input').value, lastLiveSummary.fda);">
              <span class="lang-en">Use Term for 1-Page PSUR Preview &rarr;</span>
              <span class="lang-fr">Envoyer vers Aper&ccedil;u PSUR &rarr;</span>
            </button>
          </article>

          <article class="live-card">
            <div>
              <div class="offer-tag">Pre-Check 03 &middot; Europe PMC REST Search</div>
              <h3>
                <span class="lang-en">Live PRISMA 2020 Literature Corpus Size</span>
                <span class="lang-fr">Volume Corpus Europe PMC / PubMed</span>
              </h3>
              <p class="lang-en">Surfaces real peer-reviewed hit counts and top indexed PMIDs from EMBL-EBI Europe PMC for your CER topic.</p>
              <p class="lang-fr">Affiche le nombre d'articles et les premiers PMIDs index&eacute;s sur EMBL-EBI Europe PMC pour votre th&egrave;me clinique.</p>
              <div class="live-input-row">
                <input id="lc-epmc-input" type="text" value="GLP-1 renal outcomes" placeholder="e.g. coronary stent outcomes" aria-label="Clinical topic for Europe PMC search" />
                <button type="button" class="btn-primary" onclick="runEpmcPrecheck();">
                  <span class="lang-en">Search EPMC</span><span class="lang-fr">Chercher</span>
                </button>
              </div>
              <div id="lc-epmc-out" class="live-result">Click "Search EPMC" to preview live PubMed / Europe PMC matches.</div>
            </div>
            <button type="button" class="btn-outline" onclick="prefillFromLiveCheck('Track 03 - PRISMA 2020 Clinical Evidence & Table 1', document.getElementById('lc-epmc-input').value, lastLiveSummary.epmc);">
              <span class="lang-en">Use Query for 1-Page PRISMA Preview &rarr;</span>
              <span class="lang-fr">Envoyer vers Aper&ccedil;u PRISMA &rarr;</span>
            </button>
          </article>
        </div>
      </div>
    </section>"""


def _render_seo_guide_html(
    *,
    filename: str,
    title_en: str,
    title_fr: str,
    meta_desc: str,
    eyebrow: str,
    lead_en: str,
    lead_fr: str,
    bullets_en: list[tuple[str, str]],
    bullets_fr: list[tuple[str, str]],
    sample_zip_rel: str,
    sample_label_en: str,
    sample_label_fr: str,
    track_hash: str,
    cfg: dict[str, Any],
) -> str:
    """Render a standalone zero-dependency Swiss-editorial SEO landing page (CH & FR focus)."""
    prov = cfg["provider"]
    brand = prov.get("brand_name", "Sentinel Regulatory & Technical Operations")
    email = prov.get("contact_email", "kaledbouchagraoui7@gmail.com")
    website = (prov.get("website_url") or "https://kaledbouchagraoui7-bot.github.io/medtech-regulatory-compliance-suite/").rstrip("/")

    li_en = "".join(f"<li><strong>{html.escape(k)}:</strong> {html.escape(v)}</li>" for k, v in bullets_en)
    li_fr = "".join(f"<li><strong>{html.escape(k)} :</strong> {html.escape(v)}</li>" for k, v in bullets_fr)

    template = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>__TITLE_EN__ &mdash; __BRAND__</title>
  <meta name="description" content="__META_DESC__" />
  <link rel="canonical" href="__CANONICAL__" />
  <style>
    :root { --navy:#0F172A; --teal:#0F766E; --slate:#F8FAFC; --border:#E2E8F0; --muted:#475569; }
    * { box-sizing:border-box; }
    body { margin:0; font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Arial,sans-serif; background:var(--slate); color:var(--navy); line-height:1.6; }
    .lang-fr, div.lang-fr, ul.lang-fr, p.lang-fr { display:none; }
    body.is-fr .lang-en, body.is-fr div.lang-en, body.is-fr ul.lang-en, body.is-fr p.lang-en { display:none; }
    body.is-fr .lang-fr { display:inline; }
    body.is-fr div.lang-fr, body.is-fr ul.lang-fr, body.is-fr p.lang-fr { display:block; }
    header { background:#FFF; border-bottom:1px solid var(--border); padding:14px 24px; }
    .nav { max-width:960px; margin:0 auto; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px; }
    .nav a { color:var(--navy); text-decoration:none; font-weight:700; font-size:14px; }
    .nav-links { display:flex; gap:14px; align-items:center; flex-wrap:wrap; }
    .lang-btn { border:1px solid var(--border); background:var(--slate); padding:5px 10px; border-radius:4px; font-weight:700; cursor:pointer; }
    main { max-width:960px; margin:34px auto; padding:0 20px; }
    .card { background:#FFF; border:1px solid var(--border); border-top:4px solid var(--teal); border-radius:6px; padding:28px; }
    .eyebrow { font-size:11.5px; font-weight:700; letter-spacing:1.3px; text-transform:uppercase; color:var(--teal); margin-bottom:8px; }
    h1 { font-family:Georgia,serif; font-size:clamp(25px,3.2vw,34px); line-height:1.2; margin:0 0 12px 0; }
    .lead { color:var(--muted); font-size:16px; margin:0 0 22px 0; }
    .card ul { padding-left:20px; margin:0 0 24px 0; }
    .card li { margin-bottom:9px; color:#1E293B; }
    .actions { display:flex; gap:12px; flex-wrap:wrap; }
    .btn-primary { background:var(--teal); color:#FFF; padding:11px 18px; border-radius:6px; text-decoration:none; font-weight:700; font-size:14px; }
    .btn-outline { background:#FFF; color:var(--navy); border:1px solid var(--border); padding:11px 18px; border-radius:6px; text-decoration:none; font-weight:700; font-size:14px; }
    footer { max-width:960px; margin:24px auto 40px auto; padding:0 20px; font-size:13px; color:var(--muted); }
    footer a { color:var(--teal); text-decoration:none; font-weight:600; }
  </style>
</head>
<body>
  <header>
    <nav class="nav" aria-label="Guide Navigation">
      <a href="index.html">&larr; __BRAND__</a>
      <div class="nav-links">
        <a href="nfadp-audit.html">nFADP / GDPR</a>
        <a href="eu-mdr-psur.html">EU MDR PSUR</a>
        <a href="prisma-2020.html">PRISMA 2020</a>
        <a href="terms.html">Terms</a>
        <a href="cgv.html">CGV</a>
        <button type="button" class="lang-btn" onclick="var f=!document.body.classList.contains('is-fr');document.body.classList.toggle('is-fr',f);this.textContent=f?'EN':'FR';">FR</button>
      </div>
    </nav>
  </header>
  <main>
    <article class="card">
      <div class="eyebrow">__EYEBROW__</div>
      <h1><span class="lang-en">__TITLE_EN__</span><span class="lang-fr">__TITLE_FR__</span></h1>
      <p class="lead lang-en">__LEAD_EN__</p>
      <p class="lead lang-fr">__LEAD_FR__</p>
      <ul class="lang-en">__LI_EN__</ul>
      <ul class="lang-fr">__LI_FR__</ul>
      <div class="actions">
        <a class="btn-primary" href="__TRACK_HASH__"><span class="lang-en">Request Free 1-Page Scope Preview</span><span class="lang-fr">Demander un Aper&ccedil;u Gratuit (1 Page)</span></a>
        <a class="btn-outline" href="__SAMPLE_ZIP__" download><span class="lang-en">&#8595; __SAMPLE_LBL_EN__</span><span class="lang-fr">&#8595; __SAMPLE_LBL_FR__</span></a>
      </div>
    </article>
  </main>
  <footer>
    <span>Contact: <a href="mailto:__EMAIL__">__EMAIL__</a> &middot; <a href="privacy.html">Privacy (GDPR / nFADP)</a> &middot; <a href="sitemap.xml">Sitemap</a></span>
  </footer>
</body>
</html>
"""
    return (
        template.replace("__TITLE_EN__", html.escape(title_en))
        .replace("__TITLE_FR__", html.escape(title_fr))
        .replace("__BRAND__", html.escape(brand))
        .replace("__META_DESC__", html.escape(meta_desc))
        .replace("__CANONICAL__", html.escape(f"{website}/{filename}"))
        .replace("__EYEBROW__", html.escape(eyebrow))
        .replace("__LEAD_EN__", html.escape(lead_en))
        .replace("__LEAD_FR__", html.escape(lead_fr))
        .replace("__LI_EN__", li_en)
        .replace("__LI_FR__", li_fr)
        .replace("__TRACK_HASH__", html.escape(track_hash))
        .replace("__SAMPLE_ZIP__", html.escape(sample_zip_rel))
        .replace("__SAMPLE_LBL_EN__", html.escape(sample_label_en))
        .replace("__SAMPLE_LBL_FR__", html.escape(sample_label_fr))
        .replace("__EMAIL__", html.escape(email))
    )


def render_seo_pages(cfg: dict[str, Any], target: Path) -> dict[str, Path]:
    """Generate focused Switzerland/France B2B SEO pages + `sitemap.xml` inside `target`."""
    prov = cfg["provider"]
    website = (prov.get("website_url") or "https://kaledbouchagraoui7-bot.github.io/medtech-regulatory-compliance-suite/").rstrip("/")
    specs = [
        (
            "nfadp_audit_html",
            "nfadp-audit.html",
            {
                "title_en": "Swiss nFADP, EU GDPR & DMARC/SPF 25-Control External Audit",
                "title_fr": "Audit Externe nLPD Suisse, RGPD France & DMARC/SPF 25 Contrôles",
                "meta_desc": "Passive DNS/DMARC (>10 SPF lookup cap), MTA-STS, Google Fonts IP leak (nFADP/GDPR Art. 44), CMP Reject symmetry, and edge TLS/CSP posture audit in 48h for CH and FR MedTech firms.",
                "eyebrow": "Track 01 · Switzerland nFADP/nLPD & France CNIL/RGPD · EUR 350–450 / CHF 350",
                "lead_en": "Built for MedTech, Diagnostics, Biotech, and regulated B2B firms across Geneva, Vaud, Zurich, Basel, Paris, Lyon, and Strasbourg needing verifiable public-posture evidence without invasive scanning.",
                "lead_fr": "Conçu pour les entreprises MedTech, Diagnostic et B2B régulées en Suisse romande/alémanique et en France (Paris, Lyon, Strasbourg, Grenoble) exigeant une preuve passive conforme.",
                "bullets_en": [
                    ("100% Passive StGB Art. 143bis / Art. 323-1 CP Posture", "Zero intrusive probing or port scanning; checks only public DNS TXT records, HTTPS headers, and initial DOM requests."),
                    ("RFC 7208 Recursive SPF Lookup Cap & MTA-STS", "Detects hidden SPF >10 lookup PermError breakage plus DMARC/DKIM alignment gaps before enterprise buyer emails bounce."),
                    ("Swiss nFADP Art. 8/19 & EU GDPR Art. 44 IP Leaks", "Identifies unconsented third-party US font/tracker calls and asymmetric cookie banners prior to vendor QA or CNIL/FDPIC scrutiny."),
                    ("Turnkey Nginx, Cloudflare _headers & DNS Configs", "Delivered within 48h alongside a landscape Word audit, 4-sheet Excel risk matrix, 300-DPI scorecard, and 14-day re-scan."),
                ],
                "bullets_fr": [
                    ("100% Passif (nLPD Suisse / Art. 323-1 CP)", "Aucun scan intrusif : analyse uniquement des champs DNS publics, en-têtes HTTPS et requêtes DOM initiales."),
                    ("Détection Plafond 10 Requêtes SPF & MTA-STS", "Repère les échecs cachés PermError (>10 recherches DNS SPF) et lacunes DMARC avant rejet antispam chez vos clients."),
                    ("Fuites IP Tiers & Bannières Cookies RGPD / nLPD", "Signale les polices US chargées sans consentement et les bandeaux cookies sans bouton de refus au premier niveau."),
                    ("Correctifs Prêts à Poser Sous 48h", "Rapport Word exécutif, matrice Excel 4 onglets, scorecard 300 DPI, fichiers DNS/Nginx/Cloudflare et re-contrôle inclus."),
                ],
                "sample_zip_rel": "samples/sentinel_swiss_sme_sample.zip",
                "sample_label_en": "Download Redacted Track 01 Sample ZIP",
                "sample_label_fr": "Télécharger l'Exemple ZIP Module 01",
                "track_hash": "index.html#intake",
            },
        ),
        (
            "eu_mdr_psur_html",
            "eu-mdr-psur.html",
            {
                "title_en": "EU MDR PSUR & OpenFDA MAUDE Z-Score Surveillance Packs",
                "title_fr": "Dossiers PSUR EU MDR Art. 83–86 & Signaux Statistiques MAUDE OpenFDA",
                "meta_desc": "Automated EU MDR Art. 83-86 & MDCG 2022-21 PSUR surveillance combining OpenFDA MAUDE monthly Z-score spike alerts, 510(k)/recall logs, and ClinicalTrials.gov v2 PMCF links.",
                "eyebrow": "Track 02 · EU MDR Art. 83–86 & MDCG 2022-21 · EUR 650 / CHF 690",
                "lead_en": "Accelerate recurring PSUR, PMS Plan, and PRRC safety reviews for Class IIa/IIb/III medical devices across Swiss (MedDO) and French/EU manufacturers.",
                "lead_fr": "Accélérez vos cycles PSUR, PMS et revues PRRC pour dispositifs médicaux Classe IIa/IIb/III en France et en Suisse (ODim / MedDO).",
                "bullets_en": [
                    ("Monthly Z-Score Signal Spike Alerts (Z >= 2.0)", "Computes chronological monthly MAUDE baseline mean and standard deviation to surface statistically abnormal event spikes."),
                    ("Predicate 510(k) & FDA Recall Stratification", "Consolidates K-numbers, decision dates, and Class I/II/III enforcement records into filterable Excel tables."),
                    ("ClinicalTrials.gov v2 Clickable PMCF Registry", "Pairs live interventional and observational study NCT links with sponsor, phase, status, and enrollment counts."),
                    ("ALCOA+ Provenance & Zero Guesses", "Blank narratives or unmapped FDA device codes are clearly shaded #FFF2CC with timestamped API query metadata."),
                ],
                "bullets_fr": [
                    ("Alertes Statistiques Mensuelles Z-Score (Z >= 2.0)", "Agrège les séries mensuelles OpenFDA MAUDE pour détecter automatiquement les pics anormaux de signalement."),
                    ("Historique 510(k) & Rappels Produits FDA", "Consolide les numéros K, dates de décision et classes de rappel dans un classeur Excel filtrable."),
                    ("Registre PMCF ClinicalTrials.gov v2 Cliquable", "Relie directement chaque étude clinique active/terminée par lien NCT officiel avec promoteur et effectifs."),
                    ("Traçabilité ALCOA+ & Zéro Donnée Inventée", "Tout champ source manquant reste surligné #FFF2CC avec horodatage exact des requêtes API."),
                ],
                "sample_zip_rel": "samples/pms_cgm_class_iib_sample.zip",
                "sample_label_en": "Download CGM PSUR Sample ZIP",
                "sample_label_fr": "Télécharger l'Exemple PSUR ZIP",
                "track_hash": "index.html#intake",
            },
        ),
        (
            "prisma_2020_html",
            "prisma-2020.html",
            {
                "title_en": "PRISMA 2020 Clinical Evidence, RoB Summary & .ris / .bib Packs",
                "title_fr": "Revues PRISMA 2020, Grille RoB & Exports .ris / .bib pour CER EU MDR",
                "meta_desc": "Traceable PubMed + Europe PMC PRISMA 2020 literature synthesis with conserved integer flow equations, ICH E9 Table 1 baseline stats, RoB 2 / NOS mapping, and Zotero/EndNote .ris/.bib export.",
                "eyebrow": "Track 03 · EU MDR Annex XIV CER & ICH E6/E9 · EUR 750 / CHF 790",
                "lead_en": "Built for CROs, Medical Writers, and Clinical Affairs leaders in Switzerland and France compiling Clinical Evaluation Reports (CER), IVDR performance files, and CTD Module 2.5 digests.",
                "lead_fr": "Conçu pour les CRO, rédacteurs médicaux et directions cliniques en France et Suisse préparant des rapports CER (Annexe XIV), dossiers IVDR ou synthèses CTD 2.5.",
                "bullets_en": [
                    ("Conserved PRISMA 2020 Arithmetic Flow", "Strict N_identified - N_dup - N_excluded = N_included verification baked into Excel COUNTIFS and 300-DPI PNG/PDF diagrams."),
                    ("Ready-to-Import .ris & .bib Reference Files", "Every pack ships UTF-8 .ris (EndNote / Zotero) and .bib (LaTeX / JabRef) libraries built from included PubMed/Europe PMC studies."),
                    ("Study-Design Risk-of-Bias Framework Summary", "Automatically maps randomized (RoB 2), observational (NOS), and appraisal (JBI) counts without inventing unverified scores."),
                    ("ICH E6/E9 Cohort Table 1 & #FFF2CC QA Flags", "Includes Shapiro-Wilk parametric/non-parametric summary workbook alongside full Word Vancouver dossier."),
                ],
                "bullets_fr": [
                    ("Équation PRISMA 2020 Vérifiée par Formules", "Conservation arithmétique stricte intégrée aux formules COUNTIFS Excel et au diagramme 300 DPI PNG/PDF."),
                    ("Exports .ris (Zotero / EndNote) & .bib (BibTeX)", "Chaque livraison inclut les fichiers bibliographiques UTF-8 prêts à importer depuis les études retenues."),
                    ("Cartographie Biais par Schéma (RoB 2 / NOS)", "Agrège automatiquement les cadres d'évaluation adaptés aux essais randomisés et études observationnelles."),
                    ("Table 1 Biostatistiques ICH E9 & Contrôle #FFF2CC", "Inclut les tests de normalité Shapiro-Wilk et le dossier Word Vancouver avec DOI cliquables."),
                ],
                "sample_zip_rel": "samples/prisma_glp1_clinical_sample.zip",
                "sample_label_en": "Download PRISMA & .ris/.bib Sample ZIP",
                "sample_label_fr": "Télécharger Exemple PRISMA + .ris/.bib ZIP",
                "track_hash": "index.html#intake",
            },
        ),
    ]

    written: dict[str, Path] = {}
    sitemap_urls: list[str] = [f"{website}/"]
    for key, fname, params in specs:
        p = target / fname
        p.write_text(_render_seo_guide_html(filename=fname, cfg=cfg, **params), encoding="utf-8")
        written[key] = p
        sitemap_urls.append(f"{website}/{fname}")

    for extra_page in ("terms.html", "cgv.html", "privacy.html"):
        sitemap_urls.append(f"{website}/{extra_page}")

    today_iso = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    url_nodes = "\n".join(
        f"  <url><loc>{html.escape(u)}</loc><lastmod>{today_iso}</lastmod></url>"
        for u in sitemap_urls
    )
    sitemap_p = target / "sitemap.xml"
    sitemap_p.write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{url_nodes}\n"
        "</urlset>\n",
        encoding="utf-8",
    )
    written["sitemap_xml"] = sitemap_p
    return written


def render_storefront_html(cfg: dict[str, Any] | None = None) -> str:
    """Render bilingual EN/FR executive storefront `index.html` with zero third-party network calls."""
    c = cfg or load_provider_config()
    prov = c["provider"]
    pay = c["payment"]
    ops = c["operations"]

    brand = prov.get("brand_name", "Sentinel Regulatory & Technical Operations")
    operator = prov.get("operator_name", "Kaled Bouchagraoui")
    city = prov.get("jurisdiction_city", "Strasbourg, France")
    email = prov.get("contact_email", "kaledbouchagraoui7@gmail.com")
    website = (prov.get("website_url") or "https://kaledbouchagraoui7-bot.github.io/medtech-regulatory-compliance-suite/").rstrip("/")
    intake_url = (ops.get("intake_form_url") or "").strip()
    stripe_links = pay.get("stripe_payment_links", {})

    schema_json = json.dumps(
        {
            "@context": "https://schema.org",
            "@type": "ProfessionalService",
            "name": brand,
            "url": website,
            "email": email,
            "areaServed": ["Switzerland", "European Union", "United Kingdom", "North America", "APAC"],
            "serviceType": [
                "MedTech Post-Market Surveillance (EU MDR PSUR / OpenFDA MAUDE)",
                "PRISMA 2020 Systematic Clinical Literature Synthesis",
                "Swiss nFADP & EU GDPR Passive Domain & Email Security Audit",
                "eCTD M1-M5 Cross-Check & RA Submission Gatekeeping",
            ],
            "address": {"@type": "PostalAddress", "addressLocality": "Strasbourg", "addressCountry": "FR"},
        },
        ensure_ascii=False,
    )

    def _cta_button(track: str, en_label: str, fr_label: str, select_val: str) -> str:
        url = (stripe_links.get(track) or "").strip()
        if url.startswith("http"):
            return (
                f'<a class="btn-outline" href="{html.escape(url)}" target="_blank" rel="noopener noreferrer">'
                f'<span class="lang-en">{html.escape(en_label)}</span>'
                f'<span class="lang-fr">{html.escape(fr_label)}</span></a>'
            )
        return (
            f'<a class="btn-outline" href="#intake" onclick="selectTrack(\'{html.escape(select_val)}\');">'
            f'<span class="lang-en">{html.escape(en_label)}</span>'
            f'<span class="lang-fr">{html.escape(fr_label)}</span></a>'
        )

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{html.escape(brand)} — EU MDR, Swiss nFADP &amp; Clinical Evidence Automation</title>
  <meta name="description" content="Audit-ready EU MDR PSUR/MAUDE surveillance, PRISMA 2020 clinical evidence tables, Swiss nFADP/GDPR passive domain posture audits, and eCTD cross-check packs delivered in 48 hours." />
  <link rel="canonical" href="{html.escape(website)}/" />
  <script type="application/ld+json">{schema_json}</script>
  <style>
    :root {{
      --navy: #0F172A;
      --navy-soft: #1E293B;
      --teal: #0F766E;
      --teal-dark: #0D5C56;
      --slate-bg: #F8FAFC;
      --card: #FFFFFF;
      --border: #E2E8F0;
      --text: #0F172A;
      --muted: #475569;
      --ok-bg: #ECFDF5;
      --ok-fg: #065F46;
      --amber-bg: #FFFBEB;
      --amber-fg: #92400E;
    }}
    * {{ box-sizing: border-box; }}
    html {{ scroll-behavior: smooth; }}
    code {{
      background: #F1F5F9;
      border: 1px solid #E2E8F0;
      border-radius: 4px;
      padding: 1px 5px;
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      font-size: 0.88em;
      color: var(--navy);
    }}
    body {{
      margin: 0;
      background: var(--slate-bg);
      color: var(--text);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      line-height: 1.58;
      -webkit-font-smoothing: antialiased;
    }}
    .lang-fr {{ display: none; }}
    body.is-fr .lang-en {{ display: none; }}
    body.is-fr .lang-fr {{ display: inline; }}
    div.lang-fr, section.lang-fr, p.lang-fr, ul.lang-fr {{ display: none; }}
    body.is-fr div.lang-en, body.is-fr p.lang-en, body.is-fr ul.lang-en {{ display: none; }}
    body.is-fr div.lang-fr, body.is-fr p.lang-fr, body.is-fr ul.lang-fr {{ display: block; }}

    .topbar {{
      background: var(--navy);
      color: #F8FAFC;
      font-size: 12.5px;
      padding: 8px 24px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 10px;
    }}
    .topbar span {{ opacity: 0.92; }}
    header.nav-wrap {{
      background: #FFFFFF;
      border-bottom: 1px solid var(--border);
      position: sticky;
      top: 0;
      z-index: 20;
    }}
    nav.nav {{
      max-width: 1120px;
      margin: 0 auto;
      padding: 14px 24px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 16px;
      flex-wrap: wrap;
    }}
    .brand-link {{
      display: flex;
      align-items: center;
      gap: 12px;
      text-decoration: none;
      color: var(--navy);
      font-weight: 700;
      font-size: 16px;
    }}
    .brand-link img {{
      height: 36px;
      width: auto;
      display: block;
    }}
    .nav-right {{
      display: flex;
      align-items: center;
      gap: 18px;
      flex-wrap: wrap;
    }}
    .nav-links {{
      display: flex;
      gap: 18px;
      flex-wrap: wrap;
      font-size: 14px;
    }}
    .nav-links a {{
      color: var(--navy-soft);
      text-decoration: none;
      font-weight: 600;
    }}
    .nav-links a:hover {{ color: var(--teal); }}
    .lang-toggle {{
      display: inline-flex;
      border: 1px solid var(--border);
      border-radius: 6px;
      overflow: hidden;
      background: var(--slate-bg);
    }}
    .lang-toggle button {{
      border: none;
      background: transparent;
      padding: 6px 11px;
      font-size: 12.5px;
      font-weight: 700;
      cursor: pointer;
      color: var(--muted);
    }}
    .lang-toggle button.active {{
      background: var(--navy);
      color: #FFFFFF;
    }}

    .container {{
      max-width: 1120px;
      margin: 0 auto;
      padding: 0 24px;
    }}
    .hero {{
      padding: 54px 0 42px 0;
      border-bottom: 1px solid var(--border);
      background: #FFFFFF;
    }}
    .hero-grid {{
      display: grid;
      grid-template-columns: 1.25fr 0.95fr;
      gap: 36px;
      align-items: center;
    }}
    .eyebrow {{
      font-size: 11.5px;
      font-weight: 700;
      letter-spacing: 1.5px;
      text-transform: uppercase;
      color: var(--teal);
      margin-bottom: 10px;
    }}
    h1 {{
      font-family: Georgia, "Times New Roman", serif;
      font-size: clamp(28px, 3.6vw, 40px);
      line-height: 1.18;
      margin: 0 0 16px 0;
      color: var(--navy);
    }}
    .hero-sub {{
      font-size: 16.5px;
      color: var(--muted);
      margin: 0 0 24px 0;
      max-width: 610px;
    }}
    .hero-actions {{
      display: flex;
      gap: 12px;
      flex-wrap: wrap;
      margin-bottom: 22px;
    }}
    .btn-primary {{
      display: inline-block;
      background: var(--teal);
      color: #FFFFFF;
      padding: 12px 22px;
      border-radius: 6px;
      text-decoration: none;
      font-weight: 700;
      font-size: 14.5px;
      border: 1px solid var(--teal);
      cursor: pointer;
    }}
    .btn-primary:hover {{ background: var(--teal-dark); }}
    .btn-outline {{
      display: inline-block;
      background: #FFFFFF;
      color: var(--navy);
      padding: 11px 18px;
      border-radius: 6px;
      text-decoration: none;
      font-weight: 700;
      font-size: 14px;
      border: 1px solid var(--border);
    }}
    .btn-outline:hover {{ border-color: var(--teal); color: var(--teal); }}
    .trust-strip {{
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
    }}
    .pill {{
      background: var(--slate-bg);
      border: 1px solid var(--border);
      padding: 6px 11px;
      border-radius: 4px;
      font-size: 12.5px;
      font-weight: 600;
      color: var(--navy-soft);
    }}
    .hero-card {{
      background: var(--slate-bg);
      border: 1px solid var(--border);
      border-top: 4px solid var(--navy);
      padding: 22px;
      border-radius: 6px;
    }}
    .hero-card h2 {{
      font-size: 16px;
      margin: 0 0 10px 0;
      color: var(--navy);
    }}
    .hero-card ul {{
      margin: 0;
      padding-left: 18px;
      color: var(--muted);
      font-size: 13.5px;
    }}
    .hero-card li {{ margin-bottom: 8px; }}

    section.band {{ padding: 48px 0; border-bottom: 1px solid var(--border); }}
    .sec-head {{ margin-bottom: 26px; }}
    .sec-head h2 {{
      font-family: Georgia, "Times New Roman", serif;
      font-size: 27px;
      margin: 0 0 8px 0;
      color: var(--navy);
    }}
    .sec-head p {{ margin: 0; color: var(--muted); max-width: 680px; }}

    .offers-grid {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 22px;
    }}
    .offer-card {{
      background: var(--card);
      border: 1px solid var(--border);
      border-top: 3.5px solid var(--teal);
      border-radius: 6px;
      padding: 24px;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
    }}
    .offer-top {{
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      gap: 12px;
      margin-bottom: 10px;
    }}
    .offer-tag {{
      font-size: 11px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 1.1px;
      color: var(--teal);
    }}
    .price-badge {{
      background: var(--ok-bg);
      color: var(--ok-fg);
      font-weight: 700;
      font-size: 13px;
      padding: 4px 10px;
      border-radius: 4px;
      white-space: nowrap;
    }}
    .offer-card h3 {{
      margin: 4px 0 10px 0;
      font-size: 19px;
      color: var(--navy);
    }}
    .offer-card p {{
      margin: 0 0 14px 0;
      font-size: 14px;
      color: var(--muted);
    }}
    .offer-card ul {{
      margin: 0 0 18px 0;
      padding-left: 18px;
      font-size: 13.5px;
      color: var(--navy-soft);
    }}
    .offer-card li {{ margin-bottom: 5px; }}

    .gallery-grid {{
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 20px;
    }}
    .specimen {{
      background: #FFFFFF;
      border: 1px solid var(--border);
      border-radius: 6px;
      overflow: hidden;
    }}
    .specimen img {{
      width: 100%;
      height: auto;
      display: block;
      border-bottom: 1px solid var(--border);
    }}
    .specimen-body {{ padding: 14px 16px; }}
    .specimen-body h3 {{ margin: 0 0 6px 0; font-size: 15px; color: var(--navy); }}
    .specimen-body p {{ margin: 0; font-size: 13px; color: var(--muted); }}

    .intake-box {{
      background: #FFFFFF;
      border: 1px solid var(--border);
      border-left: 4px solid var(--teal);
      border-radius: 6px;
      padding: 28px;
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 28px;
      align-items: start;
    }}
    .form-row {{ margin-bottom: 12px; }}
    .form-row label {{
      display: block;
      font-size: 13px;
      font-weight: 700;
      margin-bottom: 4px;
      color: var(--navy-soft);
    }}
    .form-row input, .form-row select, .form-row textarea {{
      width: 100%;
      padding: 9px 11px;
      border: 1px solid var(--border);
      border-radius: 5px;
      font-family: inherit;
      font-size: 14px;
      background: var(--slate-bg);
    }}
    .notice-box {{
      background: var(--amber-bg);
      color: var(--amber-fg);
      border: 1px solid #FDE68A;
      border-radius: 6px;
      padding: 14px 16px;
      font-size: 13px;
      margin-top: 16px;
    }}

    footer.site-foot {{
      background: var(--navy);
      color: #CBD5E1;
      padding: 30px 24px;
      font-size: 13px;
    }}
    .foot-inner {{
      max-width: 1120px;
      margin: 0 auto;
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 16px;
    }}
    footer.site-foot a {{ color: #5EEAD4; text-decoration: none; font-weight: 600; }}
    footer.site-foot a:hover {{ text-decoration: underline; }}
    {_specimen_inspector_css()}
    {_live_check_css()}

    @media (max-width: 860px) {{
      .hero-grid, .offers-grid, .gallery-grid, .intake-box {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
  <div class="topbar">
    <span>
      <span class="lang-en">Sentinel Regulatory &amp; Technical Operations &middot; Strasbourg, France &middot; Switzerland (nFADP) &amp; EU (GDPR / MDR)</span>
      <span class="lang-fr">Sentinel Regulatory &amp; Technical Operations &middot; Strasbourg, France &middot; Suisse (nLPD) &amp; UE (RGPD / MDR)</span>
    </span>
    <span>
      <span class="lang-en">48h Fixed-Scope Delivery &middot; Verified Against Primary Public Registries</span>
      <span class="lang-fr">Livraison sous 48h &middot; Traçabilité Directe sur Registres Publics Officiels</span>
    </span>
  </div>

  <header class="nav-wrap">
    <nav class="nav" aria-label="Main Navigation">
      <a class="brand-link" href="#top">
        <img src="assets/sentinel_logo_editorial.png" alt="Sentinel Regulatory &amp; Technical Operations" />
      </a>
      <div class="nav-right">
        <div class="nav-links">
          <a href="#offers"><span class="lang-en">Solutions</span><span class="lang-fr">Solutions</span></a>
          <a href="#live-check"><span class="lang-en">Live Pre-Check</span><span class="lang-fr">Test Direct</span></a>
          <a href="#specimens"><span class="lang-en">Sample Outputs</span><span class="lang-fr">Exemples</span></a>
          <a href="#intake"><span class="lang-en">Free 1-Page Preview</span><span class="lang-fr">Aperçu Gratuit</span></a>
          <a href="terms.html">Terms (EN)</a>
          <a href="cgv.html">CGV (FR)</a>
        </div>
        <div class="lang-toggle" role="group" aria-label="Language switch">
          <button id="btn-en" class="active" type="button" onclick="setLang('en')">EN</button>
          <button id="btn-fr" type="button" onclick="setLang('fr')">FR</button>
        </div>
      </div>
    </nav>
  </header>

  <main id="top">
    <section class="hero">
      <div class="container hero-grid">
        <div>
          <div class="eyebrow">
            <span class="lang-en">Switzerland &middot; France &middot; EU MedTech &middot; Biotech &middot; CROs &middot; RA Consultancies</span>
            <span class="lang-fr">Suisse &middot; France &middot; UE MedTech &middot; Biotech &middot; CROs &middot; Cabinets AR</span>
          </div>
          <h1>
            <span class="lang-en">Audit-Ready Technical Compliance, PSUR Safety &amp; PRISMA 2020 Dossiers in 48 Hours.</span>
            <span class="lang-fr">Audits de Conformité, Dossiers PSUR/MAUDE &amp; Revues PRISMA 2020 Livrés en 48 Heures.</span>
          </h1>
          <p class="hero-sub lang-en">
            Built for QA/RA Directors, PRRCs, Medical Writers, and DPOs across Switzerland, France, and the EU. Every deliverable ships as a sign-off-ready Word dossier, 4-to-6-sheet Excel matrix, 300-DPI executive visual, and SHA-256 ALCOA+ provenance log &mdash; with zero fabricated citations.
          </p>
          <p class="hero-sub lang-fr">
            Conçu pour les Directions Qualité/AR, PRRC, Rédacteurs Médicaux et DPO en Suisse, France et UE. Chaque mission produit un rapport Word structuré, un classeur Excel filtrable à 4–6 onglets, un visuel 300 DPI et un manifeste d'audit ALCOA+ SHA-256 sans aucune donnée inventée.
          </p>
          <div class="hero-actions">
            <a class="btn-primary" href="#intake">
              <span class="lang-en">Request Complimentary 1-Page Scope Preview</span>
              <span class="lang-fr">Demander un Aperçu Gratuit (1 Page)</span>
            </a>
            <a class="btn-outline" href="#live-check">
              <span class="lang-en">Run Live Pre-Check</span>
              <span class="lang-fr">Tester en Direct</span>
            </a>
            <a class="btn-outline" href="#offers">
              <span class="lang-en">Inspect Fixed-Fee Packages</span>
              <span class="lang-fr">Voir les Forfaits</span>
            </a>
          </div>
          <div class="trust-strip">
            <span class="pill">100% Passive DNS/TLS/HTTPS (StGB Art. 143bis)</span>
            <span class="pill">OpenFDA Z-Score Spikes &amp; CT.gov v2</span>
            <span class="pill">PRISMA 2020 + .ris/.bib + RoB</span>
            <span class="pill">#FFF2CC Zero-Fabrication QA Flagging</span>
          </div>
        </div>

        <aside class="hero-card">
          <h2>
            <span class="lang-en">Every Fixed-Fee Engagement Includes</span>
            <span class="lang-fr">Inclus dans Chaque Dossier Clé en Main</span>
          </h2>
          <ul class="lang-en">
            <li><strong>Landscape Word Executive Dossier (<code>.docx</code>):</strong> Ready for internal PRRC, Notified Body, or vendor due diligence review.</li>
            <li><strong>Multi-Sheet Filterable Excel Register (<code>.xlsx</code>):</strong> Frozen headers, AutoFilters, formulas, and <code>#FFF2CC</code> QA flags for unverified items.</li>
            <li><strong>300-DPI Boardroom Visual Brief (<code>.png</code> &amp; <code>.pdf</code>):</strong> Print-grade scorecard, PSUR safety radar, or PRISMA 2020 flowchart.</li>
            <li><strong>ALCOA+ SHA-256 Manifest &amp; Turnkey Fixes:</strong> Reproducible query provenance plus copy-paste Nginx, Cloudflare, and DMARC/SPF DNS configs.</li>
          </ul>
          <ul class="lang-fr">
            <li><strong>Dossier Exécutif Word Paysage (<code>.docx</code>) :</strong> Prêt pour relecture PRRC, Organisme Notifié ou audit fournisseur.</li>
            <li><strong>Classeur Excel Filtrable Multi-Onglets (<code>.xlsx</code>) :</strong> Formules actives, liens DOI/NCT cliquables et drapeaux QA <code>#FFF2CC</code>.</li>
            <li><strong>Synthèse Visuelle 300 DPI (<code>.png</code> &amp; <code>.pdf</code>) :</strong> Scorecard sécurité, radar MAUDE ou diagramme PRISMA 2020 haute résolution.</li>
            <li><strong>Manifeste ALCOA+ SHA-256 &amp; Correctifs IT :</strong> Preuve d'extraction horodatée et configurations Nginx, Cloudflare et DNS DMARC/SPF prêtes à déployer.</li>
          </ul>
        </aside>
      </div>

      <div class="container ch-fr-strip">
        <div class="jurisdiction-card">
          <h3>
            <span class="lang-en">Switzerland (CH) &middot; Romandie &amp; DACH MedTech Focus</span>
            <span class="lang-fr">Suisse (CH) &middot; Romandie &amp; Pôle MedTech Alémanique</span>
          </h3>
          <p class="lang-en">Dedicated 1-to-1 scope diagnostics (CHF 350&ndash;1,150) covering Swiss nFADP/nLPD visitor-IP compliance, MedDO/EU MDR PSUR surveillance, and CER literature matrices &mdash; strictly manual and compliant with UWG Art. 3(1)(o).</p>
          <p class="lang-fr">Diagnostics individuels dédiés (350&ndash;1 150 CHF) couvrant la nLPD (art. 8/19), la surveillance ODim / EU MDR PSUR et les synthèses cliniques CER &mdash; traitement 100% manuel conforme LCD art. 3 al. 1 let. o.</p>
          <div class="jurisdiction-links">
            <a href="nfadp-audit.html"><span class="lang-en">Swiss nFADP Audit Guide &rarr;</span><span class="lang-fr">Guide Audit nLPD Suisse &rarr;</span></a>
          </div>
        </div>
        <div class="jurisdiction-card fr-accent">
          <h3>
            <span class="lang-en">France &amp; Benelux (FR / BE / LU) &middot; Direct Strasbourg Base</span>
            <span class="lang-fr">France &amp; Benelux (FR / BE / LU) &middot; Base Strasbourg</span>
          </h3>
          <p class="lang-en">Native bilingual FR/EN delivery (EUR 350&ndash;1,100; TVA art. 293 B CGI) built for French/Belgian MedTech, Diagnostics, CRO, and Digital Health teams seeking CNIL, EU MDR Art. 83&ndash;86, and PRISMA 2020 evidence packs.</p>
          <p class="lang-fr">Livraison bilingue FR/EN (350&ndash;1 100 EUR ; TVA art. 293 B CGI) pour acteurs français et belges MedTech, Diagnostic, CRO et e-santé : posture CNIL/RGPD, PSUR EU MDR Art. 83&ndash;86 et revues PRISMA 2020.</p>
          <div class="jurisdiction-links">
            <a href="eu-mdr-psur.html"><span class="lang-en">EU MDR PSUR Guide &rarr;</span><span class="lang-fr">Guide PSUR MDR &rarr;</span></a> &middot;
            <a href="prisma-2020.html"><span class="lang-en">PRISMA 2020 &amp; .ris/.bib &rarr;</span><span class="lang-fr">Guide PRISMA 2020 &rarr;</span></a>
          </div>
        </div>
      </div>
    </section>

    <section class="band" id="offers">
      <div class="container">
        <div class="sec-head">
          <div class="eyebrow"><span class="lang-en">Productized B2B Deliverables</span><span class="lang-fr">Offres Forfaitaires B2B</span></div>
          <h2>
            <span class="lang-en">Four Audited Regulatory &amp; Technical Modules</span>
            <span class="lang-fr">Quatre Modules Réglementaires &amp; Techniques Automatisés</span>
          </h2>
          <p class="lang-en">Transparent fixed-scope delivery in 48 hours. Complimentary 1-page pre-engagement diagnostics allow your QA/IT team to verify accuracy before commissioning a full package.</p>
          <p class="lang-fr">Forfaits clairs livrés sous 48 heures. Demandez d'abord un aperçu diagnostique gratuit d'une page pour valider la précision technique avant toute commande.</p>
        </div>

        <div class="offers-grid">
          <article class="offer-card">
            <div>
              <div class="offer-top">
                <span class="offer-tag">Track 01 &middot; Cyber, Privacy &amp; DMARC</span>
                <span class="price-badge">EUR 350–450 &middot; CHF 350</span>
              </div>
              <h3>
                <span class="lang-en">Sentinel 25-Control External Posture &amp; Privacy Audit</span>
                <span class="lang-fr">Audit Externe 25 Contrôles : Vie Privée, DMARC &amp; Sécurité Edge</span>
              </h3>
              <p class="lang-en">Passive check of DMARC, recursive SPF (&gt;10 lookup PermError risk), MTA-STS, pre-consent US Google Fonts / tracker leaks (Swiss nFADP / EU GDPR Art. 44), TLS/HSTS/CSP edge headers, and WCAG 2.1 AA readiness.</p>
              <p class="lang-fr">Analyse strictement passive des risques DMARC, plafond 10 requêtes SPF, MTA-STS, fuites IP avant consentement (nFADP suisse / RGPD art. 44), en-têtes TLS/HSTS/CSP et accessibilité WCAG 2.1 AA.</p>
              <ul>
                <li>Word Executive Audit + 4-Sheet Excel Risk Matrix</li>
                <li>Ready-to-paste DNS (DMARC/SPF/CAA), Nginx &amp; Cloudflare <code>_headers</code></li>
                <li>1 complimentary verification re-scan within 14 days</li>
              </ul>
            </div>
            {_cta_button("sentinel_compliance", "Request Track 01 Scope", "Commander / Aperçu Module 01", "Track 01 - Sentinel 25-Control External Audit")}
          </article>

          <article class="offer-card">
            <div>
              <div class="offer-top">
                <span class="offer-tag">Track 02 &middot; EU MDR Art. 83–86 PMS</span>
                <span class="price-badge">EUR 650 &middot; CHF 690</span>
              </div>
              <h3>
                <span class="lang-en">OpenFDA MAUDE &amp; ClinicalTrials.gov PSUR Surveillance</span>
                <span class="lang-fr">Dossier Veille Post-Marché (PMS / PSUR) OpenFDA &amp; ClinicalTrials</span>
              </h3>
              <p class="lang-en">Automates FDA MAUDE event stratification (Malfunction, Injury, Death, monthly Z-score signal spikes), predicate 510(k)/recall tracking, and active/completed PMCF trial links under MDCG 2022-21.</p>
              <p class="lang-fr">Structuration automatisée des rapports MAUDE (pannes, blessures, décès, pics statistiques mensuels Z-score), rappels/510(k) et études PMCF actives sous Règlement UE MDR &amp; MDCG 2022-21.</p>
              <ul>
                <li>Landscape Word PSUR Surveillance Draft + 300-DPI Dashboard</li>
                <li>4-Sheet Excel Workbook with Monthly Spike Alerts &amp; <code>NCTId</code> Links</li>
                <li>Documented API query snapshot &amp; ALCOA+ SHA-256 manifest</li>
              </ul>
            </div>
            {_cta_button("pms_openfda_psur", "Request Track 02 Scope", "Commander / Aperçu Module 02", "Track 02 - OpenFDA MAUDE & PSUR Surveillance")}
          </article>

          <article class="offer-card">
            <div>
              <div class="offer-top">
                <span class="offer-tag">Track 03 &middot; EU MDR Annex XIV / CER</span>
                <span class="price-badge">EUR 750 &middot; CHF 790</span>
              </div>
              <h3>
                <span class="lang-en">PRISMA 2020 Literature Synthesis &amp; ICH E9 Table 1 Pack</span>
                <span class="lang-fr">Revue Systématique PRISMA 2020, CER &amp; Table 1 Biostatistiques</span>
              </h3>
              <p class="lang-en">Dual-source NCBI PubMed + Europe PMC literature screening with verified PRISMA arithmetic conservation, RoB 2 / NOS mapping, Zotero/EndNote <code>.ris</code> &amp; <code>.bib</code> files, and optional ICH E9 Table 1 cohort stats.</p>
              <p class="lang-fr">Criblage documentaire PubMed / Europe PMC avec équation PRISMA 2020 vérifiée, cartographie RoB 2 / NOS, exports <code>.ris</code> / <code>.bib</code> pour Zotero/EndNote et Table 1 biostatistiques ICH E9.</p>
              <ul>
                <li>Vancouver-Cited Word Table + 300-DPI PRISMA 2020 Flow Diagram</li>
                <li>4-Sheet Excel Matrix (<code>COUNTIFS</code> formulas &amp; <code>#FFF2CC</code> QA flags)</li>
                <li>Ready-to-import <code>.ris</code> / <code>.bib</code> citations — zero invented data</li>
              </ul>
            </div>
            {_cta_button("clinical_lit_prisma", "Request Track 03 Scope", "Commander / Aperçu Module 03", "Track 03 - PRISMA 2020 Clinical Evidence & Table 1")}
          </article>

          <article class="offer-card">
            <div>
              <div class="offer-top">
                <span class="offer-tag">Track 04 &middot; Full Dossier &amp; eCTD</span>
                <span class="price-badge">EUR 950–1,100 &middot; CHF 1,150</span>
              </div>
              <h3>
                <span class="lang-en">Unified MedTech Suite &amp; eCTD M1–M5 Gatekeeper Pack</span>
                <span class="lang-fr">Suite Unifiée MedTech &amp; Linter Réglementaire eCTD M1–M5</span>
              </h3>
              <p class="lang-en">Combines full external posture review + clinical PRISMA 2020 CER pack, OR delivers our 6-sheet RA Command Center (Upstream SLA Blame-Shield, Agency Drift Radar, eCTD N-count cross-check linter).</p>
              <p class="lang-fr">Combine l'audit externe + dossier clinique PRISMA 2020, ou déploie le Centre de Commande AR à 6 onglets (suivi SLA inter-départements, veille FDA/EMA, contrôle croisé eCTD M1–M5).</p>
              <ul>
                <li><code>00_Unified_Executive_Brief.docx</code> + Combined Track Directories</li>
                <li>6-Sheet eCTD &amp; Upstream Delay Attribution Register</li>
                <li>Full SHA-256 ALCOA+ Provenance &amp; Signed QA Sign-Off Checklist</li>
              </ul>
            </div>
            {_cta_button("unified_dossier", "Request Unified Scope", "Commander / Aperçu Pack Unifié", "Track 04 - Unified Dossier / eCTD RA Command")}
          </article>
        </div>
      </div>
    </section>

{render_live_check_section_html()}

    <section class="band" id="specimens" style="background:#FFFFFF;">
      <div class="container">
        <div class="sec-head">
          <div class="eyebrow"><span class="lang-en">Verified Architecture &amp; Output Specimens</span><span class="lang-fr">Spécimens de Livrables Réels</span></div>
          <h2>
            <span class="lang-en">Swiss-Editorial Briefings Built for QA &amp; Board Review</span>
            <span class="lang-fr">Livrables Éditoriaux Haute Précision (300 DPI)</span>
          </h2>
          <p class="lang-en">Click any specimen sheet below to inspect the methodology, regulatory mappings, and audit trails delivered alongside every Word and Excel archive.</p>
          <p class="lang-fr">Cliquez sur chaque fiche méthodologique pour consulter l'architecture exacte des contrôles et tableaux remis au client.</p>
        </div>
{render_specimen_inspector_html()}
        <div class="gallery-grid">
          <article class="specimen">
            <a href="assets/Sentinel_25_Control_Evaluation_System.png" target="_blank" rel="noopener noreferrer">
              <img src="assets/Sentinel_25_Control_Evaluation_System.png" alt="Sentinel 25-Control Passive External Assessment Specification Sheet" />
            </a>
            <div class="specimen-body">
              <h3>Sentinel 25-Control Specification</h3>
              <p>DMARC/SPF, nFADP/GDPR pre-consent trackers, HTTP headers &amp; WCAG 2.1 AA.</p>
            </div>
          </article>
          <article class="specimen">
            <a href="assets/PMS_MAUDE_PSUR_Evaluation_System.png" target="_blank" rel="noopener noreferrer">
              <img src="assets/PMS_MAUDE_PSUR_Evaluation_System.png" alt="Automated OpenFDA MAUDE and ClinicalTrials.gov PSUR Framework Sheet" />
            </a>
            <div class="specimen-body">
              <h3>OpenFDA MAUDE &amp; PSUR Framework</h3>
              <p>EU MDR Art. 83–86 event stratification, 510(k)/recall logs &amp; ClinicalTrials v2 links.</p>
            </div>
          </article>
          <article class="specimen">
            <a href="assets/Clinical_Literature_Biostats_Evaluation_System.png" target="_blank" rel="noopener noreferrer">
              <img src="assets/Clinical_Literature_Biostats_Evaluation_System.png" alt="PRISMA 2020 Clinical Literature, Biostatistics Table 1 and RefSeq QC Suite" />
            </a>
            <div class="specimen-body">
              <h3>PRISMA 2020 &amp; Biostats Suite</h3>
              <p>Europe PMC/PubMed deduplication, conserved flowcharts, Table 1 &amp; <code>#FFF2CC</code> QA audit.</p>
            </div>
          </article>
        </div>
      </div>
    </section>

    <section class="band" id="intake">
      <div class="container">
        <div class="intake-box">
          <div>
            <div class="eyebrow"><span class="lang-en">Zero-Obligation First Step</span><span class="lang-fr">Premier Pas Sans Engagement</span></div>
            <h2 style="font-family:Georgia,serif;font-size:26px;margin:0 0 10px 0;color:var(--navy);">
              <span class="lang-en">Request a Complimentary 1-Page Preview</span>
              <span class="lang-fr">Demander Votre Aperçu Gratuit (1 Page)</span>
            </h2>
            <p class="lang-en" style="color:var(--muted);font-size:14.5px;">
              Provide your corporate domain or target device/literature scope. Within 48 hours we prepare a strictly passive 1-page diagnostic snapshot (EUR 0.00, no obligation) plus an exact fixed-fee confirmation sheet for internal QA approval.
            </p>
            <p class="lang-fr" style="color:var(--muted);font-size:14.5px;">
              Indiquez votre domaine d'entreprise ou thème dispositif/clinique. Sous 48h, recevez un aperçu diagnostique passif d'une page (0,00 EUR, sans engagement) accompagné du périmètre forfaitaire exact pour validation Qualité/AR.
            </p>
            <div class="notice-box">
              <strong>
                <span class="lang-en">Legal &amp; Commercial Transparency (v{TERMS_VERSION}):</span>
                <span class="lang-fr">Transparence Juridique &amp; Facturation (v{TERMS_VERSION}) :</span>
              </strong>
              <span class="lang-en">Complimentary diagnostics are non-invoiced preparation aids (EUR 0 liability). Any paid mission is formalized cleanly through an authorized French legal billing structure prior to payment or invoice issuance (<a href="terms.html">Terms</a> &middot; <a href="privacy.html">Privacy</a>).</span>
              <span class="lang-fr">Les diagnostics initiaux d'une page sont gracieux (0 EUR, sans facturation). Toute mission payante est formalisée au préalable via une structure de facturation dûment habilitée conformément au droit français (<a href="cgv.html">CGV</a> &middot; <a href="privacy.html">Confidentialité</a>).</span>
            </div>
          </div>

          <form onsubmit="return handleIntakeSubmit(event);">
            <div class="form-row">
              <label for="f-company"><span class="lang-en">Company / Organization</span><span class="lang-fr">Société / Organisation</span></label>
              <input id="f-company" type="text" required placeholder="e.g. Helvetia MedTech AG" />
            </div>
            <div class="form-row">
              <label for="f-domain"><span class="lang-en">Corporate Domain or Product / Topic</span><span class="lang-fr">Domaine Web ou Dispositif / Sujet Clinique</span></label>
              <input id="f-domain" type="text" required placeholder="e.g. example-medtech.ch / cardiac catheter / GLP-1 CER" />
            </div>
            <div class="form-row">
              <label for="f-track"><span class="lang-en">Target Module</span><span class="lang-fr">Module Souhaité</span></label>
              <select id="f-track">
                <option value="Track 01 - Sentinel 25-Control External Audit">Track 01 &mdash; External Privacy, DMARC &amp; Edge Audit</option>
                <option value="Track 02 - OpenFDA MAUDE &amp; PSUR Surveillance">Track 02 &mdash; OpenFDA MAUDE &amp; ClinicalTrials PSUR</option>
                <option value="Track 03 - PRISMA 2020 Clinical Evidence &amp; Table 1">Track 03 &mdash; PRISMA 2020 &amp; ICH E9 Table 1</option>
                <option value="Track 04 - Unified Dossier / eCTD RA Command">Track 04 &mdash; Unified Dossier / eCTD Cross-Check</option>
              </select>
            </div>
            <div class="form-row">
              <label for="f-notes"><span class="lang-en">Optional Context (FDA Product Code, PICO keywords, or jurisdiction)</span><span class="lang-fr">Précisions (Code produit FDA, mots-clés PICO, juridiction)</span></label>
              <textarea id="f-notes" rows="2" placeholder="Swiss nFADP, EU MDR Annex XIV CER, 5-year Europe PMC window..."></textarea>
            </div>
            <button type="submit" class="btn-primary" style="width:100%;">
              <span class="lang-en">Open Pre-Filled Scope Request Email</span>
              <span class="lang-fr">Pr&eacute;parer la Demande par E-mail Pr&eacute;-rempli</span>
            </button>
            <div class="intake-secondary-actions">
              <button type="button" class="btn-outline" onclick="openGmailWebCompose();">
                <span class="lang-en">Open in Gmail Web</span>
                <span class="lang-fr">Ouvrir dans Gmail Web</span>
              </button>
              <button type="button" class="btn-outline" onclick="copyScopeBrief();">
                <span class="lang-en">Copy Scope Brief</span>
                <span class="lang-fr">Copier le Brief</span>
              </button>
            </div>
            <p id="form-feedback" style="font-size:12.5px;color:var(--muted);margin:8px 0 0 0;"></p>
          </form>
        </div>
      </div>
    </section>
  </main>

  <footer class="site-foot">
    <div class="foot-inner">
      <div>
        &copy; {datetime.now(timezone.utc).year} {html.escape(brand)} &middot; {html.escape(operator)} ({html.escape(city)})<br />
        <span style="opacity:0.8;">{html.escape(prov.get('vat_notice', 'TVA non applicable, art. 293 B du CGI'))}</span>
      </div>
      <div>
        <a href="nfadp-audit.html">nFADP / GDPR Audit</a> &middot;
        <a href="eu-mdr-psur.html">EU MDR PSUR</a> &middot;
        <a href="prisma-2020.html">PRISMA 2020 CER</a> &middot;
        <a href="terms.html">Terms (EN)</a> &middot;
        <a href="cgv.html">CGV (FR)</a> &middot;
        <a href="privacy.html">GDPR / nFADP Privacy</a> &middot;
        <a href="TERMS_OF_SERVICE_AND_DISCLAIMER.txt">Plaintext Terms</a> &middot;
        <a href="sitemap.xml">Sitemap</a> &middot;
        <a href="mailto:{html.escape(email)}">{html.escape(email)}</a>
      </div>
    </div>
  </footer>

  <script>
{_storefront_core_js(json.dumps(intake_url), html.escape(email))}
{_live_check_js()}
  </script>
</body>
</html>
"""


def build_storefront_bundle(
    out_dir: str | Path,
    cfg: dict[str, Any] | None = None,
    sync_docs_dir: str | Path | None = None,
) -> dict[str, Path]:
    """Write `index.html`, SEO guides, `sitemap.xml`, `robots.txt`, `.well-known/security.txt`, local images, and sample ZIPs."""
    c = cfg or load_provider_config()
    prov = c["provider"]
    website = (prov.get("website_url") or "https://kaledbouchagraoui7-bot.github.io/medtech-regulatory-compliance-suite").rstrip("/")
    target = Path(out_dir)
    target.mkdir(parents=True, exist_ok=True)
    assets_dir = target / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)
    samples_dir = target / "samples"
    samples_dir.mkdir(parents=True, exist_ok=True)
    wk_dir = target / ".well-known"
    wk_dir.mkdir(parents=True, exist_ok=True)

    index_p = target / "index.html"
    index_p.write_text(render_storefront_html(c), encoding="utf-8")

    robots_p = target / "robots.txt"
    robots_p.write_text(
        f"User-agent: *\nAllow: /\nSitemap: {website}/sitemap.xml\n",
        encoding="utf-8",
    )

    sec_p = wk_dir / "security.txt"
    sec_p.write_text(
        f"Contact: mailto:{prov.get('contact_email', 'kaledbouchagraoui7@gmail.com')}\n"
        f"Expires: 2027-12-31T23:59:00.000Z\n"
        f"Preferred-Languages: en, fr\n"
        f"Policy: {website}/terms.html\n",
        encoding="utf-8",
    )

    # Copy self-hosted PNG visual assets so zero external image requests happen
    copy_candidates = [
        SUITE_DIR / "assets" / "sentinel_logo_editorial.png",
        SUITE_DIR / "assets" / "sentinel_avatar_github.png",
        SUITE_DIR / "Sentinel_25_Control_Evaluation_System.png",
        SUITE_DIR / "PMS_MAUDE_PSUR_Evaluation_System.png",
        SUITE_DIR / "Clinical_Literature_Biostats_Evaluation_System.png",
    ]
    copied: list[Path] = []
    for src in copy_candidates:
        if src.exists():
            dst = assets_dir / src.name
            shutil.copy2(src, dst)
            copied.append(dst)

    # Copy 100%-synthetic/redacted downloadable public sample ZIP archives
    pub_samples_src = SUITE_DIR / "examples" / "public_samples"
    copied_samples: list[Path] = []
    if pub_samples_src.exists():
        for src_zip in sorted(pub_samples_src.glob("*.zip")):
            dst_zip = samples_dir / src_zip.name
            shutil.copy2(src_zip, dst_zip)
            copied_samples.append(dst_zip)

    seo_written = render_seo_pages(c, target)

    result = {
        "index_html": index_p,
        "robots_txt": robots_p,
        "security_txt": sec_p,
    }
    result.update(seo_written)
    if copied:
        result["assets_dir"] = assets_dir
    if copied_samples:
        result["samples_dir"] = samples_dir

    # Optional mirror into `<repo>/docs/` for instant GitHub Pages deployment
    if sync_docs_dir is not None:
        docs_p = Path(sync_docs_dir)
        docs_p.mkdir(parents=True, exist_ok=True)
        for fp in target.rglob("*"):
            if fp.is_file():
                rel = fp.relative_to(target)
                dest_f = docs_p / rel
                dest_f.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(fp, dest_f)
        result["docs_dir"] = docs_p

    return result


if __name__ == "__main__":
    from legal_terms import build_legal_web_pages

    site_out = SUITE_DIR / "site_deploy_ready"
    res = build_legal_web_pages(site_out)
    docs_out = SUITE_DIR / "docs"
    build_storefront_bundle(site_out, sync_docs_dir=docs_out)
    print(f"[site_builder] Built bilingual storefront & legal pages -> {site_out} & {docs_out}")
