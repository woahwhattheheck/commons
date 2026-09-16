import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FILES = [
    "ground/tokens/autogtm.md",
    "ground/tokens/commerce-agents.md",
    "ground/tokens/google-ai-mode-hall-pass.md",
    "ground/tokens/super-mcp.md",
]
PRODUCTS = [
    "agent-rescue.html",
    "dealer-service-lead-rescue.html",
    "referral-intake-completeness.html",
    "repair-booking-preflight.html",
    "plant-downtime-handoff.html",
]


class TestNewbotGroundTokensLiveCash2026091610(unittest.TestCase):
    def test_product_pages_exist(self):
        for name in PRODUCTS:
            self.assertTrue((ROOT / name).is_file(), name)

    def test_all_token_targets(self):
        self.assertEqual(len(FILES), 4)
        for rel in FILES:
            t = (ROOT / rel).read_text(encoding="utf-8")
            self.assertIn("## Live cash", t, rel)
            self.assertEqual(t.count("## Live cash"), 1, rel)
            for prod in PRODUCTS:
                self.assertIn(prod, t, f"{rel} missing {prod}")
            self.assertIn("newbot-ground-tokens-live-cash-20260916-10", t, rel)
            self.assertNotIn("buy.stripe.com", t, rel)


if __name__ == "__main__":
    unittest.main()
