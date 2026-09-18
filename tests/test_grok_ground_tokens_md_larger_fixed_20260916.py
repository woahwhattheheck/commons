from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
CLAIM = "grok-ground-tokens-md-larger-fixed-20260916-01"
KEEP = "newbot-ground-tokens-live-cash-20260916-10"
FILES = [
    "ground/tokens/autogtm.md",
    "ground/tokens/commerce-agents.md",
    "ground/tokens/google-ai-mode-hall-pass.md",
    "ground/tokens/super-mcp.md",
]


class T(unittest.TestCase):
    def test_ground_tokens_md_larger_fixed(self):
        for rel in FILES:
            with self.subTest(rel=rel):
                text = (ROOT / rel).read_text(encoding="utf-8")
                self.assertIn("Live cash", text)
                self.assertIn("../../agent-rescue.html", text)
                self.assertIn("Larger fixed engagements", text)
                self.assertIn("../../diagnostic.html", text)
                self.assertIn("../../commercial.html", text)
                self.assertIn("$12,000", text)
                self.assertIn("$30,000", text)
                self.assertNotIn("buy.stripe.com", text)
                self.assertIn(KEEP, text)
                self.assertIn(CLAIM, text)


if __name__ == "__main__":
    unittest.main()
