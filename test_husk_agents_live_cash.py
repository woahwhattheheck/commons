#!/usr/bin/env python3
"""Hermetic: AGENTS.md surfaces Autopsy $29 + four $199 product pages."""
from __future__ import annotations
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parent
AGENTS = ROOT / "AGENTS.md"
PRODUCT = (
    "agent-rescue.html",
    "dealer-service-lead-rescue.html",
    "referral-intake-completeness.html",
    "repair-booking-preflight.html",
    "plant-downtime-handoff.html",
)
class HuskAgentsLiveCashTest(unittest.TestCase):
    def test_agents_md_live_cash(self) -> None:
        text = AGENTS.read_text(encoding="utf-8")
        self.assertIn("## Live cash", text)
        self.assertIn("Autopsy", text)
        self.assertIn("$29", text)
        for m in PRODUCT:
            self.assertIn(m, text)
        self.assertNotIn("$2500", text)
        self.assertNotIn("buy.stripe.com", text)
if __name__ == "__main__":
    unittest.main()
