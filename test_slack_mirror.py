#!/usr/bin/env python3
"""Unit tests for host/slack_mirror.py. No Slack or ntfy network."""
from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "host"))

import slack_mirror as sm  # noqa: E402


class ClaimTests(unittest.TestCase):
    def test_bryce_user_id(self):
        self.assertEqual(sm.claim_of({"user": sm.BRYCE_UID}), "BRYCE")

    def test_header_from_wins(self):
        self.assertEqual(
            sm.claim_of({"user": sm.BRYCE_UID, "text": "from: GLINT\n---\nhi"}),
            "GLINT",
        )

    def test_steal_guard(self):
        self.assertEqual(
            sm.claim_of({"user": "U999", "text": "from: PLAYER2\n---\nhi"}),
            "UNSEATED",
        )

    def test_empty_is_unseated(self):
        self.assertEqual(sm.claim_of({}), "UNSEATED")

    def test_footer_claude_not_bryce(self):
        self.assertEqual(
            sm.claim_of(
                {
                    "user": sm.BRYCE_UID,
                    "text": "boards.html stale\n*Sent using* Claude",
                }
            ),
            "CLAUDE",
        )

    def test_footer_gemini(self):
        self.assertEqual(sm.footer_claim("hi\nSent using Gemini"), "GEMINI")

    def test_footer_chatgpt_mention(self):
        self.assertEqual(
            sm.footer_claim("review\nSent using <@U0BSAL3CZ4Y|ChatGPT>"),
            "CHATGPT",
        )

    def test_footer_cursor_unmapped(self):
        self.assertEqual(sm.footer_claim("hello\n_Sent using Cursor_"), "")
        self.assertEqual(
            sm.claim_of({"user": sm.BRYCE_UID, "text": "hello\n_Sent using Cursor_"}),
            "BRYCE",
        )

    def test_header_beats_footer(self):
        self.assertEqual(
            sm.claim_of(
                {
                    "user": sm.BRYCE_UID,
                    "text": "from: GLINT\n---\nhi\n*Sent using* Claude",
                }
            ),
            "GLINT",
        )


class SkipTests(unittest.TestCase):
    def test_keep_cursor_echo(self):
        self.assertFalse(sm.skip_slack({"text": "hello\n_Sent using Cursor_"}))

    def test_keep_claude_footer(self):
        self.assertFalse(sm.skip_slack({"text": "boards.html stale\n*Sent using* Claude"}))

    def test_keep_gemini_footer(self):
        self.assertFalse(sm.skip_slack({"text": "hi\nSent using Gemini"}))

    def test_skip_mirror_watermark(self):
        self.assertTrue(sm.skip_slack({"text": "board → slack\nSLACK_MIRROR"}))

    def test_keep_human(self):
        self.assertFalse(sm.skip_slack({"text": "claude and gemini?"}))


class IdTests(unittest.TestCase):
    def test_board_block_keeps_id(self):
        text = "from: BRYCE\nto: TABLE\nkind: note\nid: bryce-test-id-01\n---\nbody"
        row = sm.payload_from_slack({"ts": "1.2", "text": text})
        self.assertEqual(row["id"], "bryce-test-id-01")
        self.assertEqual(row["from"], "BRYCE")

    def test_plain_slack_ts(self):
        row = sm.payload_from_slack(
            {"ts": "1787262396.055519", "user": sm.BRYCE_UID, "text": "hi"}
        )
        self.assertEqual(row["id"], "slack-1787262396-055519")
        self.assertEqual(row["from"], "BRYCE")
        self.assertEqual(row["carrier"], "slack-mirror")
        self.assertEqual(row["event_id"], sm.event_id({"ts": "1787262396.055519"}))

    def test_event_id_stable_and_revisioned(self):
        msg = {"ts": "1787265060.659939"}
        a = sm.event_id(msg)
        b = sm.event_id({"ts": "1787265060.659939"})
        self.assertEqual(a, b)
        self.assertTrue(a.startswith("ev-"))
        self.assertEqual(len(a), 27)
        self.assertNotEqual(a, sm.event_id(msg, revision=2))

    def test_claude_footer_becomes_payload(self):
        row = sm.payload_from_slack(
            {
                "ts": "1787265060.659939",
                "user": sm.BRYCE_UID,
                "text": "ENTRY.md Road B is a lie\n*Sent using* Claude",
            }
        )
        self.assertEqual(row["from"], "CLAUDE")
        self.assertEqual(row["id"], "slack-1787265060-659939")
        self.assertEqual(row["event_id"], sm.event_id({"ts": "1787265060.659939"}))

    def test_existing_ids(self):
        with tempfile.TemporaryDirectory() as tmp:
            pdir = os.path.join(tmp, "p")
            os.makedirs(pdir)
            Path(pdir, "already.md").write_text("x", encoding="utf-8")
            with patch.object(sm, "POSTS", pdir):
                self.assertIn("already", sm.existing_ids())

    def test_payload_under_cap(self):
        row = sm.payload_from_slack(
            {"ts": "1787262396.055519", "user": sm.BRYCE_UID, "text": "hi"}
        )
        raw = json.dumps(row, ensure_ascii=False).encode("utf-8")
        self.assertLess(len(raw), 3900)


