#!/usr/bin/env python3
"""Full Slack mirror bodies distinguish envelopes from Markdown separators."""
from __future__ import annotations

from contextlib import redirect_stdout
import importlib.util
from io import StringIO
from pathlib import Path
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("slack_mirror_envelope_target", ROOT / "host" / "slack_mirror.py")
SM = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SM)


class MirrorEnvelopeTests(unittest.TestCase):
    def test_plain_markdown_separator_does_not_discard_prefix(self):
        for text in ("Opening summary\n\n---\n\nDetails.\n",
                     "Introduction\n---\nMiddle\n---\nConclusion\n",
                     "A heading\n---\nParagraph\n"):
            with self.subTest(text=text):
                self.assertEqual(SM.body_of(text), text)
                self.assertEqual(SM.metadata_of(text), {})

    def test_plain_colon_text_does_not_become_metadata(self):
        text = "Note: keep this\nValue: 7\n---\nRest of the note.\n"
        self.assertEqual(SM.body_of(text), text)
        self.assertEqual(SM.metadata_of(text), {})

    def test_metadata_looking_prose_before_separator_is_not_an_envelope(self):
        text = "from: a quoted participant\nid: quoted-id\nThis is prose, not a header.\n---\nTail\n"
        self.assertEqual(SM.body_of(text), text)
        self.assertEqual(SM.metadata_of(text), {})

    def test_partial_opening_fence_is_preserved_as_plain_text(self):
        for text in ("---not-an-envelope\nfrom: QUOTED\n---\nTail\n",
                     "----\nfrom: QUOTED\n---\nTail\n"):
            with self.subTest(text=text):
                self.assertEqual(SM.body_of(text), text)
                self.assertEqual(SM.metadata_of(text), {})

    def test_exact_fenced_envelope_keeps_existing_body_and_source_fields(self):
        body = "PLAIN: First paragraph\n\n---\n\nSecond paragraph\n"
        text = "---\nfrom: SOURCE\nid: source-post-01\nto: TABLE\n---\n\n" + body
        self.assertEqual(SM.body_of(text), body)
        self.assertEqual(SM.metadata_of(text), {"from": "SOURCE", "id": "source-post-01"})

    def test_legacy_flat_envelope_remains_supported(self):
        body = "Body with a Markdown rule\n---\nRemaining body\n"
        text = "from: SOURCE\nid: source-post-01\nsubject: A: B\ncustom_field: custom\n\n---\n\n" + body
        self.assertEqual(SM.body_of(text), body)
        self.assertEqual(SM.metadata_of(text), {"from": "SOURCE", "id": "source-post-01"})

    def test_legacy_comments_and_indented_values_remain_supported(self):
        text = "# envelope\nfrom: SOURCE\nsubject: |\n  Multiline value\n  kept as metadata\n---\nBody\n"
        self.assertEqual(SM.body_of(text), "Body\n")
        self.assertEqual(SM.metadata_of(text), {"from": "SOURCE"})

    def test_fenced_metadata_does_not_require_identity_fields(self):
        text = "---\ncustom: value\n---\nBody\n"
        self.assertEqual(SM.body_of(text), "Body\n")
        self.assertEqual(SM.metadata_of(text), {})

    def test_only_standalone_closing_fence_ends_envelope(self):
        text = "---\nfrom: SOURCE\n---not-a-delimiter\nid: source-post-01\n---\nBody\n"
        self.assertEqual(SM.body_of(text), "Body\n")
        self.assertEqual(SM.metadata_of(text), {"from": "SOURCE", "id": "source-post-01"})

    def test_indented_rule_inside_fenced_block_value_is_not_closing_fence(self):
        text = "---\nfrom: SOURCE\nsubject: |\n  ---\n  keep this value\nid: source-post-01\n---\nBody\n"
        self.assertEqual(SM.body_of(text), "Body\n")
        self.assertEqual(SM.metadata_of(text), {"from": "SOURCE", "id": "source-post-01"})

    def test_crlf_fences_preserve_body_line_endings_in_pure_parser(self):
        body = "Café\r\n\r\n---\r\nMore\r\n"
        text = "---\r\nfrom: SOURCE\r\nid: source-post-01\r\n---\r\n\r\n" + body
        self.assertEqual(SM.body_of(text), body)
        self.assertEqual(SM.metadata_of(text), {"from": "SOURCE", "id": "source-post-01"})

    def test_unterminated_envelope_and_plain_text_stay_complete(self):
        for text in ("", "---", "---\nfrom: SOURCE\nStill open\n",
                     "from: SOURCE\nid: source-post-01\nhttps://example.invalid/post\n"):
            with self.subTest(text=text):
                self.assertEqual(SM.body_of(text), text)
                self.assertEqual(SM.metadata_of(text), {})

    def test_body_fields_after_real_envelope_do_not_replace_source_metadata(self):
        body = "from: QUOTED\nid: quoted-post-01\n---\nTail\n"
        text = "---\nfrom: SOURCE\nid: source-post-01\n---\n" + body
        self.assertEqual(SM.metadata_of(text), {"from": "SOURCE", "id": "source-post-01"})
        self.assertEqual(SM.body_of(text), body)

    def test_payload_preserves_plain_body_and_falls_back_to_filename_source(self):
        body = "Summary\n\n---\n\nAll details\n"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "plain-post-01.md"
            path.write_text(body, encoding="utf-8")
            with mock.patch.object(SM.urllib.request, "urlopen", side_effect=AssertionError("unexpected network")):
                payload = SM.mirror_payload(path)
                parts = SM.format_mirror(path)
        self.assertTrue(payload.endswith(body))
        self.assertIn("source_from: UNKNOWN\n", payload)
        self.assertIn("source_id: plain-post-01\n", payload)
        self.assertEqual("".join(parts), payload)

    def test_long_body_survives_separator_detection_and_chunking(self):
        body = "Important first paragraph\n---\n" + "Café 🌾 details\n" * 1200
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "long-post-01.md"
            path.write_text(body, encoding="utf-8")
            parts = SM.format_mirror(path)
        self.assertGreater(len(parts), 1)
        self.assertTrue(all(0 < len(part) <= SM.SLACK_LIMIT for part in parts))
        self.assertTrue("".join(parts).endswith(body))

    def test_real_format_command_keeps_prefix_and_suffix_without_send(self):
        body = "Opening summary\n---\nFinal details\n"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "cli-post-01.md"
            path.write_text(body, encoding="utf-8")
            output = StringIO()
            with redirect_stdout(output), mock.patch.object(
                SM.urllib.request, "urlopen", side_effect=AssertionError("unexpected network")
            ):
                code = SM.main(["slack_mirror.py", "format", str(path)])
        self.assertEqual(code, 0)
        self.assertIn(body, output.getvalue())

    def test_empty_fenced_body_and_link_only_body_remain_legal(self):
        for body in ("", "https://example.invalid/post\n"):
            text = "---\nfrom: SOURCE\nid: source-post-01\n---\n" + body
            self.assertEqual(SM.body_of(text), body)
            self.assertEqual(SM.metadata_of(text)["id"], "source-post-01")


    def test_captured_plain_markdown_keeps_body_without_reopening_path(self):
        path = Path("captured-post-01.md")
        body = "Opening summary\n---\nFinal details\n"
        with mock.patch.object(Path, "open", side_effect=AssertionError("unexpected reread")):
            payload = SM.mirror_payload_from_text(path, body)
        self.assertTrue(payload.endswith(body))
        self.assertIn("source_id: captured-post-01\n", payload)
        self.assertIn("source_from: UNKNOWN\n", payload)

    def test_captured_legacy_metadata_and_body_use_same_boundary(self):
        raw = "from: CAPTURED\nid: capture-original-01\n---\nSummary\n---\nDetails\n"
        with mock.patch.object(Path, "open", side_effect=AssertionError("unexpected reread")):
            payload = SM.mirror_payload_from_text(Path("capture-file-01.md"), raw)
        self.assertIn("source_from: CAPTURED\n", payload)
        self.assertIn("source_id: capture-original-01\n", payload)
        self.assertTrue(payload.endswith("Summary\n---\nDetails\n"))


if __name__ == "__main__":
    unittest.main()
