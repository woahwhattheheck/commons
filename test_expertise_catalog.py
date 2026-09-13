from __future__ import annotations

import copy
import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("expertise_catalog", ROOT / "host" / "expertise_catalog.py")
assert SPEC and SPEC.loader
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


class ExpertiseCatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog_path = ROOT / "revenue" / "expertise_catalog" / "catalog.json"
        cls.schema_path = ROOT / "revenue" / "expertise_catalog" / "catalog.schema.json"
        cls.page_path = ROOT / "expertise.html"
        cls.catalog = json.loads(cls.catalog_path.read_text(encoding="utf-8"))

    def test_catalog_validates(self):
        module.validate_catalog(self.catalog, root=ROOT)

    def test_schema_is_draft_2020_12_and_catalog_matches_when_jsonschema_available(self):
        schema = json.loads(self.schema_path.read_text(encoding="utf-8"))
        self.assertEqual(schema["$schema"], "https://json-schema.org/draft/2020-12/schema")
        try:
            import jsonschema
        except ImportError:
            return
        jsonschema.Draft202012Validator.check_schema(schema)
        jsonschema.validate(self.catalog, schema)

    def test_required_capability_set_is_explicit(self):
        caps = {row["capability"] for row in self.catalog["entries"]}
        self.assertTrue(module.REQUIRED_CAPABILITIES.issubset(caps))
        self.assertGreaterEqual(len(self.catalog["entries"]), len(module.REQUIRED_CAPABILITIES))

    def test_only_whitebox_hour_is_live_and_exact(self):
        live = [row for row in self.catalog["entries"] if row["commercial"]["mode"] == "LIVE_EXISTING_SKU"]
        self.assertEqual(len(live), 1)
        self.assertEqual(live[0]["id"], "expertise-whitebox-hour")
        self.assertEqual(live[0]["commercial"]["amount_usd"], "250.00")
        self.assertEqual(live[0]["commercial"]["unit"], "hour")
        self.assertEqual(live[0]["commercial"]["buyer_route"], "commerce.html#sku-whitebox-hour-20260826")
        self.assertNotIn("stripe.com", live[0]["commercial"]["buyer_route"])

    def test_quote_only_entries_carry_no_price_or_checkout(self):
        quote_only = [row for row in self.catalog["entries"] if row["commercial"]["mode"] == "QUOTE_ONLY"]
        self.assertEqual(len(quote_only), 7)
        for row in quote_only:
            self.assertIsNone(row["commercial"]["amount_usd"])
            self.assertIsNone(row["commercial"]["unit"])
            self.assertIsNone(row["commercial"]["checkout_reference"])
            self.assertTrue(row["commercial"]["buyer_route"].startswith("mailto:tokenjunkielabs@gmail.com?subject="))

    def test_money_truth_is_false(self):
        truth = self.catalog["truth_boundary"]
        for field in module.TRUTH_FALSE_FIELDS:
            self.assertIs(truth[field], False)

    def test_mutation_quote_only_price_is_rejected(self):
        bad = copy.deepcopy(self.catalog)
        bad["entries"][1]["commercial"]["amount_usd"] = "500.00"
        with self.assertRaises(module.CatalogError):
            module.validate_catalog(bad, root=ROOT)

    def test_mutation_direct_stripe_route_is_rejected(self):
        bad = copy.deepcopy(self.catalog)
        bad["entries"][0]["commercial"]["buyer_route"] = "https://buy.stripe.com/not-allowed-here"
        with self.assertRaises(module.CatalogError):
            module.validate_catalog(bad, root=ROOT)

    def test_mutation_missing_source_is_rejected(self):
        bad = copy.deepcopy(self.catalog)
        bad["entries"][2]["source_evidence"].append("revenue/does-not-exist.json")
        with self.assertRaises(module.CatalogError):
            module.validate_catalog(bad, root=ROOT)

    def test_mutation_non_string_list_item_is_rejected_as_catalog_error(self):
        bad = copy.deepcopy(self.catalog)
        bad["entries"][2]["source_evidence"].append({"not": "a path"})
        with self.assertRaises(module.CatalogError):
            module.validate_catalog(bad, root=ROOT)

    def test_public_page_has_all_entries_and_no_stripe_url(self):
        html = self.page_path.read_text(encoding="utf-8")
        self.assertNotIn("buy.stripe.com", html)
        self.assertNotIn("donate.stripe.com", html)
        for row in self.catalog["entries"]:
            self.assertEqual(html.count(f'data-expertise-id="{row["id"]}"'), 1)
        self.assertIn('href="./commerce.html#sku-whitebox-hour-20260826"', html)
        self.assertIn("Seven additional expertise lanes are quote-only", html)


if __name__ == "__main__":
    unittest.main()
