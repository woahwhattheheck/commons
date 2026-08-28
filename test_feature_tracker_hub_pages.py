#!/usr/bin/env python3
"""boards.html is generated from hub_pages.py.

Hand-editing the bake is reverted on the next ingest
(hub_pages.py BAILIFF 2026-08-20). Keep the feature tracker door in the
generator so the catalog chip survives.
"""
from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
NEEDLE = 'href="./feature-tracker.html">FEATURE TRACKER</a>'


class FeatureTrackerHubPagesTests(unittest.TestCase):
    def test_generator_and_boards_keep_feature_tracker_door(self):
        gen = (ROOT / "hub_pages.py").read_text(encoding="utf-8")
        boards = (ROOT / "boards.html").read_text(encoding="utf-8")
        self.assertIn(NEEDLE, gen)
        self.assertIn(NEEDLE, boards)

    def test_feature_tracker_html_exists(self):
        self.assertTrue((ROOT / "feature-tracker.html").is_file())


if __name__ == "__main__":
    unittest.main()
