# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import copy
from pathlib import Path
import sys
import unittest


HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from d1_public_supply_order import apply_public_supply_order, public_rival_supply  # noqa: E402


class Poison:
    def __getattribute__(self, name):
        raise AssertionError(f"private state must not be read: {name}")

    def __getitem__(self, key):
        raise AssertionError(f"private state must not be read: {key}")


class DictLikeConfiguration:
    def __init__(self, values=None):
        self.values = dict(values or {})

    def get(self, key, default=None):
        return self.values.get(key, default)


def observation(*tiles, player=0):
    board = [list(tiles)]
    return {
        "player": player,
        "farms": [
            {"tiles": [[None for _ in tiles]]},
            {"tiles": board},
        ],
        "private": Poison(),
        "market": {"prices": {}},
    }


def sell_action():
    return {
        "farmer": ["PASS"],
        "hands": [],
        "market": [["SELL", "MILK", 2], ["SELL", "WOOL", 2]],
    }


class D1PublicSupplyOrderTest(unittest.TestCase):
    def test_public_signal_uses_only_strict_visible_yield(self):
        obs = observation(
            {"kind": "PLANT", "crop": "STRAWBERRY", "yield_units": 3},
            {"kind": "PASTURE", "animal": "SHEEP", "yield_units": 2},
            {"kind": "PLANT", "crop": "MELON", "yield_units": True},
            {"kind": "PLANT", "crop": "CARROT", "yield_units": "4"},
            {"kind": "PLANT", "crop": "NOT_A_PRODUCT", "yield_units": 8},
            {"kind": "WEED", "yield_units": 9},
        )
        self.assertEqual(public_rival_supply(obs), {"STRAWBERRY": 3, "WOOL": 2})

    def test_disabled_is_exact_parent_identity(self):
        action = sell_action()
        self.assertIs(apply_public_supply_order(observation(), action, enabled=False), action)

    def test_no_signal_is_exact_parent_identity(self):
        action = sell_action()
        self.assertIs(apply_public_supply_order(observation(None), action), action)

    def test_custom_market_params_fail_closed(self):
        obs = observation({"kind": "PASTURE", "animal": "SHEEP", "yield_units": 2})
        action = sell_action()
        for configuration in (
            {"marketParams": {"WOOL": {"base": 999}}},
            DictLikeConfiguration({"marketParams": {"WOOL": {"base": 999}}}),
        ):
            with self.subTest(configuration=configuration):
                self.assertIs(apply_public_supply_order(obs, action, configuration), action)

    def test_falsey_malformed_market_params_and_non_mapping_config_fail_closed(self):
        obs = observation({"kind": "PASTURE", "animal": "SHEEP", "yield_units": 2})
        for malformed in (False, 0, [], ""):
            with self.subTest(marketParams=malformed):
                action = sell_action()
                self.assertIs(
                    apply_public_supply_order(obs, action, {"marketParams": malformed}),
                    action,
                )
        action = sell_action()
        self.assertIs(apply_public_supply_order(obs, action, object()), action)

    def test_missing_none_or_empty_market_params_preserve_default_contract(self):
        obs = observation({"kind": "PASTURE", "animal": "SHEEP", "yield_units": 2})
        for configuration in (
            None,
            {},
            {"marketParams": None},
            {"marketParams": {}},
            DictLikeConfiguration(),
            DictLikeConfiguration({"marketParams": {}}),
        ):
            with self.subTest(configuration=configuration):
                action = sell_action()
                changed = apply_public_supply_order(obs, action, configuration)
                self.assertEqual(changed["market"], [action["market"][1], action["market"][0]])

    def test_stable_promote_pressured_rows_only_inside_leading_sell_block(self):
        milk = ["SELL", "MILK", 4]
        strawberry = ["SELL", "STRAWBERRY", 3]
        wool = ["SELL", "WOOL", 2]
        hire = ["HIRE"]
        later = ["SELL", "CARROT", 8]
        market = [milk, strawberry, wool, hire, later]
        action = {"farmer": ["PASS"], "hands": [["PASS"]], "market": market, "marker": object()}
        before = copy.deepcopy(action)
        obs = observation(
            {"kind": "PASTURE", "animal": "SHEEP", "yield_units": 5},
            {"kind": "PLANT", "crop": "STRAWBERRY", "yield_units": 1},
        )
        changed = apply_public_supply_order(obs, action)

        self.assertIsNot(changed, action)
        self.assertEqual(changed["market"], [strawberry, wool, milk, hire, later])
        self.assertIs(changed["market"][0], strawberry)
        self.assertIs(changed["market"][1], wool)
        self.assertIs(changed["market"][2], milk)
        self.assertIs(changed["market"][3], hire)
        self.assertIs(changed["market"][4], later)
        self.assertIs(changed["farmer"], action["farmer"])
        self.assertIs(changed["hands"], action["hands"])
        self.assertIs(changed["marker"], action["marker"])
        self.assertEqual(action["market"], market)
        self.assertEqual(action["market"], before["market"])

    def test_parent_order_retained_inside_pressure_and_quiet_groups(self):
        rows = [
            ["SELL", "MILK", 1],
            ["SELL", "WOOL", 7],
            ["SELL", "STRAWBERRY", 2],
            ["SELL", "CARROT", 9],
        ]
        obs = observation(
            {"kind": "PLANT", "crop": "STRAWBERRY", "yield_units": 99},
            {"kind": "PASTURE", "animal": "SHEEP", "yield_units": 1},
        )
        changed = apply_public_supply_order(obs, {"farmer": ["PASS"], "hands": [], "market": rows})
        self.assertEqual(changed["market"], [rows[1], rows[2], rows[0], rows[3]])

    def test_already_prioritized_returns_exact_parent_identity(self):
        wool = ["SELL", "WOOL", 2]
        milk = ["SELL", "MILK", 4]
        action = {"farmer": ["PASS"], "hands": [], "market": [wool, milk]}
        obs = observation({"kind": "PASTURE", "animal": "SHEEP", "yield_units": 3})
        self.assertIs(apply_public_supply_order(obs, action), action)

    def test_malformed_literal_sell_prefix_is_exact_parent_identity(self):
        obs = observation({"kind": "PASTURE", "animal": "SHEEP", "yield_units": 4})
        malformed_rows = (
            ["SELL", [], 1],
            ["SELL", "WOOL", "7"],
            ["SELL", "WOOL", True],
            ["SELL", "WOOL", 0],
            ["SELL", "NOT_A_PRODUCT", 3],
            ["SELL", "WOOL"],
        )
        for malformed in malformed_rows:
            with self.subTest(malformed=malformed):
                milk = ["SELL", "MILK", 2]
                strawberry = ["SELL", "STRAWBERRY", 4]
                action = {
                    "farmer": ["PASS"],
                    "hands": [],
                    "market": [milk, strawberry, malformed],
                }
                before = copy.deepcopy(action)
                result = apply_public_supply_order(obs, action)
                self.assertIs(result, action)
                self.assertEqual(action, before)

    def test_non_sell_row_ends_leading_block_without_touching_tail(self):
        wool = ["SELL", "WOOL", 2]
        milk = ["SELL", "MILK", 4]
        hire = ["HIRE"]
        malformed_tail = ["SELL", [], 1]
        action = {"farmer": ["PASS"], "hands": [], "market": [milk, wool, hire, malformed_tail]}
        obs = observation({"kind": "PASTURE", "animal": "SHEEP", "yield_units": 3})
        changed = apply_public_supply_order(obs, action)
        self.assertEqual(changed["market"], [wool, milk, hire, malformed_tail])
        self.assertIs(changed["market"][2], hire)
        self.assertIs(changed["market"][3], malformed_tail)

    def test_wrong_farm_shape_fails_closed(self):
        action = sell_action()
        for obs in ({}, {"player": 0, "farms": []}, {"player": True, "farms": [{}, {}]}):
            with self.subTest(obs=obs):
                self.assertIs(apply_public_supply_order(obs, action), action)


if __name__ == "__main__":
    unittest.main()
