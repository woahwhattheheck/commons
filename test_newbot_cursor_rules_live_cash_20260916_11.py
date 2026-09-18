import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FILES = [
    "commons.mdc",
    "cursor-quota-hold.mdc",
    "execute-immediately.mdc",
    "github-already-logged-in.mdc",
    "github-identity.mdc",
    "hold-quote.mdc",
    "no-claude-import.mdc",
    "no-worktrees-main.mdc",
    "products-private.mdc",
    "run-first.mdc",
    "ship-by-default.mdc",
    "sprint-integration.mdc",
    "swarm-order.mdc",
]
PRODUCTS = [
    "dealer-service-lead-rescue.html",
    "referral-intake-completeness.html",
    "repair-booking-preflight.html",
    "plant-downtime-handoff.html",
]


class TestNewbotCursorRulesLiveCash2026091611(unittest.TestCase):
    def test_product_pages_exist(self):
        for name in PRODUCTS:
            self.assertTrue((ROOT / name).is_file(), name)

    def test_all_rule_targets(self):
        self.assertEqual(len(FILES), 13)
        for name in FILES:
            rel = f".cursor/rules/{name}"
            t = (ROOT / rel).read_text(encoding="utf-8")
            self.assertIn("## Live cash", t, rel)
            self.assertEqual(t.count("## Live cash"), 1, rel)
            for prod in PRODUCTS:
                self.assertIn(prod, t, f"{rel} missing {prod}")
            self.assertIn("newbot-cursor-rules-live-cash-20260916-11", t, rel)
            self.assertNotIn("buy.stripe.com", t, rel)


if __name__ == "__main__":
    unittest.main()
