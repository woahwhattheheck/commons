"""goat-cash-now-json-keep-larger-fixed-20260916-01 — KEEP Larger fixed on CASH_NOW.json."""
from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CLAIM = "goat-cash-now-json-keep-larger-fixed-20260916-01"
CATALOG = ROOT / "ground" / "CASH_NOW.json"
TIP_PATHS = (
    "agent-rescue.html",
    "dealer-service-lead-rescue.html",
    "referral-intake-completeness.html",
    "repair-booking-preflight.html",
    "plant-downtime-handoff.html",
)
LARGER_PATHS = ("diagnostic.html", "commercial.html")


class TestGoatCashNowJsonKeepLargerFixed2026091601(unittest.TestCase):
    def test_catalog_keeps_tip_pages_and_adds_larger_fixed(self) -> None:
        raw = CATALOG.read_text(encoding="utf-8")
        data = json.loads(raw)
        pages = data.get("product_pages")
        self.assertIsInstance(pages, list)
        tip_paths = [item.get("path") for item in pages]
        self.assertEqual(tip_paths, list(TIP_PATHS))
        by_path = {item["path"]: item for item in pages}
        self.assertEqual(by_path["agent-rescue.html"].get("amount_usd"), 29)
        for rel in TIP_PATHS[1:]:
            self.assertEqual(by_path[rel].get("amount_usd"), 199, rel)

        larger = data.get("larger_fixed")
        self.assertIsInstance(larger, list)
        lf_paths = [item.get("path") for item in larger]
        self.assertEqual(lf_paths, list(LARGER_PATHS))
        lf = {item["path"]: item for item in larger}
        self.assertEqual(lf["diagnostic.html"].get("amount_usd"), 12000)
        self.assertEqual(lf["diagnostic.html"].get("days"), 10)
        self.assertEqual(lf["commercial.html"].get("amount_usd"), 30000)
        self.assertEqual(lf["commercial.html"].get("days"), 30)
        self.assertIn("Larger fixed engagements", data.get("larger_fixed_note") or "")
        self.assertEqual(data.get("cite_larger_fixed"), CLAIM)
        self.assertEqual(data.get("claim"), "reed-ground-cash-now-autopsy-doors-20260909-01")
        self.assertEqual(data.get("collectable_usd"), "NOT_LANDED")
        self.assertNotIn("buy.stripe.com", raw)
        self.assertNotIn("plink_", raw)
        for rel in LARGER_PATHS:
            self.assertNotIn(rel, tip_paths)

    def test_product_pages_exist(self) -> None:
        for name in TIP_PATHS + LARGER_PATHS:
            self.assertTrue((ROOT / name).is_file(), name)

    def test_receipt_exists(self) -> None:
        receipt = ROOT / "p" / f"{CLAIM}.md"
        text = receipt.read_text(encoding="utf-8")
        self.assertIn(f"id: {CLAIM}", text)
        self.assertIn("Hands off #8802", text)
        self.assertIn("Tip KEEP", text)
        self.assertIn("ground/CASH_NOW.json", text)
        self.assertNotIn("buy.stripe.com", text)


if __name__ == "__main__":
    unittest.main()
