"""latch-ops-pack-md-keep-larger-fixed-20260916-01 — KEEP Larger on ops-pack ground MD."""
from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CLAIM = "latch-ops-pack-md-keep-larger-fixed-20260916-01"

PATHS = (
    ("ground/BATTERY_RED.md", "spy-ground-batch-live-cash-20260905-02"),
    ("ground/BREATH.md", "spy-ground-batch-live-cash-20260905-04"),
    ("ground/ACCORDION.md", "spy-ground-batch-live-cash-20260905-03"),
    ("ground/ARTIFACT_REGISTRY.md", "spy-ground-livecash-match-empty-20260909-01"),
    ("ground/BRANCH_REVIEW.md", "spy-ground-batch-live-cash-20260905-14"),
    ("ground/BUSINESS_PACK_KEEP_SELL.md", "spy-ground-batch-live-cash-20260905-05"),
    ("ground/BUSINESS_PACK_OPERATOR.md", "spy-ground-batch-live-cash-20260905-05"),
    ("ground/CLASS_17.md", "spy-claude-priors-live-cash"),
    ("ground/AGENT_GROUNDING.md", "spy-claude-priors-live-cash"),
    ("ground/BACKUP_OPEN_REPO.md", "spy-ground-batch-live-cash-20260905-03"),
)
PRODUCTS = (
    "dealer-service-lead-rescue.html",
    "referral-intake-completeness.html",
    "repair-booking-preflight.html",
    "plant-downtime-handoff.html",
    "diagnostic.html",
    "commercial.html",
)


def _cash(text: str) -> str:
    idx = text.find("## Live cash")
    nxt = text.find("\n## ", idx + 1)
    return text[idx:] if nxt < 0 else text[idx:nxt]


class TestLatchOpsPackMdKeepLargerFixed2026091601(unittest.TestCase):
    def test_tip_ops_pack_has_autopsy_and_larger(self):
        for rel, cite in PATHS:
            text = (ROOT / rel).read_text(encoding="utf-8")
            cash = _cash(text)
            self.assertIn("## Live cash", text, rel)


            self.assertIn("$199", cash, rel)
            self.assertIn("../dealer-service-lead-rescue.html", cash, rel)
            self.assertIn("../plant-downtime-handoff.html", cash, rel)
            self.assertIn("Larger fixed engagements", cash, rel)
            self.assertIn("../diagnostic.html", cash, rel)
            self.assertIn("../commercial.html", cash, rel)
            self.assertIn("$12,000", cash, rel)
            self.assertIn("$30,000", cash, rel)
            self.assertIn(cite, cash, rel)
            self.assertNotIn("buy.stripe.com", cash, rel)
            plant = cash.find("[$199 plant diagnostic]")
            larger = cash.find("Larger fixed engagements")
            self.assertGreaterEqual(plant, 0, rel)
            self.assertGreater(larger, plant, rel)

    def test_product_pages_exist(self):
        for name in PRODUCTS:
            self.assertTrue((ROOT / name).is_file(), name)

    def test_receipt_exists(self):
        receipt = ROOT / "p" / f"{CLAIM}.md"
        text = receipt.read_text(encoding="utf-8")
        self.assertIn(f"id: {CLAIM}", text)
        self.assertIn("CLAIM LATCH", text)
        self.assertIn("Hands off #8802", text)
        self.assertIn("Tip KEEP", text)
        self.assertIn("337 is not law", text)
        for rel, _cite in PATHS:
            self.assertIn(rel, text, rel)


if __name__ == "__main__":
    unittest.main()
