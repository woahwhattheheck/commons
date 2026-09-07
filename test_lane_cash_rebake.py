#!/usr/bin/env python3
"""All lane publishers retain product links together with their board state."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import board_ingest
import hub_pages


class LaneCashRebakeTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.rows = [
            ("2026-09-07T03:00:00Z", {"id": "harbor-lane-" + lane.lower(), "from": "HARBOR", "to": "TABLE", "board": lane}, "Fixture lane record")
            for lane in hub_pages.LANE_BOARDS
        ]

    def bake(self, rows):
        with patch.object(board_ingest, "ROOT", str(self.root)):
            hub_pages.rebuild_lanes(board_ingest, rows)
        return {lane: (self.root / (lane.lower() + ".html")).read_text(encoding="utf-8") for lane in hub_pages.LANE_BOARDS}

    def assert_products_and_form(self, lane, page):
        self.assertEqual(page.count('id="live-cash"'), 1)
        expected = hub_pages.LIVE_CASH_HTML if lane == "FEATURES" else hub_pages.LIVE_CASH_PRODUCTS_HTML
        self.assertIn(expected, page)
        self.assertIn('<form id="say">', page)
        self.assertIn('data-lane="%s"' % lane, page)
        self.assertNotIn("buy.stripe.com", page)
        if lane != "FEATURES":
            self.assertNotIn("tools-cash.html", page)
        expected_script = "lane-head.js" if lane in hub_pages.LANE_HEAD_BOARDS else "board.js"
        self.assertIn('src="./%s?' % expected_script, page)

    def test_populated_lane_rebuild_keeps_products_forms_and_records(self):
        pages = self.bake(self.rows)
        self.assertEqual(self.bake(self.rows), pages)
        lanes = json.loads((self.root / "lanes.json").read_text())
        for lane, page in pages.items():
            with self.subTest(lane=lane):
                self.assert_products_and_form(lane, page)
                self.assertEqual(lanes[lane.lower()]["n"], 1)
                self.assertEqual(lanes[lane.lower()]["posts"][0]["id"], "harbor-lane-" + lane.lower())

    def test_empty_rebuild_replaces_stale_pages_and_clears_old_records(self):
        self.bake(self.rows)
        for lane in hub_pages.LANE_BOARDS:
            (self.root / (lane.lower() + ".html")).write_text("stale output", encoding="utf-8")
        pages = self.bake([])
        lanes = json.loads((self.root / "lanes.json").read_text())
        self.assertEqual(lanes["n"], 0)
        for lane, page in pages.items():
            with self.subTest(lane=lane):
                self.assert_products_and_form(lane, page)
                self.assertNotIn("stale output", page)
                self.assertEqual(lanes[lane.lower()], {"n": 0, "posts": []})

    def test_next_rebuild_projects_changed_lane_records(self):
        self.bake(self.rows)
        updated = [("2026-09-07T03:01:00Z", {"id": "harbor-new-request", "from": "HARBOR", "to": "TABLE", "lane": "REQUESTS"}, "Updated fixture")]
        pages = self.bake(updated)
        lanes = json.loads((self.root / "lanes.json").read_text())
        self.assertEqual(lanes["n"], 1)
        self.assertEqual(lanes["requests"]["posts"][0]["id"], "harbor-new-request")
        self.assertEqual(lanes["salon"]["posts"], [])
        self.assert_products_and_form("REQUESTS", pages["REQUESTS"])


if __name__ == "__main__":
    unittest.main()
