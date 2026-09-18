#!/usr/bin/env python3
"""Hermetic: newbot JSON doors live_cash — product pages only."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CLAIM = "newbot-json-doors-live-cash-20260916-05"
FILES = [
    "commands.json",
    "compress.json",
    "delta.json",
    "embassy.json",
    "feature-tracker.json",
    "mirrors.json",
    "observatory.json",
    "reach.json",
    "ringdelta.json",
    "unbuilt-items.json",
]
REQUIRED_PATHS = [
    "dealer-service-lead-rescue.html",
    "referral-intake-completeness.html",
    "repair-booking-preflight.html",
    "plant-downtime-handoff.html",
]


class NewbotJsonDoorsLiveCashTest(unittest.TestCase):
    def test_each_json_has_live_cash_products(self) -> None:
        for name in FILES:
            path = ROOT / name
            self.assertTrue(path.is_file(), f"{name} missing")
            data = json.loads(path.read_text(encoding="utf-8"))
            live = data.get("live_cash")
            self.assertIsInstance(live, dict, name)
            self.assertIn(CLAIM, live.get("cite") or [])
            products = live.get("products")
            self.assertIsInstance(products, list, name)
            paths = [p.get("path") for p in products]
            for req in REQUIRED_PATHS:
                self.assertIn(req, paths, f"{name} missing {req}")
            dealer = next(p for p in products if p["path"] == "dealer-service-lead-rescue.html")
            self.assertEqual(dealer.get("price_usd"), 199)
            blob = path.read_text(encoding="utf-8")
            self.assertNotIn("buy.stripe.com", blob)
            self.assertNotIn("plink_", blob)

    def test_receipt_exists(self) -> None:
        receipt = ROOT / "p" / f"{CLAIM}.md"
        self.assertTrue(receipt.is_file())
        text = receipt.read_text(encoding="utf-8")
        self.assertIn(CLAIM, text)
        for name in FILES:
            self.assertIn(name, text)


if __name__ == "__main__":
    unittest.main()
