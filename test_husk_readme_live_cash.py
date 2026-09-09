#!/usr/bin/env python3
from __future__ import annotations
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parent
DOC = ROOT / "README.md"
PRODUCT = (
    "agent-rescue.html",
    "dealer-service-lead-rescue.html",
    "referral-intake-completeness.html",
    "repair-booking-preflight.html",
    "plant-downtime-handoff.html",
)
class HuskReadmeLiveCashTest(unittest.TestCase):
    def test_readme_live_cash(self) -> None:
        text = DOC.read_text(encoding="utf-8")
        self.assertIn("## Live cash", text)
        self.assertIn("Autopsy", text)
        self.assertIn("$29", text)
        for m in PRODUCT:
            self.assertIn(m, text)
        self.assertNotIn("buy.stripe.com", text)
if __name__ == "__main__":
    unittest.main()
