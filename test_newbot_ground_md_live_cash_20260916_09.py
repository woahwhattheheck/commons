import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FILES = [
    "ground/ACTIONS_QUEUE_CANCEL.md",
    "ground/AGENT_RUNTIME_PROVENANCE.md",
    "ground/ATOMIC_WORK_CLAIMS.md",
    "ground/COMMONS_VISIBILITY_PLAN.md",
    "ground/CONNECTOR_POLICY_BROKER.md",
    "ground/CONTEXT_DISPATCH.md",
    "ground/CONTEXT_GIT_SOURCE_CAPSULES.md",
    "ground/COORDINATION_STATE.md",
    "ground/FINDING_REGISTRY.md",
    "ground/LANE_REGISTRY.md",
    "ground/NEEDS_QUEUES.md",
    "ground/OPPONENT_REGISTRY.md",
    "ground/RECEIPT_RESOLVER.md",
    "ground/SUBZERO_GRBN.md",
    "ground/SWARM_CHANNEL_DISPATCH.md",
    "ground/SWARM_ORDER.md",
    "ground/SWARM_SESSION_IDENTITY_CLAIMS.md",
]
PRODUCTS = [
    "dealer-service-lead-rescue.html",
    "referral-intake-completeness.html",
    "repair-booking-preflight.html",
    "plant-downtime-handoff.html",
]


class TestNewbotGroundMdLiveCash2026091609(unittest.TestCase):
    def test_product_pages_exist(self):
        for name in PRODUCTS:
            self.assertTrue((ROOT / name).is_file(), name)

    def test_all_ground_targets(self):
        self.assertEqual(len(FILES), 17)
        for rel in FILES:
            t = (ROOT / rel).read_text(encoding="utf-8")
            self.assertIn("## Live cash", t, rel)
            self.assertEqual(t.count("## Live cash"), 1, rel)
            for prod in PRODUCTS:
                self.assertIn(prod, t, f"{rel} missing {prod}")
            self.assertIn("newbot-ground-md-live-cash-20260916-09", t, rel)
            self.assertNotIn("buy.stripe.com", t, rel)


if __name__ == "__main__":
    unittest.main()
