from __future__ import annotations

from html.parser import HTMLParser
import csv
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parent
OFFER = ROOT / "revenue" / "muhlnickel_inference" / "offer.json"
PAGE = ROOT / "attested-inference.html"
SHOPIFY = ROOT / "revenue" / "muhlnickel_inference" / "shopify_products.csv"
TOKEN_OFFER = ROOT / "revenue" / "muhlnickel_inference" / "token_capacity_offer.json"
TOKEN_SHOPIFY = ROOT / "revenue" / "muhlnickel_inference" / "shopify_token_capacity.csv"
FEATURE = ROOT / "features" / "registry" / "muhlnickel-attested-inference-shopify-20260830-01.json"


class StrictHTMLParser(HTMLParser):
    pass


class MuhlnickelInferenceOfferTests(unittest.TestCase):
    def setUp(self) -> None:
        self.offer = json.loads(OFFER.read_text(encoding="utf-8"))
        self.token_offer = json.loads(TOKEN_OFFER.read_text(encoding="utf-8"))
        self.page = PAGE.read_text(encoding="utf-8")

    def test_generated_token_ladder_undercuts_cited_cloud_output_rates(self) -> None:
        variants = self.token_offer["variants"]
        self.assertEqual([row["price_usd"] for row in variants], [1, 5, 20])
        self.assertEqual(
            [row["generated_tokens"] for row in variants],
            [10_000_000, 100_000_000, 1_000_000_000],
        )
        rates = [row["usd_per_million_generated_tokens"] for row in variants]
        cited = [
            row["usd_per_million_output_tokens"]
            for row in self.token_offer["competitive_snapshot"]["providers"]
        ]
        self.assertEqual(rates, [0.1, 0.05, 0.02])
        self.assertLess(max(rates), min(cited))
        self.assertFalse(self.token_offer["truth"]["model_quality_equivalence_claimed"])
        self.assertFalse(self.token_offer["truth"]["frontier_capacity_claimed"])

    def test_token_shopify_import_has_three_non_shipping_variants(self) -> None:
        with TOKEN_SHOPIFY.open(newline="", encoding="utf-8") as source:
            rows = list(csv.DictReader(source))
        self.assertEqual(len(rows), 3)
        self.assertEqual(
            [row["SKU"] for row in rows],
            ["MUHL-TOK-10M", "MUHL-TOK-100M", "MUHL-TOK-1B"],
        )
        self.assertEqual([row["Price"] for row in rows], ["1.00", "5.00", "20.00"])
        self.assertEqual({row["Requires shipping"] for row in rows}, {"false"})
        self.assertEqual({row["Fulfillment service"] for row in rows}, {"manual"})
        self.assertEqual(self.token_offer["commerce"]["state"], "SHOPIFY_IMPORT_READY")
        self.assertIsNone(self.token_offer["commerce"]["storefront_url"])

    def test_price_ladder_is_a_real_range(self) -> None:
        prices = [self.offer["entry_offer"]["price_usd"]] + [
            row["price_usd"] for row in self.offer["ladder"]
        ]
        self.assertEqual(prices, [500, 1500, 2500])
        self.assertGreater(len(set(prices)), 1)
        self.assertEqual(self.offer["product_id"], "muhlnickel-attested-inference-run")

    def test_fulfillment_binds_to_existing_machine_and_evidence(self) -> None:
        fulfillment = self.offer["fulfillment"]
        for path in (
            fulfillment["machine_path"],
            fulfillment["public_capability_source"],
            fulfillment["market_source"],
        ):
            self.assertTrue((ROOT / path).is_file(), path)
        self.assertTrue(fulfillment["receipt_required_before_run_claim"])

    def test_public_page_has_direct_intake_and_no_false_sale(self) -> None:
        parser = StrictHTMLParser()
        parser.feed(self.page)
        parser.close()
        for marker in ("10 million generated tokens for $1", "$500", "$1,500", "$2,500", "Send the task for scope confirmation", "Current buyer-side fit"):
            self.assertIn(marker, self.page)
        for field in ("buyer_contacted_for_this_offer", "accepted_scope", "paid"):
            self.assertFalse(self.offer["truth"][field])
        self.assertEqual(self.offer["truth"]["cash_usd"], 0)
        self.assertFalse(self.offer["truth"]["cloud_runtime_executed"])
        self.assertFalse(self.offer["truth"]["shopify_product_published"])

    def test_shopify_import_has_three_non_shipping_service_variants(self) -> None:
        with SHOPIFY.open(newline="", encoding="utf-8") as source:
            rows = list(csv.DictReader(source))
        self.assertEqual(len(rows), 3)
        self.assertEqual({row["URL handle"] for row in rows}, {"muhlnickel-attested-inference"})
        self.assertEqual(
            [row["Option1 value"] for row in rows],
            ["One attested run", "Evaluated batch", "Bespoke compute job"],
        )
        self.assertEqual([row["Price"] for row in rows], ["500.00", "1500.00", "2500.00"])
        self.assertEqual({row["Requires shipping"] for row in rows}, {"false"})
        self.assertEqual({row["Fulfillment service"] for row in rows}, {"manual"})
        self.assertEqual({row["Status"] for row in rows}, {"active"})
        self.assertEqual(self.offer["commerce"]["provider"], "shopify")
        self.assertEqual(self.offer["commerce"]["state"], "SHOPIFY_IMPORT_READY")
        self.assertIsNone(self.offer["commerce"]["storefront_url"])

    def test_storefront_and_sitemap_surface_the_offer(self) -> None:
        commerce = (ROOT / "commerce.html").read_text(encoding="utf-8")
        sitemap = (ROOT / "sitemap.xml").read_text(encoding="utf-8")
        self.assertIn("sku-muhlnickel-attested-inference", commerce)
        self.assertIn("./attested-inference.html", commerce)
        self.assertIn("/attested-inference.html", sitemap)

    def test_feature_registry_tracks_the_shopify_road(self) -> None:
        feature = json.loads(FEATURE.read_text(encoding="utf-8"))
        self.assertEqual(feature["schema"], "commons-feature-v1")
        self.assertEqual(feature["public_entrypoint"], "attested-inference.html")
        self.assertIn("revenue/muhlnickel_inference/shopify_products.csv", feature["claimed_paths"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
