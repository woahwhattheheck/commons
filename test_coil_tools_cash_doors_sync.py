#!/usr/bin/env python3
"""Hermetic: tools.json cash.doors hrefs match tools-cash.html product links."""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TOOLS = ROOT / "tools.json"
SHELF = ROOT / "tools-cash.html"

# product pages (not nav)
PRODUCT_RE = re.compile(
    r'href="(\./(?:agent-rescue|dealer-service-lead-rescue|referral-intake-completeness|repair-booking-preflight|plant-downtime-handoff)\.html)"'
)


class CoilToolsCashDoorsSyncTest(unittest.TestCase):
    def test_cash_doors_match_shelf(self) -> None:
        data = json.loads(TOOLS.read_text(encoding="utf-8"))
        cash = data.get("cash")
        self.assertIsInstance(cash, dict)
        doors = cash.get("doors")
        self.assertIsInstance(doors, list)
        self.assertGreaterEqual(len(doors), 5)
        hrefs = [d["href"] for d in doors]
        self.assertEqual(len(hrefs), len(set(hrefs)), "duplicate cash door href")
        shelf = SHELF.read_text(encoding="utf-8")
        shelf_hrefs = PRODUCT_RE.findall(shelf)
        self.assertEqual(sorted(hrefs), sorted(set(shelf_hrefs)), "tools.json cash.doors drifted from tools-cash.html")
        self.assertEqual(cash.get("shelf"), "./tools-cash.html")


if __name__ == "__main__":
    unittest.main()
