"""type-ground-subzero-md-keep-larger-fixed-20260916-01 — KEEP Larger on SUBZERO doors."""
from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PATHS = (
    "ground/SUBZERO_BUYERS.md",
    "ground/SUBZERO_BYZQ.md",
    "ground/SUBZERO_CENSUS.md",
    "ground/SUBZERO_CHFS.md",
    "ground/SUBZERO_CHGS.md",
    "ground/SUBZERO_CHHS.md",
    "ground/SUBZERO_CHIH.md",
    "ground/SUBZERO_CHLS.md",
    "ground/SUBZERO_CHPD.md",
    "ground/SUBZERO_CHPR.md",
)


class TestTypeGroundSubzeroMdKeepLargerFixed2026091601(unittest.TestCase):
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
        for name in ("diagnostic.html", "commercial.html"):
            self.assertTrue((ROOT / name).is_file(), name)


if __name__ == "__main__":
    unittest.main()
