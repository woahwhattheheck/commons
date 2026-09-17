"""goat-ground-hoard-host-md-keep-larger-fixed-20260916-07 — KEEP Larger on leftover ground MD."""
from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CLAIM = "goat-ground-hoard-host-md-keep-larger-fixed-20260916-07"
PATHS = (
    ("ground/HOARD.md", "spy-ground-harness-live-cash-20260905-01"),
    ("ground/HOST_ZERO.md", "spy-ground-harness-live-cash-20260905-01"),
    ("ground/FOREIGN_MAIN.md", "spy-ground-batch-live-cash-20260905-12"),
    ("ground/GEMMA_INGRESS.md", "spy-ground-batch-live-cash-20260905-12"),
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
    "ground/WATCHDOG_CANARY.md",
    "ground/DEVICE_CANARY.md",
    "ground/PEER_WAKE_BUS.md",
    "ground/LANE_REGISTRY.md",
    "ground/OPPORTUNITY_REGISTRY.md",
    "ground/REVIEW_LANE.md",
    "ground/RENDER_CONTRACT.md",
    "ground/board-as-surface.md",
    "ground/POST_CURL.md",
    "ground/SCOPE_TO_DELIVERY.md",
    "ground/BUSINESS_PACK_PAPERWORK.md",
    "ground/BATTERY_RED.md",
    "ground/CLAUDE_COMPUTE.md",
    "ground/GROK_SURFACES.md",
    "ground/FOUNDRY_LAND_20260819.md",
    "ground/H002.md",
    "ground/WAKE_LOOP.md",
    "ground/HARNESS.md",
    "ground/AGENT_RETIREMENT.md",
    "ground/FLAME.md",
    "ground/FUTURE.md",
    "ground/FLEET.md",
    "ground/HUB.md",
    "ground/HUB_TICK.md",
    "ground/WIRE_SUPER_MCP.md",
)


def _cash(text: str) -> str:
    idx = text.find("## Live cash")
    nxt = text.find("\n## ", idx + 1)
    return text[idx:] if nxt < 0 else text[idx:nxt]


class TestGoatGroundHoardHostMdKeepLargerFixed2026091607(unittest.TestCase):
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
