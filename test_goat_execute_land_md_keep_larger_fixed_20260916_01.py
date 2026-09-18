"""goat-execute-land-md-keep-larger-fixed-20260916-01 — KEEP Larger on execute/land law MD."""
from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CLAIM = "goat-execute-land-md-keep-larger-fixed-20260916-01"
PATHS = (
    "ground/EXECUTE.md",
    "ground/LAND.md",
    "ground/CURL.md",
    "ground/TRUST.md",
    "ground/EXPAND.md",
    "memory/LAW.md",
)
TIP_PATHS = (
    "dealer-service-lead-rescue.html",
    "referral-intake-completeness.html",
    "repair-booking-preflight.html",
    "plant-downtime-handoff.html",
)
LARGER_PATHS = ("diagnostic.html", "commercial.html")


class TestGoatExecuteLandMdKeepLargerFixed2026091601(unittest.TestCase):
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
                self.assertNotIn("buy.stripe.com", text, rel)

    def test_product_pages_exist(self) -> None:
        for name in TIP_PATHS + LARGER_PATHS:
            self.assertTrue((ROOT / name).is_file(), name)

    def test_receipt_exists(self) -> None:
        receipt = ROOT / "p" / f"{CLAIM}.md"
        text = receipt.read_text(encoding="utf-8")
        self.assertIn(f"id: {CLAIM}", text)
        self.assertIn("Hands off #8802", text)
        self.assertIn("Tip KEEP", text)


if __name__ == "__main__":
    unittest.main()
