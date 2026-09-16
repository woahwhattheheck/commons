"""KEEP: commercial/expertise/diagnostic carry exactly one Larger-fixed note."""
from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DOORS = (
    "commercial.html",
    "expertise.html",
    "diagnostic.html",
)
NOTE = "Larger fixed engagements"
H1 = 'href="./diagnostic.html"'
H2 = 'href="./commercial.html"'
SKU1 = "GGUF diagnostic · $12,000 / 10 days"
SKU2 = "White Box pilot · $30,000 / 30 days"


class ReedCommercialExpertiseDiagnosticLargerFixedTests(unittest.TestCase):
    def test_exactly_one_note_with_both_larger_skus(self) -> None:
        for name in DOORS:
            with self.subTest(page=name):
                text = (ROOT / name).read_text(encoding="utf-8")
                self.assertEqual(text.count(NOTE), 1, name)
                self.assertIn(H1, text)
                self.assertIn(H2, text)
                self.assertIn(SKU1, text)
                self.assertIn(SKU2, text)
                self.assertIn("Not remints of tip SKUs", text)
                self.assertNotIn("buy.stripe.com", text.split(NOTE, 1)[1][:800])


if __name__ == "__main__":
    unittest.main()
