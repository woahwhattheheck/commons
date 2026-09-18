#!/usr/bin/env python3
"""The Slack chunk header is one reversible physical line for every Git path."""
from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "host"))
import commons_slack_full_body_chunk as channel  # noqa: E402


class HeaderLineTests(unittest.TestCase):
    def pack(self, stem, payload="BODY\n"):
        blob = "c" * 40
        with patch.object(
            channel.leftover,
            "commons_to_slack",
            return_value={"blob": blob, "payload": payload},
        ):
            return channel.format_channel_and_thread(Path("p") / (stem + ".md"))

    def test_ordinary_id_keeps_existing_first_line(self):
        packed = self.pack("ordinary-post")
        self.assertEqual(packed["first_line"], "ordinary-post " + "c" * 40)
        self.assertEqual(packed.get("header_post_id"), "ordinary-post")
        self.assertEqual(packed.get("header_post_id_encoding"), "plain")
        self.assertEqual(packed["post_id"], "ordinary-post")

    def test_printable_unicode_without_whitespace_stays_plain(self):
        for stem in ("café", "稲-post", "dots.and_under-score"):
            with self.subTest(stem=stem):
                packed = self.pack(stem)
                self.assertEqual(packed["first_line"], stem + " " + "c" * 40)
                self.assertEqual(packed.get("header_post_id"), stem)
                self.assertEqual(packed.get("header_post_id_encoding"), "plain")

    def test_controls_whitespace_backslash_and_quote_use_reversible_json(self):
        stems = (
            "new\nline", "tab\tname", "carriage\rreturn", "form\ffeed",
            "next\u2028line", "space inside", " leading", "trailing ",
            r"literal\nsequence", 'a"quote',
        )
        for stem in stems:
            with self.subTest(stem=repr(stem)):
                packed = self.pack(stem)
                display = packed.get("header_post_id")
                self.assertIsInstance(display, str)
                self.assertEqual(packed.get("header_post_id_encoding"), "json-string")
                decoded = json.loads(display) if isinstance(display, str) else None
                self.assertEqual(decoded, stem)
                self.assertTrue(packed["first_line"].isprintable())
                self.assertEqual(packed["first_line"].splitlines(), [packed["first_line"]])
                self.assertTrue(packed["first_line"].endswith(" " + packed["blob"]))

    def test_literal_escape_and_control_name_do_not_alias(self):
        control = self.pack("new\nline")
        literal = self.pack(r"new\nline")
        self.assertNotEqual(control["first_line"], literal["first_line"])
        self.assertEqual(json.loads(control.get("header_post_id") or "null"), "new\nline")
        self.assertEqual(json.loads(literal.get("header_post_id") or "null"), r"new\nline")

    def test_control_filename_keeps_raw_identity_but_sha_is_on_physical_line_one(self):
        raw = "new\nline"
        packed = self.pack(raw)
        physical = packed["channel"].splitlines()[0]
        self.assertEqual(physical, packed["first_line"])
        self.assertTrue(physical.endswith(" " + packed["blob"]))
        self.assertEqual(packed["post_id"], raw)
        self.assertEqual(json.loads(packed.get("header_post_id") or "null"), raw)

    def test_chunking_remains_lossless_and_bounded(self):
        body = "x" * 9000
        packed = self.pack("new\nline", body)
        combined = packed["channel"] + "".join(packed["thread_replies"])
        self.assertEqual(combined, packed["first_line"] + "\n" + body)
        self.assertLessEqual(packed["channel_chars"], channel.CHANNEL_LIMIT)
        self.assertTrue(all(len(part) <= channel.CHANNEL_LIMIT for part in packed["thread_replies"]))
        self.assertGreater(packed["thread_parts"], 0)

    def test_blob_and_body_fields_are_unchanged(self):
        body = "source payload\n"
        packed = self.pack("space inside", body)
        self.assertEqual(packed["blob"], "c" * 40)
        self.assertEqual(
            packed["channel"] + "".join(packed["thread_replies"]),
            packed["first_line"] + "\n" + body,
        )
        self.assertFalse(packed["cursor_advanced"])
        self.assertFalse(packed["confirmed_post"])
        self.assertEqual(packed["sends"], 0)

    def test_measure_rejects_multiline_self_consistent_header(self):
        catalog = {
            "id": "fixture", "ride": "fixture", "default_table": "fixture",
            "last_mirrored_sha": "", "keep_unread": {},
            "rule": {
                "channel_limit": 4000, "remainder_as_thread": True,
                "id_and_sha_first_line": True,
                "cursor_advances_only_after_confirmed_post": True,
                "five_minute_job": True, "login": False, "gate": False,
                "new_token": False,
            },
        }
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sample = root / "p" / "cursor-commons-slack-full-body-20260902-01.md"
            sample.parent.mkdir()
            sample.write_text("body\n", encoding="utf-8")
            bad = {
                "channel": "broken\nname " + "d" * 40 + "\nbody",
                "first_line": "broken\nname " + "d" * 40,
                "blob": "d" * 40,
                "channel_chars": 52,
                "thread_parts": 0,
                "cursor_advanced": False,
            }
            with (
                patch.object(channel, "ROOT", root),
                patch.object(channel, "load_catalog", return_value=catalog),
                patch.object(channel, "format_channel_and_thread", return_value=bad),
            ):
                packet = channel.measure()
        self.assertEqual(packet["verdict"], "FINDER-FAILED")
        self.assertIn("first_physical_line_mismatch", packet["errors"])
        self.assertIn("sha_not_on_first_line", packet["errors"])
        self.assertIn("first_line_control_character", packet["errors"])


if __name__ == "__main__":
    unittest.main()
