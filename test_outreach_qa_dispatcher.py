#!/usr/bin/env python3
"""Unit & integration tests for outreach_qa_dispatcher.py."""

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

    def test_heavy_ai_draft_is_flagged_high_and_blocked_when_spammy(self) -> None:
        ai_spam = (
            "Dear Sir/Madam,\n\n"
            "I hope this email finds you well. In today's rapidly evolving digital landscape, "
            "ensuring comprehensive compliance is paramount. We are delighted to leverage our "
            "cutting-edge solution to seamlessly streamline your infrastructure. Furthermore, "
            "it is important to highlight that we offer guaranteed results. Please do not hesitate "
            "to schedule a brief 15-minute discovery call to revolutionize your workflow."
        )
        initial = evaluate_4_detectors(ai_spam)
        self.assertGreater(initial["average_ai_pct"], 25.0)

        # Even after rewriting, "guaranteed" + missing domain/opt-out causes Professionalism Gate to block send
        qa = run_qa_humanizer_loop(
            subject="Compliance platform",
            body=ai_spam,
            to_email="info@treuhand-demo.ch",
            required_domain="treuhand-demo.ch",
            threshold_pct=10.0,
            max_passes=3,
        )
        self.assertFalse(qa["approved"])
        self.assertFalse(qa["professionalism_ok"])

    def test_humanizer_reduces_rewritable_ai_draft_below_threshold(self) -> None:
        stiff_draft = (
            "Hello Treuhand Demo team,\n\n"
            "I hope this email finds you well. In today's digital landscape, I am writing to share "
            "a comprehensive security note for treuhand-demo.ch. We noticed your domain lacks DMARC.\n\n"
            "1. Missing DMARC policy lets spoofers fake your address.\n"
            "2. Remote Google Fonts transmit visitor IPs.\n\n"
            "We can leverage our cutting-edge config snippets to streamline this cleanly for your IT.\n"
            "If not relevant right now, just reply 'no' and I will not follow up.\n\n"
            "Best regards,\nKaled"
        )
        initial = evaluate_4_detectors(stiff_draft)
        self.assertGreater(initial["average_ai_pct"], 10.0)

        qa = run_qa_humanizer_loop(
            subject="Quick note on treuhand-demo.ch",
            body=stiff_draft,
            to_email="info@treuhand-demo.ch",
            required_domain="treuhand-demo.ch",
            threshold_pct=10.0,
            max_passes=5,
        )
        self.assertTrue(qa["approved"], f"Expected approval after humanizing, got: {qa}")
        self.assertLess(qa["final_average_ai_pct"], 10.0)
        self.assertGreaterEqual(qa["passes_used"], 2)

    def test_evidence_emails_en_de_fr_pass_under_10_pct_and_build_eml_with_attachment(self) -> None:
        ev_json = self.temp_dir / "treuhand_demo_ch_raw_evidence.json"
        ev_json.write_text(json.dumps(self.sample_audit), encoding="utf-8")
        fake_png = self.temp_dir / "scorecard.png"
        fake_png.write_bytes(b"\x89PNG\r\n\x1a\nfakepng")

        manifest = self.temp_dir / "manifest.csv"
        with open(manifest, "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(["domain", "company_name", "to_email", "lang", "evidence_json_path", "attachment_path"])
            w.writerow(["treuhand-demo.ch", "Treuhand Demo AG", "info@treuhand-demo.ch", "de", str(ev_json), str(fake_png)])
            w.writerow(["treuhand-demo.ch", "Fiduciaire Demo SA", "contact@treuhand-demo.ch", "fr", str(ev_json), str(fake_png)])
            w.writerow(["treuhand-demo.ch", "MedTech Demo Ltd", "team@treuhand-demo.ch", "en", str(ev_json), str(fake_png)])

        out_dir = self.temp_dir / "queue"
        res = process_dispatch_queue(manifest, out_dir, dispatch_mode="draft", threshold_pct=10.0)
        self.assertEqual(res["approved_count"], 3)
        self.assertEqual(res["blocked_count"], 0)
        self.assertTrue(res["qa_report_csv"].exists())

        eml_files = list(res["drafts_dir"].glob("*.eml"))
        self.assertEqual(len(eml_files), 3)
        parsed = BytesParser(policy=policy.default).parsebytes(eml_files[0].read_bytes())
        self.assertEqual(parsed["X-Unsent"], "1")
        attachments = list(parsed.iter_attachments())
        self.assertEqual(len(attachments), 1)
        self.assertEqual(attachments[0].get_filename(), "scorecard.png")

    def test_en_email_bullet_count_matches_actual_findings(self) -> None:
        two_gap_audit = {
            "domain": "two-gaps.ch",
            "overall_score": 57,
            "findings": [
                {"id": "EML-01", "title": "DMARC", "status": "FAIL", "evidence": "Missing _dmarc"},
                {"id": "SEC-02", "title": "HSTS", "status": "FAIL", "evidence": "Missing HSTS"},
            ],
        }
        _subj, body = build_evidence_email(two_gap_audit, "Two Gaps GmbH", "info@two-gaps.ch", lang="en")
        self.assertNotIn("three quick fixes", body.lower())
        self.assertNotIn("`", body)

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
            w.writerow(["domain", "company_name", "to_email", "lang", "evidence_json_path", "attachment_path"])
            w.writerow(["treuhand-demo.ch", "Treuhand Demo", "info@treuhand-demo.ch", "en", str(ev_json), ""])

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
