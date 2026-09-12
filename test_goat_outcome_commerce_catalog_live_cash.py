#!/usr/bin/env python3
"""Hermetic: revenue/outcome_commerce/catalog.json top-level live_cash."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CATALOG = ROOT / "revenue" / "outcome_commerce" / "catalog.json"
CLAIM = "goat-outcome-commerce-catalog-json-live-cash-20260909-01"


class GoatOutcomeCommerceCatalogLiveCashTest(unittest.TestCase):
    def test_live_cash(self) -> None:
        self.assertTrue(CATALOG.is_file(), "catalog.json missing")
        data = json.loads(CATALOG.read_text(encoding="utf-8"))
        live = data.get("live_cash")
        self.assertIsInstance(live, dict, "live_cash must be a dict")
        products = live.get("products")
        self.assertIsInstance(products, list, "live_cash.products must be a list")
        self.assertTrue(len(products) > 0, "live_cash.products must be nonempty")
        cite = live.get("cite")
        self.assertIsInstance(cite, list, "live_cash.cite must be a list")
        self.assertIn(CLAIM, cite, f"cite must contain {CLAIM}")


if __name__ == "__main__":
    unittest.main()
