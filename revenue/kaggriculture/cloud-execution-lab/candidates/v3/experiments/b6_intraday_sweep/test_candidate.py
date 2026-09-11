from __future__ import annotations

import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import candidate as b6  # noqa: E402


PRODUCTS = ("WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON",
            "EGG", "MILK", "WOOL", "FERTILIZER")


def observation(step=34, *, shed=None, prices=None, inventory=None, player=0):
    shed_values = {item: 0 for item in PRODUCTS}
    shed_values.update(shed or {})
    price_values = {item: 100 for item in PRODUCTS}
    price_values.update(prices or {})
    tiles = [[None for _ in range(10)] for _ in range(10)]
    return {
        "step": step,
        "player": player,
        "farms": [{
            "tiles": tiles,
            "farmer": [4, 4],
            "hands": [],
            "money": 10000,
        }],
        "private": {
            "inventories": [dict(inventory or {})],
            "shed": shed_values,
        },
        "market": {"prices": price_values, "inventory": {}},
        "town": {"unlocked_shops": []},
    }


def action(*, market=None, farmer=None):
    return {
        "farmer": list(farmer or ["PASS"]),
        "hands": [],
        "market": [list(row) for row in (market or [])],
    }


class IntradaySweepTests(unittest.TestCase):
    def setUp(self):
        b6.reset_b6_state()

    def test_exact_v31_baseline_is_pinned(self):
        self.assertEqual(b6.base.SALE_HORIZON, 8)
        self.assertEqual(b6.base.OPEN_ROUNDTRIP, 0)
        self.assertIs(b6.base.ROW_ORDER, True)
        self.assertIs(b6.base.EVENING_FLUSH, True)
        self.assertEqual(b6.base.SALE_EXCLUDED, ("WHEAT",))
        self.assertIs(b6.base._V231_EARLY, True)

    def test_disabled_is_object_identity(self):
        obs = observation(shed={"WOOL": 4})
        original = action()
        result = b6.intraday_sweep(obs, original, enabled=False)
        self.assertIs(result, original)
        self.assertEqual(b6.B6_REPORT["activations"], 0)

    def test_day0_and_outside_window_are_identity(self):
        original = action()
        self.assertIs(
            b6.intraday_sweep(observation(step=10, shed={"WOOL": 4}), original),
            original,
        )
        self.assertIs(
            b6.intraday_sweep(observation(step=24 + 9, shed={"WOOL": 4}), original),
            original,
        )
        self.assertEqual(b6.B6_REPORT["activations"], 0)

    def test_sells_only_parent_flush_items_and_only_once_per_day(self):
        obs = observation(
            step=24 + 10,
            shed={"WOOL": 3, "MILK": 2, "WHEAT": 9, "FERTILIZER": 7, "EGG": 5},
            prices={"WOOL": 200, "MILK": 160},
        )
        original = action()
        result = b6.intraday_sweep(obs, original)
        self.assertEqual(result["market"], [["SELL", "WOOL", 3], ["SELL", "MILK", 2]])
        self.assertEqual(original["market"], [])
        self.assertEqual(b6.B6_REPORT["activations"], 1)
        self.assertEqual(b6.B6_REPORT["units_advanced"], 5)
        self.assertEqual(b6.B6_REPORT["sell_rows_added"], 2)
        self.assertEqual(b6.B6_REPORT["posted_quote_value"], 920)

        # Even if a synthetic fixture still shows stock next turn, the arm must not sweep twice.
        next_turn = observation(step=24 + 11, shed={"WOOL": 3, "MILK": 2})
        untouched = action()
        self.assertIs(b6.intraday_sweep(next_turn, untouched), untouched)
        self.assertEqual(b6.B6_REPORT["activations"], 1)

    def test_existing_parent_sell_is_subtracted_not_reordered(self):
        obs = observation(step=24 + 12, shed={"WOOL": 5}, prices={"WOOL": 200})
        original = action(market=[["SELL", "WOOL", 2], ["BUY_SEED", "WHEAT", 1]])
        result = b6.intraday_sweep(obs, original)
        self.assertEqual(
            result["market"],
            [["SELL", "WOOL", 3], ["SELL", "WOOL", 2], ["BUY_SEED", "WHEAT", 1]],
        )
        self.assertEqual(original["market"], [["SELL", "WOOL", 2], ["BUY_SEED", "WHEAT", 1]])

    def test_full_order_cap_declines_without_consuming_daily_chance(self):
        full = [["BUY_SEED", "WHEAT", 1] for _ in range(b6.base.MAX_ORDERS)]
        first = action(market=full)
        obs = observation(step=24 + 10, shed={"WOOL": 4})
        self.assertIs(b6.intraday_sweep(obs, first), first)
        self.assertEqual(b6.B6_REPORT["capacity_declines"], 1)
        self.assertEqual(b6.B6_REPORT["activations"], 0)

        # A later open slot in the same midday window can still activate.
        second = action()
        later = observation(step=24 + 11, shed={"WOOL": 4})
        result = b6.intraday_sweep(later, second)
        self.assertEqual(result["market"], [["SELL", "WOOL", 4]])
        self.assertEqual(b6.B6_REPORT["activations"], 1)

    def test_order_cap_keeps_all_parent_rows_and_takes_highest_quote_value_extras(self):
        parent = [["BUY_SEED", "WHEAT", 1] for _ in range(b6.base.MAX_ORDERS - 1)]
        original = action(market=parent)
        obs = observation(
            step=24 + 12,
            shed={"WOOL": 1, "MILK": 5, "MELON": 2},
            prices={"WOOL": 200, "MILK": 160, "MELON": 250},
        )
        result = b6.intraday_sweep(obs, original)
        # MILK quote-value 800 beats MELON 500 and WOOL 200 for the only free slot.
        self.assertEqual(result["market"][0], ["SELL", "MILK", 5])
        self.assertEqual(result["market"][1:], parent)
        self.assertEqual(len(result["market"]), b6.base.MAX_ORDERS)
        self.assertEqual(b6.B6_REPORT["capacity_declines"], 1)

    def test_uses_parent_projected_shed_for_same_turn_drop(self):
        obs = observation(
            step=24 + 13,
            shed={"WOOL": 1},
            inventory={"WOOL": 4},
            prices={"WOOL": 200},
        )
        original = action(farmer=["DROP"])
        result = b6.intraday_sweep(obs, original)
        self.assertEqual(result["market"], [["SELL", "WOOL", 5]])
        self.assertEqual(result["farmer"], ["DROP"])

    def test_game_restart_clears_per_player_daily_latch(self):
        first = b6.intraday_sweep(
            observation(step=24 + 10, shed={"WOOL": 2}), action()
        )
        self.assertEqual(first["market"], [["SELL", "WOOL", 2]])

        # New game: step moves backwards, resetting player memory.
        zero = action()
        self.assertIs(b6.intraday_sweep(observation(step=0, shed={"WOOL": 2}), zero), zero)
        second = b6.intraday_sweep(
            observation(step=24 + 10, shed={"WOOL": 2}), action()
        )
        self.assertEqual(second["market"], [["SELL", "WOOL", 2]])
        self.assertEqual(b6.B6_REPORT["activations"], 2)

    def test_low_or_zero_quote_is_not_swept(self):
        obs = observation(
            step=24 + 14,
            shed={"WOOL": 4, "MILK": 3},
            prices={"WOOL": 1, "MILK": 0},
        )
        original = action()
        self.assertIs(b6.intraday_sweep(obs, original), original)
        self.assertEqual(b6.B6_REPORT["activations"], 0)


if __name__ == "__main__":
    unittest.main()
