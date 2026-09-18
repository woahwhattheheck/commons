#!/usr/bin/env python3
"""Hermetic: tip $199/$199 doors keep exactly one Larger-fixed note.

Regression for 9a8d1ebe, which reminted a second note on doors that already
carried Reed/moth Larger-fixed bytes. Compose keeps the unique shelf cite
(commerce.html · tools-cash.html) and id=larger-fixed without duplicating
the commercial paragraph. Tip KEEP. Hands off #8802.
"""
from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DOORS = (
    "dealer-service-lead-rescue.html",
    "referral-intake-completeness.html",
    "repair-booking-preflight.html",
    "plant-downtime-handoff.html",
)
NOTE = "Larger fixed engagements"
H1 = 'href="./diagnostic.html"'
H2 = 'href="./commercial.html"'
H3 = 'href="./commerce.html"'
H4 = 'href="./tools-cash.html"'
SKU1 = "GGUF diagnostic · $12,000 / 10 days"
SKU2 = "White Box pilot · $30,000 / 30 days"


class TipProductDoorsLargerFixedTests(unittest.TestCase):
    def test_exactly_one_composed_note_per_door(self) -> None:
        for name in DOORS:
            with self.subTest(page=name):
                text = (ROOT / name).read_text(encoding="utf-8")
                self.assertEqual(text.count(NOTE), 1, name)
                self.assertEqual(text.count('id="larger-fixed"'), 1, name)
                self.assertIn(H1, text)
                self.assertIn(H2, text)
                self.assertIn(H3, text)
                self.assertIn(H4, text)
                self.assertIn(SKU1, text)
                self.assertIn(SKU2, text)
                self.assertIn("Not remints of tip SKUs", text)


if __name__ == "__main__":
    unittest.main()
