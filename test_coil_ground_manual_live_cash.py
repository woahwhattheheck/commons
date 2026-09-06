#!/usr/bin/env python3
"""Hermetic: ground/MANUAL.md live cash section — product pages only."""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MANUAL = ROOT / "ground" / "MANUAL.md"

REQUIRED = [
    "## Live cash",
    "../agent-rescue.html",
    "../dealer-service-lead-rescue.html",
    "../referral-intake-completeness.html",
    "../repair-booking-preflight.html",
    "../plant-downtime-handoff.html",
    "$29 Autopsy",
    "$199 dealer diagnostic",
]


class CoilGroundManualLiveCashTest(unittest.TestCase):
    def test_manual_has_live_cash_section(self) -> None:
        self.assertTrue(MANUAL.is_file(), "ground/MANUAL.md missing")
        text = MANUAL.read_text(encoding="utf-8")
        for needle in REQUIRED:
            self.assertIn(needle, text, f"missing {needle}")
        self.assertNotIn("buy.stripe.com", text)
        # section appears before File a job
        self.assertLess(text.index("## Live cash"), text.index("## File a job"))


if __name__ == "__main__":
    unittest.main()
