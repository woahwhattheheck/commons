"""type-build-quote-md-keep-larger-fixed-20260916-01."""
from __future__ import annotations
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parent
PATHS = (
    "ground/HOLD_QUOTE.md",
    "ground/PROFITABILITY_BUILD_MAP.md",
    "ground/WORKING_BUILDS.md",
    "ground/NAMED_BUILDER.md",
    "ground/CROSS_CARRIER_GROUP.md",
    "ground/AGENT_TOOLKIT_AUDIT.md",
    "ground/BRYCE_BUILD_ASKS.md",
    "ground/SLACK_BUILD_FLOOR.md",
)
class TestTypeBuildQuoteMdKeepLargerFixed2026091601(unittest.TestCase):
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