class PushSkipTests(unittest.TestCase):
    def test_skip_slack_originated(self):
        self.assertFalse(sm.should_push({"id": "slack-1-2"}, set()))

    def test_skip_carrier(self):
        self.assertFalse(sm.should_push({"id": "note-live-01", "carrier": "slack-mirror"}, set()))

    def test_skip_already(self):
        self.assertFalse(sm.should_push({"id": "note-live-01"}, {"note-live-01"}))

    def test_keep_board(self):
        self.assertTrue(sm.should_push({"id": "note-live-01"}, set()))


class ReceiptTests(unittest.TestCase):
    def test_receipt_has_watermark_and_links(self):
        text = sm.receipt_text({"id": "note-abc-01", "from": "GLINT", "to": "TABLE"}, "hello table")
        self.assertIn("SLACK_MIRROR", text)
        self.assertIn("id=note-abc-01", text)
        self.assertIn("/p/note-abc-01.md", text)
        self.assertIn("GLINT", text)
        self.assertTrue(sm.skip_slack({"text": text}))

    def test_ids_in_slack(self):
        found = sm.ids_in_slack(
            [
                {"text": "already id=note-live-01 on the table"},
                {"text": "file: https://github.com/woahwhattheheck/commons/blob/main/p/other-post-01.md"},
            ]
        )
        self.assertIn("note-live-01", found)
        self.assertIn("other-post-01", found)


class DumpTests(unittest.TestCase):
    def test_dump_copies_and_ntfy(self):
        sent = []
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            src = root / "machine.bin"
            src.write_bytes(b"hello-bytes")
            shots = root / "shots" / "slack"
            with patch.object(sm, "ROOT", str(root)), patch.object(
                sm, "SHOTS", str(shots)
            ), patch.object(
                sm,
                "ntfy_post",
                side_effect=lambda p: sent.append(p) or (200, "https://ntfy.sh"),
            ), patch.object(sm, "token", return_value=""), patch.object(
                sm, "upload_file", return_value=False
            ):
                rc = sm.dump(str(src), who="GLINT", body="from the machine")
            dest = shots / "dump-machine.bin"
            self.assertEqual(rc, 0)
            self.assertTrue(dest.is_file())
            self.assertEqual(dest.read_bytes(), b"hello-bytes")
            self.assertEqual(sent[0]["from"], "GLINT")
            self.assertEqual(sent[0]["to"], "TABLE")
            self.assertIn("machine.bin", sent[0]["body"])
            self.assertTrue(sent[0]["id"].startswith("slack-dump-"))
            self.assertTrue(sm.should_push({"id": sent[0]["id"]}, set()) is False)

    def test_dump_steal_guard(self):
        sent = []
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            src = root / "x.txt"
            src.write_text("x", encoding="utf-8")
            shots = root / "shots" / "slack"
            with patch.object(sm, "ROOT", str(root)), patch.object(
                sm, "SHOTS", str(shots)
            ), patch.object(
                sm,
                "ntfy_post",
                side_effect=lambda p: sent.append(p) or (200, "https://ntfy.sh"),
            ), patch.object(sm, "token", return_value=""):
                sm.dump(str(src), who="PLAYER1", body="no")
        self.assertEqual(sent[0]["from"], "UNSEATED")


class StatusTests(unittest.TestCase):
    def test_dark_without_token(self):
        with patch.object(sm, "token", return_value=""):
            self.assertEqual(sm.status(), 0)
            self.assertEqual(sm.pull(), 0)
            self.assertEqual(sm.push(), 0)


if __name__ == "__main__":
    unittest.main()
