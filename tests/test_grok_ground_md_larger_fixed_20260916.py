from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
CLAIM = "grok-ground-md-larger-fixed-20260916-01"
KEEP = "newbot-ground-md-live-cash-20260916-09"
STEMS = [
    "ACTIONS_QUEUE_CANCEL",
    "AGENT_RUNTIME_PROVENANCE",
    "ATOMIC_WORK_CLAIMS",
    "COMMONS_VISIBILITY_PLAN",
    "CONNECTOR_POLICY_BROKER",
    "CONTEXT_DISPATCH",
    "CONTEXT_GIT_SOURCE_CAPSULES",
    "COORDINATION_STATE",
    "FINDING_REGISTRY",
    "LANE_REGISTRY",
    "NEEDS_QUEUES",
    "OPPONENT_REGISTRY",
    "RECEIPT_RESOLVER",
    "SUBZERO_GRBN",
    "SWARM_CHANNEL_DISPATCH",
    "SWARM_ORDER",
    "SWARM_SESSION_IDENTITY_CLAIMS",
]


class T(unittest.TestCase):
    def test_ground_md_larger_fixed(self):
        for stem in STEMS:
            with self.subTest(stem=stem):
                text = (ROOT / "ground" / f"{stem}.md").read_text(encoding="utf-8")
                self.assertIn("Live cash", text)

                self.assertIn("../dealer-service-lead-rescue.html", text)
                self.assertIn("../plant-downtime-handoff.html", text)
                self.assertIn("Larger fixed engagements", text)
                self.assertIn("../diagnostic.html", text)
                self.assertIn("../commercial.html", text)
                self.assertIn("$12,000", text)
                self.assertIn("$30,000", text)
                self.assertNotIn("buy.stripe.com", text)
                self.assertIn(KEEP, text)
                self.assertIn(CLAIM, text)


if __name__ == "__main__":
    unittest.main()
