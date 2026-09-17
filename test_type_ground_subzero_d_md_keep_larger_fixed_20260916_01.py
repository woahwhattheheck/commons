"""type-ground-subzero-d-md-keep-larger-fixed-20260916-01 — KEEP Larger on SUBZERO RGCG–WALK."""
from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PATHS = (
    "ground/SUBZERO_RGCG.md",
    "ground/SUBZERO_SDMK.md",
    "ground/SUBZERO_SOCR.md",
    "ground/SUBZERO_STIG.md",
    "ground/SUBZERO_SYND.md",
    "ground/SUBZERO_TECH.md",
    "ground/SUBZERO_TITAN_PACKET.md",
    "ground/SUBZERO_TITF.md",
    "ground/SUBZERO_TITM.md",
    "ground/SUBZERO_TITX.md",
    "ground/SUBZERO_TSET.md",
    "ground/SUBZERO_WALK.md",
)


class TestTypeGroundSubzeroDMdKeepLargerFixed2026091601(unittest.TestCase):
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
