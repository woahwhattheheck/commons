#!/usr/bin/env python3
"""Contracts for the Commons distribution layer.

No fake listings, accounts, approvals, customers, interest, revenue, or
provider readiness. The layer never submits. Buyer interest routes back to
canonical conversion pages. Unique files only; does not replace outcome commerce.
"""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path


ROOT = Path(__file__).resolve().parent
DIST = ROOT / "revenue" / "distribution"


def load_mod():
    spec = importlib.util.spec_from_file_location(
        "commons_distribution", ROOT / "host" / "distribution.py"
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


MOD = load_mod()


class DistributionLayerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = MOD
        cls.catalog = cls.mod.load_catalog()
        cls.channels = cls.mod.load_channels()
        cls.matrix = cls.mod.build_matrix(cls.catalog, cls.channels)
        cls.packages = cls.mod.build_packages(cls.catalog, cls.channels)
        cls.status = cls.mod.build_status(cls.catalog, cls.channels)
        cls.listings = {row["id"]: row for row in cls.catalog["listings"]}
        cls.channel_rows = {row["id"]: row for row in cls.channels["channels"]}

    def test_channels_load_and_refuse_submit_flag(self):
        self.assertEqual(self.channels["kind"], "COMMONS_DISTRIBUTION_LAYER")
        self.assertGreaterEqual(len(self.channels["channels"]), 12)
        for channel in self.channels["channels"]:
            self.assertIs(channel["submit_allowed"], False)

    def test_catalog_listings_all_appear(self):
        offer_ids = {p["offer_id"] for p in self.matrix["pairs"]}
        self.assertEqual(offer_ids, set(self.listings))
        self.assertEqual(self.matrix["offer_count"], 15)
        self.assertEqual(self.matrix["pair_count"], 15 * len(self.channels["channels"]))

    def test_does_not_replace_canonical_commerce(self):
        for path in self.channels["does_not_replace"]:
            self.assertTrue((ROOT / path).exists(), path)
        catalog = json.loads((ROOT / "revenue/outcome_commerce/catalog.json").read_text(encoding="utf-8"))
        self.assertEqual(catalog["kind"], "OUTCOME_COMMERCE_CATALOG")
        self.assertEqual(len(catalog["listings"]), 15)

    def test_micro_skus_unfit_marketplaces(self):
        for oid in (
            "sku-tip-20260826",
            "sku-seat-20260826",
            "sku-unlock-20260826",
            "sku-monthly-tip-20260826",
            "sku-boost-20260826",
        ):
            for cid in (
                "upwork-project-catalog",
                "upwork-job-feed",
                "contra-services",
                "fiverr-gig",
                "sam-gov-procurement",
                "github-marketplace",
            ):
                pair = self._pair(oid, cid)
                self.assertEqual(pair["fit"], "UNFIT", (oid, cid, pair))

    def test_survival_proof_fits_upwork_and_contra(self):
        for cid in ("upwork-project-catalog", "upwork-job-feed", "contra-services"):
            pair = self._pair("same-day-agent-survival-proof", cid)
            self.assertEqual(pair["fit"], "FIT", pair)
            self.assertEqual(pair["package_state"], "PACKAGE_READY")
            self.assertEqual(pair["listing_state"], "BLOCKED_PROVIDER_ACCOUNT")
            self.assertIs(pair["submit_allowed"], False)

    def test_survival_proof_fits_fiverr_but_blocked(self):
        pair = self._pair("same-day-agent-survival-proof", "fiverr-gig")
        self.assertEqual(pair["fit"], "FIT")
        self.assertEqual(pair["listing_state"], "BLOCKED_PROVIDER_ACCOUNT")

    def test_high_ticket_unfit_fiverr(self):
        for oid in (
            "production-survival-sprint",
            "gguf-diagnostic-10d-12k",
            "white-box-gguf-pilot-30d",
            "sku-muhlnickel-titan-20260826",
        ):
            pair = self._pair(oid, "fiverr-gig")
            self.assertEqual(pair["fit"], "UNFIT", oid)

    def test_titan_fits_procurement_blocked_registration(self):
        pair = self._pair("sku-muhlnickel-titan-20260826", "sam-gov-procurement")
        self.assertEqual(pair["fit"], "FIT")
        self.assertEqual(pair["listing_state"], "BLOCKED_REGISTRATION")

    def test_stripe_rail_recorded_not_marketplace_live(self):
        pair = self._pair("sku-tip-20260826", "stripe-payment-links")
        self.assertEqual(pair["fit"], "FIT")
        self.assertEqual(pair["listing_state"], "NOT_LISTED")
        self.assertIs(pair["submit_allowed"], False)
        self.assertIsNone(pair["blocked_reason"])
        pair2 = self._pair("same-day-agent-survival-proof", "stripe-payment-links")
        self.assertEqual(pair2["fit"], "UNFIT")

    def test_stripe_rail_fail_closed_without_payouts(self):
        listing = json.loads(json.dumps(self.listings["sku-tip-20260826"]))
        listing["checkout"]["account_payouts_enabled"] = False
        channel = self.channel_rows["stripe-payment-links"]
        pair = self.mod.fit_pair(listing, channel)
        self.assertEqual(pair["listing_state"], "BLOCKED_CHARGES_DISABLED")
        self.assertIs(pair["submit_allowed"], False)

    def test_commons_pages_are_surface_live_not_marketplace_live(self):
        pair = self._pair("same-day-agent-survival-proof", "commons-pages")
        self.assertEqual(pair["fit"], "FIT")
        self.assertEqual(pair["listing_state"], "SURFACE_LIVE")
        self.assertEqual(pair["channel_family"], "commons_surface")
        self.assertEqual(self.status["counts"]["live_marketplace_listings"], 0)

    def test_no_live_marketplace_listings(self):
        for pair in self.matrix["pairs"]:
            if pair["channel_family"] in {"public_marketplace", "developer_ecosystem"}:
                self.assertNotEqual(pair["listing_state"], "LIVE", pair)
                self.assertIs(pair["submit_allowed"], False)

    def test_packages_exist_only_for_fit_pairs(self):
        package_ids = {row["id"] for row in self.packages["packages"]}
        fit_ids = {p["id"] for p in self.matrix["pairs"] if p["fit"] == "FIT"}
        self.assertEqual(package_ids, fit_ids)
        self.assertGreaterEqual(self.packages["count"], 20)

    def test_packages_are_honest(self):
        forbidden = (
            "live on upwork",
            "live on fiverr",
            "live on contra",
            "listed on upwork",
            "customers are waiting",
            "approved seller",
        )
        for package in self.packages["packages"]:
            self.assertIs(package["listed"], False)
            self.assertIs(package["submitted"], False)
            self.assertIs(package["submit_allowed"], False)
            self.assertEqual(package["honesty"]["customers"], 0)
            self.assertEqual(package["honesty"]["leads"], 0)
            self.assertEqual(package["honesty"]["revenue_usd"], "0.00")
            self.assertIsNone(package["honesty"]["live_url"])
            blob = json.dumps(package).lower()
            for needle in forbidden:
                self.assertNotIn(needle, blob, package["id"])
            self.assertIn("not a live listing", package["channel_copy"].lower())
            self.assertTrue(package["conversion"]["human"].endswith(".html"))
            self.assertEqual(package["conversion"]["intake"], "OFFER")
            self.assertEqual(package["conversion"]["contact"], "tokenjunkielabs@gmail.com")

    def test_inbound_routes_to_canonical_conversion(self):
        listing = self.listings["same-day-agent-survival-proof"]
        channel = self.channel_rows["upwork-project-catalog"]
        inbound = self.mod.inbound_template(listing, channel)
        self.assertEqual(inbound["canonical_conversion"], "agent-rescue.html")
        self.assertEqual(inbound["intake_board"], "OFFER")
        self.assertIs(inbound["not_a_lead"], True)
        self.assertIs(inbound["verified_lead"], False)
        self.assertIn("do not open a second crm", inbound["crm"].lower())
        self.assertIn("CHANNEL: upwork-project-catalog", inbound["body"])
        self.assertIn("OFFER_ID: same-day-agent-survival-proof", inbound["body"])

    def test_submit_always_forbidden(self):
        with self.assertRaises(self.mod.DistributionError) as ctx:
            self.mod.submit_listing("upwork-project-catalog", "same-day-agent-survival-proof")
        self.assertIn("SUBMIT_FORBIDDEN", str(ctx.exception))

    def test_status_counts_are_measured_zeros_for_money_and_leads(self):
        counts = self.status["counts"]
        self.assertEqual(counts["live_marketplace_listings"], 0)
        self.assertEqual(counts["verified_leads"], 0)
        self.assertEqual(counts["verified_customers"], 0)
        self.assertEqual(counts["collected_cash_usd"], "0.00")
        self.assertGreater(counts["packages_ready"], 0)
        self.assertGreater(counts["live_commons_surfaces"], 0)

    def test_classify_offer_amounts(self):
        self.assertEqual(self.mod.classify_offer(self.listings["sku-tip-20260826"]), "micro_sku")
        self.assertEqual(self.mod.classify_offer(self.listings["same-day-agent-survival-proof"]), "bounded_service")
        self.assertEqual(self.mod.classify_offer(self.listings["gguf-diagnostic-10d-12k"]), "high_ticket_service")
        self.assertEqual(self.mod.classify_offer(self.listings["sku-whitebox-hour-20260826"]), "expertise_hour")
        self.assertEqual(self.mod.classify_offer(self.listings["sku-muhlnickel-titan-20260826"]), "high_ticket_product")
        self.assertEqual(self.mod.listing_amount(self.listings["same-day-agent-survival-proof"]), Decimal("2500.00"))
        self.assertEqual(self.mod.listing_amount(self.listings["gguf-diagnostic-10d-12k"]), Decimal("12000.00"))
        self.assertEqual(self.mod.listing_amount(self.listings["sku-whitebox-hour-20260826"]), Decimal("250.00"))

    def test_developer_channels_unfit_current_catalog(self):
        for cid in ("github-marketplace", "mcp-public-registry", "npm-public-registry", "huggingface-hub"):
            fits = [p for p in self.matrix["pairs"] if p["channel_id"] == cid and p["fit"] == "FIT"]
            self.assertEqual(fits, [], cid)

    def test_cli_validate_and_submit(self):
        validate = subprocess.run(
            [sys.executable, str(ROOT / "host" / "distribution.py"), "validate"],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(validate.returncode, 0, validate.stderr)
        payload = json.loads(validate.stdout)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["live_marketplace_listings"], 0)
        submit = subprocess.run(
            [sys.executable, str(ROOT / "host" / "distribution.py"), "submit"],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(submit.returncode, 2)
        self.assertIn("SUBMIT_FORBIDDEN", submit.stderr)

    def test_export_is_deterministic_and_committed(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_root = Path(tmp)
            (tmp_root / "revenue" / "distribution").mkdir(parents=True)
            (tmp_root / "revenue" / "outcome_commerce").mkdir(parents=True)
            (tmp_root / "revenue" / "outcome_commerce" / "catalog.json").write_text(
                (ROOT / "revenue" / "outcome_commerce" / "catalog.json").read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            (tmp_root / "revenue" / "distribution" / "channels.json").write_text(
                (DIST / "channels.json").read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            paths = self.mod.write_export(tmp_root)
            for name in ("matrix", "packages", "status"):
                produced = paths[name].read_text(encoding="utf-8")
                committed = (DIST / ("%s.json" % name)).read_text(encoding="utf-8")
                self.assertEqual(produced, committed, name)

    def test_refuses_float_money(self):
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as handle:
            json.dump({"kind": "COMMONS_DISTRIBUTION_LAYER", "x": 1.25}, handle)
            name = handle.name
        with self.assertRaises(self.mod.DistributionError):
            self.mod._load_json(name)

    def test_open_door_no_auth_gate_in_layer(self):
        text = (ROOT / "host" / "distribution.py").read_text(encoding="utf-8")
        html = (ROOT / "distribution.html").read_text(encoding="utf-8")
        for hay in (text, html):
            self.assertNotRegex(hay, r"requireAuth|login required|permission gate|api[-_]?key required")

    def test_browser_script_parses_and_escapes_dynamic_html(self):
        script = ROOT / "distribution.js"
        checked = subprocess.run(
            ["node", "--check", str(script)],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(checked.returncode, 0, checked.stderr)
        source = script.read_text(encoding="utf-8")
        for escaped in ("&amp;", "&lt;", "&gt;", "&quot;", "&#39;"):
            self.assertIn(escaped, source)

    def _pair(self, offer_id: str, channel_id: str) -> dict:
        for pair in self.matrix["pairs"]:
            if pair["offer_id"] == offer_id and pair["channel_id"] == channel_id:
                return pair
        self.fail("missing pair %s x %s" % (offer_id, channel_id))
        raise AssertionError


if __name__ == "__main__":
    unittest.main()
