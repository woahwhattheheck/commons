"""type-ground-subzero-c-md-keep-larger-fixed-20260916-01 — KEEP Larger on SUBZERO ISPN–RECEIPT."""
from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PATHS = (
    "ground/SUBZERO_ISPN.md",
    "ground/SUBZERO_LVIN.md",
    "ground/SUBZERO_MINDS.md",
    "ground/SUBZERO_PDAP.md",
    "ground/SUBZERO_PETR.md",
    "ground/SUBZERO_POTS.md",
    "ground/SUBZERO_PRED.md",
    "ground/SUBZERO_PROOF.md",
    "ground/SUBZERO_QUOTE.md",
    "ground/SUBZERO_RECEIPT.md",
)


class TestTypeGroundSubzeroCMdKeepLargerFixed2026091601(unittest.TestCase):
    def test_tip_doors_have_autopsy_and_larger(self):
        for rel in PATHS:
            text = (ROOT / rel).read_text(encoding="utf-8")
            self.assertIn("## Live cash", text, rel)
            self.assertIn("../agent-rescue.html", text, rel)
            self.assertIn("Larger fixed engagements", text, rel)
            self.assertIn("../diagnostic.html", text, rel)
            self.assertIn("../commercial.html", text, rel)
            self.assertNotIn("buy.stripe.com", text, rel)

    def test_product_pages_exist(self):
        for name in ("agent-rescue.html", "diagnostic.html", "commercial.html"):
            self.assertTrue((ROOT / name).is_file(), name)


if __name__ == "__main__":
    unittest.main()
