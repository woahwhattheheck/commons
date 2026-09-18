#!/usr/bin/env python3
"""Unusual source paths remain one-line and round-trip through mirror links."""
from __future__ import annotations

import json
from pathlib import Path
import sys
import unittest
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "host"))
import slack_mirror as sm  # noqa: E402


class MirrorPathIdentityTests(unittest.TestCase):
    def payload(self, stem: str, raw: str = "body") -> str:
        return sm.mirror_payload_from_text(Path("p") / (stem + ".md"), raw)

    def link(self, payload: str) -> str:
        return next(
            line
            for line in payload.splitlines()
            if line.startswith("https://github.com/")
        )

    def test_ordinary_payload_is_byte_identical(self):
        raw = "from: ALPHA\nid: stable-id\n\n---\n\nbody"
        expected = (
            sm.RELAY_DECLARATION.format(id="ordinary-post")
            + "source_from: ALPHA\nsource_id: stable-id\n"
            + sm.GIT_BLOB.format(id="ordinary-post")
            + "\n\nbody\n"
        )
        self.assertEqual(self.payload("ordinary-post", raw), expected)

    def test_unusual_stems_keep_declaration_on_physical_lines(self):
        stems = (
            "new\nline",
            "tab\tname",
            "carriage\rreturn",
            "space inside",
            "next\u2028line",
            r"literal\nsequence",
            'a"quote',
        )
        suffix = ".md; Slack #commons " + sm.CHANNEL
        for stem in stems:
            with self.subTest(stem=repr(stem)):
                payload = self.payload(stem)
                resources = next(
                    line
                    for line in payload.splitlines()
                    if line.startswith("resources: source p/")
                )
                token = resources[len("resources: source p/") : -len(suffix)]
                self.assertEqual(json.loads(token), stem)
                self.assertEqual(resources.splitlines(), [resources])
                self.assertTrue(resources.isprintable())

    def test_source_link_path_component_round_trips(self):
        stems = (
            "new\nline",
            "space inside",
            "hash#mark",
            "query?mark",
            "percent%mark",
            r"back\slash",
            'a"quote',
            "稲-post",
        )
        for stem in stems:
            with self.subTest(stem=repr(stem)):
                link = self.link(self.payload(stem))
                self.assertNotIn("\n", link)
                self.assertNotIn(" ", link)
                component = urlsplit(link).path.rsplit("/", 1)[-1]
                self.assertTrue(component.endswith(".md"))
                self.assertEqual(unquote(component[:-3]), stem)

    def test_literal_escape_and_actual_control_do_not_alias(self):
        actual = self.payload("new\nline")
        literal = self.payload(r"new\nline")
        self.assertNotEqual(actual, literal)
        self.assertNotEqual(self.link(actual), self.link(literal))

    def test_raw_post_id_api_remains_exact(self):
        for stem in ("new\nline", r"new\nline", "space inside", "稲-post"):
            with self.subTest(stem=repr(stem)):
                self.assertEqual(sm.post_id(Path("p") / (stem + ".md")), stem)

    def test_metadata_id_stays_authoritative(self):
        raw = "from: ALPHA\nid: stable-id\n\n---\n\nbody"
        payload = self.payload("new\nline", raw)
        self.assertIn("source_from: ALPHA\nsource_id: stable-id\n", payload)
        self.assertNotIn('source_id: "new\\nline"', payload)

    def test_missing_metadata_id_uses_reversible_one_line_fallback(self):
        payload = self.payload("new\nline", "from: ALPHA\n\n---\n\nbody")
        source_line = next(
            line for line in payload.splitlines() if line.startswith("source_id: ")
        )
        token = source_line[len("source_id: ") :]
        self.assertEqual(json.loads(token), "new\nline")
        self.assertEqual(source_line.splitlines(), [source_line])

    def test_body_and_chunking_are_unchanged(self):
        raw = "x" * 12000
        payload = self.payload("space inside", raw)
        self.assertTrue(payload.endswith(raw + "\n"))
        parts = sm.chunks(payload)
        self.assertEqual("".join(parts), payload)
        self.assertTrue(all(len(part) <= sm.SLACK_LIMIT for part in parts))


if __name__ == "__main__":
    unittest.main()
