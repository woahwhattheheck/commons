#!/usr/bin/env python3
"""Hermetic: tools.json cash object — product pages only."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TOOLS = ROOT / "tools.json"

REQUIRED_HREFS = [
    "./agent-rescue.html",
    "./dealer-service-lead-rescue.html",
    "./referral-intake-completeness.html",
    "./repair-booking-preflight.html",
    "./plant-downtime-handoff.html",
]


class CoilToolsJsonLiveCashTest(unittest.TestCase):
    def test_tools_json_cash_object(self) -> None:
        self.assertTrue(TOOLS.is_file(), "tools.json missing")
        data = json.loads(TOOLS.read_text(encoding="utf-8"))
        cash = data.get("cash")
        self.assertIsInstance(cash, dict)
        self.assertEqual(cash.get("shelf"), "./tools-cash.html")
        doors = cash.get("doors")
        self.assertIsInstance(doors, list)
        self.assertEqual(len(doors), 5)
        hrefs = [d.get("href") for d in doors]
        for href in REQUIRED_HREFS:
            self.assertIn(href, hrefs, f"missing {href}")
        labels = " ".join(str(d.get("label") or "") for d in doors)
        self.assertIn("$29 Autopsy", labels)
        self.assertIn("$199 dealer diagnostic", labels)
        blob = TOOLS.read_text(encoding="utf-8")
        self.assertNotIn("buy.stripe.com", blob)


if __name__ == "__main__":
    unittest.main()
