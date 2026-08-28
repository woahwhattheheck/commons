#!/usr/bin/env python3
"""Contracts for the Commons canonical listing registry.

No fake listings, accounts, submissions, publication, buyers, or cash.
One row per (offer, surface). submit always forbidden.
Does not replace distribution, commerce, checkout, current-work, or profitability.
"""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
REG = ROOT / "revenue" / "listing_registry"


def load_mod():
    spec = importlib.util.spec_from_file_location(
        "commons_listing_registry", ROOT / "host" / "listing_registry.py"
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


MOD = load_mod()


class ListingRegistryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = MOD
        cls.catalog = cls.mod.load_catalog()
        cls.surfaces = cls.mod.load_surfaces()
        cls.checkout = cls.mod.load_checkout()
        cls.mcp = cls.mod.load_mcp()
        cls.registry = cls.mod.build_registry(
            cls.catalog, cls.surfaces, cls.checkout, cls.mcp
        )
        cls.assets = cls.mod.build_assets(
            cls.catalog, cls.surfaces, cls.checkout, cls.mcp, cls.registry
        )
        cls.rows = {row["id"]: row for row in cls.registry["listings"]}
        cls.surface_rows = {row["id"]: row for row in cls.surfaces["surfaces"]}

    def test_kind_and_honesty(self):
        self.assertEqual(self.registry["kind"], "COMMONS_LISTING_REGISTRY")
        self.assertEqual(self.registry["schema_version"], "listing-registry/v1")
        honesty = self.registry["honesty"]
        for flag in (
            "no_fake_listings", "no_fake_accounts", "no_fake_submissions",
            "no_fake_publication", "no_fake_buyers", "no_fake_revenue",
            "no_duplicate_posting", "no_unauthorized_submit", "no_terms_accepted",
        ):
            self.assertIs(honesty[flag], True, flag)

    def test_required_fields_on_every_listing(self):
        required = (
            "id", "offer_id", "sku", "evidence_packet", "chargeability_state",
            "submission_status", "published_status", "account_status", "owner",
            "url", "last_verified", "next_action", "duplicate",
        )
        for row in self.registry["listings"]:
            for field in required:
                self.assertIn(field, row, (row["id"], field))
            self.assertIs(row["submit_allowed"], False)
            self.assertIs(row["submitted"], False)
            self.assertIs(row["duplicate"], False)
            self.assertEqual(row["submission_status"], "NOT_SUBMITTED")
            self.assertNotEqual(row["published_status"], "EXTERNAL_LIVE")
            self.assertTrue(row["last_verified"])
            self.assertTrue(row["next_action"])
            self.assertIn("refs", row["evidence_packet"])
            self.assertTrue(row["evidence_packet"]["refs"])

    def test_no_duplicate_offer_surface(self):
        keys = [(r["offer_id"], r["surface_id"]) for r in self.registry["listings"]]
        self.assertEqual(len(keys), len(set(keys)))
        ids = [r["id"] for r in self.registry["listings"]]
        self.assertEqual(len(ids), len(set(ids)))

    def test_cartesian_size(self):
        products = len(self.catalog["listings"]) + 1
        surfaces = len(self.surfaces["surfaces"])
        self.assertEqual(self.registry["counts"]["listings"], products * surfaces)
        self.assertEqual(self.registry["counts"]["products"], products)
        self.assertGreaterEqual(surfaces, 17)

    def test_honest_counts(self):
        counts = self.registry["counts"]
        self.assertEqual(counts["external_live_listings"], 0)
        self.assertEqual(counts["submitted"], 0)
        self.assertEqual(counts["duplicate_postings"], 0)
        self.assertEqual(counts["verified_buyers"], 0)
        self.assertEqual(counts["verified_leads"], 0)
        self.assertEqual(counts["collected_cash_usd"], "0.00")
        self.assertEqual(self.assets["submitted"], 0)
        self.assertIs(self.assets["submit_allowed"], False)

    def test_submit_forbidden(self):
        with self.assertRaises(self.mod.ListingRegistryError) as ctx:
            self.mod.submit_listing()
        self.assertIn("SUBMIT_FORBIDDEN", str(ctx.exception))
        proc = subprocess.run(
            [sys.executable, str(ROOT / "host" / "listing_registry.py"), "submit"],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("SUBMIT_FORBIDDEN", proc.stderr)

    def test_does_not_replace_landed_roads(self):
        for path in self.registry["does_not_replace"]:
            self.assertTrue((ROOT / path).exists(), path)
        catalog = json.loads((ROOT / "revenue/outcome_commerce/catalog.json").read_text(encoding="utf-8"))
        self.assertEqual(catalog["kind"], "OUTCOME_COMMERCE_CATALOG")
        channels = json.loads((ROOT / "revenue/distribution/channels.json").read_text(encoding="utf-8"))
        self.assertEqual(channels["kind"], "COMMONS_DISTRIBUTION_LAYER")

    def test_github_marketplace_only_mcp_product(self):
        mcp = self.rows["commons-mcp__github-marketplace"]
        self.assertEqual(mcp["fit"], "FIT")
        self.assertEqual(mcp["published_status"], "NOT_PUBLISHED")
        self.assertIsNone(mcp["url"])
        self.assertEqual(mcp["chargeability_state"], "NOT_A_PRICED_SKU")
        self.assertEqual(mcp["account_status"], "NONE_IN_THIS_SESSION")
        for listing in self.catalog["listings"]:
            row = self.rows["%s__github-marketplace" % listing["id"]]
            self.assertEqual(row["fit"], "UNFIT", listing["id"])

    def test_mcp_directories_draft_only(self):
        for sid in (
            "mcp-so-directory", "smithery", "glama-mcp", "pulsemcp", "awesome-mcp-servers",
        ):
            row = self.rows["commons-mcp__%s" % sid]
            self.assertEqual(row["fit"], "FIT", sid)
            self.assertEqual(row["published_status"], "NOT_PUBLISHED", sid)
            self.assertIsNone(row["url"], sid)
            self.assertFalse(row["submitted"])
            asset = next(a for a in self.assets["assets"] if a["id"] == row["id"])
            lowered = asset["copy"].lower()
            self.assertIn("not submitted", lowered)
            self.assertNotIn("listed on mcp.so", lowered)
            self.assertIn("board reads", lowered)
            self.assertIn("append_post", lowered)
            self.assertIn("commerce.html", lowered)

    def test_survival_proof_upwork_blocked_account(self):
        row = self.rows["same-day-agent-survival-proof__upwork-project-catalog"]
        self.assertEqual(row["fit"], "FIT")
        self.assertEqual(row["package_state"], "PACKAGE_READY")
        self.assertEqual(row["listing_state"], "BLOCKED_PROVIDER_ACCOUNT")
        self.assertEqual(row["published_status"], "NOT_PUBLISHED")
        self.assertIsNone(row["url"])
        self.assertIn("Do not", row["next_action"])

    def test_micro_sku_unfit_upwork(self):
        row = self.rows["sku-tip-20260826__upwork-project-catalog"]
        self.assertEqual(row["fit"], "UNFIT")
        self.assertIsNone(row["url"])

    def test_commons_catalog_surface_published_not_marketplace_live(self):
        row = self.rows["sku-tip-20260826__commons-service-catalog"]
        self.assertEqual(row["fit"], "FIT")
        self.assertEqual(row["published_status"], "SURFACE_PUBLISHED")
        self.assertTrue(row["url"].startswith("https://woahwhattheheck.github.io/commons/"))
        self.assertEqual(row["chargeability_state"], "ACTIVE_CHARGEABLE")
        self.assertEqual(row["listing_state"], "SURFACE_LIVE")
        self.assertIs(row["submitted"], False)

    def test_external_surface_not_chargeable_even_with_stripe(self):
        row = self.rows["sku-tip-20260826__upwork-project-catalog"]
        self.assertEqual(row["chargeability_state"], "NOT_CHARGEABLE_ON_THIS_SURFACE")
        slack = self.rows["sku-tip-20260826__slack-commons"]
        self.assertEqual(slack["chargeability_state"], "NOT_CHARGEABLE_ON_THIS_SURFACE")
        self.assertEqual(slack["published_status"], "SURFACE_PUBLISHED")

    def test_procurement_blocked_registration(self):
        row = self.rows["sku-muhlnickel-titan-20260826__sam-gov-procurement"]
        self.assertEqual(row["fit"], "FIT")
        self.assertEqual(row["listing_state"], "BLOCKED_REGISTRATION")
        self.assertEqual(row["published_status"], "NOT_PUBLISHED")
        self.assertIsNone(row["url"])

    def test_github_about_owner_platform(self):
        row = self.rows["commons-mcp__github-about-topics"]
        self.assertEqual(row["fit"], "FIT")
        self.assertEqual(row["published_status"], "OWNER_PLATFORM_UNCLAIMED")
        self.assertEqual(row["account_status"], "OWNER_PLATFORM")
        self.assertIn("owner", row["next_action"].lower())

    def test_show_hn_draft_only(self):
        row = self.rows["same-day-agent-survival-proof__show-hn-post"]
        self.assertEqual(row["fit"], "FIT")
        self.assertEqual(row["published_status"], "NOT_PUBLISHED")
        self.assertIsNone(row["url"])
        tip = self.rows["sku-tip-20260826__show-hn-post"]
        self.assertEqual(tip["fit"], "UNFIT")

    def test_assets_ready_match_fit_and_forbid_live_claims(self):
        fit_ids = {r["id"] for r in self.registry["listings"] if r["fit"] == "FIT"}
        asset_ids = {a["id"] for a in self.assets["assets"]}
        self.assertEqual(fit_ids, asset_ids)
        for asset in self.assets["assets"]:
            self.assertIs(asset["submit_allowed"], False)
            self.assertIs(asset["submitted"], False)
            lowered = asset["copy"].lower()
            for needle in (
                "live on upwork", "listed on mcp.so", "we have buyers",
                "listing is live", "already submitted",
            ):
                self.assertNotIn(needle, lowered, (asset["id"], needle))

    def test_current_work_and_profitability_binds(self):
        self.assertEqual(
            self.registry["current_work_bind"]["ledger"], "ground/CURRENT_WORK.json"
        )
        self.assertTrue((ROOT / "ground/CURRENT_WORK.json").is_file())
        self.assertTrue((ROOT / "ground/PROFITABILITY_BUILD_MAP.md").is_file())
        items = " ".join(self.registry["profitability_bind"]["items"]).lower()
        self.assertIn("mcp.so", items)
        self.assertIn("github about", items)

    def test_export_matches_engine(self):
        exported = json.loads((REG / "registry.json").read_text(encoding="utf-8"))
        self.assertEqual(exported["kind"], self.registry["kind"])
        self.assertEqual(exported["counts"], self.registry["counts"])
        self.assertEqual(len(exported["listings"]), len(self.registry["listings"]))

    def test_cli_self_test(self):
        proc = subprocess.run(
            [sys.executable, str(ROOT / "host" / "listing_registry.py"), "--self-test"],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertTrue(payload["ok"])

    def test_public_html_door_exists(self):
        html = (ROOT / "listing-registry.html").read_text(encoding="utf-8")
        self.assertIn("listing-registry.js", html)
        self.assertIn("TRUST AFTER PROOF", html)
        self.assertIn("live marketplace listings", html.lower())
        js = (ROOT / "listing-registry.js").read_text(encoding="utf-8")
        self.assertIn("revenue/listing_registry/registry.json", js)

    def test_public_html_door_js_parses_and_escapes(self):
        js_path = ROOT / "listing-registry.js"
        js = js_path.read_text(encoding="utf-8")
        self.assertIn('"&": "&amp;"', js)
        self.assertIn('"<": "&lt;"', js)
        self.assertIn('">": "&gt;"', js)
        self.assertIn('&quot;', js)
        self.assertIn("&#39;", js)
        html = (ROOT / "listing-registry.html").read_text(encoding="utf-8")
        self.assertIn("listing-registry.js?v=20260828b", html)
        proc = subprocess.run(
            ["node", "--check", str(js_path)],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)


if __name__ == "__main__":
    unittest.main()
