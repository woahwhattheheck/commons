#!/usr/bin/env python3
"""Hermetic: trust.html surfaces live Autopsy + $199 product doors."""
from __future__ import annotations
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parent
PAGE = ROOT / "trust.html"
class BassTrustLiveCashTest(unittest.TestCase):
    def test_live_cash(self) -> None:
        text = PAGE.read_text(encoding="utf-8")
        self.assertIn('id="live-cash"', text)
        self.assertIn("agent-rescue.html", text)
        self.assertIn("$29", text)
        self.assertIn("dealer-service-lead-rescue.html", text)
        self.assertIn("referral-intake-completeness.html", text)
        self.assertIn("repair-booking-preflight.html", text)
        self.assertIn("plant-downtime-handoff.html", text)
        self.assertIn('id="buy-now-live-checkout"', text)
        # Convert shelf reuses existing live buys; Live cash product-page
        # doors stay relative (type-trust-topics-convert-shelf-20260917-01).
        live_cash = text.split('id="live-cash"', 1)[1].split("</section>", 1)[0]
        self.assertNotIn("buy.stripe.com", live_cash)
if __name__ == "__main__":
    unittest.main()
