# SPDX-License-Identifier: Apache-2.0
import unittest

from row_shed import effective_quantity, order_sells


class RowShedContracts(unittest.TestCase):
    @staticmethod
    def price(item, level):
        # Deliberately simple monotone fixtures; production supplies R04._ro_price.
        slopes = {"WOOL": 4, "STRAWBERRY": 1, "MILK": 2}
        return max(1, 1000 - slopes[item] * (level - 10000))

    def test_effective_quantity_caps_tape_dump_to_projected_stock(self):
        self.assertEqual(effective_quantity(["SELL", "STRAWBERRY", 1000], {"STRAWBERRY": 8}), 8)
        self.assertEqual(effective_quantity(["SELL", "WOOL", 7], {"WOOL": 30}), 7)

    def test_requested_quantity_is_never_rewritten(self):
        market = [["SELL", "STRAWBERRY", 1000], ["SELL", "WOOL", 4]]
        original = [list(row) for row in market]
        result = order_sells(market, {"STRAWBERRY": 10000, "WOOL": 10000},
                             {"STRAWBERRY": 2, "WOOL": 4}, self.price,
                             {"STRAWBERRY": object(), "WOOL": object()})
        self.assertCountEqual(result, original)
        self.assertEqual(market, original)
        self.assertEqual(sorted(row[2] for row in result), [4, 1000])

    def test_row_shed_can_reverse_raw_quantity_priority(self):
        # Raw requested quantities favor the 1000-unit strawberry row.  The physical shed
        # has only 1 strawberry but 8 wool, so executable-impact ranking puts WOOL first.
        market = [["SELL", "STRAWBERRY", 1000], ["SELL", "WOOL", 8]]
        result = order_sells(market, {"STRAWBERRY": 10000, "WOOL": 10000},
                             {"STRAWBERRY": 1, "WOOL": 8}, self.price,
                             {"STRAWBERRY": object(), "WOOL": object()})
        self.assertEqual(result[0], ["SELL", "WOOL", 8])
        self.assertEqual(result[1], ["SELL", "STRAWBERRY", 1000])

    def test_only_contiguous_leading_sell_block_moves(self):
        market = [
            ["SELL", "STRAWBERRY", 1000],
            ["SELL", "WOOL", 8],
            ["HIRE"],
            ["SELL", "MILK", 1000],
        ]
        result = order_sells(market, {"STRAWBERRY": 10000, "WOOL": 10000, "MILK": 10000},
                             {"STRAWBERRY": 1, "WOOL": 8, "MILK": 99}, self.price,
                             {"STRAWBERRY": 1, "WOOL": 1, "MILK": 1})
        self.assertEqual(result[2:], market[2:])
        self.assertEqual(result[0], ["SELL", "WOOL", 8])

    def test_equal_scores_are_stable(self):
        def flat_price(item, level):
            return 10
        market = [["SELL", "WOOL", 5], ["SELL", "MILK", 5]]
        result = order_sells(market, {"WOOL": 10000, "MILK": 10000},
                             {"WOOL": 5, "MILK": 5}, flat_price, {"WOOL": 1, "MILK": 1})
        self.assertEqual(result, market)

    def test_malformed_projected_stock_fails_closed(self):
        market = [["SELL", "WOOL", 5], ["SELL", "MILK", 5]]
        for projected in ({"WOOL": True, "MILK": 5}, {"WOOL": -1, "MILK": 5},
                          {"WOOL": 5}, None):
            with self.subTest(projected=projected):
                self.assertIs(order_sells(market, {"WOOL": 10000, "MILK": 10000}, projected,
                                          self.price, {"WOOL": 1, "MILK": 1}), market)

    def test_bool_or_noninteger_order_quantity_fails_closed(self):
        for quantity in (True, 1.0, "1", -1):
            market = [["SELL", "WOOL", quantity], ["SELL", "MILK", 5]]
            with self.subTest(quantity=quantity):
                self.assertIs(order_sells(market, {"WOOL": 10000, "MILK": 10000},
                                          {"WOOL": 5, "MILK": 5}, self.price,
                                          {"WOOL": 1, "MILK": 1}), market)


if __name__ == "__main__":
    unittest.main()
