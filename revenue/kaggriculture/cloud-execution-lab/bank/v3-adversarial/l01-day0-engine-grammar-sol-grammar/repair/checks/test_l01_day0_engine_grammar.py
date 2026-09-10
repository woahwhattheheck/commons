# SPDX-License-Identifier: Apache-2.0
"""Predecessor killers for L01's engine-invalid day-zero basket."""
from __future__ import annotations

from collections import Counter
import copy
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import l01_mechanics as l01  # noqa: E402


def flags(**on):
    result = {key: False for key in l01.FLAG_KEYS}
    result.update(on)
    return result


class L01Day0GrammarTests(unittest.TestCase):
    def route(self):
        return [{"farmer": ["PASS"], "hands": [], "market": [["BUY_PRODUCT", "WHEAT", 13]]}]

    def test_exact_shipped_basket_has_five_unsupported_products(self):
        wanted = [["BUY_PRODUCT", item, quantity] for item, quantity in l01.DAY0_BASKET]
        issues = l01.day0_basket_issues(wanted)
        self.assertEqual(issues, (
            (0, "unsupported_product:'CARROT'"),
            (1, "unsupported_product:'MELON'"),
            (2, "unsupported_product:'MILK'"),
            (3, "unsupported_product:'STRAWBERRY'"),
            (4, "unsupported_product:'TOMATO'"),
        ))

    def test_day0_flag_preserves_canonical_wheat_thirteen(self):
        route = self.route()
        routes = {"MAIN": route, "ALIAS": route}
        before = copy.deepcopy(routes)
        activations = Counter()
        reasons = []
        l01.patch_routes(routes, flags(DAY0BUY=True), activations, reasons)
        self.assertEqual(routes, before)
        self.assertEqual(activations, Counter())
        self.assertEqual(len(reasons), 1)
        self.assertTrue(reasons[0].startswith(l01.DAY0_REJECT_PREFIX))
        self.assertIn("unsupported_product:'MILK'", reasons[0])

    def test_repeated_rejection_is_idempotent(self):
        routes = {"MAIN": self.route()}
        before = copy.deepcopy(routes)
        activations = Counter()
        reasons = []
        for _ in range(3):
            l01.patch_routes(routes, flags(DAY0BUY=True), activations, reasons)
        self.assertEqual(routes, before)
        self.assertEqual(activations, Counter())
        self.assertEqual(len(reasons), 1)

    def test_supported_product_rows_pass_grammar_only(self):
        self.assertEqual(l01.day0_basket_issues([
            ["BUY_PRODUCT", "WHEAT", 13],
            ["BUY_PRODUCT", "FERTILIZER", 2],
        ]), ())

    def test_malformed_cap_and_quantity_fail_closed(self):
        self.assertIn((0, "noncanonical_quantity"), l01.day0_basket_issues([
            ["BUY_PRODUCT", "WHEAT", True],
        ]))
        self.assertIn((l01.MAX_ORDERS, "prefix_truncation"), l01.day0_basket_issues([
            ["BUY_PRODUCT", "WHEAT", 1] for _ in range(l01.MAX_ORDERS + 1)
        ]))
        self.assertIn((0, "unsupported_op"), l01.day0_basket_issues([
            ["BUY_SEED", "CARROT", 14],
        ]))

    def test_all_flags_off_remains_exact_identity(self):
        routes = {"MAIN": self.route()}
        before = copy.deepcopy(routes)
        activations = Counter()
        reasons = []
        l01.patch_routes(routes, flags(), activations, reasons)
        self.assertEqual(routes, before)
        self.assertEqual(activations, Counter())
        self.assertEqual(reasons, [l01.NOOP])


if __name__ == "__main__":
    unittest.main(verbosity=2)
