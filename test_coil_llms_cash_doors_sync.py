#!/usr/bin/env python3
"""Hermetic: llms.txt Commercial product pages match tools.json cash.doors."""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TOOLS = ROOT / "tools.json"
LLMS = ROOT / "llms.txt"

PRODUCT_BASENAMES = {
    "agent-rescue.html",
    "dealer-service-lead-rescue.html",
    "referral-intake-completeness.html",
    "repair-booking-preflight.html",
    "plant-downtime-handoff.html",
}


class CoilLlmsCashDoorsSyncTest(unittest.TestCase):
    def test_llms_commercial_matches_doors(self) -> None:
        doors = json.loads(TOOLS.read_text(encoding="utf-8"))["cash"]["doors"]
        door_bases = {d["href"].lstrip("./") for d in doors}
        self.assertEqual(door_bases, PRODUCT_BASENAMES)
        text = LLMS.read_text(encoding="utf-8")
        self.assertIn("## Commercial", text)
        section = text.split("## Commercial", 1)[1].split("##", 1)[0]
        hrefs = re.findall(r"/commons/([a-z0-9-]+\.html)", section)
        product = {h for h in hrefs if h in PRODUCT_BASENAMES}
        self.assertEqual(product, door_bases, "llms.txt Commercial drifted from tools.json cash.doors")


if __name__ == "__main__":
    unittest.main()
