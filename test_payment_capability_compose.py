#!/usr/bin/env python3
"""Payment-capability leftover: hub, listing compose, honest failover."""
from __future__ import annotations

import copy
import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def _load(name: str, rel: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


CAP = _load("payment_capability_compose", "host/payment_capability.py")
LISTING = _load("listing_registry_compose", "host/listing_registry.py")


class PaymentCapabilityComposeTests(unittest.TestCase):
    def test_current_tree_stays_integrated(self):
        row = CAP.measure_root(str(ROOT))
        self.assertEqual(row["errors"], [], row["errors"])
        self.assertEqual(row["state"], "INTEGRATED")
        self.assertTrue(row["projected"]["has_lawfully_chargeable_path"])
        self.assertEqual(row["projected"]["collected_cash_usd"], 0)

    def test_dead_stripe_policy_is_integrated_not_invented(self):
        registry = json.loads(
            (ROOT / "revenue" / "payment_capability" / "registry.json").read_text(
                encoding="utf-8"
            )
        )
        dead = copy.deepcopy(registry)
        for rail in dead["rails"]:
            if rail["provider"] == "stripe":
                rail["capability_state"] = "INERT_CHARGES_DISABLED"
                rail["charges_enabled"] = False
                rail["payouts_enabled"] = False
                rail["public_presentation"] = "INERT"
        projected = CAP.project(dead)
        self.assertEqual(CAP.storefront_policy_errors(projected), [])
        self.assertFalse(projected["has_public_storefront"])
        self.assertFalse(projected["has_lawfully_chargeable_path"])
        self.assertEqual(projected["active_storefront_rail_id"], "")
        self.assertTrue(projected["failover_owner_actions"])
        self.assertEqual(projected["collected_cash_usd"], 0)

    def test_listing_registry_composes_payment_capability(self):
        self.assertIn(
            "revenue/payment_capability/registry.json", LISTING.DOES_NOT_REPLACE
        )
        self.assertTrue(LISTING.payment_capability_public_stripe(ROOT))
        catalog = LISTING.load_catalog()
        checkout = LISTING.load_checkout()
        tip = next(row for row in catalog["listings"] if row["id"] == "sku-tip-20260826")
        charge = LISTING.checkout_for("sku-tip-20260826", tip, checkout, ROOT)
        self.assertTrue(charge["commons_rail"])
        self.assertEqual(charge["state"], "ACTIVE_CHARGEABLE")

    def test_listing_failsover_when_registry_stripe_is_inert(self):
        catalog = LISTING.load_catalog()
        checkout = LISTING.load_checkout()
        tip = next(row for row in catalog["listings"] if row["id"] == "sku-tip-20260826")
        original = LISTING.payment_capability_public_stripe

        def _dead(_root=None):
            return False

        LISTING.payment_capability_public_stripe = _dead
        try:
            charge = LISTING.checkout_for("sku-tip-20260826", tip, checkout, ROOT)
        finally:
            LISTING.payment_capability_public_stripe = original
        self.assertFalse(charge["commons_rail"])
        self.assertEqual(charge["state"], "NOT_CHARGEABLE_ON_THIS_SURFACE")
        self.assertIsNone(charge["url"])

    def test_resource_and_profitability_and_features_cite_the_registry(self):
        ledger = json.loads(
            (ROOT / "ground" / "RESOURCE_LEDGER.json").read_text(encoding="utf-8")
        )
        names = [row["name"] for row in ledger["surfaces"]]
        self.assertIn("payment-capability-registry", names)
        row = next(r for r in ledger["surfaces"] if r["name"] == "payment-capability-registry")
        self.assertEqual(row["stage"], "PRODUCING")
        self.assertEqual(row["condition"], "CONSTRAINED")
        profit = (ROOT / "ground" / "PROFITABILITY_BUILD_MAP.md").read_text(encoding="utf-8")
        self.assertIn("payment-capability.html", profit)
        features = (ROOT / "ground" / "FEATURES.md").read_text(encoding="utf-8")
        self.assertIn("PAYMENT_CAPABILITY", features)
        commerce = (ROOT / "ground" / "COMMERCE.md").read_text(encoding="utf-8")
        self.assertIn("payment-capability.html", commerce)
        feature = ROOT / "features" / "registry" / "payment-capability-hub-failover-20260828-02.json"
        self.assertTrue(feature.is_file(), "feature tracker row must exist")
        row = json.loads(feature.read_text(encoding="utf-8"))
        self.assertEqual(row["id"], "payment-capability-hub-failover-20260828-02")
        self.assertEqual(row["public_entrypoint"], "payment-capability.html")


if __name__ == "__main__":
    unittest.main()
