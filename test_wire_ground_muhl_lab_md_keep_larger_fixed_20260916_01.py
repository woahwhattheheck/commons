"""wire-ground-muhl-lab-md-keep-larger-fixed-20260916-01"""
from __future__ import annotations
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parent
PAGES = (
    "ground/LAB.md",
    "ground/MIRROR_MESH_0.md",
    "ground/MODEL_LANGUAGE.md",
    "ground/MOVING_MAIN_MIRROR.md",
    "ground/MUHC.md",
    "ground/MUHC_CORPUS.md",
    "ground/MUHL_FILM_ORGAN.md",
    "ground/MUHL_PNG.md",
    "ground/MUHL_RECEIPT_LANE.md",
    "ground/MUHL_TRAIN_BRIDGE.md",
)
class T(unittest.TestCase):
    def test_batch(self):
        for rel in PAGES:
            text = (ROOT / rel).read_text(encoding="utf-8")
            self.assertIn("Larger fixed engagements", text, rel)
            self.assertIn("../diagnostic.html", text, rel)
            self.assertIn("../commercial.html", text, rel)
            self.assertIn("$12,000", text, rel)
            self.assertIn("$30,000", text, rel)
    def test_products(self):
        for name in ("diagnostic.html", "commercial.html"):
            self.assertTrue((ROOT / name).is_file(), name)
if __name__ == "__main__":
    unittest.main()
