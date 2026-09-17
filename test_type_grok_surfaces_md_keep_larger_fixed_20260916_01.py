"""type-grok-surfaces-md-keep-larger-fixed-20260916-01."""
from __future__ import annotations
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parent
PATHS = (
    "ground/GROK_APP_ROUTE.md","ground/GROK_AUTOMATION_HARVEST.md","ground/GROK_CLAUDE_HYGIENE.md",
    "ground/GROK_HARNESS.md","ground/GROK_HYGIENE.md","ground/GROK_RECEIPT.md","ground/GROK_RECOVERY.md",
    "ground/GROK_ROUTE.md","ground/GROK_SURFACES.md",
)
class TestTypeGrokSurfacesMdKeepLargerFixed2026091601(unittest.TestCase):
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
