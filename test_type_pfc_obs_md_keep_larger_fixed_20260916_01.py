"""type-pfc-obs-md-keep-larger-fixed-20260916-01."""
from __future__ import annotations
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parent
PATHS = (
    "ground/OBSERVATORY.md",
    "ground/OBS_ADDITIVE.md",
    "ground/PFC_BAKE_CENSUS.md",
    "ground/PFC_COMPUTER.md",
    "ground/PFC_GROUNDING.md",
    "ground/PFC_PROOF_REPORT.md",
    "ground/PFC_X_DEFINED.md",
    "ground/PORTFOLIO_OVERDRIVE.md",
    "ground/PROOF_TO_PROPOSAL.md",
    "ground/RESOURCE_LEDGER.md",
)
class TestTypePfcObsMdKeepLargerFixed2026091601(unittest.TestCase):
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
        for name in ("agent-rescue.html", "diagnostic.html", "commercial.html"):
            self.assertTrue((ROOT / name).is_file(), name)
if __name__ == "__main__":
    unittest.main()
