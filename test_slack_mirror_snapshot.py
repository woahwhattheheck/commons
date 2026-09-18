"""One captured post revision supplies the body, chunks and source blob.

All writes use temporary files. No Slack/network request or live cursor is used.
"""
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "host"))
import slack_mirror as sm
import commons_slack_full_body as full
import commons_slack_full_body_chunk as channel

FIRST = b"from: FIRST\nid: snapshot-first\n---\nOriginal body.\n"
SECOND = b"from: SECOND\nid: snapshot-second\n---\n" + b"replacement " * 1200


def blob(data):
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


@contextmanager
def change_after_first_read(path, replacement):
    """Deterministically replace/unlink a real file after its first capture."""
    read_bytes, read_text = Path.read_bytes, Path.read_text
    reads = []

    def capture(reader, item, *args, **kwargs):
        result = reader(item, *args, **kwargs)
        if item == path:
            reads.append(len(result))
            if len(reads) == 1:
                if replacement is None:
                    path.unlink()
                else:
                    next_path = path.with_suffix(".next")
                    next_path.write_bytes(replacement)
                    next_path.replace(path)
        return result

    with patch.object(Path, "read_bytes", lambda item: capture(read_bytes, item)), \
         patch.object(Path, "read_text", lambda item, *a, **k: capture(read_text, item, *a, **k)):
        yield reads


class SnapshotTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "source-post.md"
        self.path.write_bytes(FIRST)

    def test_replacement_cannot_mix_payload_body_or_part_count(self):
        with change_after_first_read(self.path, SECOND):
            packed = full.commons_to_slack(self.path)
        self.assertEqual(packed["body"], "Original body.\n")
        self.assertIn(packed["body"], packed["payload"])
        self.assertIn("source_from: FIRST", packed["payload"])
        self.assertNotIn("replacement", packed["payload"])
        self.assertEqual(packed["parts"], len(sm.chunks(packed["payload"])))
        self.assertEqual(packed["char_count"], len(packed["payload"]))
        self.assertEqual(self.path.read_bytes(), SECOND)

    def test_channel_hash_stays_with_payload_when_path_changes_after_format(self):
        original = full.commons_to_slack
        def replace_after_format(path):
            packed = original(path)
            path.write_bytes(SECOND)
            return packed
        with patch.object(full, "commons_to_slack", side_effect=replace_after_format):
            packed = channel.format_channel_and_thread(self.path)
        self.assertEqual(packed["blob"], blob(FIRST))
        self.assertEqual(packed["first_line"], "source-post " + blob(FIRST))
        self.assertIn("Original body.", packed["channel"])
        self.assertNotIn("replacement", packed["channel"])

    def test_unlink_after_capture_does_not_invalidate_complete_snapshot(self):
        with change_after_first_read(self.path, None):
            packed = channel.format_channel_and_thread(self.path)
        self.assertFalse(self.path.exists())
        self.assertEqual(packed["blob"], blob(FIRST))
        self.assertIn("Original body.", packed["channel"])

    def test_full_body_reads_source_once(self):
        with change_after_first_read(self.path, FIRST) as reads:
            full.commons_to_slack(self.path)
        self.assertEqual(len(reads), 1)

    def test_channel_reads_source_once(self):
        with change_after_first_read(self.path, FIRST) as reads:
            channel.format_channel_and_thread(self.path)
        self.assertEqual(len(reads), 1)

    def test_newlines_keep_existing_rendering_but_hash_exact_bytes(self):
        for separator in ("\n", "\r\n", "\r"):
            with self.subTest(separator=repr(separator)):
                raw = separator.join(("---", "from: Unicode", "id: example-post", "---", "é🙂", ""))
                source = raw.encode("utf-8")
                self.path.write_bytes(source)
                expected = sm.mirror_payload(self.path)
                packed = full.commons_to_slack(self.path)
                self.assertEqual(packed["payload"], expected)
                self.assertEqual(packed["body"], "é🙂\n")
                self.assertEqual(packed["blob"], blob(source))

    def test_blob_agrees_with_git_raw_object(self):
        for source in (FIRST, FIRST.replace(b"\n", b"\r\n"), b"", "🙂é".encode()):
            with self.subTest(source=source):
                self.path.write_bytes(source)
                expected = subprocess.check_output(["git", "hash-object", "--stdin"], input=source).decode().strip()
                self.assertEqual(full.commons_to_slack(self.path)["blob"], expected)
                self.assertEqual(channel.header_line(self.path), "source-post " + expected)

    def test_unicode_long_body_reassembles_with_both_existing_limits(self):
        source = ("from: SOURCE\nid: source-post\n---\n" + "é🙂\n\n" * 3000).encode()
        self.path.write_bytes(source)
        packed = full.commons_to_slack(self.path)
        split = channel.format_channel_and_thread(self.path)
        self.assertEqual("".join(sm.format_mirror(self.path)), packed["payload"])
        parts = [split["channel"], *split["thread_replies"]]
        self.assertEqual("".join(parts), split["first_line"] + "\n" + packed["payload"])
        self.assertTrue(all(0 < len(p) <= 4000 for p in parts))
        self.assertEqual(split["thread_parts"], len(parts) - 1)
        self.assertEqual(split["channel_chars"], len(parts[0]))
        self.assertEqual(split["leftover_slack_limit_keep"], 5000)

    def test_empty_and_link_only_posts_preserve_format(self):
        for source in (b"", b"https://example.com/post\n", b"from: PERSON\nid: source-post\n---\n"):
            with self.subTest(source=source):
                self.path.write_bytes(source)
                self.assertEqual(full.commons_to_slack(self.path)["payload"], sm.mirror_payload(self.path))

    def test_snapshot_formatter_does_not_open_path(self):
        self.path.unlink()
        with patch.object(Path, "open", side_effect=AssertionError("unexpected file read")):
            result = sm.mirror_payload_from_text(self.path, FIRST.decode())
        self.assertIn("source_from: FIRST", result)
        self.assertTrue(result.endswith("Original body.\n"))

    def test_missing_source_retains_original_error(self):
        self.path.unlink()
        for function in (sm.mirror_payload, full.commons_to_slack, channel.format_channel_and_thread):
            with self.subTest(function=function.__name__), self.assertRaises(FileNotFoundError):
                function(self.path)

    def test_invalid_utf8_retains_original_error(self):
        self.path.write_bytes(b"bad\xffbody")
        for function in (sm.mirror_payload, full.commons_to_slack, channel.format_channel_and_thread):
            with self.subTest(function=function.__name__), self.assertRaises(UnicodeDecodeError):
                function(self.path)

    def test_format_cli_works_without_a_git_checkout(self):
        proc = subprocess.run([sys.executable, str(ROOT / "host/commons_slack_full_body_chunk.py"),
                               "--format", str(self.path), "--json"],
                              cwd=self.tmp.name, capture_output=True, text=True, timeout=10)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(json.loads(proc.stdout)["blob"], blob(FIRST))

    def test_formatting_does_not_send_or_advance_cursor(self):
        with patch.object(sm.urllib.request, "urlopen", side_effect=AssertionError("unexpected network")):
            packed = channel.format_channel_and_thread(self.path)
        self.assertFalse(packed["new_token"])
        self.assertFalse(packed["cursor_advanced"])
        self.assertFalse(packed["confirmed_post"])
        self.assertEqual(packed["sends"], 0)


if __name__ == "__main__":
    unittest.main()
