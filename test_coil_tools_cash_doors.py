#!/usr/bin/env python3
"""Hermetic: tools.html surfaces live cash doors to product pages only."""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TOOLS = ROOT / "tools.html"

REQUIRED = [
    'id="cash-doors"',
    "./agent-rescue.html",
    "./dealer-service-lead-rescue.html",
    "./referral-intake-completeness.html",
    "./repair-booking-preflight.html",
    "./plant-downtime-handoff.html",
    "$29 Autopsy checkout",
    "$199 dealer diagnostic",
]


class CoilToolsCashDoorsTest(unittest.TestCase):
    def test_tools_cash_shelf(self) -> None:
        self.assertTrue(TOOLS.is_file(), "tools.html missing")
        text = TOOLS.read_text(encoding="utf-8")
        for needle in REQUIRED:
            self.assertIn(needle, text, f"missing {needle}")
        cash = text.split('id="cash-doors"', 1)[1].split("</section>", 1)[0]
        self.assertNotIn("buy.stripe.com", cash)


if __name__ == "__main__":
    unittest.main()
