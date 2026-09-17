"""type-owner-slack-md-keep-larger-fixed-20260916-01."""
from __future__ import annotations
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parent
PATHS = (
    "ground/GROK_LAND_UPFRONT.md",
    "ground/OWNER_NOW.md",
    "ground/OWNER_CONTEXT.md",
    "ground/OWNER_MACHINE_BUILD_SWEEP.md",
    "ground/SLACK_ACCESS.md",
    "ground/SLACK_CONTROL_PLANE.md",
    "ground/SLACK_RECEIPT.md",
    "ground/OPEN-DOOR.md",
)
class TestTypeOwnerSlackMdKeepLargerFixed2026091601(unittest.TestCase):
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
