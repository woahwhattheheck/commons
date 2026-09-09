#!/usr/bin/env python3
"""Hermetic: tools.json cash.doors hrefs appear on commerce.html tip shelf."""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TOOLS = ROOT / "tools.json"
COMMERCE = ROOT / "commerce.html"

PRODUCT_RE = re.compile(
    r'href="(\./(?:agent-rescue|dealer-service-lead-rescue|referral-intake-completeness|repair-booking-preflight|plant-downtime-handoff)\.html)"'
)


class CoilCommerceCashDoorsSyncTest(unittest.TestCase):
    def test_cash_doors_on_commerce(self) -> None:
        data = json.loads(TOOLS.read_text(encoding="utf-8"))
        cash = data["cash"]
        doors = [d["href"] for d in cash["doors"]]
        self.assertEqual(cash.get("commerce"), "./commerce.html")
        page = COMMERCE.read_text(encoding="utf-8")
        page_hrefs = set(PRODUCT_RE.findall(page))
        for href in doors:
            self.assertIn(href, page_hrefs, f"cash door {href} missing from commerce.html")
        self.assertEqual(sorted(doors), sorted(page_hrefs))


if __name__ == "__main__":
    unittest.main()
