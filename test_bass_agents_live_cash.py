#!/usr/bin/env python3
"""Hermetic: AGENTS.md Commercial ladder surfaces $29 Autopsy + four $199 tip-shelf doors."""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
AGENTS = ROOT / "AGENTS.md"


class BassAgentsLiveCashTest(unittest.TestCase):
    def test_tip_shelf_doors(self) -> None:
        text = AGENTS.read_text(encoding="utf-8")
        self.assertIn("## Commercial ladder", text)
        self.assertIn("agent-rescue.html", text)
        self.assertIn("$29", text)
        self.assertIn("dealer-service-lead-rescue.html", text)
        self.assertIn("referral-intake-completeness.html", text)
        self.assertIn("repair-booking-preflight.html", text)
        self.assertIn("plant-downtime-handoff.html", text)
        self.assertIn("$199", text)
        self.assertNotIn("buy.stripe.com", text)
        self.assertNotIn("donate.stripe.com", text)


if __name__ == "__main__":
    unittest.main()
