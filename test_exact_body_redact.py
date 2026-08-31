#!/usr/bin/env python3
"""Canaries for exact-body source preservation and attachment URL redaction.

Leftover: exact-body-republish-private-paths-attachments
PICK: preserve ordinary local paths; redact raw attachment URLs. Not a gate.
"""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

import exact_body_redact as ebr
import slack_ingest as si


MARKER = ebr.LOCAL_PATH_REDACTED
WIN = r"C:\Users\lucys.codex\config.toml"
HOME = "/home/canary/.ssh/id_ed25519"
MAC = "/Users/canary/Desktop/notes.md"
SLACK_FILE = "https://files.slack.com/files-pri/T1-F1/download/shot.png"
NTFY_FILE = "https://ntfy.sh/file/AbCdEf123456.txt"
CLEAN = "PLAIN: Slack ↔ Commons exact body.\nNo private spans here.\n"


class RedactHelperTests(unittest.TestCase):
    def test_windows_user_path_stays_exact(self) -> None:
        body = "see %s then continue" % WIN
        self.assertEqual(ebr.redact_private_spans(body), body)

    def test_unix_home_path_stays_exact(self) -> None:
        body = "key at %s end" % HOME
        self.assertEqual(ebr.redact_private_spans(body), body)

    def test_macos_users_path_stays_exact(self) -> None:
        body = "pic %s done" % MAC
        self.assertEqual(ebr.redact_private_spans(body), body)

    def test_attachment_urls_do_not_republish_raw(self) -> None:
        body = "slack %s and ntfy %s done" % (SLACK_FILE, NTFY_FILE)
        out = ebr.redact_private_spans(body)
        self.assertNotIn(SLACK_FILE, out)
        self.assertNotIn(NTFY_FILE, out)
        self.assertNotIn("files.slack.com", out)
        self.assertNotIn("ntfy.sh/file/", out)
        self.assertEqual(out, "slack %s and ntfy %s done" % (MARKER, MARKER))

    def test_clean_body_stays_byte_identical(self) -> None:
        self.assertEqual(ebr.redact_private_spans(CLEAN), CLEAN)
        self.assertIs(ebr.redact_private_spans(""), "")

    def test_public_and_repo_paths_stay(self) -> None:
        body = (
            "run /usr/bin/python ground/HEAD.md "
            "https://github.com/woahwhattheheck/commons "
            "https://ntfy.sh/woahwhattheheck-commons-board"
        )
        self.assertEqual(ebr.redact_private_spans(body), body)

    def test_same_after_redact_only_equates_attachment_urls(self) -> None:
        attachment = "PLAIN: file %s\n" % SLACK_FILE
        redacted = "PLAIN: file %s\n" % MARKER
        local_path = "PLAIN: file %s\n" % WIN
        self.assertTrue(ebr.same_after_redact(attachment, redacted))
        self.assertFalse(ebr.same_after_redact(local_path, redacted))
        self.assertFalse(ebr.same_after_redact(local_path, "PLAIN: other\n"))


