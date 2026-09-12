#!/usr/bin/env python3
"""Keep browser checkout readiness aligned with the canonical Python projector."""
from __future__ import annotations

import copy
import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "checkout_capability", ROOT / "host" / "checkout_capability.py"
)
assert SPEC and SPEC.loader
capability = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(capability)


class PayCheckoutCapabilityParityTests(unittest.TestCase):
    def test_browser_account_ready_requires_the_canonical_provider_capabilities(self) -> None:
        pay_js = (ROOT / "pay.js").read_text(encoding="utf-8")
        self.assertIn('provider.card_payments === "active"', pay_js)
        self.assertIn('provider.transfers === "active"', pay_js)
        self.assertIn('if (!accountReady(snapshot)) return false;', pay_js)
        self.assertIn('var stripeReady = accountReady(snapshot);', pay_js)

        snapshot = json.loads(
            (ROOT / "revenue" / "checkout_capability" / "snapshot.json").read_text(
                encoding="utf-8"
            )
        )
        catalog = json.loads(
            (ROOT / "revenue" / "outcome_commerce" / "catalog.json").read_text(
                encoding="utf-8"
            )
        )
        sku = "sku-whitebox-hour-20260826"

        baseline = capability.project(snapshot, catalog)
        self.assertTrue(baseline["account_ready"])
        self.assertIn(sku, {row["sku"] for row in baseline["public_rails"]})

        for field in ("card_payments", "transfers"):
            with self.subTest(field=field):
                dead = copy.deepcopy(snapshot)
                dead["provider"][field] = "inactive"
                projected = capability.project(dead, catalog)
                self.assertFalse(projected["account_ready"])
                self.assertNotIn(sku, {row["sku"] for row in projected["public_rails"]})


if __name__ == "__main__":
    unittest.main()
