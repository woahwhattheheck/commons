#!/usr/bin/env python3
"""Contract tests for the Commons public arbitrage scout."""

import json
import pathlib
import re
import unittest


ROOT = pathlib.Path(__file__).resolve().parent
KIMI_RECORD = ROOT / "revenue/arbitrage/kimi-agent-survival-proof-20260830-01.json"
WHITEBOX_RECORD = ROOT / "revenue/arbitrage/whitebox-range-audit-20260830.json"


class ArbitrageScoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.page = (ROOT / "arbitrage.html").read_text(encoding="utf-8")
        cls.schema = json.loads((ROOT / "revenue/arbitrage/opportunity.schema.json").read_text(encoding="utf-8"))
        cls.kimi = json.loads(KIMI_RECORD.read_text(encoding="utf-8"))
        cls.whitebox = json.loads(WHITEBOX_RECORD.read_text(encoding="utf-8"))

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
        hub = (ROOT / "hub_pages.py").read_text(encoding="utf-8")
        asset_v = re.search(r'^ASSET_V\s*=\s*"([^"]+)"', hub, re.M).group(1)
        self.assertIn('src="./carrier.js?v=%s"' % asset_v, self.page)
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

    def test_quotable_candidate_cards_match_machine_records(self):
        self.assertEqual(self.page.count('id="quotable-candidates"'), 1)
        self.assertIn(
            "Opening a buyer page or checkout is not acceptance, payment, settlement, payout, or cash.",
            self.page,
        )
        ids = re.findall(r'data-opportunity-id="([^"]+)"', self.page)
        self.assertEqual(ids, [
            "kimi-agent-survival-proof-20260830-01",
            "whitebox-range-audit-20260830",
        ])
        expected = (
            (
                self.kimi,
                "./agent-rescue.html",
                "./revenue/arbitrage/kimi-agent-survival-proof-20260830-01.json",
            ),
            (
                self.whitebox,
                "./commercial.html",
                "./revenue/arbitrage/whitebox-range-audit-20260830.json",
            ),
        )
        for record, buyer_href, json_href in expected:
            self.assertEqual(record["state"], "QUOTABLE")
            self.assertGreater(record["economics"]["unit_edge_before_tax"], 0)
            self.assertIs(record["execution_boundary"]["cash_claimed"], False)
            oid = record["opportunity_id"]
            card = re.search(
                rf'<article class="card" data-opportunity-id="{re.escape(oid)}">.*?</article>',
                self.page,
                flags=re.S,
            )
            self.assertIsNotNone(card, oid)
            self.assertIn(f'href="{buyer_href}"', card.group(0))
            self.assertIn(f'href="{json_href}"', card.group(0))
            self.assertIn(
                "No buyer, acceptance, payment, settlement, payout, or cash is claimed.",
                card.group(0),
            )


class ArbitrageRecordTests(unittest.TestCase):
    """Measured opportunity records must conform to the fail-closed schema."""

    @classmethod
    def setUpClass(cls):
        cls.schema = json.loads((ROOT / "revenue/arbitrage/opportunity.schema.json").read_text(encoding="utf-8"))
        cls.record = json.loads((ROOT / "revenue/arbitrage/whitebox-range-audit-20260830.json").read_text(encoding="utf-8"))

    def test_record_has_exactly_the_schema_keys(self):
        self.assertEqual(set(self.record), set(self.schema["required"]))
        self.assertRegex(self.record["opportunity_id"], r"^[a-z0-9][a-z0-9-]{7,95}$")

    def test_record_category_and_state_are_in_enum(self):
        props = self.schema["properties"]
        self.assertIn(self.record["category"], props["category"]["enum"])
        self.assertIn(self.record["state"], props["state"]["enum"])

    def test_record_sides_match_side_def(self):
        for key in ("source_side", "buyer_side"):
            side = self.record[key]
            with self.subTest(side=key):
                self.assertEqual(set(side), {"description", "price_status"})
                self.assertIn(side["price_status"], ("UNKNOWN", "PUBLIC_OBSERVED", "WRITTEN_QUOTE", "CONTRACTED"))
                self.assertTrue(side["description"].strip())

    def test_record_economics_are_internally_exact(self):
        econ = self.record["economics"]
        self.assertEqual(set(econ), set(self.schema["properties"]["economics"]["required"]))
        self.assertRegex(econ["currency"], r"^[A-Z]{3}$")
        unit = econ["unit_sell_revenue"] - econ["unit_buy_cost"] - econ["unit_fees"] - econ["unit_delivery_cost"]
        self.assertAlmostEqual(unit, econ["unit_edge_before_tax"], places=6)
        self.assertAlmostEqual(unit * econ["quantity"], econ["total_edge_before_tax"], places=6)
        self.assertGreater(econ["quantity"], 0)
        self.assertGreater(econ["unit_edge_before_tax"], 0)

    def test_record_evidence_is_public_and_two_sided(self):
        evidence = self.record["evidence"]
        self.assertGreaterEqual(len(evidence), 2)
        sides = {row["side"] for row in evidence}
        self.assertIn("SOURCE", sides)
        self.assertIn("BUYER", sides)
        for row in evidence:
            with self.subTest(url=row["public_url"]):
                self.assertEqual(set(row), {"side", "public_url", "observed_at", "establishes"})
                self.assertTrue(row["public_url"].startswith("https://"))
                self.assertIn(row["side"], ("SOURCE", "BUYER", "FEE", "DELIVERY"))
                self.assertTrue(row["establishes"].strip())

    def test_record_executes_nothing_and_claims_no_cash(self):
        boundary = self.record["execution_boundary"]
        self.assertEqual(set(boundary), set(self.schema["properties"]["execution_boundary"]["required"]))
        self.assertIs(boundary["automatic_purchase"], False)
        self.assertIs(boundary["automatic_trade"], False)
        self.assertIs(boundary["provider_authorization_required"], True)
        self.assertIs(boundary["cash_claimed"], False)
        self.assertIsInstance(boundary["rights_cleared"], bool)
        self.assertNotEqual(self.record["state"], "SETTLED")


if __name__ == "__main__":
    unittest.main()
