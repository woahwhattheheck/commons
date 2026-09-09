#!/usr/bin/env python3
"""Hermetic: START.md Live cash product hrefs match tools.json cash.doors."""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TOOLS = ROOT / "tools.json"
START = ROOT / "START.md"

PRODUCT_BASENAMES = {
    "agent-rescue.html",
    "dealer-service-lead-rescue.html",
    "referral-intake-completeness.html",
    "repair-booking-preflight.html",
    "plant-downtime-handoff.html",
}


class CoilStartCashDoorsSyncTest(unittest.TestCase):
    def test_start_live_cash_matches_doors(self) -> None:
        doors = json.loads(TOOLS.read_text(encoding="utf-8"))["cash"]["doors"]
        door_bases = {d["href"].lstrip("./") for d in doors}
        self.assertEqual(door_bases, PRODUCT_BASENAMES)
        text = START.read_text(encoding="utf-8")
        self.assertIn("## Live cash", text)
        section = text.split("## Live cash", 1)[1].split("##", 1)[0]
        hrefs = re.findall(r"\((?:\./)?([a-z0-9-]+\.html)\)", section)
        product = {h for h in hrefs if h in PRODUCT_BASENAMES}
        self.assertEqual(product, door_bases, "START Live cash drifted from tools.json cash.doors")


if __name__ == "__main__":
    unittest.main()