class SlackRepublishTests(unittest.TestCase):
    def test_home_path_republish_stays_exact(self) -> None:
        text = "from: GPT\nto: TABLE\n\nPLAIN: keep me. path %s done." % HOME
        record = si.issue_record({"ts": "1788085000.1", "text": text, "user": "U1"})
        self.assertEqual(si._record_body(record.body), text)

    def test_windows_path_republish_stays_exact(self) -> None:
        text = "from: GPT\nto: TABLE\n\nPLAIN: keep me. path %s done." % WIN
        record = si.issue_record({"ts": "1788085000.2", "text": text, "user": "U1"})
        self.assertEqual(si._record_body(record.body), text)

    def test_attachment_url_republish_does_not_emit_raw(self) -> None:
        text = "from: GPT\nto: TABLE\n\nPLAIN: keep me. file %s done." % SLACK_FILE
        record = si.issue_record({"ts": "1788085000.3", "text": text, "user": "U1"})
        payload = si._record_body(record.body)
        self.assertIn("PLAIN: keep me. file %s done." % MARKER, payload)
        self.assertNotIn(SLACK_FILE, record.body)
        self.assertNotIn("files.slack.com", record.body)

    def test_clean_exact_body_stays_byte_identical(self) -> None:
        text = "from: GPT\nto: TABLE\n\n" + CLEAN
        record = si.issue_record({"ts": "1788085000.4", "text": text, "user": "U1"})
        self.assertEqual(si._record_body(record.body), text)

    def test_verify_existing_accepts_redaction_equivalent_without_overwrite(self) -> None:
        leaked = "from: GPT\nto: TABLE\n\nPLAIN: %s\n" % WIN
        record = si.issue_record({"ts": "1788085000.5", "text": leaked, "user": "U1"})
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / (record.title + ".md")
            path.write_text(
                "---\nid: %s\n---\n%s" % (record.title, leaked),
                encoding="utf-8",
            )
            self.assertTrue(si.verify_existing(path, record))
            self.assertIn(WIN, path.read_text(encoding="utf-8"))


class IngestWriteTests(unittest.TestCase):
    def setUp(self) -> None:
        import board_ingest

        self.ingest = board_ingest
        self.tmp = tempfile.mkdtemp(prefix="exact-body-redact-")
        self.saved = (board_ingest.ROOT, board_ingest.POSTS)
        board_ingest.ROOT = self.tmp
        board_ingest.POSTS = os.path.join(self.tmp, "p")
        os.makedirs(board_ingest.POSTS, exist_ok=True)

    def tearDown(self) -> None:
        self.ingest.ROOT, self.ingest.POSTS = self.saved

    def test_write_post_preserves_home_and_redacts_attachment(self) -> None:
        body = "PLAIN: keep me. %s and %s done." % (HOME, NTFY_FILE)
        st = self.ingest.write_post(
            "SETH", "TABLE", "exact-body-redact-canary-20260830-01", body
        )
        self.assertEqual(st, "wrote")
        path = os.path.join(self.ingest.POSTS, "exact-body-redact-canary-20260830-01.md")
        with open(path, encoding="utf-8") as f:
            text = f.read()
        self.assertIn("PLAIN: keep me. %s and %s done." % (HOME, MARKER), text)
        self.assertIn(HOME, text)
        self.assertNotIn(NTFY_FILE, text)
        self.assertNotIn("ntfy.sh/file/", text)

    def test_write_post_clean_body_stays_exact(self) -> None:
        st = self.ingest.write_post(
            "SETH", "TABLE", "exact-body-redact-clean-20260830-01", CLEAN
        )
        self.assertEqual(st, "wrote")
        path = os.path.join(self.ingest.POSTS, "exact-body-redact-clean-20260830-01.md")
        with open(path, encoding="utf-8") as f:
            raw = f.read()
        self.assertIn(CLEAN, raw)

    def test_replay_of_leaked_existing_is_exists_not_conflict(self) -> None:
        mid = "exact-body-redact-replay-20260830-01"
        leaked = "PLAIN: leftover %s\n" % WIN
        md_path = os.path.join(self.ingest.POSTS, mid + ".md")
        os.makedirs(self.ingest.POSTS, exist_ok=True)
        with open(md_path, "w", encoding="utf-8", newline="\n") as f:
            f.write(
                "---\nfrom: SETH\nto: TABLE\nid: %s\nts: 2026-08-30T10:00:00Z\n"
                "state: DURABLE_PAGE\n---\n%s" % (mid, leaked)
            )
        st = self.ingest.write_post("SETH", "TABLE", mid, leaked)
        self.assertEqual(st, "exists")
        with open(md_path, encoding="utf-8") as f:
            self.assertIn(WIN, f.read())
        self.assertFalse(os.path.isfile(os.path.join(self.tmp, "conflicts", mid + ".jsonl")))


if __name__ == "__main__":
    unittest.main()
