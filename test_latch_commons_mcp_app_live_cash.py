#!/usr/bin/env python3
"""Hermetic: commons_mcp_app.html Live cash."""
from __future__ import annotations
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parent
PAGE = ROOT / "commons_mcp_app.html"
REQUIRED = ['id="live-cash"', "./agent-rescue.html", "./dealer-service-lead-rescue.html", "./referral-intake-completeness.html", "./repair-booking-preflight.html", "./plant-downtime-handoff.html", "$29 Autopsy", "$199 dealer diagnostic"]
class LatchCommonsMcpAppLiveCashTest(unittest.TestCase):
    def test_direct_product_doors(self) -> None:
        text = PAGE.read_text(encoding="utf-8")
        for n in REQUIRED: self.assertIn(n, text)
        self.assertNotIn("buy.stripe.com", text)
        self.assertNotIn("tools-cash.html", text)
if __name__ == "__main__":
    unittest.main()
