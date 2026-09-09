#!/usr/bin/env python3
"""Hermetic: gpt-grok-ship-loop.html live cash doors."""
from __future__ import annotations
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parent
PAGE = ROOT / "gpt-grok-ship-loop.html"
class BassGptGrokShipLoopLiveCashTest(unittest.TestCase):
    def test_live_cash(self) -> None:
        text = PAGE.read_text(encoding="utf-8")
        self.assertIn('id="live-cash"', text)
        self.assertIn("agent-rescue.html", text)
        self.assertIn("dealer-service-lead-rescue.html", text)
        self.assertIn("referral-intake-completeness.html", text)
        self.assertIn("repair-booking-preflight.html", text)
        self.assertIn("plant-downtime-handoff.html", text)
        self.assertNotIn("buy.stripe.com", text)
if __name__ == "__main__":
    unittest.main()
