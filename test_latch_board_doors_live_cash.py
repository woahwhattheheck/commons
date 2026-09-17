#!/usr/bin/env python3
"""Hermetic: board doors Live cash."""
from __future__ import annotations
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parent
PAGES = ['annex.html', 'archive.html', 'books.html', 'claims.html', '8bit.html']
REQUIRED = ['id="live-cash"', "./agent-rescue.html", "./dealer-service-lead-rescue.html", "./referral-intake-completeness.html", "./repair-booking-preflight.html", "./plant-downtime-handoff.html", "$29 Autopsy", "$199 dealer diagnostic"]
class LatchBoardDoorsLiveCashTest(unittest.TestCase):
    def test_all(self) -> None:
        for name in PAGES:
            with self.subTest(page=name):
                text = (ROOT / name).read_text(encoding="utf-8")
                for n in REQUIRED:
                    self.assertIn(n, text, f"{name} missing {n}")
                if name in ("claims.html", "annex.html", "archive.html"):
                    # Convert shelf reuses existing live buys; Live cash product-page
                    # doors stay relative (wire-opportunity-claims / latch-annex-archive).
                    live_cash = text.split('id="live-cash"', 1)[1].split("</section>", 1)[0]
                    self.assertNotIn("buy.stripe.com", live_cash)
                else:
                    self.assertNotIn("buy.stripe.com", text)
                self.assertNotIn("tools-cash.html", text)
if __name__ == "__main__":
    unittest.main()
