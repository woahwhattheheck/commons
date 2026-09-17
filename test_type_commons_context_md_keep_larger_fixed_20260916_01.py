"""type-commons-context-md-keep-larger-fixed-20260916-01."""
from __future__ import annotations
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parent
PATHS = (
    "ground/COMMONS_ADMISSIBILITY_AND_EXECUTION.md",
    "ground/COMMONS_ARCHITECTURE_300FT.md",
    "ground/COMMONS_PROVIDER_MAP.md",
    "ground/COMMONS_SLACK_FULL_BODY.md",
    "ground/CONNECTOR_REVAL.md",
    "ground/CONTAINMENT.md",
    "ground/CONTEXT_INTEGRITY.md",
    "ground/CURRENT_WORK.md",
    "ground/CLOCK_FANOUT_AUTOFAB.md",
    "ground/DEST_IS_THE_MACHINE.md",
)
class TestTypeCommonsContextMdKeepLargerFixed2026091601(unittest.TestCase):
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
