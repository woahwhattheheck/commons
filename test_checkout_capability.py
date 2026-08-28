#!/usr/bin/env python3
"""Public checkout rails stay fail-closed until charges and payouts are proven."""
from __future__ import annotations

import copy
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "checkout_capability", ROOT / "host" / "checkout_capability.py"
)
assert SPEC and SPEC.loader
capability = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(capability)


class CheckoutCapability(unittest.TestCase):
    def test_self_test_hides_rails_when_charges_are_disabled(self):
        self.assertEqual(capability.main(["--self-test"]), 0)

    def test_current_tree_projects_seven_proven_rails_and_zero_cash(self):
        row = capability.measure_root(str(ROOT))
        self.assertEqual(row["errors"], [], row["errors"])
        self.assertEqual(row["state"], "INTEGRATED")
        projected = row["projected"]
        self.assertTrue(projected["account_ready"])
        self.assertTrue(projected["charges_enabled"])
        self.assertTrue(projected["payouts_enabled"])
        self.assertEqual(projected["collected_cash_usd"], 0)
        self.assertEqual(projected["owner_action_id"], "NONE")
        self.assertEqual(
            projected["checkout_first_skus"],
            ["sku-tip-20260826", "sku-monthly-tip-20260826"],
        )
        self.assertEqual(len(projected["public_rails"]), 7)
        self.assertEqual(len(projected["inert_urls"]), 3)

    def test_duplicate_urls_never_become_public_anchors(self):
        snapshot = json.loads(
            (ROOT / "revenue" / "checkout_capability" / "snapshot.json").read_text(
                encoding="utf-8"
            )
        )
        projected = capability.project(snapshot)
        public_urls = {row["url"] for row in projected["public_rails"]}
        for url in snapshot["inert_duplicate_urls"]:
            self.assertNotIn(url, public_urls)

    def test_cli_exits_zero_on_current_tree(self):
        proc = subprocess.run(
            [sys.executable, str(ROOT / "host" / "checkout_capability.py"), "--root", str(ROOT)],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["state"], "INTEGRATED")

    def test_renderer_and_host_require_payouts_and_keep_static_html_inert(self):
        js = (ROOT / "commerce.js").read_text(encoding="utf-8")
        pay_js = (ROOT / "pay.js").read_text(encoding="utf-8")
        self.assertIn("checkout.account_payouts_enabled !== true", js)
        self.assertIn("checkout.account_payouts_enabled !== true", pay_js)
        self.assertIn("inert_duplicate_urls", pay_js)
        self.assertIn("&amp;", pay_js)
        self.assertIn("&lt;", pay_js)
        self.assertIn("&quot;", pay_js)
        self.assertNotIn("sendBeacon", pay_js)
        self.assertNotIn("localStorage", pay_js)
        stripe_url = r"https://(?:buy|donate)\.stripe\.com/"
        for name in ("pay.html", "tips.html", "commerce.html"):
            html = (ROOT / name).read_text(encoding="utf-8")
            self.assertRegex(html, r"js-checkout-slot")
            self.assertIn("mailto:tokenjunkielabs@gmail.com", html)
            self.assertNotRegex(html, stripe_url)
            self.assertIn("pay.js", html)

    def test_missing_payouts_keeps_catalog_inert(self):
        snapshot = json.loads(
            (ROOT / "revenue" / "checkout_capability" / "snapshot.json").read_text(
                encoding="utf-8"
            )
        )
        dead = copy.deepcopy(snapshot)
        dead["provider"]["payouts_enabled"] = False
        projected = capability.project(dead)
        self.assertFalse(projected["account_ready"])
        self.assertTrue(all(row["public"] == "INERT" for row in projected["public_rails"]))
        self.assertTrue(all(row["url"] == "" for row in projected["public_rails"]))


if __name__ == "__main__":
    unittest.main()
