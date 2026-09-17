#!/usr/bin/env python3
"""Hermetic: misc board doors Live cash batch 2."""
from __future__ import annotations
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parent
PAGES = ['8walk.html', 'autogtm.html', 'claudes.html']
REQUIRED = ['id="live-cash"', "./agent-rescue.html", "./dealer-service-lead-rescue.html", "./referral-intake-completeness.html", "./repair-booking-preflight.html", "./plant-downtime-handoff.html", "$29 Autopsy", "$199 dealer diagnostic"]
class LatchMiscDoorsLiveCashTest(unittest.TestCase):
    def test_all(self) -> None:
        for name in PAGES:
            with self.subTest(page=name):
                text = (ROOT / name).read_text(encoding="utf-8")
                for n in REQUIRED:
                    self.assertIn(n, text, f"{name} missing {n}")
                if name == "8walk.html":
                    # Convert shelf reuses existing live buys; Live cash product-page
                    # doors stay relative (latch-8bit-8walk-convert-shelf-20260917-01).
                    live_cash = text.split('id="live-cash"', 1)[1].split("</section>", 1)[0]
                    self.assertNotIn("buy.stripe.com", live_cash)
                else:
                    self.assertNotIn("buy.stripe.com", text)
                self.assertNotIn("tools-cash.html", text)
if __name__ == "__main__":
    unittest.main()
