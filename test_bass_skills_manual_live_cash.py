#!/usr/bin/env python3
"""Hermetic: skills/MANUAL.md surfaces live Autopsy + $199 product doors."""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MANUAL = ROOT / "skills" / "MANUAL.md"


class BassSkillsManualLiveCashTest(unittest.TestCase):
    def test_live_cash_section(self) -> None:
        text = MANUAL.read_text(encoding="utf-8")
        self.assertIn("## Live cash", text)
        self.assertIn("agent-rescue.html", text)
        self.assertIn("$29", text)
        self.assertIn("dealer-service-lead-rescue.html", text)
        self.assertIn("referral-intake-completeness.html", text)
        self.assertIn("repair-booking-preflight.html", text)
        self.assertIn("plant-downtime-handoff.html", text)
        self.assertNotIn("buy.stripe.com", text)
        self.assertNotIn("donate.stripe.com", text)


if __name__ == "__main__":
    unittest.main()
