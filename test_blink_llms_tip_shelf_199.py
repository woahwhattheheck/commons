#!/usr/bin/env python3
"""Hermetic: llms.txt Commercial surfaces $29 Autopsy + four $199 tip-shelf doors."""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LLMS = ROOT / "llms.txt"


class BlinkLlmsTipShelf199Test(unittest.TestCase):
    def test_tip_shelf_doors(self) -> None:
        text = LLMS.read_text(encoding="utf-8")
        commercial = text.split("## Fresh")[0]
        self.assertIn("## Commercial", commercial)
        self.assertIn("agent-rescue.html", commercial)
        self.assertIn("$29", commercial)
        self.assertIn("dealer-service-lead-rescue.html", commercial)
        self.assertIn("referral-intake-completeness.html", commercial)
        self.assertIn("repair-booking-preflight.html", commercial)
        self.assertIn("plant-downtime-handoff.html", commercial)
        self.assertIn("$199", commercial)
        self.assertNotIn("buy.stripe.com", commercial)
        self.assertNotIn("donate.stripe.com", commercial)


if __name__ == "__main__":
    unittest.main()
