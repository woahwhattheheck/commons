#!/usr/bin/env python3
"""Hermetic checks for the Agent Survival X landscape card (FORGE)."""
from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CARD = ROOT / "agent-rescue-x-card.html"
PAGE = ROOT / "agent-rescue.html"

HEADLINE = "One scoped agent failure. A working recovery proof."
LIMITS = (
    "One business day is the delivery window for one agreed failure. "
    "This is not a certification that your production agent runs reliably for 24 hours."
)
SLOT = (
    "If the link says it is no longer active, the slot is taken; "
    "send the sentence by email and you are next."
)


class AgentRescueXCardTests(unittest.TestCase):
    def test_card_carries_sextant_headline_limits_and_slot_line(self):
        html = CARD.read_text(encoding="utf-8")
        self.assertIn(HEADLINE, html)
        self.assertIn(LIMITS, html)
        self.assertIn(SLOT, html)
        self.assertIn("$2,500", html)
        self.assertIn("1200px", html)
        self.assertIn("628px", html)
        # Static card: no remote scripts, fetch, or tracking pixels.
        self.assertNotIn("<script", html.lower())
        self.assertNotIn("http://", html.replace("http-equiv", ""))
        self.assertNotIn("https://", html)
        self.assertNotIn("fetch(", html)
        page = PAGE.read_text(encoding="utf-8")
        self.assertIn(HEADLINE, page)
        self.assertIn(LIMITS, page)


if __name__ == "__main__":
    unittest.main()
