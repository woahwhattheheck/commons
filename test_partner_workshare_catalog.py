from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import unittest

from revenue.human_reply_workshare_kit.catalog import (
    PUBLIC_PACK_IDS,
    build_public_catalog,
    render_public_catalog_json,
)

ROOT = Path(__file__).resolve().parent


def _money(minor: int) -> str:
    return f"${minor // 100:,}"


class PartnerWorkshareCatalogContractTests(unittest.TestCase):
    def setUp(self):
        self.machine = json.loads((ROOT / "workshares.json").read_text(encoding="utf-8"))
        self.html = (ROOT / "workshares.html").read_text(encoding="utf-8")

    def test_machine_catalog_is_exact_code_owned_projection(self):
        self.assertEqual(self.machine, build_public_catalog())
        self.assertEqual(json.loads(render_public_catalog_json()), self.machine)

    def test_pack_set_and_economics_are_bounded(self):
        self.assertEqual(tuple(row["pack_id"] for row in self.machine["packs"]), PUBLIC_PACK_IDS)
        for row in self.machine["packs"]:
            with self.subTest(pack_id=row["pack_id"]):
                fee = row["fixed_fee"]
                days = row["delivery_business_days"]
                self.assertEqual(fee["currency"], "USD")
                self.assertEqual(fee["decimals"], 2)
                self.assertLessEqual(fee["min_minor"], fee["reference_minor"])
                self.assertLessEqual(fee["reference_minor"], fee["max_minor"])
                self.assertLessEqual(days["min"], days["reference"])
                self.assertLessEqual(days["reference"], days["max"])
                self.assertEqual(row["commercial_state"], "PROPOSED_NOT_ACCEPTED")

    def test_public_page_exposes_every_pack_and_reference_terms(self):
        for row in self.machine["packs"]:
            with self.subTest(pack_id=row["pack_id"]):
                self.assertIn(row["name"], self.html)
                self.assertIn(_money(row["fixed_fee"]["min_minor"]), self.html)
                self.assertIn(_money(row["fixed_fee"]["reference_minor"]), self.html)
                self.assertIn(_money(row["fixed_fee"]["max_minor"]), self.html)
                self.assertIn(f'{row["delivery_business_days"]["reference"]}-day reference', self.html)

    def test_public_page_has_inquiry_but_no_checkout_road(self):
        folded = self.html.casefold()
        for forbidden in ("buy.stripe.com", "data-checkout", "checkout-active"):
            self.assertNotIn(forbidden, folded)
        self.assertIn("mailto:tokenjunkielabs@gmail.com", self.html)
        self.assertIn("No checkout on this page", self.html)
        self.assertIn("No payment link is minted here", self.html)

    def test_catalog_hard_false_commercial_claims(self):
        self.assertEqual(self.machine["commercial_state"], "PROPOSED_NOT_ACCEPTED")
        self.assertFalse(self.machine["checkout_available"])
        for key in (
            "buyer_acceptance_claimed",
            "contract_claimed",
            "invoice_claimed",
            "payment_claimed",
            "revenue_claimed",
        ):
            self.assertIs(self.machine[key], False, key)
        self.assertIn("not evidence of a buyer", self.machine["truth_boundary"])

    def test_first_contact_excludes_sensitive_intake(self):
        rule = self.machine["contact"]["first_contact_rule"]
        for phrase in ("credentials", "production secrets", "regulated records", "confidential datasets"):
            self.assertIn(phrase, rule)
        self.assertIn("Do not send credentials", self.html)

    def test_static_page_binds_machine_and_source_receipts(self):
        self.assertIn('href="./workshares.json"', self.html)
        self.assertIn("Commons PR #15334", self.html)
        self.assertIn("revenue/human_reply_workshare_kit/", self.html)
        self.assertEqual(self.machine["source_release"]["pull_request"], 15334)
        self.assertEqual(
            self.machine["source_release"]["merge_sha"],
            "5b49ee7ee5ff731d1f94ef6d296f944cfd5e529a",
        )


class PartnerWorkshareCatalogOptimizedBridgeTests(unittest.TestCase):
    def test_contract_under_python_optimized_mode(self):
        completed = subprocess.run(
            [
                sys.executable,
                "-O",
                "-m",
                "unittest",
                "test_partner_workshare_catalog.PartnerWorkshareCatalogContractTests",
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(
            completed.returncode,
            0,
            msg=(completed.stdout + "\n" + completed.stderr).strip(),
        )


if __name__ == "__main__":
    unittest.main()
