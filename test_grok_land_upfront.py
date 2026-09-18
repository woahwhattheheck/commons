#!/usr/bin/env python3
"""Grok-facing memory and pins carry land-upfront so groks do not leave unique leftovers off main."""
from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent

LAND = "Land unique work on current main in the same turn you build it."
SKIP = "No skip lists of unique bytes."
BLOCK = "If something blocks that land, fix the blocker then put it on main."
MOVES = "Main moves under you."

GROK_FACING = (
    "AGENTS.md",
    "START.md",
    "ENTRY.md",
    "memory/LAW.md",
    "memory/GROK_LAND_UPFRONT.md",
    "ground/LAND.md",
    "ground/GROK_LAND_UPFRONT.md",
    "ground/EXECUTE.md",
    ".agents/skills/commons-worker/SKILL.md",
)


class TestGrokLandUpfront(unittest.TestCase):
    def test_every_grok_facing_file_carries_the_land_sentence(self):
        missing = []
        for rel in GROK_FACING:
            text = (ROOT / rel).read_text(encoding="utf-8")
            if LAND not in text:
                missing.append(rel)
        self.assertEqual(missing, [], missing)

    def test_pins_and_cards_carry_skip_block_moves(self):
        for rel in (
            "AGENTS.md",
            "START.md",
            "ENTRY.md",
            "memory/LAW.md",
            "memory/GROK_LAND_UPFRONT.md",
            "ground/LAND.md",
            "ground/GROK_LAND_UPFRONT.md",
            "ground/EXECUTE.md",
        ):
            text = (ROOT / rel).read_text(encoding="utf-8")
            self.assertIn(SKIP, text, rel)
            self.assertIn(BLOCK, text, rel)
            self.assertIn(MOVES, text, rel)

    def test_execute_now_still_sits_above_the_action_pad(self):
        law = "Do not ask if I want you to do something"
        pad = "ACTION PAD IS AN UNRESTRICTED OPEN DOOR"
        for rel in ("START.md", "AGENTS.md", "ENTRY.md"):
            text = (ROOT / rel).read_text(encoding="utf-8")
            self.assertLess(text.index(law), text.index(pad), rel)

    def test_card_does_not_remint_named_grok_leftovers(self):
        card = (ROOT / "ground/GROK_LAND_UPFRONT.md").read_text(encoding="utf-8")
        for name in (
            "GROK_HYGIENE",
            "GROK_HARNESS",
            "GROK_RECEIPT",
            "SUPERGROK_HEAVY",
            "GROK_ROUTE",
        ):
            self.assertIn("Do not remint", card)
            self.assertIn(name, card)


if __name__ == "__main__":
    unittest.main()
