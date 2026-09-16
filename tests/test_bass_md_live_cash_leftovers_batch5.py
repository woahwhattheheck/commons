from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
CLAIM = "bass-md-live-cash-20260916-05"
FILES = [
    "revenue/accounts_receivable_leakage_desk/README.md",
    "revenue/affordable_housing_compliance_demo/OFFER.md",
    "revenue/affordable_housing_compliance_demo/README.md",
    "revenue/agent_capability_constraint_registry/README.md",
    "revenue/agent_false_success_survival/README.md",
    "revenue/agentic_genai_evaluation_gate/README.md",
    "revenue/agentic_gxp_lineage_gate/README.md",
    "revenue/agents_for_humans/commercial_decision_relay/README.md",
]


class T(unittest.TestCase):
    def test_exact_live_cash_batch(self):
        self.assertEqual(len(FILES), 8)
        for rel in FILES:
            with self.subTest(rel=rel):
                data = (ROOT / rel).read_bytes()
                text = data.decode("utf-8")
                prefix = "../" * rel.count("/")
                self.assertEqual(text.count("## Live cash"), 1)
                self.assertIn("Verified product pages only — no invented Stripe links.", text)
                for page in (
                    "agent-rescue.html",
                    "dealer-service-lead-rescue.html",
                    "referral-intake-completeness.html",
                    "repair-booking-preflight.html",
                    "plant-downtime-handoff.html",
                ):
                    self.assertIn(f"{prefix}{page}", text)
                self.assertNotIn("buy.stripe.com", text)
                self.assertNotIn("\x00", text)
        self.assertTrue(CLAIM)


if __name__ == "__main__":
    unittest.main()
