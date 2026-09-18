"""goat-ground-harness-md-keep-larger-fixed-20260916-05 — KEEP Larger on leftover ground MD."""
from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CLAIM = "goat-ground-harness-md-keep-larger-fixed-20260916-05"
PATHS = (
    ("ground/GITHUB_CALL_NOT_LOGIN.md", "spy-ground-batch-live-cash-20260905-17"),
    ("ground/HARNESS.md", "spy-ground-harness-live-cash-20260905-01"),
    ("ground/ELITIST_WAY.md", "spy-ground-batch-live-cash-20260905-12"),
)
TIP_PATHS = (
    "dealer-service-lead-rescue.html",
    "referral-intake-completeness.html",
    "repair-booking-preflight.html",
    "plant-downtime-handoff.html",
)
LARGER_PATHS = ("diagnostic.html", "commercial.html")
HANDS_OFF_GROK = (
    "ground/GROK_APP_ROUTE.md",
    "ground/GROK_AUTOMATION_HARVEST.md",
    "ground/GROK_CLAUDE_HYGIENE.md",
    "ground/GROK_HARNESS.md",
    "ground/GROK_HYGIENE.md",
    "ground/GROK_RECEIPT.md",
    "ground/GROK_RECOVERY.md",
    "ground/GROK_ROUTE.md",
    "ground/GROK_SURFACES.md",
)
HANDS_OFF_LATCH = (
    "ground/BATTERY_RED.md",
    "ground/BREATH.md",
    "ground/ACCORDION.md",
)


def _cash(text: str) -> str:
    idx = text.find("## Live cash")
    nxt = text.find("\n## ", idx + 1)
    return text[idx:] if nxt < 0 else text[idx:nxt]


class TestGoatGroundHarnessMdKeepLargerFixed2026091605(unittest.TestCase):
    def test_leftover_ground_cards_keep_autopsy_and_larger(self) -> None:
        for rel, cite in PATHS:
            with self.subTest(rel=rel):
                text = (ROOT / rel).read_text(encoding="utf-8")
                cash = _cash(text)
                self.assertIn("## Live cash", text, rel)

                self.assertIn("../dealer-service-lead-rescue.html", cash, rel)
                self.assertIn("../plant-downtime-handoff.html", cash, rel)
                self.assertIn("Larger fixed engagements", cash, rel)
                self.assertIn("../diagnostic.html", cash, rel)
                self.assertIn("../commercial.html", cash, rel)
                self.assertIn("$12,000", cash, rel)
                self.assertIn("$30,000", cash, rel)
                self.assertIn(cite, cash, rel)
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
        self.assertIn("type-grok-surfaces-md-keep-larger-fixed-20260916-01", text)
        self.assertNotIn("buy.stripe.com", text)
        for rel, _cite in PATHS:
            self.assertIn(rel, text, rel)
        for rel in HANDS_OFF_GROK + HANDS_OFF_LATCH:
            self.assertNotIn(rel, text, rel)
        self.assertNotIn("leftover-census.md", text)
        self.assertNotIn("lda/README.md", text)


if __name__ == "__main__":
    unittest.main()
