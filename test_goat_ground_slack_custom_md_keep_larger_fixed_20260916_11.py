"""goat-ground-slack-custom-md-keep-larger-fixed-20260916-11 — KEEP Larger on leftover ground MD."""
from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CLAIM = "goat-ground-slack-custom-md-keep-larger-fixed-20260916-11"
PATHS = (
    ("ground/SLACK_CUSTOM_TOOLS_CLI_CHALLENGE.md", "spy-ground-batch-live-cash-20260909-04"),
    ("ground/SLACK_CUSTOM_TOOLS_CLI_PROJECT.md", "spy-ground-batch-live-cash-20260909-04"),
    ("ground/SLACK_CUSTOM_TOOLS_INSTALL.md", "spy-ground-batch-live-cash-20260909-04"),
)
TIP_PATHS = (
    "agent-rescue.html",
    "dealer-service-lead-rescue.html",
    "referral-intake-completeness.html",
    "repair-booking-preflight.html",
    "plant-downtime-handoff.html",
)
LARGER_PATHS = ("diagnostic.html", "commercial.html")
HANDS_OFF = (
    "ground/LAB.md",
    "ground/MUHL_PNG.md",
    "ground/MUHL_RECEIPT_LANE.md",
    "ground/MUHL_TRAIN_BRIDGE.md",
    "ground/MUHL_FILM_ORGAN.md",
    "ground/MUHL_SELF_TRAIN_ADDRESS_CONTRACT.md",
    "ground/MUHC_CORPUS.md",
    "ground/MNO_DATASHEETS_20260819.md",
    "ground/NEEDS_BRYCE.md",
    "ground/P4_CLOSED.md",
    "ground/PC_SHARE.md",
    "ground/PEER_PACKET_20260819.md",
    "ground/POWER_CORD_DEMO.md",
    "ground/PREDICATE_JAIL.md",
    "ground/PRTSCN.md",
    "ground/REMEASURE.md",
    "ground/REPO.md",
    "ground/SPECTER_FINAL.md",
    "ground/STEALABLE_LANES.md",
    "ground/RESOURCES_TAB.md",
    "ground/SHARED_ONE.md",
    "ground/JOJO_ASSIGN.md",
    "ground/LDA_ANDROID_CI.md",
    "ground/LDA_RECEIPT.md",
    "ground/FOUNDRY_LAND_20260819.md",
    "ground/RINGDELTA.md",
    "ground/SETTLED_FACTS.md",
    "ground/SITTING_PR.md",
    "ground/SIZE_ONLY.md",
    "ground/ACCORDION.md",
    "ground/BATTERY_RED.md",
    "ground/DELTA.md",
    "ground/FACTS.md",
    "ground/OBSERVATORY.md",
    "ground/PFC_COMPUTER.md",
    "ground/FEATURE_TRACKER.md",
    "ground/CLAUDE_COMPUTE.md",
    "ground/GROK_SURFACES.md",
    "ground/MCP_WAKE.md",
    "ground/FLEET.md",
    "ground/HUB.md",
    "ground/WATCHDOG_CANARY.md",
    "ground/WAKE_LOOP.md",
    "ground/HARNESS.md",
)


def _cash(text: str) -> str:
    idx = text.find("## Live cash")
    nxt = text.find("\n## ", idx + 1)
    return text[idx:] if nxt < 0 else text[idx:nxt]


class TestGoatGroundSlackCustomMdKeepLargerFixed2026091611(unittest.TestCase):
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
