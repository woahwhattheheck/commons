#!/usr/bin/env python3
"""Hermetic: interconnect.html live cash product-page doors.

CONVERT MONEY SHIP reuses two existing live buy.stripe.com Payment Links on
the first-screen convert shelf. Those URLs stay out of #live-cash. Cite
anvil-opendoor-interconnect-convert-shelf-20260917-01 · type-expertise-
interconnect-convert-shelf-20260917-01 · bass live-cash doors — do not remint.
Compose: page-wide buy.stripe.com ban becomes section-scoped.
"""
from __future__ import annotations
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parent
PAGE = ROOT / "interconnect.html"
class BassInterconnectLiveCashTest(unittest.TestCase):
    def test_live_cash(self) -> None:
        text = PAGE.read_text(encoding="utf-8")
        self.assertIn('id="live-cash"', text)
        self.assertIn("agent-rescue.html", text)
        self.assertIn("dealer-service-lead-rescue.html", text)
        self.assertIn("referral-intake-completeness.html", text)
        self.assertIn("repair-booking-preflight.html", text)
        self.assertIn("plant-downtime-handoff.html", text)
        live_cash = text.split('id="live-cash"', 1)[1].split("</section>", 1)[0]
        self.assertNotIn("buy.stripe.com", live_cash)
        self.assertIn("https://buy.stripe.com/4gM9AS3Ot8bfeOZ78S43S0g", text)
        self.assertIn("https://buy.stripe.com/8x27sK2Kp3UZ9uF2SC43S07", text)
if __name__ == "__main__":
    unittest.main()
