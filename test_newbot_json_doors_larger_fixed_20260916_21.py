#!/usr/bin/env python3
"""Hermetic: newbot tip JSON doors larger_fixed batch-21 — thin additive."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CLAIM = "newbot-json-doors-larger-fixed-20260916-21"
FILES = [
    "crawler-access.json",
    "agent-discovery.json",
    "compress_measured.json",
    "ringdelta_measured.json",
]
REQUIRED_PATHS = [
    "agent-rescue.html",
    "dealer-service-lead-rescue.html",
    "referral-intake-completeness.html",
    "repair-booking-preflight.html",
    "plant-downtime-handoff.html",
]
LARGER = ("diagnostic.html", "commercial.html")


class NewbotJsonDoorsLargerFixed21Test(unittest.TestCase):
    def test_each_json_has_larger_fixed(self) -> None:
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
            autopsy = next(p for p in products if p["path"] == "agent-rescue.html")
            self.assertEqual(autopsy.get("price_usd"), 29)
            larger = live.get("larger_fixed")
            self.assertIsInstance(larger, list, name)
            lf_paths = [p.get("path") for p in larger]
            for req in LARGER:
                self.assertIn(req, lf_paths, f"{name} missing larger {req}")
            by_path = {p["path"]: p for p in larger}
            self.assertEqual(by_path["diagnostic.html"].get("price_usd"), 12000)
            self.assertEqual(by_path["commercial.html"].get("price_usd"), 30000)
            blob = path.read_text(encoding="utf-8")
            self.assertNotIn("buy.stripe.com", blob)
            self.assertNotIn("plink_", blob)
            self.assertIn("Larger fixed", live.get("note") or "")

    def test_receipt_exists(self) -> None:
        receipt = ROOT / "p" / f"{CLAIM}.md"
        self.assertTrue(receipt.is_file())
        text = receipt.read_text(encoding="utf-8")
        self.assertIn(CLAIM, text)
        for name in FILES:
            self.assertIn(name, text)


if __name__ == "__main__":
    unittest.main()
