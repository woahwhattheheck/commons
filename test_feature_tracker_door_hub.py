#!/usr/bin/env python3
"""Landing hub must surface the feature-tracker door.

PR 4968 cataloged feature-tracker.html on boards.html without adding it
to door.js / the no-JS index hub. test_door_hub.js failed:
"hub surfaces every HTML door cataloged by boards.html: feature-tracker.html".
Later hub_pages regen dropped the catalog row because the generator was
never updated. Keep the Use-tab chip next to resources, and keep the
boards catalog row so ingest cannot erase the door.
"""
from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
NEEDLE_JS = '["feature-tracker.html", "feature tracker"]'
NEEDLE_HUB = 'href="./feature-tracker.html">feature tracker</a>'
NEEDLE_BOARDS = 'href="./feature-tracker.html">FEATURE TRACKER</a>'


class FeatureTrackerDoorHubTests(unittest.TestCase):
    def test_door_js_and_index_surface_feature_tracker(self) -> None:
        door = (ROOT / "door.js").read_text(encoding="utf-8")
        index = (ROOT / "index.html").read_text(encoding="utf-8")
        boards = (ROOT / "boards.html").read_text(encoding="utf-8")
        self.assertIn(NEEDLE_JS, door)
        self.assertIn(NEEDLE_HUB, index)
        self.assertIn(NEEDLE_BOARDS, boards)
        self.assertTrue((ROOT / "feature-tracker.html").is_file())


if __name__ == "__main__":
    unittest.main()
