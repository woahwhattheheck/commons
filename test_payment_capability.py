#!/usr/bin/env python3
"""Provider-neutral payment rails stay fail-closed until chargeable."""
from __future__ import annotations

import copy
import importlib.util
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "payment_capability", ROOT / "host" / "payment_capability.py"
)
assert SPEC and SPEC.loader
capability = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(capability)


class PaymentCapability(unittest.TestCase):
    def test_self_test_failsover_without_pretending_a_url(self):
        self.assertEqual(capability.main(["--self-test"]), 0)

    def test_current_tree_keeps_stripe_chargeable_and_alternatives_inert(self):
        row = capability.measure_root(str(ROOT))
        self.assertEqual(row["errors"], [], row["errors"])
        self.assertEqual(row["state"], "INTEGRATED")
        projected = row["projected"]
        self.assertTrue(projected["has_lawfully_chargeable_path"])
        self.assertTrue(projected["has_public_storefront"])
        self.assertEqual(
            projected["active_storefront_rail_id"],
            "stripe-livemode-acct_1U6HI9ATH4EDE7XD",
        )
        self.assertEqual(projected["collected_cash_usd"], 0)
        self.assertIn("paypal-wallet-unmeasured", projected["inert_rails"])
        self.assertIn("github-sponsors-woahwhattheheck", projected["inert_rails"])
        self.assertIn("square-unmeasured", projected["inert_rails"])
        self.assertTrue(projected["failover_owner_actions"])
        public_skus = {
            link["sku"]
            for rail in projected["public_rails"]
            for link in rail["public_links"]
        }
        self.assertEqual(
            public_skus,
            {
                "sku-tip-20260826",
                "sku-seat-20260826",
                "sku-unlock-20260826",
                "sku-monthly-tip-20260826",
                "sku-boost-20260826",
                "sku-whitebox-hour-20260826",
                "sku-muhlnickel-titan-20260826",
            },
        )

    def test_stripe_fail_closed_does_not_activate_kyc_rails(self):
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
        projected = capability.project(dead)
        self.assertFalse(projected["has_public_storefront"])
        self.assertFalse(projected["has_lawfully_chargeable_path"])
        self.assertEqual(projected["active_storefront_rail_id"], "")
        self.assertTrue(projected["failover_owner_actions"])
        hosts = {action["url"] for action in projected["failover_owner_actions"]}
        self.assertTrue(any("paypal.com" in url for url in hosts))
        self.assertTrue(any("github.com" in url for url in hosts))
        self.assertTrue(any("squareup.com" in url for url in hosts))
        for rail in projected["rails"]:
            self.assertEqual(rail["public_links"], [])
            self.assertEqual(rail["public_presentation"], "INERT")

    def test_cli_exits_zero_on_current_tree(self):
        proc = subprocess.run(
            [
                sys.executable,
                str(ROOT / "host" / "payment_capability.py"),
                "--root",
                str(ROOT),
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["state"], "INTEGRATED")

    def test_static_html_stays_inert_and_pay_js_loads_registry(self):
        stripe_url = r"https://(?:buy|donate)\.stripe\.com/"
        for name in (
            "pay.html",
            "tips.html",
            "commerce.html",
            "payment-capability.html",
        ):
            html = (ROOT / name).read_text(encoding="utf-8")
            self.assertNotRegex(html, stripe_url)
            self.assertNotRegex(html, r"paypal\.me/")
            self.assertIn("mailto:tokenjunkielabs@gmail.com", html)
        page = (ROOT / "payment-capability.html").read_text(encoding="utf-8")
        self.assertIn("js-rail-list", page)
        self.assertIn("js-owner-actions", page)
        pay_js = (ROOT / "pay.js").read_text(encoding="utf-8")
        self.assertIn("payment_capability/registry.json", pay_js)
        self.assertIn("failover-owner-action", pay_js)

    def test_registry_records_settlement_without_routing_secrets(self):
        text = (ROOT / "revenue" / "payment_capability" / "registry.json").read_text(
            encoding="utf-8"
        )
        self.assertEqual(capability.forbidden_hits(text), [])
        registry = json.loads(text)
        stripe = registry["rails"][0]
        dest = stripe["settlement_destination"]
        self.assertEqual(dest["status"], "verified")
        self.assertEqual(dest["kind"], "stripe_external_account")
        self.assertEqual(dest["last4"], "7243")
        self.assertNotIn("031101279", text)
        self.assertNotRegex(text, r"routing[_\s-]?number\s+\d{9}")


if __name__ == "__main__":
    unittest.main()
