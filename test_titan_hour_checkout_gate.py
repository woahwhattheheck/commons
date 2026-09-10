#!/usr/bin/env python3
"""TITAN hour must reuse the canonical fail-closed White Box checkout road."""
from __future__ import annotations

import copy
import importlib.util
import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "checkout_capability", ROOT / "host" / "checkout_capability.py"
)
assert SPEC and SPEC.loader
capability = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(capability)


def field(text: str, name: str) -> str:
    match = re.search(rf"(?m)^{re.escape(name)}:\s*(\S+)\s*$", text)
    return match.group(1).strip("`") if match else ""


class TitanHourCheckoutGate(unittest.TestCase):
    def test_page_uses_canonical_slot_without_raw_stripe_url_or_checkout_override(self):
        html = (ROOT / "titan-hour.html").read_text(encoding="utf-8")
        pay_js = (ROOT / "pay.js").read_text(encoding="utf-8")
        sku = (ROOT / "land" / "sku-whitebox-hour-20260826.md").read_text(
            encoding="utf-8"
        )
        checkout = field(sku, "checkout")

        self.assertEqual(field(sku, "status"), "ACTIVE_CHARGEABLE")
        self.assertRegex(checkout, r"^https://(?:buy|donate)\.stripe\.com/[A-Za-z0-9]+$")
        self.assertNotIn('data-checkout-first="1"', html)
        self.assertIn('class="js-checkout-slot"', html)
        self.assertIn('data-sku="sku-whitebox-hour-20260826"', html)
        self.assertIn('src="./pay.js?v=20260902a"', html)
        self.assertIn("mailto:tokenjunkielabs@gmail.com", html)
        self.assertNotRegex(html, r"https://(?:buy|donate)\.stripe\.com/")
        self.assertNotIn(checkout, html)

        self.assertIn("if (!railEligible(snapshot, listing))", pay_js)
        self.assertIn("Provider rail is inert. Unverified URLs stay unpublished.", pay_js)
        self.assertIn("Catalog unavailable:", pay_js)
        self.assertIn("checkout.account_payouts_enabled !== true", pay_js)
        self.assertIn("inert_duplicate_urls", pay_js)
        self.assertIn("Start public intake, then pay", pay_js)
        self.assertIn("./commerce.html#", pay_js)

    def test_whitebox_stays_intake_first_and_fails_closed_when_provider_is_not_ready(self):
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

        self.assertEqual(catalog["funnels"][sku]["readiness"], "READY_FOR_QUALIFICATION")
        ready = capability.project(snapshot, catalog)
        ready_rows = {row["sku"]: row for row in ready["public_rails"]}
        self.assertIn(sku, ready_rows)
        self.assertTrue(ready_rows[sku]["chargeable"])
        self.assertEqual(ready_rows[sku]["public"], "EXPOSE_INTAKE_THEN_CHECKOUT")
        self.assertNotEqual(ready_rows[sku]["url"], "")
        self.assertNotIn(sku, ready["checkout_first_skus"])

        dead = copy.deepcopy(snapshot)
        dead["provider"]["payouts_enabled"] = False
        projected = capability.project(dead, catalog)
        dead_rows = {row["sku"]: row for row in projected["public_rails"]}
        self.assertNotIn(sku, dead_rows)
        self.assertFalse(projected["account_ready"])
        self.assertFalse(projected["payouts_enabled"])


if __name__ == "__main__":
    unittest.main()
