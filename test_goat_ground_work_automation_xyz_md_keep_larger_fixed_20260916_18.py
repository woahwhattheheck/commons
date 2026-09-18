"""goat-ground-work-automation-xyz-md-keep-larger-fixed-20260916-18 — KEEP Larger on leftover ground MD."""
from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CLAIM = "goat-ground-work-automation-xyz-md-keep-larger-fixed-20260916-18"
PATHS = (
    ("ground/WORK_AUTOMATION.md", "spy-ground-batch-live-cash-20260909-19"),
    ("ground/corpus-2026-08-02-substance.md", "spy-ground-batch-live-cash-20260909-19"),
    ("ground/corpus-2026-08-07-instruments.md", "spy-ground-batch-live-cash-20260909-19"),
    ("ground/XYZ_ZERO.md", "coil MANUAL"),
)
TIP_PATHS = (
    "dealer-service-lead-rescue.html",
    "referral-intake-completeness.html",
    "repair-booking-preflight.html",
    "plant-downtime-handoff.html",
)
LARGER_PATHS = ("diagnostic.html", "commercial.html")
HANDS_OFF = (
    "ground/VENT.md",
    "ground/VISUAL.md",
    "ground/WAKE_CONTRACT.md",
    "ground/WHISPER.md",
    "ground/WIDTH200.md",
    "ground/UNLISTED.md",
    "ground/UNUSED_INVOKE.md",
    "ground/VERIFY_CITE.md",
    "ground/WALLS_PLAIN.md",
    "ground/WHAT_THE_PFC_IS.md",
    "ground/TJLABS_PACK_TERMS.md",
    "ground/TOPICS.md",
    "ground/TWO_PATHS.md",
    "ground/TWO_ROOMS.md",
    "ground/UNBUILT_ITEMS.md",
    "ground/WORKING_BUILDS.md",
    "ground/copy-paste-manufacturing.md",
    "ground/ACCORDION.md",
    "ground/AGENT_GROUNDING.md",
    "ground/BATTERY_RED.md",
    "ground/BUSINESS_PACK_KEEP_SELL.md",
    "ground/LAB.md",
    "ground/MUHL_PNG.md",
    "ground/MUHL_SELF_TRAIN_ADDRESS_CONTRACT.md",
    "ground/SUBZERO_WALK.md",
    "ground/SUBZERO_BUYERS.md",
    "ground/WAKE_LOOP.md",
    "ground/HARNESS.md",
    "ground/FLEET.md",
    "ground/HUB.md",
)


def _cash(text: str) -> str:
    idx = text.find("## Live cash")
    nxt = text.find("\n## ", idx + 1)
    return text[idx:] if nxt < 0 else text[idx:nxt]


class TestGoatGroundWorkAutomationXyzMdKeepLargerFixed2026091618(unittest.TestCase):
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
        self.assertNotIn("buy.stripe.com", text)
        for rel, _cite in PATHS:
            self.assertIn(rel, text, rel)
        for rel in HANDS_OFF:
            self.assertNotIn(rel, text, rel)
        self.assertNotIn("leftover-census.md", text)
        self.assertNotIn("lda/README.md", text)


if __name__ == "__main__":
    unittest.main()
