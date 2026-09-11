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


class D1PublicSupplyOrderTest(unittest.TestCase):
    def test_public_signal_uses_only_strict_visible_yield(self):
        obs = observation(
            {"kind": "PLANT", "crop": "STRAWBERRY", "yield_units": 3},
            {"kind": "PASTURE", "animal": "SHEEP", "yield_units": 2},
            {"kind": "PLANT", "crop": "MELON", "yield_units": True},
            {"kind": "PLANT", "crop": "CARROT", "yield_units": "4"},
            {"kind": "WEED", "yield_units": 9},
        )
        self.assertEqual(public_rival_supply(obs), {"STRAWBERRY": 3, "WOOL": 2})

    def test_disabled_is_exact_parent_identity(self):
        action = {"farmer": ["PASS"], "hands": [], "market": [["SELL", "MILK", 2], ["SELL", "WOOL", 2]]}
        self.assertIs(apply_public_supply_order(observation(), action, enabled=False), action)

    def test_no_signal_is_exact_parent_identity(self):
        action = {"farmer": ["PASS"], "hands": [], "market": [["SELL", "MILK", 2], ["SELL", "WOOL", 2]]}
        self.assertIs(apply_public_supply_order(observation(None), action), action)

    def test_custom_market_params_fail_closed(self):
        obs = observation({"kind": "PASTURE", "animal": "SHEEP", "yield_units": 2})
        action = {"farmer": ["PASS"], "hands": [], "market": [["SELL", "MILK", 2], ["SELL", "WOOL", 2]]}
        self.assertIs(
            apply_public_supply_order(obs, action, {"marketParams": {"WOOL": {"base": 999}}}),
            action,
        )

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

    def test_noninteger_sell_quantity_terminates_leading_eligible_block(self):
        milk = ["SELL", "MILK", 2]
        malformed = ["SELL", "WOOL", "7"]
        strawberry = ["SELL", "STRAWBERRY", 4]
        action = {"farmer": ["PASS"], "hands": [], "market": [milk, malformed, strawberry]}
        obs = observation({"kind": "PLANT", "crop": "STRAWBERRY", "yield_units": 4})
        self.assertIs(apply_public_supply_order(obs, action), action)

    def test_wrong_farm_shape_fails_closed(self):
        action = {"farmer": ["PASS"], "hands": [], "market": [["SELL", "MILK", 2], ["SELL", "WOOL", 2]]}
        for obs in ({}, {"player": 0, "farms": []}, {"player": True, "farms": [{}, {}]}):
            with self.subTest(obs=obs):
                self.assertIs(apply_public_supply_order(obs, action), action)


if __name__ == "__main__":
    unittest.main()
