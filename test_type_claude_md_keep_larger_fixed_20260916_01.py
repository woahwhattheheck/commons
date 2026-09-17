"""type-claude-md-keep-larger-fixed-20260916-01."""
from __future__ import annotations
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parent
PATHS = (
    "ground/CLAUDE_COMPUTE.md",
    "ground/CLAUDE_INTERMEDIATE.md",
    "ground/CLAUDE_OVER_REFUSAL_LOCAL.md",
    "ground/CLAUDE_PARK.md",
    "ground/CLAUDE_PEER_CHECK.md",
    "ground/CLAUDE_PRIORS_VS_TRUTH.md",
    "ground/CLAUDE_ROLE.md",
    "ground/CLAUDE_TESTER.md",
    "ground/CLAUDE_ZERO.md",
    "ground/CLAUDE_ZERO_DAMAGE.md",
)
class TestTypeClaudeMdKeepLargerFixed2026091601(unittest.TestCase):
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
