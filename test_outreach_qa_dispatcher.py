#!/usr/bin/env python3
"""Unit & integration tests for outreach_qa_dispatcher.py (85–125 words, deliverability shield, smoking-gun gates)."""

import csv
import datetime as dt
import json
import os
import shutil
import tempfile
import unittest
from email import policy
from email.parser import BytesParser
from pathlib import Path
from unittest.mock import MagicMock, patch

from outreach_qa_dispatcher import (
    build_evidence_email,
    classify_recipient_mailbox,
    count_recent_24h_sent_breakdown,
    count_words,
    evaluate_4_detectors,
    evaluate_smoking_gun_trigger,
    is_email_suppressed,
    is_target_icp_entity,
    is_valid_mx_exchange,
    load_dotenv_files,
    parse_mx_answer_record,
    process_dispatch_queue,
    receptionist_routing_line,
    run_qa_humanizer_loop,
    verify_email_and_domain_hygiene,
    verify_professionalism,
)


class TestOutreachQADispatcher(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = Path(tempfile.mkdtemp(prefix="qa_disp_test_"))
        self.sample_audit = {
            "domain": "treuhand-demo.ch",
            "overall_score": 47,
            "findings": [
                {"id": "EML-01", "title": "DMARC", "status": "FAIL", "evidence": "Missing _dmarc"},
                {"id": "PRV-01", "title": "Google Fonts", "status": "FAIL", "evidence": "fonts.googleapis.com"},
                {"id": "SEC-02", "title": "HSTS", "status": "FAIL", "evidence": "Missing HSTS"},
            ],
        }

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_heavy_ai_draft_or_for_free_offer_is_blocked(self) -> None:
        ai_spam = (
            "Dear Sir/Madam,\n\n"
            "I hope this email finds you well. In today's rapidly evolving digital landscape, "
            "ensuring comprehensive compliance is paramount. We are delighted to leverage our "
            "cutting-edge solution to seamlessly streamline your infrastructure for free. Furthermore, "
            "it is important to highlight that we offer guaranteed results. Please do not hesitate "
            "to schedule a brief 15-minute discovery call to revolutionize your workflow."
        )
        initial = evaluate_4_detectors(ai_spam)
        self.assertGreater(initial["average_ai_pct"], 25.0)

        qa = run_qa_humanizer_loop(
            subject="Compliance platform",
            body=ai_spam,
            to_email="info@treuhand-demo.ch",
            required_domain="treuhand-demo.ch",
            threshold_pct=15.0,
            max_passes=1,
        )
        self.assertFalse(qa["approved"])
        self.assertFalse(qa["professionalism_ok"])
        self.assertTrue(any("for free" in issue or "Below" in issue or "Missing explicit price" in issue for issue in qa["professionalism_issues"]))

    def test_single_pass_humanizer_strips_cliches_and_enforces_85_to_125_words_with_price(self) -> None:
        stiff_draft = (
            "Hello Treuhand Demo team,\n\n"
            "I hope this email finds you well. In today's digital landscape, while reviewing public compliance posture for "
            "Treuhand Demo on treuhand-demo.ch, I evaluated treuhand-demo.ch using my passive 25-control Sentinel evaluation "
            "system (scorecard and evaluation system PDF attached, with source code on GitHub at medtech-regulatory-compliance-suite), "
            "where your domain scored 47/100.\n\n"
            "Specifically, the scan flagged that no _dmarc.treuhand-demo.ch policy is published, remote Google Fonts "
            "transmit visitor IPs before consent, and HTTP HSTS/CSP headers are missing. Fixing these stops spoofed "
            "emails from impersonating your advisors and protects client tax portal submissions.\n\n"
            "For a flat fee of 350 CHF, we leverage our cutting-edge config snippets to streamline this and deliver "
            "the full Word/Excel audit plus ready-to-paste DNS and server headers.\n\n"
            "If this is not a priority right now, simply reply 'no' and I will not follow up.\n\n"
            "Best regards,\nKaled Bouchagraoui"
        )
        initial = evaluate_4_detectors(stiff_draft)
        self.assertGreater(initial["average_ai_pct"], 10.0)

        qa = run_qa_humanizer_loop(
            subject="Technical evaluation of treuhand-demo.ch (47/100)",
            body=stiff_draft,
            to_email="info@treuhand-demo.ch",
            required_domain="treuhand-demo.ch",
            threshold_pct=15.0,
            max_passes=1,
        )
        self.assertTrue(qa["approved"], f"Expected single-pass approval, got: {qa}")
        self.assertEqual(qa["passes_used"], 1)
        self.assertGreaterEqual(qa["word_count"], 85)
        self.assertLessEqual(qa["word_count"], 125)
        self.assertIn("350 CHF", qa["final_body"])
        self.assertNotIn("for free", qa["final_body"].lower())

    def test_evidence_emails_en_de_fr_are_85_to_125_words_and_attach_both_scorecard_and_system_pdf(self) -> None:
        ev_json = self.temp_dir / "treuhand_demo_ch_raw_evidence.json"
        ev_json.write_text(json.dumps(self.sample_audit), encoding="utf-8")
        fake_png = self.temp_dir / "scorecard.png"
        fake_png.write_bytes(b"\x89PNG\r\n\x1a\nfakepng")

        manifest = self.temp_dir / "manifest.csv"
        with open(manifest, "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(["domain", "company_name", "to_email", "lang", "country", "sector", "price", "evidence_json_path", "attachment_path"])
            w.writerow(["treuhand-demo.ch", "Treuhand Demo AG", "info@treuhand-demo.ch", "de", "CH", "cpa_fiduciary", "350 CHF", str(ev_json), str(fake_png)])
            w.writerow(["treuhand-demo.ch", "Fiduciaire Demo SA", "contact@treuhand-demo.ch", "fr", "CH", "cpa_fiduciary", "350 CHF", str(ev_json), str(fake_png)])
            w.writerow(["treuhand-demo.ch", "MedTech Demo Ltd", "team@treuhand-demo.ch", "en", "UK", "medtech_cer", "£380", str(ev_json), str(fake_png)])

        out_dir = self.temp_dir / "queue"
        res = process_dispatch_queue(manifest, out_dir, dispatch_mode="draft", threshold_pct=15.0)
        self.assertEqual(res["approved_count"], 3, f"Expected 3 approved, got: {res['results']}")
        self.assertEqual(res["blocked_count"], 0)
        for r in res["results"]:
            self.assertGreaterEqual(r["word_count"], 85)
            self.assertLessEqual(r["word_count"], 125)
            self.assertEqual(r["passes_used"], 1)

        eml_files = list(res["drafts_dir"].glob("*.eml"))
        self.assertEqual(len(eml_files), 3)
        parsed = BytesParser(policy=policy.default).parsebytes(eml_files[0].read_bytes())
        self.assertEqual(parsed["X-Unsent"], "1")
        attachments = list(parsed.iter_attachments())
        filenames = [a.get_filename() for a in attachments]
        self.assertIn("scorecard.png", filenames)
        self.assertIn("Sentinel_25_Control_Evaluation_System.pdf", filenames)

    def test_en_email_has_no_for_free_and_respects_word_count(self) -> None:
        two_gap_audit = {
            "domain": "two-gaps.co.uk",
            "overall_score": 57,
            "findings": [
                {"id": "EML-01", "title": "DMARC", "status": "FAIL", "evidence": "Missing _dmarc"},
                {"id": "SEC-02", "title": "HSTS", "status": "FAIL", "evidence": "Missing HSTS"},
            ],
        }
        _subj, body = build_evidence_email(two_gap_audit, "Two Gaps Ltd", "info@two-gaps.co.uk", lang="en", country="UK")
        wc = count_words(body)
        self.assertGreaterEqual(wc, 85)
        self.assertLessEqual(wc, 125)
        self.assertNotIn("for free", body.lower())
        self.assertNotIn("github.com", body.lower())
        self.assertNotIn("kaledbouchagraoui7-bot", body.lower())
        self.assertIn("£", body)
        self.assertIn("forward this brief", body.lower())

    def test_load_dotenv_files_reads_custom_env_without_overwriting(self) -> None:
        env_file = self.temp_dir / ".env"
        env_file.write_text('SMTP_USER="user@example.ch"\n# comment\nEXISTING_KEY=from_file\n', encoding="utf-8")
        with patch.dict("os.environ", {"EXISTING_KEY": "already_set"}, clear=True):
            load_dotenv_files([env_file], include_defaults=False)
            self.assertEqual(os.environ.get("SMTP_USER"), "user@example.ch")
            self.assertEqual(os.environ.get("EXISTING_KEY"), "already_set")

    def test_smtp_refuses_without_confirm_and_sends_with_mock(self) -> None:
        ev_json = self.temp_dir / "ev.json"
        ev_json.write_text(json.dumps(self.sample_audit), encoding="utf-8")
        manifest = self.temp_dir / "manifest.csv"
        with open(manifest, "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(["domain", "company_name", "to_email", "lang", "country", "sector", "price", "evidence_json_path", "attachment_path"])
            w.writerow(["treuhand-demo.ch", "Treuhand Demo", "info@treuhand-demo.ch", "en", "US", "cpa_fiduciary", "$380", str(ev_json), ""])

        with self.assertRaises(RuntimeError):
            process_dispatch_queue(manifest, self.temp_dir / "q1", dispatch_mode="smtp", confirm_send=False)

        with patch.dict("os.environ", {"SMTP_USER": "sender@example.ch", "SMTP_PASSWORD": "secret"}), \
             patch("outreach_qa_dispatcher.smtplib.SMTP") as mock_smtp:
            mock_srv = MagicMock()
            mock_smtp.return_value.__enter__.return_value = mock_srv
            res = process_dispatch_queue(
                manifest,
                self.temp_dir / "q2",
                dispatch_mode="smtp",
                provider="outlook",
                confirm_send=True,
            )
            self.assertEqual(res["sent_via_smtp"], 1)
            mock_srv.send_message.assert_called_once()

    def test_suppression_csv_blocks_optout_and_respects_email_scope_and_expired_holds(self) -> None:
        ev_json = self.temp_dir / "ev.json"
        ev_json.write_text(json.dumps(self.sample_audit), encoding="utf-8")
        ev_mhlab = self.temp_dir / "ev_mhlab.json"
        ev_mhlab.write_text(json.dumps({**self.sample_audit, "domain": "mhlab.ca"}), encoding="utf-8")
        fake_png = self.temp_dir / "scorecard.png"
        fake_png.write_bytes(b"\x89PNG\r\n\x1a\nfakepng")

        sup_csv = self.temp_dir / "optout_suppression.csv"
        with open(sup_csv, "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(["timestamp_utc", "domain", "email", "reason", "source_message_id", "scope", "hold_until_utc"])
            # Domain-level permanent opt-out
            w.writerow(["2026-11-10T06:24:35Z", "optout-dom.de", "no@optout-dom.de", "OPT_OUT: Nein danke", "m1", "domain", ""])
            # Email-level bounce only (should NOT block alternate address on same domain)
            w.writerow(["2026-11-10T14:39:33Z", "mhlab.ca", "info@mhlab.ca", "AUTO_NO_REPLY_ALT_AVAILABLE", "m2", "email", ""])
            # Active future hold
            w.writerow(["2026-11-10T14:32:59Z", "pureclinic.ch", "info@pureclinic.ch", "HOLD_AUTO_ACK_7D", "m3", "domain", "2099-01-01T00:00:00Z"])
            # Expired hold (must be lifted automatically)
            w.writerow(["2026-11-01T10:00:00Z", "treuhand-demo.ch", "info@treuhand-demo.ch", "HOLD_OOO_EXPIRED", "m4", "domain", "2020-01-01T00:00:00Z"])

        manifest = self.temp_dir / "manifest.csv"
        with open(manifest, "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(["domain", "company_name", "to_email", "lang", "country", "sector", "price", "evidence_json_path", "attachment_path"])
            w.writerow(["optout-dom.de", "OptOut GmbH", "other@optout-dom.de", "en", "DE", "cpa_fiduciary", "EUR 350", str(ev_json), str(fake_png)])
            w.writerow(["mhlab.ca", "Med-Health Labs", "info@mhlab.ca", "en", "CA", "diagnostics_lab", "CAD 460", str(ev_mhlab), str(fake_png)])
            w.writerow(["mhlab.ca", "Med-Health Labs", "support@mhlab.ca", "en", "CA", "diagnostics_lab", "CAD 460", str(ev_mhlab), str(fake_png)])
            w.writerow(["pureclinic.ch", "Pure Clinic", "info@pureclinic.ch", "de", "CH", "clinic", "350 CHF", str(ev_json), str(fake_png)])
            w.writerow(["treuhand-demo.ch", "Treuhand Demo", "info@treuhand-demo.ch", "en", "CH", "cpa_fiduciary", "350 CHF", str(ev_json), str(fake_png)])

        res = process_dispatch_queue(manifest, self.temp_dir / "q_sup", dispatch_mode="draft", suppression_csv=sup_csv)
        statuses = {(r["domain"], r["to_email"]): r["status"] for r in res["results"]}
        self.assertEqual(statuses[("optout-dom.de", "other@optout-dom.de")], "BLOCKED_SUPPRESSED")
        self.assertEqual(statuses[("mhlab.ca", "info@mhlab.ca")], "BLOCKED_SUPPRESSED")
        self.assertEqual(statuses[("mhlab.ca", "support@mhlab.ca")], "APPROVED")
        self.assertEqual(statuses[("pureclinic.ch", "info@pureclinic.ch")], "BLOCKED_SUPPRESSED")
        self.assertEqual(statuses[("treuhand-demo.ch", "info@treuhand-demo.ch")], "APPROVED")
        self.assertEqual(res["approved_count"], 2)

    def test_icp_filter_blocks_consumer_clinics_and_big4_and_allows_b2b_icps(self) -> None:
        blocked_cases = [
            ("OT&P Healthcare HK", "otandp.com", "Healthcare"),
            ("Goji Women's and Family Physiotherapy", "gojiphysio.com", "Healthcare"),
            ("Andrew Choong Vascular Surgery", "drandrewchoong.com", "Healthcare"),
            ("Digestive Centre", "digestivecentre.com.sg", "Healthcare"),
            ("Sankar's Health Care Scans & Diagnostics", "shcd.in", "Diagnostics"),
            ("Arockiya Speciality Clinic & Diagnostic", "arockiyaclinic.com", "Healthcare"),
            ("Santé Labs", "santelabs.com", "Diagnostics"),
            ("Fukiage Maternity Clinic", "fukiage-mclinic.jp", "Healthcare"),
            ("Highmark Dental LLC", "highmarkcares.com", "Healthcare"),
            ("Christic Institute", "romeroinstitute.org", "Legal/IP"),
            ("Grant Thornton Taiyo LLC", "gtjapan.or.jp", "Accounting/Tax"),
            ("Fiducial Expertise", "fiducial.fr", "Accounting/Tax"),
        ]
        for comp, dom, sec in blocked_cases:
            ok, reason = is_target_icp_entity(comp, dom, sec)
            self.assertFalse(ok, f"Expected off-ICP block for {comp} ({dom}), got OK")
            self.assertTrue(reason)

        allowed_cases = [
            ("Cabinet Berenfus", "berenfus-sante.fr", "Accounting/Tax"),
            ("Stanley Advisors", "stanley.com", "Wealth & Family Office"),
            ("Ultraceuticals", "ultraceuticals.in", "MedTech RA"),
            ("Castor EDC", "castoredc.com", "HealthTech"),
            ("Stanhope Capital", "stanhopecapital.com", "Wealth & Family Office"),
            ("Spendesk SaaS", "spendesk.com", "B2B SaaS"),
            ("Laboratoire SVR", "labo-svr.com", "Dermo-Cosmetics"),
            ("Laboratoire Nutergia", "nutergia.com", "Nutraceuticals"),
            ("ECO Animal Health", "ecoanimalhealth.com", "Veterinary Pharma"),
            ("Naobios Biomanufacturing", "naobios.com", "CDMO / Pharma"),
            ("Greenlight Guru", "greenlight.guru", "MedTech RA"),
            ("Banner & Witcoff", "bannerwitcoff.com", "Legal/IP"),
        ]
        for comp, dom, sec in allowed_cases:
            ok, reason = is_target_icp_entity(comp, dom, sec)
            self.assertTrue(ok, f"Expected ICP pass for {comp} ({dom}, {sec}), blocked: {reason}")

    def test_verify_professionalism_rejects_raw_code_repo_and_snippets(self) -> None:
        base_body = (
            "Hi Team,\n\n"
            "While benchmarking vendor risk for example.com, I prepared a 1-page review showing "
            "16 of 25 controls passed alongside the attached scorecard preview and methodology PDF.\n\n"
            "Two public items need review: DMARC enforcement and HTTP HSTS headers. Fixing these protects "
            "partner communication and avoids client vendor-audit delays.\n\n"
            "If helpful, I can deliver the full Word executive audit, 4-sheet Excel risk log, "
            "PLACEHOLDER, and re-verified attestation PDF within 48 hours for EUR 350 flat.\n\n"
            "If not relevant right now, simply reply 'no' and I won't follow up.\n\n"
            "Best regards,\nKaled Bouchagraoui"
        )
        for bad_phrase in [
            "github.com/kaled/repo",
            "remediation snippets",
            "config snippets",
            "screening scripts",
            "python scripts",
            "source code",
        ]:
            ok, issues = verify_professionalism(
                subject="Example (example.com) - 1-page risk preview",
                body=base_body.replace("PLACEHOLDER", bad_phrase),
                to_email="info@example.com",
                required_domain="example.com",
                min_words=80,
                max_words=160,
            )
            self.assertFalse(ok, f"Expected verify_professionalism to reject '{bad_phrase}'")
            self.assertTrue(any("Banned phrase" in x for x in issues))

    def test_deliverability_shield_hygiene_mx_and_classification(self) -> None:
        self.assertEqual(classify_recipient_mailbox("info@medtech.fr"), "receptionist_generic")
        self.assertEqual(classify_recipient_mailbox("contact@medtech.fr"), "receptionist_generic")
        self.assertEqual(classify_recipient_mailbox("regulatory@medtech.fr"), "functional_owner")
        self.assertEqual(classify_recipient_mailbox("j.dupont@medtech.fr"), "named_direct")

        self.assertIn("transmettre", receptionist_routing_line("info@medtech.fr", "MedTech SAS", lang="fr", sector="MedTech OEM"))
        self.assertIn("forward", receptionist_routing_line("contact@medtech.fr", "MedTech Ltd", lang="en", sector="MedTech RA"))
        self.assertEqual(receptionist_routing_line("regulatory@medtech.fr", "MedTech SAS", lang="fr"), "")

        self.assertEqual(parse_mx_answer_record("0 ."), (0, "."))
        self.assertEqual(parse_mx_answer_record("10 aspmx.l.google.com."), (10, "aspmx.l.google.com"))
        self.assertFalse(is_valid_mx_exchange(".", priority=0)[0])
        self.assertFalse(is_valid_mx_exchange("mail.sedoparking.com", priority=10)[0])
        self.assertTrue(is_valid_mx_exchange("aspmx.l.google.com", priority=10)[0])

        # Free webmail, disposable, off-domain checks
        self.assertFalse(verify_email_and_domain_hygiene("yourglobalrep@gmail.com", "biotech.com", check_mx=False)[0])
        self.assertTrue(verify_email_and_domain_hygiene("founder@gmail.com", "gmail.com", check_mx=False, allow_verified_webmail=True)[0])
        self.assertFalse(verify_email_and_domain_hygiene("qa@mailinator.com", "mailinator.com", check_mx=False)[0])
        self.assertFalse(verify_email_and_domain_hygiene("contact@unrelatedagency.io", "medtech.fr", check_mx=False)[0])
        self.assertTrue(verify_email_and_domain_hygiene("info@medtech-group.fr", "medtech.fr", check_mx=False)[0])

        # DoH Null MX rejection vs valid MX acceptance
        null_mx_resp = MagicMock(status_code=200)
        null_mx_resp.json.return_value = {"Status": 0, "Answer": [{"type": 15, "data": "0 ."}]}
        with patch("outreach_qa_dispatcher.requests.get", return_value=null_mx_resp):
            ok_null, reason_null, _ = verify_email_and_domain_hygiene("qa@nullmx.fr", "nullmx.fr", check_mx=True)
        self.assertFalse(ok_null)
        self.assertEqual(reason_null, "NULL_MX_REJECTED")

        good_mx_resp = MagicMock(status_code=200)
        good_mx_resp.json.return_value = {"Status": 0, "Answer": [{"type": 15, "data": "10 mx.medtech.fr."}]}
        with patch("outreach_qa_dispatcher.requests.get", return_value=good_mx_resp):
            ok_good, reason_good, meta_good = verify_email_and_domain_hygiene("qa@medtech.fr", "medtech.fr", check_mx=True)
        self.assertTrue(ok_good, reason_good)
        self.assertIn("10 mx.medtech.fr", meta_good["mx_hosts"])

        self.assertEqual(is_email_suppressed("no@bad.fr", "bad.fr", {"bad.fr": "OPTOUT"}, {}), (True, "OPTOUT"))
        self.assertEqual(is_email_suppressed("alt@bad.fr", "bad.fr", {}, {"only@bad.fr": "BOUNCE"}), (False, ""))

        # Primary vs follow-up 24h breakdown counter
        now_ts = dt.datetime(2026, 11, 12, 10, 0, tzinfo=dt.timezone.utc)
        ledger = self.temp_dir / "sent_ledger.csv"
        master = self.temp_dir / "outreach_master_status.csv"
        ledger.write_text(
            "timestamp_utc,to_email,domain,country,sector,price,word_count,avg_ai_pct,gmail_message_id\n"
            "2026-11-12T08:00:00+00:00,qa@a.fr,a.fr,FR,MedTech OEM,EUR 350,100,0.0,m1\n"
            "2026-11-12T09:00:00+00:00,qa@b.fr,b.fr,FR,MedTech OEM,EUR 350,100,0.0,m2\n"
            "2026-11-10T09:00:00+00:00,old@c.fr,c.fr,FR,MedTech OEM,EUR 350,100,0.0,m0\n",
            encoding="utf-8",
        )
        master.write_text(
            "Wave,Timestamp_UTC,Domain,Company,Country,Sector,Language,To_Email,Price,Word_Count,Avg_AI_Pct,Gmail_ID,Status\n"
            "Wave_6,2026-11-12T08:00:00+00:00,a.fr,A SAS,FR,MedTech OEM,fr,qa@a.fr,EUR 350,100,0.0,m1,DELIVERED_AWAITING_REPLY\n"
            "FollowUp_1,2026-11-12T09:00:00+00:00,b.fr,B SAS,FR,MedTech OEM,fr,qa@b.fr,EUR 350,100,0.0,m2,DELIVERED_AWAITING_REPLY\n",
            encoding="utf-8",
        )
        brk = count_recent_24h_sent_breakdown(ledger, master_csv=master, now_utc=now_ts)
        self.assertEqual(brk, {"total": 2, "primary": 1, "followup": 1})

    def test_smoking_gun_trigger_gates_all_tracks(self) -> None:
        # Track 1: mild score (>75) and headers-only rejected; SPF PermError or DMARC+CAA accepted
        mild_audit = {"overall_score": 82, "fail_count": 0, "warn_count": 1, "pass_count": 24, "findings": []}
        self.assertFalse(evaluate_smoking_gun_trigger("sentinel_compliance", mild_audit, sector="MedTech OEM")[0])

        headers_only = {
            "overall_score": 70, "fail_count": 1, "warn_count": 1, "pass_count": 20,
            "spf_diagnostics": {"total_lookups": 3, "exceeds_limit": False},
            "cmp_diagnostics": {"has_reject_copy_in_html": True},
            "findings": [
                {"id": "EML-01", "status": "PASS", "evidence": "v=DMARC1; p=reject;"},
                {"id": "EML-02", "status": "PASS", "evidence": "3/10 DNS lookups"},
                {"id": "EML-04", "status": "PASS", "evidence": "CAA present"},
                {"id": "PRV-01", "status": "PASS", "evidence": "Local fonts"},
                {"id": "SEC-09", "status": "PASS", "evidence": "security.txt present"},
                {"id": "SEC-03", "status": "FAIL", "evidence": "Missing CSP"},
            ],
        }
        self.assertFalse(evaluate_smoking_gun_trigger("sentinel_compliance", headers_only, sector="MedTech OEM")[0])

        spf_broken = {
            "overall_score": 68, "fail_count": 2, "warn_count": 1, "pass_count": 18,
            "spf_diagnostics": {"total_lookups": 12, "exceeds_limit": True},
            "findings": [{"id": "EML-02", "status": "FAIL", "title": "SPF exceeding 10", "evidence": "12/10 DNS lookups"}],
        }
        ok_t1, reason_t1, _ = evaluate_smoking_gun_trigger("sentinel_compliance", spf_broken, sector="MedTech OEM")
        self.assertTrue(ok_t1)
        self.assertEqual(reason_t1, "SPF_PERMERROR_OR_BROKEN")

        # Track 2: PMS MAUDE concrete problem vs low generic signal
        weak_pms = {
            "maude_summary": {"total_events_analyzed": 5, "event_type_counts": {"Malfunction": 5}, "top_device_problems": [{"problem": "Unknown"}]},
            "recalls_and_510k": [], "clinical_trials": [],
        }
        self.assertFalse(evaluate_smoking_gun_trigger("pms_openfda_psur", weak_pms)[0])
        strong_pms = {
            "maude_summary": {"total_events_analyzed": 85, "event_type_counts": {"Malfunction": 70, "Injury": 15}, "top_device_problems": [{"problem": "Battery Depletion"}]},
            "recalls_and_510k": [{"record_type": "510(k)"}], "clinical_trials": [{"nct_id": "NCT1"}],
        }
        ok_t2, reason_t2, _ = evaluate_smoking_gun_trigger("pms_openfda_psur", strong_pms)
        self.assertTrue(ok_t2)
        self.assertIn("MAUDE_85_EVENTS", reason_t2)

        # Track 3: PRISMA workflow hours trigger
        weak_lit = {"prisma_verified": {"total_identified": 6, "duplicates_removed": 0, "excluded_at_screening": 0, "excluded_at_full_text": 0, "studies_included": 6}}
        self.assertFalse(evaluate_smoking_gun_trigger("clinical_lit_prisma", weak_lit)[0])
        strong_lit = {"prisma_verified": {"total_identified": 24, "duplicates_removed": 3, "excluded_at_screening": 7, "excluded_at_full_text": 2, "studies_included": 12}}
        ok_t3, reason_t3, meta_t3 = evaluate_smoking_gun_trigger("clinical_lit_prisma", strong_lit)
        self.assertTrue(ok_t3)
        self.assertIn("PRISMA_24TO12_SAVES_", reason_t3)
        self.assertGreater(meta_t3["est_hours_saved"], 5.0)


if __name__ == "__main__":
    unittest.main()
