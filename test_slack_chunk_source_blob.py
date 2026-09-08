"""The chunk packet's source blob comes from capture, never display text.

Only temporary files and offline format/CLI calls are used. No Slack sends.
"""
from pathlib import Path
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "host"))
import commons_slack_full_body_chunk as channel
import commons_slack_full_body as full
import slack_mirror as sm

SOURCE = b"Opening summary\n---\nRemaining details\n"


def source_blob(data):
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


class ChunkSourceBlobTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def source(self, name="review notes.md", raw=SOURCE):
        path = self.root / name
        path.write_bytes(raw)
        return path

    def test_space_bearing_names_report_exact_git_blob(self):
        for name in ("review notes.md", " leading.md", "two  spaces.md",
                     "trailing .md", " .md", "récolte 稲 notes.md"):
            with self.subTest(name=name):
                path = self.source(name)
                expected = subprocess.check_output(
                    ["git", "hash-object", "--stdin"], input=SOURCE
                ).decode("ascii").strip()
                packed = channel.format_channel_and_thread(path)
                self.assertEqual(packed["blob"], expected)
                self.assertRegex(packed["blob"], r"^[0-9a-f]{40}$")
                self.assertEqual(packed["post_id"], path.stem)
                self.assertEqual(packed["first_line"], f"{path.stem} {expected}")

    def test_ordinary_names_keep_the_complete_packet_contract(self):
        for name in ("source-post.md", "récolte.md", "notes.txt"):
            with self.subTest(name=name):
                path = self.source(name)
                first = f"{path.stem} {source_blob(SOURCE)}"
                parts = sm.chunks(first + "\n" + sm.mirror_payload(path), channel.CHANNEL_LIMIT)
                expected = {
                    "kind": "COMMONS_SLACK_FULL_BODY_CHUNK", "id": channel.ID,
                    "post_id": path.stem, "blob": source_blob(SOURCE), "first_line": first,
                    "channel_limit": 4000, "leftover_slack_limit_keep": 5000,
                    "channel": parts[0], "thread_replies": parts[1:],
                    "channel_chars": len(parts[0]), "thread_parts": len(parts) - 1,
                    "full_body": True, "remainder_as_thread": len(parts) > 1,
                    "new_token": False, "cursor_advanced": False,
                    "confirmed_post": False, "sends": 0,
                }
                self.assertEqual(channel.format_channel_and_thread(path), expected)

    def test_after_capture_replacement_keeps_the_original_blob(self):
        path = self.source()
        original = full.commons_to_slack
        replacement = b"New content which was not captured\n"
        def captured_then_replaced(source):
            packet = original(source)
            source.write_bytes(replacement)
            return packet
        with patch.object(full, "commons_to_slack", side_effect=captured_then_replaced) as capture:
            packet = channel.format_channel_and_thread(path)
        capture.assert_called_once_with(path)
        self.assertEqual(path.read_bytes(), replacement)
        self.assertEqual(packet["blob"], source_blob(SOURCE))
        self.assertEqual(packet["first_line"], f"review notes {source_blob(SOURCE)}")
        self.assertTrue((packet["channel"] + "".join(packet["thread_replies"])).endswith(SOURCE.decode()))

    def test_unlink_after_capture_preserves_the_source_blob(self):
        path = self.source()
        original = full.commons_to_slack
        def captured_then_unlinked(source):
            packet = original(source)
            source.unlink()
            return packet
        with patch.object(full, "commons_to_slack", side_effect=captured_then_unlinked):
            packet = channel.format_channel_and_thread(path)
        self.assertFalse(path.exists())
        self.assertEqual(packet["blob"], source_blob(SOURCE))
        self.assertIn("Opening summary", packet["channel"])

    def test_long_body_and_spaced_name_preserve_header_and_reassembly(self):
        raw = ("from: SOURCE\nid: long-post-01\n---\n" + "é🙂 original paragraph\n\n" * 1000).encode()
        path = self.source("long review notes.md", raw)
        expected_payload = sm.mirror_payload(path)
        packet = channel.format_channel_and_thread(path)
        self.assertEqual(packet["blob"], source_blob(raw))
        expected_first = f"long review notes {source_blob(raw)}"
        parts = [packet["channel"], *packet["thread_replies"]]
        self.assertEqual("".join(parts), expected_first + "\n" + expected_payload)
        self.assertTrue(all(0 < len(part) <= 4000 for part in parts))
        self.assertGreater(packet["thread_parts"], 0)

    def test_cli_json_reports_exact_blob_without_a_git_checkout(self):
        path = self.source("review notes café.md")
        run = subprocess.run(
            [sys.executable, str(ROOT / "host" / "commons_slack_full_body_chunk.py"),
             "--format", str(path), "--json"], cwd=self.root,
            text=True, capture_output=True, timeout=10, check=False,
        )
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stderr, "")
        packet = json.loads(run.stdout)
        self.assertEqual(packet["blob"], source_blob(SOURCE))
        self.assertEqual(packet["post_id"], "review notes café")
        self.assertFalse(packet["cursor_advanced"])
        self.assertEqual(packet["sends"], 0)

    def test_single_capture_no_new_hash_process_and_no_send(self):
        path = self.source()
        original_read = Path.read_bytes
        reads = []
        def read_once(source):
            reads.append(source)
            return original_read(source)
        with patch.object(Path, "read_bytes", read_once), \
             patch.object(channel.subprocess, "check_output", side_effect=AssertionError("unexpected Git call")), \
             patch.object(sm.urllib.request, "urlopen", side_effect=AssertionError("unexpected network")):
            packet = channel.format_channel_and_thread(path)
        self.assertEqual(reads, [path])
        self.assertEqual(packet["blob"], source_blob(SOURCE))
        self.assertFalse(packet["cursor_advanced"])
        self.assertFalse(packet["confirmed_post"])
        self.assertEqual(packet["sends"], 0)


if __name__ == "__main__":
    unittest.main()
