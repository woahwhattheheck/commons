#!/usr/bin/env python3
"""boards.html is generated from hub_pages.py.

Keep the unbuilt-items door, plus the already-landed data-license and
arbitrage doors, in the generator so the catalog chips survive ingest.
"""
from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent


class UnbuiltItemsHubPagesTests(unittest.TestCase):
    def test_generator_and_boards_keep_unbuilt_and_landed_doors(self):
        gen = (ROOT / "hub_pages.py").read_text(encoding="utf-8")
        boards = (ROOT / "boards.html").read_text(encoding="utf-8")
        for needle in (
            'href="./unbuilt-items.html">UNBUILT ITEMS</a>',
            'href="./data-license.html">data licensing</a>',
            'href="./arbitrage.html">arbitrage scout</a>',
        ):
            self.assertIn(needle, gen, needle)
            self.assertIn(needle, boards, needle)

    def test_door_files_exist(self):
        self.assertTrue((ROOT / "unbuilt-items.html").is_file())
        self.assertTrue((ROOT / "data-license.html").is_file())
        self.assertTrue((ROOT / "arbitrage.html").is_file())


if __name__ == "__main__":
    unittest.main()
