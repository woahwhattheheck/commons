"""goat-ground-foundry-h00-md-keep-larger-fixed-20260916-06 — KEEP Larger on leftover ground MD."""
from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CLAIM = "goat-ground-foundry-h00-md-keep-larger-fixed-20260916-06"
PATHS = (
    ("ground/FOUNDRY_LAND_20260819.md", "spy-ground-batch-live-cash-20260905-17"),
    ("ground/GEMMA_TOKENIZER_MAP.md", "spy-ground-batch-live-cash-20260905-17"),
    ("ground/H002.md", "spy-ground-batch-live-cash-20260905-17"),
    ("ground/H009.md", "spy-ground-batch-live-cash-20260905-17"),
)
ALREADY_KEPT = "ground/GITHUB_CALL_NOT_LOGIN.md"
TIP_PATHS = (
    "agent-rescue.html",
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
HANDS_OFF_WIRE = (
    "ground/WATCHDOG_CANARY.md",
    "ground/DEVICE_CANARY.md",
)
HANDS_OFF_TYPE_CLAUDE = (
    "ground/CLAUDE_COMPUTE.md",
    "ground/CLAUDE_ZERO.md",
)


def _cash(text: str) -> str:
    idx = text.find("## Live cash")
    nxt = text.find("\n## ", idx + 1)
    return text[idx:] if nxt < 0 else text[idx:nxt]


class TestGoatGroundFoundryH00MdKeepLargerFixed2026091606(unittest.TestCase):
    def test_leftover_ground_cards_keep_autopsy_and_larger(self) -> None:
        for rel, cite in PATHS:
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
                self.assertIn(cite, cash, rel)
                self.assertNotIn("buy.stripe.com", cash, rel)
                plant = cash.find("plant-downtime-handoff.html")
                larger = cash.find("Larger fixed engagements")
                self.assertGreaterEqual(plant, 0, rel)
                self.assertGreater(larger, plant, rel)

    def test_github_call_already_kept_untouched_by_this_cite(self) -> None:
        text = (ROOT / ALREADY_KEPT).read_text(encoding="utf-8")
        cash = _cash(text)
        self.assertIn("Larger fixed engagements", cash)
        self.assertIn("../diagnostic.html", cash)
        self.assertIn("../commercial.html", cash)
        self.assertIn("spy-ground-batch-live-cash-20260905-17", cash)

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
        for rel in HANDS_OFF_GROK + HANDS_OFF_LATCH + HANDS_OFF_WIRE + HANDS_OFF_TYPE_CLAUDE:
            self.assertNotIn(rel, text, rel)
        self.assertNotIn("leftover-census.md", text)
        self.assertNotIn("lda/README.md", text)


if __name__ == "__main__":
    unittest.main()
