#!/usr/bin/env python3
"""Hermetic: tools.json cash.larger_fixed present."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TOOLS = ROOT / "tools.json"


class CoilToolsJsonLargerFixedTest(unittest.TestCase):
    def test_larger_fixed(self) -> None:
        data = json.loads(TOOLS.read_text(encoding="utf-8"))
        cash = data["cash"]
        larger = cash["larger_fixed"]
        self.assertIsInstance(larger, list)
        self.assertGreaterEqual(len(larger), 2)
        hrefs = {d.get("href") for d in larger if isinstance(d, dict)}
        self.assertIn("./diagnostic.html", hrefs)
        self.assertIn("./commercial.html", hrefs)


if __name__ == "__main__":
    unittest.main()
