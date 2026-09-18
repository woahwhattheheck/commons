#!/usr/bin/env python3
"""Hermetic: land.html Live cash surfaces four $199 tip-shelf doors."""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DOC = ROOT / "land.html"


class BlinkLandHtmlLiveCashTest(unittest.TestCase):
    def test_live_cash(self) -> None:
        text = DOC.read_text(encoding="utf-8")
        self.assertIn('id="live-cash"', text)


        self.assertIn("dealer-service-lead-rescue.html", text)
        self.assertIn("referral-intake-completeness.html", text)
        self.assertIn("repair-booking-preflight.html", text)
        self.assertIn("plant-downtime-handoff.html", text)
        self.assertIn("$199", text)
        live_cash = text.split('id="live-cash"', 1)[1]
        live_cash = live_cash.split("</section>", 1)[0]
        self.assertNotIn("buy.stripe.com", live_cash)


if __name__ == "__main__":
    unittest.main()
