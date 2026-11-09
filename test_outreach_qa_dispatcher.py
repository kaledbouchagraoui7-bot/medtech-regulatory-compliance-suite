#!/usr/bin/env python3
"""Unit & integration tests for outreach_qa_dispatcher.py (120–150 words, real pricing, single-pass humanizer)."""

import csv
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
    count_words,
    evaluate_4_detectors,
    load_dotenv_files,
    process_dispatch_queue,
    run_qa_humanizer_loop,
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

    def test_single_pass_humanizer_strips_cliches_and_enforces_120_to_150_words_with_price(self) -> None:
        stiff_draft = (
            "Hello Treuhand Demo team,\n\n"
            "I hope this email finds you well. In today's digital landscape, while reading client reviews for "
            "Treuhand Demo on treuhand-demo.ch, clients consistently praise your responsive tax advisory work. "
            "I evaluated treuhand-demo.ch using my passive 25-control Sentinel evaluation system (scorecard and "
            "evaluation system PDF attached, with source code on GitHub at medtech-regulatory-compliance-suite), "
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
        self.assertGreaterEqual(qa["word_count"], 120)
        self.assertLessEqual(qa["word_count"], 150)
        self.assertIn("350 CHF", qa["final_body"])
        self.assertNotIn("for free", qa["final_body"].lower())

    def test_evidence_emails_en_de_fr_are_120_to_150_words_and_attach_both_scorecard_and_system_pdf(self) -> None:
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
            self.assertGreaterEqual(r["word_count"], 120)
            self.assertLessEqual(r["word_count"], 150)
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
        self.assertGreaterEqual(wc, 120)
        self.assertLessEqual(wc, 150)
        self.assertNotIn("for free", body.lower())
        self.assertIn("£", body)

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


if __name__ == "__main__":
    unittest.main()
