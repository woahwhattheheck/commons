"""goat-ground-mirror-mesh-md-keep-larger-fixed-20260916-09 — KEEP Larger on leftover ground MD."""
from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CLAIM = "goat-ground-mirror-mesh-md-keep-larger-fixed-20260916-09"
PATHS = (
    ("ground/MIRROR_MESH_0.md", "spy-ground-batch-live-cash-20260905-21"),
    ("ground/MOVING_MAIN_MIRROR.md", "spy-ground-batch-live-cash-20260905-21"),
    ("ground/MODEL_LANGUAGE.md", "spy-ground-batch-live-cash-20260905-21"),
    ("ground/MUHC.md", "spy-ground-batch-live-cash-20260905-21"),
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
    "ground/MCP_WAKE.md",
    "ground/MCP_WAKE_JOB.md",
    "ground/MEMORY_SHIP.md",
    "ground/MEMORY_VISIBLE.md",
    "ground/SESSION_MEMORY.md",
    "ground/PAYMENT_READY.md",
    "ground/RENDER_CHECK.md",
    "ground/STRICT_RECEIPT.md",
    "ground/WATCHDOG_HEAD_PROOF.md",
    "ground/WEBMCP.md",
    "ground/FLEET.md",
    "ground/HUB.md",
    "ground/WATCHDOG_CANARY.md",
    "ground/DELTA.md",
    "ground/FACTS.md",
    "ground/DEBTS_TO_BRYCE_20260820.md",
    "ground/DIO_CRLF.md",
    "ground/DISCORD.md",
    "ground/DURABILITY.md",
    "ground/EMBASSY.md",
    "ground/EXACT_BODY_REDACT.md",
    "ground/EXPERIMENT_LEDGER.md",
    "ground/FEATURES.md",
    "ground/BATTERY_RED.md",
    "ground/BUSINESS_PACK_PAPERWORK.md",
    "ground/FEATURE_TRACKER.md",
    "ground/MEASURE_ABUSE.md",
    "ground/CLAUDE_COMPUTE.md",
    "ground/GROK_SURFACES.md",
    "ground/FOUNDRY_LAND_20260819.md",
    "ground/H002.md",
    "ground/H009.md",
    "ground/GEMMA_TOKENIZER_MAP.md",
    "ground/JOJO_ASSIGN.md",
    "ground/LDA_ANDROID_CI.md",
    "ground/LDA_RECEIPT.md",
    "ground/HOARD.md",
    "ground/WAKE_LOOP.md",
    "ground/HARNESS.md",
    "ground/LAB.md",
)


def _cash(text: str) -> str:
    idx = text.find("## Live cash")
    nxt = text.find("\n## ", idx + 1)
    return text[idx:] if nxt < 0 else text[idx:nxt]


class TestGoatGroundMirrorMeshMdKeepLargerFixed2026091609(unittest.TestCase):
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
