#!/usr/bin/env python3
"""Hermetic: tools.json cash.shelf / commerce / doors hrefs resolve to files."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TOOLS = ROOT / "tools.json"


class CoilToolsCashPathsTest(unittest.TestCase):
    def test_cash_paths_exist(self) -> None:
        cash = json.loads(TOOLS.read_text(encoding="utf-8"))["cash"]
        shelf = cash["shelf"]
        commerce = cash["commerce"]
        self.assertTrue(shelf.startswith("./"))
        self.assertTrue(commerce.startswith("./"))
        self.assertTrue((ROOT / shelf[2:]).is_file(), f"missing shelf {shelf}")
        self.assertTrue((ROOT / commerce[2:]).is_file(), f"missing commerce {commerce}")
        for door in cash["doors"]:
            href = door["href"]
            self.assertTrue(href.startswith("./"), href)
            self.assertTrue((ROOT / href[2:]).is_file(), f"missing door {href}")
            self.assertIn("label", door)
            self.assertIn("sku", door)


if __name__ == "__main__":
    unittest.main()
