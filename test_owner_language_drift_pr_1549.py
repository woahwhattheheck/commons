#!/usr/bin/env python3
"""Canary: PR 1549 owner phrases are present on live DIRECTIVES.md."""

from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
DIRECTIVES = ROOT / "DIRECTIVES.md"
RECEIPT = ROOT / "p" / "owner-language-drift-pr-1549-20260830-01.md"

PHRASE_SWARM = "not only Bryce language models"
PHRASE_PIN = "pin every remaining owner wall while Bryce is moving"
PHRASE_PREP = (
    "Do useful nonprivileged prep, measurements, and specs around them "
    "without repeatedly repinging Bryce."
)
DRIFTED_PREP = (
    "Do useful nonprivileged prep, measurements, specs, and bounded choices "
    "without repeatedly repinging Bryce."
)


class OwnerLanguageDriftPr1549Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = DIRECTIVES.read_text(encoding="utf-8")
        cls.item19 = cls.text.split("### 19. Agent Swarm", 1)[1].split("### 20.", 1)[0]
        cls.item20 = cls.text.split("### 20. Pending Owner Walls", 1)[1].split("\n## ", 1)[0]

    def test_both_exact_owner_phrases_are_present(self):
        self.assertIn(PHRASE_SWARM, self.text)
        self.assertIn(PHRASE_PIN, self.text)
        self.assertIn(PHRASE_PREP, self.text)

    def test_swarm_phrase_sits_on_item_19(self):
        self.assertIn(PHRASE_SWARM, self.item19)
        self.assertIn(
            "local intelligences—not only Bryce language models—running",
            self.item19,
        )

    def test_catch_all_sits_on_item_20_and_peers_pick_stays(self):
        self.assertIn(PHRASE_PIN, self.item20)
        self.assertIn(PHRASE_PREP, self.item20)
        self.assertNotIn(DRIFTED_PREP, self.item20)
        self.assertIn("peers choose the most optimal value", self.item20)
        self.assertIn("demon-pick-pfc-model-load-20260830-01", self.item20)

    def test_eight_walls_are_not_converted_as_a_lump(self):
        for wall in (
            "header @184 yes/no",
            "exact PFC model/load choice",
            "cure-fold first target",
            "clock fanout/autofab",
            "inbox path",
            "feature-film organ",
            "next compression organ",
            "missing-letter path",
        ):
            self.assertIn(wall, self.item20)

    def test_receipt_is_the_named_leftover_id(self):
        self.assertTrue(RECEIPT.is_file())
        receipt = RECEIPT.read_text(encoding="utf-8")
        self.assertIn("id: owner-language-drift-pr-1549-20260830-01", receipt)
        self.assertIn(PHRASE_SWARM, receipt)
        self.assertIn(PHRASE_PIN, receipt)
        self.assertIn(PHRASE_PREP, receipt)


if __name__ == "__main__":
    unittest.main()
