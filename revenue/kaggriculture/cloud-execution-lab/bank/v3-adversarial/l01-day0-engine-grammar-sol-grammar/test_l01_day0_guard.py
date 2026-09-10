# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from collections import Counter
import copy
import json
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import l01_day0_guard as guard  # noqa: E402


class CertificateTests(unittest.TestCase):
    def test_shipped_basket_has_five_unsupported_products(self):
        cert = guard.certify_buy_product_basket(guard.DAY0_ORDERS)
        self.assertFalse(cert.accepted)
        unsupported = [issue for issue in cert.issues if issue.code == "unsupported_product"]
        self.assertEqual([issue.index for issue in unsupported], [0, 1, 2, 3, 4])
        self.assertEqual([issue.detail for issue in unsupported], [
            repr("CARROT"), repr("MELON"), repr("MILK"), repr("STRAWBERRY"), repr("TOMATO")
        ])

    def test_supported_wheat_and_fertilizer_require_bound_cost(self):
        orders = [["BUY_PRODUCT", "WHEAT", 13], ["BUY_PRODUCT", "FERTILIZER", 2]]
        unbound = guard.certify_buy_product_basket(orders, starting_money=3000)
        self.assertFalse(unbound.accepted)
        self.assertEqual(unbound.issue_codes, ("unbound_price_ceiling",))
        bound = guard.certify_buy_product_basket(
            orders,
            starting_money=3000,
            unit_price_ceilings={"WHEAT": 30, "FERTILIZER": 40},
        )
        self.assertTrue(bound.accepted)
        self.assertEqual(bound.worst_case_cost, 470)

    def test_worst_case_over_budget_rejected(self):
        cert = guard.certify_buy_product_basket(
            [["BUY_PRODUCT", "WHEAT", 101]],
            starting_money=3000,
            unit_price_ceilings={"WHEAT": 30},
        )
        self.assertFalse(cert.accepted)
        self.assertIn("worst_case_over_budget", cert.issue_codes)
        self.assertEqual(cert.worst_case_cost, 3030)

    def test_order_prefix_truncation_rejected(self):
        orders = [["BUY_PRODUCT", "WHEAT", 1] for _ in range(11)]
        cert = guard.certify_buy_product_basket(orders, max_orders=10)
        self.assertFalse(cert.accepted)
        self.assertIn("prefix_truncation", cert.issue_codes)
        self.assertEqual(cert.executable_prefix_rows, 10)

    def test_non_product_operation_rejected(self):
        cert = guard.certify_buy_product_basket([["BUY_SEED", "CARROT", 1]])
        self.assertFalse(cert.accepted)
        self.assertEqual(cert.issue_codes, ("unsupported_op",))

    def test_quantity_must_be_canonical_positive_int(self):
        bad_values = [True, False, 0, -1, 1.0, "1", None]
        for value in bad_values:
            with self.subTest(value=value):
                cert = guard.certify_buy_product_basket([["BUY_PRODUCT", "WHEAT", value]])
                self.assertFalse(cert.accepted)
                self.assertIn("noncanonical_quantity", cert.issue_codes)

    def test_malformed_rows_rejected(self):
        for row in (None, [], ["BUY_PRODUCT"], ["BUY_PRODUCT", "WHEAT"],
                    ["BUY_PRODUCT", "WHEAT", 1, "extra"], "BUY_PRODUCT"):
            with self.subTest(row=row):
                cert = guard.certify_buy_product_basket([row])
                self.assertFalse(cert.accepted)
                self.assertIn("malformed_row", cert.issue_codes)

    def test_non_sequence_and_invalid_cap_fail_closed(self):
        cert = guard.certify_buy_product_basket(None, max_orders=0)
        self.assertFalse(cert.accepted)
        self.assertEqual(cert.issue_codes, ("invalid_max_orders", "orders_not_sequence"))

    def test_certificate_is_deterministic_json(self):
        first = guard.certify_buy_product_basket(guard.DAY0_ORDERS).as_dict()
        second = guard.certify_buy_product_basket(guard.DAY0_ORDERS).as_dict()
        self.assertEqual(
            json.dumps(first, sort_keys=True, separators=(",", ":")),
            json.dumps(second, sort_keys=True, separators=(",", ":")),
        )


