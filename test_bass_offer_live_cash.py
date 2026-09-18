#!/usr/bin/env python3
"""Hermetic: offer.html surfaces live $199 product doors."""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OFFER = ROOT / "offer.html"


class BassOfferLiveCashTest(unittest.TestCase):
    def test_live_cash_section(self) -> None:
        text = OFFER.read_text(encoding="utf-8")
        self.assertIn('id="live-cash"', text)


        self.assertIn("dealer-service-lead-rescue.html", text)
        self.assertIn("referral-intake-completeness.html", text)
        self.assertIn("repair-booking-preflight.html", text)
        self.assertIn("plant-downtime-handoff.html", text)
        self.assertNotIn("buy.stripe.com", text.split('id="live-cash"', 1)[1].split('</section>', 1)[0])
        self.assertNotIn("donate.stripe.com", text)


if __name__ == "__main__":
    unittest.main()
