# SPDX-License-Identifier: Apache-2.0
import unittest
from copy import deepcopy

from candidate import CURRENT_8E3, install as install_candidate
from row_shed import apply_row_shed, effective_quantity, order_sells


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
        # Raw requested quantities favor the 1000-unit strawberry row. The physical shed
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

    def test_apply_reorder_preserves_empty_slots_and_tail_indices(self):
        action = {
            "market": [
                ["SELL", "STRAWBERRY", 1000],
                ["SELL", "WOOL", 8],
                [],
                ["HIRE"],
                ["SELL", "MILK", 1000],
            ]
        }
        before = deepcopy(action)
        observation = {
            "market": {"inventory": {"STRAWBERRY": 10000, "WOOL": 10000, "MILK": 10000}}
        }

        class FakeR04:
            _RO_PARAMS = {"STRAWBERRY": object(), "WOOL": object(), "MILK": object()}
            _RO_I0 = 10000

            @staticmethod
            def FarmView(_observation):
                return object()

            @staticmethod
            def projected_shed(_action, _view):
                return {"STRAWBERRY": 1, "WOOL": 8, "MILK": 99}

        FakeR04._ro_price = staticmethod(self.price)
        result = apply_row_shed(observation, action, FakeR04, {})

        self.assertEqual(action, before)
        self.assertEqual(len(result["market"]), len(before["market"]))
        self.assertEqual(result["market"][:2], [before["market"][1], before["market"][0]])
        self.assertEqual(result["market"][2:], before["market"][2:])
        self.assertEqual(result["market"][2], [])
        self.assertEqual(result["market"][3], ["HIRE"])

    def test_equal_scores_are_stable(self):
        def flat_price(item, level):
            return 10
        market = [["SELL", "WOOL", 5], ["SELL", "MILK", 5]]
        result = order_sells(market, {"WOOL": 10000, "MILK": 10000},
                             {"WOOL": 5, "MILK": 5}, flat_price, {"WOOL": 1, "MILK": 1})
        self.assertEqual(result, market)

    def test_malformed_projection_falls_back_to_whole_block_inherited_sort(self):
        market = [["SELL", "STRAWBERRY", 1000], ["SELL", "WOOL", 8]]
        inventory = {"STRAWBERRY": 10000, "WOOL": 10000}
        known = {"STRAWBERRY": 1, "WOOL": 1}
        inherited = order_sells(market, inventory, None, self.price, known)
        self.assertEqual(inherited[0], ["SELL", "STRAWBERRY", 1000])
        malformed = (
            {"STRAWBERRY": 1},
            {"STRAWBERRY": 1, "WOOL": True},
            {"STRAWBERRY": 1, "WOOL": -1},
            None,
        )
        for projected in malformed:
            with self.subTest(projected=projected):
                self.assertEqual(order_sells(market, inventory, projected, self.price, known), inherited)

    def test_bool_or_noninteger_order_quantity_fails_closed(self):
        for quantity in (True, 1.0, "1", -1):
            market = [["SELL", "WOOL", quantity], ["SELL", "MILK", 5]]
            with self.subTest(quantity=quantity):
                self.assertIs(order_sells(market, {"WOOL": 10000, "MILK": 10000},
                                          {"WOOL": 5, "MILK": 5}, self.price,
                                          {"WOOL": 1, "MILK": 1}), market)

    def test_current_root_tuple_preserves_shipped_b5_h4_l3_and_sale_fert(self):
        self.assertTrue(CURRENT_8E3["row_order"])
        self.assertTrue(CURRENT_8E3["evening_flush"])
        self.assertTrue(CURRENT_8E3["sale_fertilizer"])
        self.assertTrue(CURRENT_8E3["no_late_sale_advance"])
        self.assertEqual(CURRENT_8E3["no_late_sale_advance_step"], 648)
        self.assertTrue(CURRENT_8E3["strawberry_topup"])
        self.assertTrue(CURRENT_8E3["b5_carrot_fertilizer"])
        self.assertTrue(CURRENT_8E3["b5_jit_fertilize"])

    def test_disabled_wrapper_delegates_native_tuple_without_recomposition(self):
        calls = []

        class FakeR04:
            @staticmethod
            def install(*args):
                calls.append(args)
                return object()

        result = install_candidate(FakeR04, row_shed=False)
        self.assertIsNotNone(result)
        self.assertEqual(len(calls), 1)
        # host, horizon, opening, row_order, evening_flush ... trailing B5 flags
        self.assertEqual(calls[0][1:5], (8, 0, True, True))
        self.assertEqual(calls[0][-2:], (True, True))


if __name__ == "__main__":
    unittest.main()
