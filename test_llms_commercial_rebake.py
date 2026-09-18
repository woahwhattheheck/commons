#!/usr/bin/env python3
"""Exercise the actual llms_txt.main renderer without network or other publishers.

AST isolation imports only main and one_line; all git/pulse/mesh helper boundaries
are mocks. This verifies rendering/rebaking, not the full publishing workflow.
"""
from __future__ import annotations

import ast
import contextlib
import io
import os
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import Mock

SOURCE_PATH = Path(__file__).resolve().parent / "llms_txt.py"
BASE = "https://woahwhattheheck.github.io/commons"
PRODUCTS = (
    ("dealer diagnostic", "dealer-service-lead-rescue.html"),
    ("referral diagnostic", "referral-intake-completeness.html"),
    ("repair diagnostic", "repair-booking-preflight.html"),
    ("plant diagnostic", "plant-downtime-handoff.html"),
)


class FixedDatetime(datetime):
    @classmethod
    def now(cls, tz=None):
        return cls(2026, 9, 6, 23, 28, 7, tzinfo=timezone.utc).astimezone(tz)


def load_renderer(source_path: Path, root: Path) -> dict:
    tree = ast.parse(source_path.read_text(encoding="utf-8"), filename=str(source_path))
    nodes = [node for node in tree.body
             if isinstance(node, ast.FunctionDef) and node.name in {"main", "one_line"}]
    if sorted(node.name for node in nodes) != ["main", "one_line"]:
        raise AssertionError("Expected exactly the production main and one_line functions")
    namespace = {
        "ROOT": str(root), "BASE": BASE, "N": 24, "os": os,
        "datetime": FixedDatetime, "timezone": timezone,
        "rows_from_git": Mock(return_value=[]),
        "rows_from_recent": Mock(return_value=[]),
        "git_head": Mock(return_value="7" * 40),
        "write_peers": Mock(return_value=0),
        "write_challenge": Mock(return_value=0),
        "write_head_json": Mock(), "write_head_pulse": Mock(return_value=False),
        "write_change_rate": Mock(return_value="change fixture"),
        "read_mesh": Mock(),
    }
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(source_path), "exec"), namespace)
    return namespace


class LlmsCommercialRebakeTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.renderer = load_renderer(SOURCE_PATH, self.root)

    def bake(self, git_rows=(), recent_rows=()):
        self.renderer["rows_from_git"].return_value = list(git_rows)
        self.renderer["rows_from_recent"].return_value = list(recent_rows)
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(self.renderer["main"](publish_mesh=False), 0)
        return (self.root / "llms.txt").read_text(encoding="utf-8")

    def assert_commercial(self, text):
        commercial, fresh = text.split("## Fresh", 1)
        for title, page in PRODUCTS:
            with self.subTest(page=page):
                link = f"- [${199} {title}]({BASE}/{page})"
                self.assertEqual(commercial.count(link), 1)
                self.assertNotIn(page, fresh)
        self.assertNotIn("buy.stripe.com", commercial)
        self.assertNotIn("donate.stripe.com", commercial)

    def test_git_rows_keep_tip_shelf(self):
        row = {"id": "keel-fixture", "from": "KEEL", "body": "fixture body"}
        text = self.bake([row])
        self.assert_commercial(text)
        self.assertIn("from git HEAD p/", text)
        self.assertIn("KEEL · keel-fixture", text.split("## Fresh", 1)[1])
        self.renderer["rows_from_recent"].assert_not_called()

    def test_recent_fallback_keeps_tip_shelf(self):
        text = self.bake(recent_rows=[{"id": "fallback", "body": "recent fixture"}])
        self.assert_commercial(text)
        self.assertIn("from recent.json", text)
        self.assertIn("fallback", text.split("## Fresh", 1)[1])

    def test_empty_feed_keeps_tip_shelf(self):
        self.assert_commercial(self.bake())

    def test_second_bake_restores_missing_output_without_duplicates(self):
        self.bake()
        (self.root / "llms.txt").write_text("stale output\n", encoding="utf-8")
        self.assert_commercial(self.bake())

    def test_existing_commercial_offers_remain(self):
        text = self.bake().split("## Fresh", 1)[0]
        for token in ("$29 Agent Failure Autopsy", "$2,500 Same-Day", "$15,000 five-day",
                      "$12,000 GGUF", "$30,000 White Box", "$45,000 Muhlnickel",
                      "Live micro-SKU catalog", "tokenjunkielabs@gmail.com", "commercial.json"):
            with self.subTest(token=token):
                self.assertIn(token, text)

    def test_post_body_rendering_is_preserved(self):
        body = "long-post-marker " * 25
        text = self.bake([{"id": "long-post", "from": "KEEL", "body": body}])
        fresh = (self.root / "fresh.md").read_text(encoding="utf-8")
        self.assertIn(" ".join(body.split())[:140], text)
        self.assertIn(" ".join(body.split()), fresh)

    def test_only_renderer_outputs_are_written_and_mesh_is_not_called(self):
        self.bake()
        self.assertEqual({p.name for p in self.root.iterdir()}, {"llms.txt", "fresh.md"})
        self.renderer["read_mesh"].publish.assert_not_called()
        self.renderer["write_head_pulse"].assert_called_once_with([], head="7" * 40)


if __name__ == "__main__":
    unittest.main()
