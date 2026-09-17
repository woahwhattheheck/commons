"""latch-ground-repo-peer-md-keep-larger-fixed-20260916-01 — KEEP Larger on repo/peer MD."""
from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CLAIM = "latch-ground-repo-peer-md-keep-larger-fixed-20260916-01"
PATHS = (
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
)
TIP_PATHS = (
    "agent-rescue.html",
    "dealer-service-lead-rescue.html",
    "referral-intake-completeness.html",
    "repair-booking-preflight.html",
    "plant-downtime-handoff.html",
)
LARGER_PATHS = ("diagnostic.html", "commercial.html")


class TestLatchGroundRepoPeerMdKeepLargerFixed2026091601(unittest.TestCase):
    def test_tip_doors_have_autopsy_and_larger(self) -> None:
        for rel in PATHS:
            with self.subTest(rel=rel):
                text = (ROOT / rel).read_text(encoding="utf-8")
                self.assertIn("## Live cash", text, rel)
                self.assertIn("../agent-rescue.html", text, rel)
                self.assertIn("../dealer-service-lead-rescue.html", text, rel)
                self.assertIn("../plant-downtime-handoff.html", text, rel)
                self.assertIn("Larger fixed engagements", text, rel)
                self.assertIn("../diagnostic.html", text, rel)
                self.assertIn("../commercial.html", text, rel)
                self.assertIn("$12,000", text, rel)
                self.assertIn("$30,000", text, rel)
                self.assertIn("$199", text, rel)
                self.assertNotIn("buy.stripe.com", text, rel)
                live, larger = text.split("Larger fixed engagements", 1)
                self.assertIn("../agent-rescue.html", live, rel)
                self.assertIn("../diagnostic.html", larger, rel)
                self.assertIn("../commercial.html", larger, rel)

    def test_product_pages_exist(self) -> None:
        for name in TIP_PATHS + LARGER_PATHS:
            self.assertTrue((ROOT / name).is_file(), name)

    def test_receipt_exists(self) -> None:
        receipt = ROOT / "p" / f"{CLAIM}.md"
        text = receipt.read_text(encoding="utf-8")
        self.assertIn(f"id: {CLAIM}", text)
        self.assertIn("Hands off #8802", text)
        self.assertIn("Tip KEEP", text)
        self.assertIn("337 not law", text)


if __name__ == "__main__":
    unittest.main()
