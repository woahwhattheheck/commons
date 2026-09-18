#!/usr/bin/env python3
"""Hermetic: bazaar.html surfaces live $199 product doors."""
from __future__ import annotations
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parent
PAGE = ROOT / "bazaar.html"
class BassBazaarLiveCashTest(unittest.TestCase):
    def test_live_cash(self) -> None:
        text = PAGE.read_text(encoding="utf-8")
        self.assertIn('id="live-cash"', text)


        self.assertIn("dealer-service-lead-rescue.html", text)
        self.assertIn("referral-intake-completeness.html", text)
        self.assertIn("repair-booking-preflight.html", text)
        self.assertIn("plant-downtime-handoff.html", text)
        self.assertIn('id="buy-now-live-checkout"', text)
        # Convert shelf may reuse existing live buys; exact allowlist is
        # test_type_tools_cash_bazaar_convert_shelf_20260917_01.py.
if __name__ == "__main__":
    unittest.main()
