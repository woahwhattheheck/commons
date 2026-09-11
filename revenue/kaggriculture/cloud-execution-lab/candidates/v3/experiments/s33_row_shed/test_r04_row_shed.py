# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import copy
import unittest

from r04_row_shed import order_sells, sellable_quantity


def linear_price(_item, inventory):
    return 100000 - int(inventory)


PARAMS = {"A": object(), "B": object(), "C": object()}


class RowShedDonorTests(unittest.TestCase):
    def test_sellable_quantity_caps_authored_dump_to_projected_stock(self):
        self.assertEqual(sellable_quantity(["SELL", "A", 1000], {"A": 7}), 7)
        self.assertEqual(sellable_quantity(["SELL", "A", 4], {"A": 7}), 4)

    def test_row_shed_can_reverse_legacy_1000_unit_ranking_error(self):
        market = [["SELL", "A", 1000], ["SELL", "B", 10]]
        ordered = order_sells(market, {"A": 0, "B": 0}, {"A": 1, "B": 10},
                              linear_price, PARAMS)
        self.assertEqual(ordered, [["SELL", "B", 10], ["SELL", "A", 1000]])

    def test_rows_and_quantities_are_never_mutated(self):
        market = [["SELL", "A", 1000], ["SELL", "B", 10], ["HIRE"], ["SELL", "C", 99]]
        before = copy.deepcopy(market)
        ordered = order_sells(market, {}, {"A": 1, "B": 10, "C": 99}, linear_price, PARAMS)
        self.assertEqual(market, before)
        self.assertCountEqual(ordered[:2], before[:2])
        self.assertEqual(ordered[2:], before[2:])
        self.assertEqual({tuple(row) for row in ordered[:2]}, {tuple(row) for row in before[:2]})

    def test_stock_covering_every_request_matches_requested_quantity_scoring(self):
        market = [["SELL", "A", 9], ["SELL", "B", 3]]
        bounded = order_sells(market, {}, {"A": 99, "B": 99}, linear_price, PARAMS)
        self.assertEqual(bounded, [["SELL", "A", 9], ["SELL", "B", 3]])

    def test_zero_or_missing_stock_scores_zero_and_sort_remains_stable(self):
        market = [["SELL", "A", 1000], ["SELL", "B", 1000]]
        self.assertEqual(order_sells(market, {}, {}, linear_price, PARAMS), market)

    def test_nonleading_sell_never_crosses_barrier(self):
        market = [["SELL", "A", 1], ["HIRE"], ["SELL", "B", 1000]]
        self.assertEqual(order_sells(market, {}, {"A": 1, "B": 1000}, linear_price, PARAMS),
                         market)


if __name__ == "__main__":
    unittest.main()