class RouteGuardTests(unittest.TestCase):
    def route(self):
        return [{"farmer": ["PASS"], "hands": [], "market": [["BUY_PRODUCT", "WHEAT", 13]]}]

    def test_shipped_basket_rejected_without_route_mutation(self):
        route = self.route()
        before = copy.deepcopy(route)
        wanted = [list(row) for row in guard.DAY0_ORDERS]
        wanted_before = copy.deepcopy(wanted)
        activations = Counter()
        reasons = []
        changed, cert = guard.guarded_replace_step0(
            route, wanted=wanted, activations=activations, reasons=reasons
        )
        self.assertFalse(changed)
        self.assertFalse(cert.accepted)
        self.assertEqual(route, before)
        self.assertEqual(wanted, wanted_before)
        self.assertEqual(activations, Counter())
        self.assertEqual(reasons, [cert.rejection_reason])

    def test_rejection_is_idempotent_and_reason_is_not_duplicated(self):
        route = self.route()
        reasons = []
        for _ in range(3):
            changed, _ = guard.guarded_replace_step0(route, reasons=reasons)
            self.assertFalse(changed)
        self.assertEqual(route[0]["market"], [["BUY_PRODUCT", "WHEAT", 13]])
        self.assertEqual(len(reasons), 1)

    def test_fully_bound_legal_replacement_commits_once(self):
        route = self.route()
        wanted = [["BUY_PRODUCT", "WHEAT", 10], ["BUY_PRODUCT", "FERTILIZER", 2]]
        activations = Counter()
        reasons = []
        kwargs = {
            "wanted": wanted,
            "activations": activations,
            "reasons": reasons,
            "unit_price_ceilings": {"WHEAT": 30, "FERTILIZER": 40},
        }
        changed, cert = guard.guarded_replace_step0(route, **kwargs)
        self.assertTrue(changed)
        self.assertTrue(cert.accepted)
        self.assertEqual(route[0]["market"], wanted)
        self.assertEqual(activations, Counter(DAY0BUY=1))
        changed, cert = guard.guarded_replace_step0(route, **kwargs)
        self.assertFalse(changed)
        self.assertTrue(cert.accepted)
        self.assertEqual(activations, Counter(DAY0BUY=1))
        self.assertEqual(reasons, [])

    def test_allocation_is_complete_before_commit(self):
        route = self.route()
        before = copy.deepcopy(route)
        wanted = [["BUY_PRODUCT", "WHEAT", 1], object()]
        changed, cert = guard.guarded_replace_step0(
            route,
            wanted=wanted,
            unit_price_ceilings={"WHEAT": 30},
        )
        self.assertFalse(changed)
        self.assertFalse(cert.accepted)
        self.assertEqual(route, before)

    def test_missing_or_malformed_route_fails_closed(self):
        for route in ([], [None]):
            with self.subTest(route=route):
                before = copy.deepcopy(route)
                changed, cert = guard.guarded_replace_step0(
                    route,
                    wanted=[["BUY_PRODUCT", "WHEAT", 1]],
                    unit_price_ceilings={"WHEAT": 30},
                )
                self.assertFalse(changed)
                self.assertFalse(cert.accepted)
                self.assertEqual(route, before)

    def test_alias_call_does_not_repeat_activation(self):
        shared = self.route()
        routes = {"MAIN": shared, "ALIAS": shared}
        activations = Counter()
        kwargs = {
            "wanted": [["BUY_PRODUCT", "WHEAT", 10]],
            "activations": activations,
            "unit_price_ceilings": {"WHEAT": 30},
        }
        self.assertTrue(guard.guarded_replace_step0(routes["MAIN"], **kwargs)[0])
        self.assertFalse(guard.guarded_replace_step0(routes["ALIAS"], **kwargs)[0])
        self.assertEqual(activations, Counter(DAY0BUY=1))


if __name__ == "__main__":
    unittest.main(verbosity=2)
