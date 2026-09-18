"""type-ground-spec-steal-md-keep-larger-fixed-20260916-01."""
from __future__ import annotations
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parent
PATHS = (
    "ground/SPECTER_FINAL.md",
    "ground/SPEC_DADDY_STUDY.md",
    "ground/SPEC_DATA.md",
    "ground/STALE_MANIFEST.md",
    "ground/STALE_SPEC.md",
    "ground/STEALABLE_LANES.md",
    "ground/STEALABLE_ROLES.md",
    "ground/STRANDED_MAP.md",
    "ground/RESOURCES_TAB.md",
    "ground/SHARED_ONE.md",
)
class TestTypeGroundSpecStealMdKeepLargerFixed2026091601(unittest.TestCase):
    def test_tip(self):
        for rel in PATHS:
            text = (ROOT / rel).read_text(encoding="utf-8")
            self.assertIn("## Live cash", text, rel)
            self.assertIn("../agent-rescue.html", text, rel)
            self.assertIn("Larger fixed engagements", text, rel)
            self.assertIn("../diagnostic.html", text, rel)
            self.assertIn("../commercial.html", text, rel)
            self.assertNotIn("buy.stripe.com", text, rel)
    def test_products(self):
        for name in ("diagnostic.html", "commercial.html"):
            self.assertTrue((ROOT / name).is_file(), name)
if __name__ == "__main__":
    unittest.main()
