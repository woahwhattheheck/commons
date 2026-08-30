#!/usr/bin/env python3
"""Contract tests for the Commons public arbitrage scout."""

import json
import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parent


class ArbitrageScoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.page = (ROOT / "arbitrage.html").read_text(encoding="utf-8")
        cls.schema = json.loads((ROOT / "revenue/arbitrage/opportunity.schema.json").read_text(encoding="utf-8"))

    def test_schema_is_fail_closed_and_requires_both_sides(self):
        self.assertFalse(self.schema["additionalProperties"])
        required = set(self.schema["required"])
        self.assertTrue({"source_side", "buyer_side", "economics", "evidence", "execution_boundary"} <= required)
        boundary = self.schema["properties"]["execution_boundary"]["properties"]
        self.assertEqual(boundary["automatic_purchase"]["const"], False)
        self.assertEqual(boundary["automatic_trade"]["const"], False)
        self.assertEqual(boundary["provider_authorization_required"]["const"], True)
        self.assertEqual(boundary["cash_claimed"]["const"], False)

    def test_categories_are_bounded_to_commons_work(self):
        categories = self.schema["properties"]["category"]["enum"]
        self.assertEqual(categories, [
            "SERVICE_DELIVERY", "COMPUTE_CAPACITY", "DATA_LICENSE",
            "PUBLIC_PROCUREMENT", "MARKETPLACE_FULFILLMENT", "EXPERTISE",
        ])
        self.assertNotIn("SECURITIES", categories)
        self.assertNotIn("CRYPTO", categories)

    def test_page_calculator_uses_full_unit_cost(self):
        self.assertIn("var unitEdge = sell - buy - fees - delivery;", self.page)
        self.assertIn("totalEdge: unitEdge * quantity", self.page)
        self.assertIn("MEASURED_POSITIVE_BEFORE_TAX", self.page)
        self.assertIn("NO_POSITIVE_EDGE_MEASURED", self.page)
        self.assertIn("this is not cash", self.page)

    def test_page_is_open_and_non_executing(self):
        self.assertIn('name="to" value="OFFER"', self.page)
        self.assertIn('name="board" value="OFFER"', self.page)
        self.assertIn('src="./carrier.js?v=20260824a"', self.page)
        self.assertIn("No login", self.page)
        self.assertIn("places no trade, purchases nothing", self.page)
        self.assertIn("License-blocked archives remain blocked", self.page)

    def test_public_intake_requires_source_and_buyer_urls(self):
        for field in (
            "CATEGORY:", "PUBLIC_USE_CASE:", "SOURCE_SIDE_PUBLIC_URL:",
            "BUYER_SIDE_PUBLIC_URL:", "OBSERVED_AT:", "PRICE_VALID_UNTIL:",
            "UNIT_BUY_COST:", "UNIT_SELL_REVENUE:", "UNIT_FEES:",
            "UNIT_DELIVERY_COST:", "QUANTITY:", "RIGHTS_OR_PROVIDER_TERMS:",
            "PUBLIC_CONTACT_URL:",
        ):
            self.assertIn(field, self.page)

    def test_commerce_links_scout(self):
        commerce = (ROOT / "commerce.html").read_text(encoding="utf-8")
        self.assertIn('<a href="./arbitrage.html">arbitrage scout</a>', commerce)


if __name__ == "__main__":
    unittest.main()
