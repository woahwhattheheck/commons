"""type-human-read-stripe-md-keep-larger-fixed-20260916-01."""
from __future__ import annotations
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parent
PATHS = (
    "ground/HUMAN_OUTCOMES.md",
    "ground/READ_IS_VOLTAGE.md",
    "ground/README.md",
    "ground/README_LIVE.md",
    "ground/HARNESS_ALREADY_LOGGED_IN.md",
    "ground/STRIPE.md",
    "ground/CURSOR_HALT.md",
    "ground/CURSOR_QUOTA_HOLD.md",
)
class TestTypeHumanReadStripeMdKeepLargerFixed2026091601(unittest.TestCase):
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
