from __future__ import annotations

import unittest
from pathlib import Path

import hub_pages
import board_ingest


ROOT = Path(__file__).parent


class FeaturesBoardTests(unittest.TestCase):
    def test_features_is_a_head_backed_lane(self):
        self.assertIn("FEATURES", hub_pages.LANE_BOARDS)
        self.assertIn("FEATURES", hub_pages.LANE_HEAD_BOARDS)
        self.assertIn("FEATURES", hub_pages.LANE_BLURB)

    def test_composer_can_route_to_features(self):
        form = hub_pages.say_form("TABLE", "FEATURES")
        self.assertIn("<option selected>FEATURES</option>", form)

    def test_generated_board_and_directory_link_exist(self):
        page = (ROOT / "features.html").read_text(encoding="utf-8")
        boards = (ROOT / "boards.html").read_text(encoding="utf-8")
        index = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertIn('data-lane="FEATURES"', page)
        self.assertIn("lane=FEATURES", page)
        self.assertIn('href="./features.html">new features</a>', boards)
        self.assertIn('class="door-btn" href="./features.html"', index)
        self.assertIn("<option>FEATURES</option>", index)
        self.assertIn("features.html", board_ingest.ASSET_PATHS)


if __name__ == "__main__":
    unittest.main()
