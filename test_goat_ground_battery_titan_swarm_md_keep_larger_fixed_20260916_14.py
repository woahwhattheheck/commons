"""goat-ground-battery-titan-swarm-md-keep-larger-fixed-20260916-14 — KEEP Larger on leftover ground MD."""
from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CLAIM = "goat-ground-battery-titan-swarm-md-keep-larger-fixed-20260916-14"
SPY_PATHS = (
    ("ground/TEST_BATTERY_INDEX.md", "spy-ground-batch-live-cash-20260909-17"),
    ("ground/TITAN_MOVE.md", "spy-ground-batch-live-cash-20260909-17"),
    ("ground/TITAN_APPEND_GUARD.md", "spy-ground-batch-live-cash-20260909-17"),
    ("ground/TITAN_TEST_QUARANTINE.md", "spy-ground-batch-live-cash-20260909-17"),
)
SWARM_PATH = "ground/SWARM.md"
TIP_PATHS = (
    "dealer-service-lead-rescue.html",
    "referral-intake-completeness.html",
    "repair-booking-preflight.html",
    "plant-downtime-handoff.html",
)
LARGER_PATHS = ("diagnostic.html", "commercial.html")
HANDS_OFF = (
    "ground/SUPERGROK_HEAVY.md",
    "ground/SWARM_DC.md",
    "ground/TAKING_TRACE.md",
    "ground/SLACK_SERVICE_ALL_DRIVERS.md",
    "ground/SLACK_SERVICE_TAGS.md",
    "ground/SLACK_SPARK_MCP_DRIVER.md",
    "ground/SLACK_CUSTOM_TOOLS_CLI_CHALLENGE.md",
    "ground/SLACK_CUSTOM_TOOLS_CLI_PROJECT.md",
    "ground/SLACK_CUSTOM_TOOLS_INSTALL.md",
    "ground/RINGDELTA.md",
    "ground/SITTING_PR.md",
    "ground/SIZE_ONLY.md",
    "ground/JOJO_ASSIGN.md",
    "ground/LDA_ANDROID_CI.md",
    "ground/LDA_RECEIPT.md",
    "ground/MIRROR_MESH_0.md",
    "ground/MODEL_LANGUAGE.md",
    "ground/MUHC_CORPUS.md",
    "ground/LAB.md",
    "ground/MUHL_PNG.md",
    "ground/MUHL_RECEIPT_LANE.md",
    "ground/MUHL_TRAIN_BRIDGE.md",
    "ground/MUHL_FILM_ORGAN.md",
    "ground/MUHL_SELF_TRAIN_ADDRESS_CONTRACT.md",
    "ground/ACCORDION.md",
    "ground/AGENT_GROUNDING.md",
    "ground/ARTIFACT_REGISTRY.md",
    "ground/BACKUP_OPEN_REPO.md",
    "ground/BATTERY_RED.md",
    "ground/BRANCH_REVIEW.md",
    "ground/BREATH.md",
    "ground/BUSINESS_PACK_KEEP_SELL.md",
    "ground/BUSINESS_PACK_OPERATOR.md",
    "ground/CLASS_17.md",
    "ground/REPO.md",
    "ground/DELTA.md",
    "ground/FACTS.md",
    "ground/OBSERVATORY.md",
    "ground/PFC_COMPUTER.md",
    "ground/FEATURE_TRACKER.md",
    "ground/CLAUDE_COMPUTE.md",
    "ground/GROK_SURFACES.md",
    "ground/SUBZERO_WALK.md",
    "ground/SUBZERO_BUYERS.md",
    "ground/TRUST.md",
    "ground/FOUNDRY_LAND_20260819.md",
    "ground/WAKE_LOOP.md",
    "ground/HARNESS.md",
    "ground/FLEET.md",
    "ground/HUB.md",
    "ground/WATCHDOG_CANARY.md",
)


def _cash(text: str) -> str:
    idx = text.find("## Live cash")
    nxt = text.find("\n## ", idx + 1)
    return text[idx:] if nxt < 0 else text[idx:nxt]


class TestGoatGroundBatteryTitanSwarmMdKeepLargerFixed2026091614(unittest.TestCase):
    def test_leftover_spy17_cards_keep_autopsy_and_larger(self) -> None:
        for rel, cite in SPY_PATHS:
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

    def test_swarm_md_keep_autopsy_and_larger(self) -> None:
        rel = SWARM_PATH
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
        self.assertNotIn("buy.stripe.com", cash, rel)
        self.assertNotIn("spy-ground-batch-live-cash-20260909-17", cash, rel)
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
        for rel, _cite in SPY_PATHS:
            self.assertIn(rel, text, rel)
        self.assertIn(SWARM_PATH, text)
        for rel in HANDS_OFF:
            self.assertNotIn(rel, text, rel)
        self.assertNotIn("leftover-census.md", text)
        self.assertNotIn("lda/README.md", text)


if __name__ == "__main__":
    unittest.main()
