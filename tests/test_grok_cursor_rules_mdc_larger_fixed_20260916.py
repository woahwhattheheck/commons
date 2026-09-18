from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
CLAIM = "grok-cursor-rules-mdc-larger-fixed-20260916-01"
KEEP = "newbot-cursor-rules-live-cash-20260916-11"
STEMS = [
    "commons",
    "cursor-quota-hold",
    "execute-immediately",
    "github-already-logged-in",
    "github-identity",
    "hold-quote",
    "no-claude-import",
    "no-worktrees-main",
    "products-private",
    "run-first",
    "ship-by-default",
    "sprint-integration",
    "swarm-order",
]


class T(unittest.TestCase):
    def test_cursor_rules_mdc_larger_fixed(self):
        for stem in STEMS:
            with self.subTest(stem=stem):
                text = (ROOT / ".cursor/rules" / f"{stem}.mdc").read_text(encoding="utf-8")
                self.assertIn("Live cash", text)

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
