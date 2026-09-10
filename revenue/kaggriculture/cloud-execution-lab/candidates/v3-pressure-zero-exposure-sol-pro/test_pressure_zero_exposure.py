# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from copy import deepcopy
from itertools import product
import json
import math
import unittest

from pressure_zero_exposure import (
    BARRIER,
    CERTIFIED_ZERO,
    EXPOSED,
    certify_zero_exposure,
    stable_certified_partition,
)


def market_for(item: str, inventory: int, visible: int | float):
    return {
        "prices": {item: visible},
        "inventory": {item: inventory},
        "params": None,
    }


def table_quote(item: str, inventory: int, params, *, expected: str, stock: int, curve):
    del params
    if item != expected:
        raise KeyError(item)
    return curve[inventory - stock]


class ZeroExposureTests(unittest.TestCase):
    def test_rounded_plateau_proxy_zero_is_not_a_certificate(self):
        # Exact pinned-engine public values from the strict-pressure reviewer:
        # TOMATO 9999->60, 10000->60, 10001->57.  A same-sized one-unit
        # proxy sees zero loss at delay 1, but delay 2 is harmful.
        stock = 9999
        curve = [60, 60, 57]
        quote = lambda item, at, params: table_quote(
            item, at, params, expected="TOMATO", stock=stock, curve=curve
        )
        cert = certify_zero_exposure(
            ["SELL", "TOMATO", 1],
            market_for("TOMATO", stock, 60),
            quote,
            2,
        )
        self.assertEqual(cert.status, EXPOSED)
        self.assertEqual(cert.first_exposed_delay, 2)
        self.assertEqual(cert.baseline_receipt, 60)
        self.assertEqual(cert.bound_receipt, 57)

    def test_counterexample_partition_preserves_parent_order(self):
        stock = 9999
        curves = {
            "TOMATO": [60, 60, 57],
            "MILK": [169, 160, 150],
        }

        def quote(item, at, _params):
            return curves[item][at - stock]

        market = {
            "prices": {"TOMATO": 60, "MILK": 169},
            "inventory": {"TOMATO": stock, "MILK": stock},
            "params": None,
        }
        parent = [["SELL", "TOMATO", 1], ["SELL", "MILK", 1]]
        # The rejected proxy partition sees 0 versus 9 and moves MILK first.
        proxy = {
            row[1]: quote(row[1], stock, None) - quote(row[1], stock + 1, None)
            for row in parent
        }
        naive = sorted(parent, key=lambda row: -proxy[row[1]])
        self.assertEqual(proxy, {"TOMATO": 0, "MILK": 9})
        self.assertEqual(naive[0][1], "MILK")

        candidate, certs = stable_certified_partition(parent, market, quote, 2)
        self.assertEqual(candidate, parent)
        self.assertEqual([cert.status for cert in certs], [EXPOSED, EXPOSED])

    def test_truly_flat_lot_can_move_behind_exposed_lot(self):
        stock = 100
        curves = {
            "CARROT": [35, 35, 35, 35],
            "MILK": [160, 159, 158, 157],
        }

        def quote(item, at, _params):
            return curves[item][at - stock]

        market = {
            "prices": {"CARROT": 35, "MILK": 160},
            "inventory": {"CARROT": stock, "MILK": stock},
            "params": None,
        }
        parent = [["SELL", "CARROT", 1], ["SELL", "MILK", 1]]
        candidate, certs = stable_certified_partition(parent, market, quote, 3)
        self.assertEqual(candidate, [parent[1], parent[0]])
        self.assertEqual([cert.status for cert in certs], [CERTIFIED_ZERO, EXPOSED])

    def test_stability_duplicates_and_barriers(self):
        stock = 10
        curves = {
            "WHEAT": [25, 25, 25, 25],
            "MILK": [160, 159, 158, 157],
            "WOOL": [200, 199, 198, 197],
        }

        def quote(item, at, _params):
            return curves[item][at - stock]

        market = {
            "prices": {key: values[0] for key, values in curves.items()},
            "inventory": {key: stock for key in curves},
            "params": None,
        }
        flat_a = ["SELL", "WHEAT", 1]
        exposed_a = ["SELL", "MILK", 1]
        exposed_b = ["SELL", "WOOL", 1]
        flat_b = ["SELL", "WHEAT", 1]
        barrier = ["BUY_SEED", "WHEAT", 1]
        parent = [flat_a, exposed_a, exposed_b, flat_b, barrier, flat_a, exposed_b]
        original = deepcopy(parent)
        candidate, certs = stable_certified_partition(parent, market, quote, 3)
        self.assertEqual(parent, original)
        self.assertEqual(
            candidate,
            [exposed_a, exposed_b, flat_a, flat_b, barrier, exposed_b, flat_a],
        )
        self.assertEqual(certs[4].status, BARRIER)

    def test_zero_bound_is_a_complete_vacuous_certificate(self):
        stock = 20
        curve = [50, 40]
        quote = lambda item, at, params: table_quote(
            item, at, params, expected="EGG", stock=stock, curve=curve
        )
        cert = certify_zero_exposure(
            ["SELL", "EGG", 2], market_for("EGG", stock, 50), quote, 0
        )
        self.assertEqual(cert.status, CERTIFIED_ZERO)
        self.assertEqual(cert.quote_calls, 2)
        self.assertEqual(cert.baseline_receipt, 90)

    def test_quote_calls_are_linear_in_quantity_plus_bound(self):
        calls = []

        def quote(_item, inventory, _params):
            calls.append(inventory)
            return 100

        cert = certify_zero_exposure(
            ["SELL", "MELON", 7], market_for("MELON", 1000, 100), quote, 11
        )
        self.assertEqual(cert.status, CERTIFIED_ZERO)
        self.assertEqual(cert.quote_calls, 18)
        self.assertEqual(len(calls), 18)

    def test_nonmonotone_curve_is_a_barrier(self):
        stock = 7
        curve = [10, 11]
        quote = lambda item, at, params: table_quote(
            item, at, params, expected="WOOL", stock=stock, curve=curve
        )
        cert = certify_zero_exposure(
            ["SELL", "WOOL", 1], market_for("WOOL", stock, 10), quote, 1
        )
        self.assertEqual(cert.status, BARRIER)
        self.assertEqual(cert.reason, "quote_curve_not_nonincreasing")

    def test_visible_quote_mismatch_is_a_barrier(self):
        quote = lambda _item, _inventory, _params: 99
        cert = certify_zero_exposure(
            ["SELL", "WHEAT", 1], market_for("WHEAT", 10, 100), quote, 1
        )
        self.assertEqual(cert.status, BARRIER)
        self.assertEqual(cert.reason, "visible_quote_mismatch")

    def test_malformed_inputs_fail_closed(self):
        valid_market = market_for("WHEAT", 10, 25)
        quote = lambda _item, _inventory, _params: 25
        cases = [
            ([], valid_market, 1),
            (["SELL", "WHEAT", True], valid_market, 1),
            (["SELL", "UNKNOWN", 1], valid_market, 1),
            (["SELL", "WHEAT", 257], valid_market, 1),
            (["SELL", "WHEAT", 1], valid_market, True),
            (["SELL", "WHEAT", 1], valid_market, 257),
            (["SELL", "WHEAT", 1], {"prices": [], "inventory": {}}, 1),
        ]
        for order, market, bound in cases:
            with self.subTest(order=order, market=market, bound=bound):
                self.assertEqual(
                    certify_zero_exposure(order, market, quote, bound).status,
                    BARRIER,
                )

    def test_nonfinite_and_below_floor_quotes_fail_closed(self):
        for value in (float("nan"), float("inf"), 0, -1, True, "25"):
            with self.subTest(value=value):
                quote = lambda _item, _inventory, _params, value=value: value
                market = market_for("WHEAT", 10, 25)
                self.assertEqual(
                    certify_zero_exposure(
                        ["SELL", "WHEAT", 1], market, quote, 1
                    ).status,
                    BARRIER,
                )

    def test_certificate_is_strict_json_serializable(self):
        quote = lambda _item, _inventory, _params: 25
        cert = certify_zero_exposure(
            ["SELL", "WHEAT", 1], market_for("WHEAT", 10, 25), quote, 5
        )
        json.dumps(cert.to_dict(), allow_nan=False, sort_keys=True)

    def test_exhaustive_small_nonincreasing_curves_match_bruteforce_oracle(self):
        checked = 0
        stock = 30
        for quantity in range(1, 4):
            for bound in range(0, 4):
                length = quantity + bound
                for values in product(range(1, 5), repeat=length):
                    if any(left < right for left, right in zip(values, values[1:])):
                        continue
                    curve = list(values)
                    quote = lambda item, at, params, curve=curve: table_quote(
                        item,
                        at,
                        params,
                        expected="WHEAT",
                        stock=stock,
                        curve=curve,
                    )
                    baseline = sum(curve[:quantity])
                    expected = all(
                        sum(curve[delay : delay + quantity]) == baseline
                        for delay in range(bound + 1)
                    )
                    cert = certify_zero_exposure(
                        ["SELL", "WHEAT", quantity],
                        market_for("WHEAT", stock, curve[0]),
                        quote,
                        bound,
                    )
                    self.assertEqual(cert.status == CERTIFIED_ZERO, expected)
                    self.assertNotEqual(cert.status, BARRIER)
                    checked += 1
        self.assertGreater(checked, 350)

    def test_overflowing_receipt_is_a_barrier(self):
        # Individual quotes are finite, but the own-lot receipt is not.
        huge = 1e308
        quote = lambda _item, _inventory, _params: huge
        cert = certify_zero_exposure(
            ["SELL", "WHEAT", 2], market_for("WHEAT", 10, huge), quote, 1
        )
        self.assertEqual(cert.status, BARRIER)
        self.assertEqual(cert.reason, "receipt_overflow")


if __name__ == "__main__":
    unittest.main()
