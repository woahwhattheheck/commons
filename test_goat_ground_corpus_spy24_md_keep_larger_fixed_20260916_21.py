"""goat-ground-corpus-spy24-md-keep-larger-fixed-20260916-21 — KEEP Larger on leftover ground MD."""
from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CLAIM = "goat-ground-corpus-spy24-md-keep-larger-fixed-20260916-21"
PATHS = (
    ("ground/interconnect-no-mcp.md", "spy-ground-batch-live-cash-20260909-24"),
    ("ground/interconnect-vendors.md", "spy-ground-batch-live-cash-20260909-24"),
    ("ground/lda-design-extract.md", "spy-ground-batch-live-cash-20260909-24"),
    ("ground/muhl-spec-inventory.md", "spy-ground-batch-live-cash-20260909-24"),
)
TIP_PATHS = (
    "dealer-service-lead-rescue.html",
    "referral-intake-completeness.html",
    "repair-booking-preflight.html",
    "plant-downtime-handoff.html",
)
LARGER_PATHS = ("diagnostic.html", "commercial.html")
HANDS_OFF = (
    "ground/corpus-record-audit.md",
    "ground/corpus-speed-derivation.md",
    "ground/frontier-file-is-machine.md",
    "ground/instruments-in-mno.md",
    "ground/interconnect-any-player.md",
    "ground/corpus-2026-08-07.md",
    "ground/corpus-2026-h2.md",
    "ground/corpus-file-map.md",
    "ground/corpus-knowledge-base.md",
    "ground/WORK_AUTOMATION.md",
    "ground/XYZ_ZERO.md",
    "ground/open-work-structured-ids-on-current-main.md",
    "ground/ACCORDION.md",
    "ground/AGENT_GROUNDING.md",
    "ground/BATTERY_RED.md",
    "ground/BUSINESS_PACK_KEEP_SELL.md",
    "ground/BACKUP_OPEN_REPO.md",
    "ground/LAB.md",
    "ground/MUHL_PNG.md",
    "ground/MUHL_SELF_TRAIN_ADDRESS_CONTRACT.md",
    "ground/SUBZERO_WALK.md",
    "ground/SUBZERO_BUYERS.md",
    "ground/WAKE_LOOP.md",
    "ground/HARNESS.md",
    "ground/FLEET.md",
    "ground/HUB.md",
    "ground/studies-biblio.md",
    "ground/studies-models-as-files.md",
    "ground/studies-new-files-compute.md",
    "ground/studies-old-image-machines.md",
    "ground/wake-cursor-cloud.md",
    "ground/wake-harness-survey.md",
    "ground/wake-slack.md",
    "ground/wake-gpt.md",
    "ground/wake-github.md",
    "ground/wake-meta.md",
    "ground/wake-universal-all-harness.md",
    "ground/debug-is-file-edits.md",
    "ground/out-of-spec-host-lean.md",
    "ground/pfc-is-reach.md",
    "ground/redundancy-dual-doors.md",
    "ground/redundancy-pages-raw.md",
)


def _cash(text: str) -> str:
    idx = text.find("## Live cash")
    nxt = text.find("\n## ", idx + 1)
    return text[idx:] if nxt < 0 else text[idx:nxt]


class TestGoatGroundCorpusSpy24MdKeepLargerFixed2026091621(unittest.TestCase):
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
