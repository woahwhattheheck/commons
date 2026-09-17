"""goat-wake-cloud-md-keep-larger-fixed-20260916-03 — KEEP Larger on leftover wake/cloud ground MD."""
from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CLAIM = "goat-wake-cloud-md-keep-larger-fixed-20260916-03"
PATHS = (
    "ground/WAKE_LOOP.md",
    "ground/NO_MOCK_ONLY.md",
    "ground/SPRINT_INTEGRATION.md",
    "ground/CLOUD_CURRENT.md",
    "ground/CLOUD_STORAGE_ONLY.md",
)
TIP_PATHS = (
    "agent-rescue.html",
    "dealer-service-lead-rescue.html",
    "referral-intake-completeness.html",
    "repair-booking-preflight.html",
    "plant-downtime-handoff.html",
)
LARGER_PATHS = ("diagnostic.html", "commercial.html")


def _cash(text: str) -> str:
    idx = text.find("## Live cash")
    nxt = text.find("\n## ", idx + 1)
    return text[idx:] if nxt < 0 else text[idx:nxt]


class TestGoatWakeCloudMdKeepLargerFixed2026091603(unittest.TestCase):
    def test_leftover_ground_cards_keep_autopsy_and_larger(self) -> None:
        for rel in PATHS:
            with self.subTest(rel=rel):
                text = (ROOT / rel).read_text(encoding="utf-8")
                cash = _cash(text)
                self.assertIn("## Live cash", text, rel)
                self.assertIn("../agent-rescue.html", cash, rel)
                self.assertIn("../dealer-service-lead-rescue.html", cash, rel)
                self.assertIn("../plant-downtime-handoff.html", cash, rel)
                self.assertIn("Larger fixed engagements", cash, rel)
                self.assertIn("../diagnostic.html", cash, rel)
                self.assertIn("../commercial.html", cash, rel)
                self.assertIn("$12,000", cash, rel)
                self.assertIn("$30,000", cash, rel)
                self.assertNotIn("buy.stripe.com", cash, rel)
                plant = cash.find("plant-downtime-handoff.html")
                larger = cash.find("Larger fixed engagements")
                self.assertGreaterEqual(plant, 0, rel)
                self.assertGreater(larger, plant, rel)

    def test_product_pages_exist(self) -> None:
        for name in TIP_PATHS + LARGER_PATHS:
            self.assertTrue((ROOT / name).is_file(), name)

    def test_receipt_exists(self) -> None:
        receipt = ROOT / "p" / f"{CLAIM}.md"
        text = receipt.read_text(encoding="utf-8")
        self.assertIn(f"id: {CLAIM}", text)
        self.assertIn("Hands off #8802", text)
        self.assertIn("Tip KEEP", text)
        self.assertNotIn("buy.stripe.com", text)
        for rel in PATHS:
            self.assertIn(rel, text, rel)
        self.assertNotIn("leftover-census.md", text)
        self.assertNotIn("lda/README.md", text)


if __name__ == "__main__":
    unittest.main()
