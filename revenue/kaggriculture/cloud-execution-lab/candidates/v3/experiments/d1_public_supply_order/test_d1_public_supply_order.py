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


class EvaluatorStruct(dict):
    """Minimal exact model of reference/evaluator/evaluate.py::Struct."""

    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(key) from None

    def __setattr__(self, key, value):
        self[key] = value


def evaluator_structify(value):
    if isinstance(value, dict):
        return EvaluatorStruct({k: evaluator_structify(v) for k, v in value.items()})
    if isinstance(value, list):
        return [evaluator_structify(v) for v in value]
    return value


def observation(*tiles, player=0):
    board = [[None for _ in range(10)] for _ in range(10)]
    for index, tile in enumerate(tiles):
        if index >= 100:
            raise ValueError("test helper accepts at most one 10x10 board")
        y, x = divmod(index, 10)
        board[y][x] = tile
    return {
        "player": player,
        "farms": [
            {"tiles": [[None for _ in range(10)] for _ in range(10)]},
            {"tiles": board},
        ],
        "private": Poison(),
        "market": {"prices": {}},
    }


def action(*rows):
    return {"farmer": ["PASS"], "hands": [], "market": list(rows)}


class D1PublicSupplyOrderTest(unittest.TestCase):
    def test_public_signal_uses_only_strict_visible_yield(self):
        obs = observation(
            {"kind": "PLANT", "crop": "STRAWBERRY", "yield_units": 3},
            {"kind": "PASTURE", "animal": "SHEEP", "yield_units": 2},
            {"kind": "COOP", "animal": "GOOSE", "yield_units": 4},
            {"kind": "PASTURE", "animal": "COW", "yield_units": 5},
            {"kind": "WEED", "yield_units": 9},
            {"kind": "COOP"},
            {"kind": "PASTURE"},
            "LOCKED",
            None,
        )
        self.assertEqual(
            public_rival_supply(obs),
            {"STRAWBERRY": 3, "WOOL": 2, "EGG": 4, "MILK": 5},
        )

    def test_evaluator_struct_wrapping_preserves_plain_json_signal_and_action(self):
        plain = observation(
            {"kind": "PLANT", "crop": "STRAWBERRY", "yield_units": 3},
            {"kind": "PASTURE", "animal": "SHEEP", "yield_units": 2},
        )
        wrapped = evaluator_structify(plain)
        self.assertEqual(public_rival_supply(wrapped), public_rival_supply(plain))
        self.assertEqual(public_rival_supply(wrapped), {"STRAWBERRY": 3, "WOOL": 2})

        milk = ["SELL", "MILK", 2]
        wool = ["SELL", "WOOL", 2]
        parent = action(milk, wool)
        changed = apply_public_supply_order(
            wrapped,
            parent,
            evaluator_structify({"marketParams": {}}),
        )
        self.assertEqual(changed["market"], [wool, milk])
        self.assertIs(changed["market"][0], wool)
        self.assertIs(changed["market"][1], milk)

    def test_evaluator_struct_wrapping_does_not_weaken_malformed_fail_closed_rules(self):
        valid = {"kind": "PASTURE", "animal": "SHEEP", "yield_units": 2}
        malformed = {"kind": "PLANT", "crop": "CARROT", "yield_units": True}
        wrapped = evaluator_structify(observation(valid, malformed))
        self.assertEqual(public_rival_supply(wrapped), {})

        parent = action(["SELL", "MILK", 2], ["SELL", "WOOL", 2])
        custom = evaluator_structify({"marketParams": {"WOOL": {"base": 999}}})
        self.assertIs(apply_public_supply_order(evaluator_structify(observation(valid)), parent, custom), parent)

    def test_malformed_producing_counter_invalidates_whole_signal(self):
        valid = {"kind": "PLANT", "crop": "STRAWBERRY", "yield_units": 3}
        for bad in (True, 1.0, "1", None):
            with self.subTest(bad=bad):
                malformed = {"kind": "PLANT", "crop": "CARROT", "yield_units": bad}
                self.assertEqual(public_rival_supply(observation(valid, malformed)), {})

    def test_malformed_rival_board_shape_invalidates_whole_signal(self):
        valid = {"kind": "PLANT", "crop": "STRAWBERRY", "yield_units": 3}
        cases = []
        obs = observation(valid)
        obs["farms"][1]["tiles"].append("not-a-row")
        cases.append(obs)
        obs = observation(valid, 17)
        cases.append(obs)
        obs = observation(valid, {"kind": "PLANT", "crop": [], "yield_units": 1})
        cases.append(obs)
        obs = observation(valid, {"kind": "PASTURE", "animal": "DRAGON", "yield_units": 1})
        cases.append(obs)
        for bad_obs in cases:
            with self.subTest(bad_obs=bad_obs):
                self.assertEqual(public_rival_supply(bad_obs), {})

    def test_partial_or_ragged_board_cannot_authorize_from_visible_subset(self):
        valid = {"kind": "PLANT", "crop": "STRAWBERRY", "yield_units": 3}
        cases = []
        truncated = observation(valid)
        truncated["farms"][1]["tiles"].pop()
        cases.append(truncated)
        ragged = observation(valid)
        ragged["farms"][1]["tiles"][9].pop()
        cases.append(ragged)
        oversized = observation(valid)
        oversized["farms"][1]["tiles"].append([None for _ in range(10)])
        cases.append(oversized)
        for bad_obs in cases:
            with self.subTest(shape=[len(row) if isinstance(row, list) else None for row in bad_obs["farms"][1]["tiles"]]):
                self.assertEqual(public_rival_supply(bad_obs), {})

    def test_animal_signal_requires_legal_structure_kind(self):
        valid = {"kind": "PLANT", "crop": "STRAWBERRY", "yield_units": 3}
        malformed = (
            {"kind": "WEED", "animal": "SHEEP", "yield_units": 4},
            {"kind": "COOP", "animal": "SHEEP", "yield_units": 4},
            {"kind": "PASTURE", "animal": "GOOSE", "yield_units": 4},
            {"kind": "COOP", "animal": "COW", "yield_units": 4},
            {"animal": "SHEEP", "yield_units": 4},
        )
        for tile in malformed:
            with self.subTest(tile=tile):
                self.assertEqual(public_rival_supply(observation(valid, tile)), {})

    def test_unknown_or_conflicting_nonproducing_kind_invalidates_whole_signal(self):
        valid = {"kind": "PLANT", "crop": "STRAWBERRY", "yield_units": 3}
        malformed = (
            {"kind": "BARN"},
            {},
            {"kind": "WEED", "crop": "CARROT"},
            {"kind": "COOP", "crop": "CARROT"},
            {"kind": "PASTURE", "crop": "CARROT"},
        )
        for tile in malformed:
            with self.subTest(tile=tile):
                self.assertEqual(public_rival_supply(observation(valid, tile)), {})

    def test_disabled_is_exact_parent_identity(self):
        parent = action(["SELL", "MILK", 2], ["SELL", "WOOL", 2])
        self.assertIs(apply_public_supply_order(observation(), parent, enabled=False), parent)

    def test_no_signal_is_exact_parent_identity(self):
        parent = action(["SELL", "MILK", 2], ["SELL", "WOOL", 2])
        self.assertIs(apply_public_supply_order(observation(None), parent), parent)

    def test_custom_or_malformed_configuration_fails_closed(self):
        obs = observation({"kind": "PASTURE", "animal": "SHEEP", "yield_units": 2})
        parent = action(["SELL", "MILK", 2], ["SELL", "WOOL", 2])
        self.assertIs(
            apply_public_supply_order(obs, parent, {"marketParams": {"WOOL": {"base": 999}}}),
            parent,
        )
        for bad in ([], "bad", True, 1):
            with self.subTest(bad=bad):
                self.assertIs(apply_public_supply_order(obs, parent, bad), parent)

    def test_falsey_market_params_type_poison_fails_closed(self):
        obs = observation({"kind": "PASTURE", "animal": "SHEEP", "yield_units": 2})
        for market_params in ([], "", 0, False, 1, True, "custom"):
            with self.subTest(market_params=market_params):
                parent = action(["SELL", "MILK", 2], ["SELL", "WOOL", 2])
                self.assertIs(
                    apply_public_supply_order(obs, parent, {"marketParams": market_params}),
                    parent,
                )
        for default_config in ({}, {"marketParams": None}, {"marketParams": {}}):
            with self.subTest(default_config=default_config):
                parent = action(["SELL", "MILK", 2], ["SELL", "WOOL", 2])
                changed = apply_public_supply_order(obs, parent, default_config)
                self.assertEqual(changed["market"], [["SELL", "WOOL", 2], ["SELL", "MILK", 2]])

    def test_stable_promote_pressured_rows_only_inside_leading_sell_block(self):
        milk = ["SELL", "MILK", 4]
        strawberry = ["SELL", "STRAWBERRY", 3]
        wool = ["SELL", "WOOL", 2]
        hire = ["HIRE"]
        later = ["SELL", "CARROT", 8]
        market = [milk, strawberry, wool, hire, later]
        parent = {"farmer": ["PASS"], "hands": [["PASS"]], "market": market, "marker": object()}
        before = copy.deepcopy(parent)
        obs = observation(
            {"kind": "PASTURE", "animal": "SHEEP", "yield_units": 5},
            {"kind": "PLANT", "crop": "STRAWBERRY", "yield_units": 1},
        )
        changed = apply_public_supply_order(obs, parent)

        self.assertIsNot(changed, parent)
        self.assertEqual(changed["market"], [strawberry, wool, milk, hire, later])
        self.assertIs(changed["market"][0], strawberry)
        self.assertIs(changed["market"][1], wool)
        self.assertIs(changed["market"][2], milk)
        self.assertIs(changed["market"][3], hire)
        self.assertIs(changed["market"][4], later)
        self.assertIs(changed["farmer"], parent["farmer"])
        self.assertIs(changed["hands"], parent["hands"])
        self.assertIs(changed["marker"], parent["marker"])
        self.assertEqual(parent["market"], market)
        self.assertEqual(parent["market"], before["market"])

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
        changed = apply_public_supply_order(obs, action(*rows))
        self.assertEqual(changed["market"], [rows[1], rows[2], rows[0], rows[3]])

    def test_already_prioritized_returns_exact_parent_identity(self):
        wool = ["SELL", "WOOL", 2]
        milk = ["SELL", "MILK", 4]
        parent = action(wool, milk)
        obs = observation({"kind": "PASTURE", "animal": "SHEEP", "yield_units": 3})
        self.assertIs(apply_public_supply_order(obs, parent), parent)

    def test_noninteger_sell_quantity_terminates_leading_eligible_block(self):
        milk = ["SELL", "MILK", 2]
        malformed = ["SELL", "WOOL", "7"]
        strawberry = ["SELL", "STRAWBERRY", 4]
        parent = action(milk, malformed, strawberry)
        obs = observation({"kind": "PLANT", "crop": "STRAWBERRY", "yield_units": 4})
        self.assertIs(apply_public_supply_order(obs, parent), parent)

    def test_malformed_sell_product_never_hashes_or_reorders(self):
        obs = observation({"kind": "PASTURE", "animal": "SHEEP", "yield_units": 4})
        for product in ([], {}, True, 7, 1.0, "DRAGON_FRUIT"):
            with self.subTest(product=product):
                parent = action(["SELL", "MILK", 2], ["SELL", product, 1], ["SELL", "WOOL", 2])
                self.assertIs(apply_public_supply_order(obs, parent), parent)

    def test_partial_malformed_public_signal_cannot_trigger_reorder(self):
        obs = observation(
            {"kind": "PASTURE", "animal": "SHEEP", "yield_units": 4},
            {"kind": "PLANT", "crop": "CARROT", "yield_units": True},
        )
        parent = action(["SELL", "MILK", 2], ["SELL", "WOOL", 2])
        self.assertIs(apply_public_supply_order(obs, parent), parent)

    def test_wrong_farm_shape_fails_closed(self):
        parent = action(["SELL", "MILK", 2], ["SELL", "WOOL", 2])
        for obs in ({}, {"player": 0, "farms": []}, {"player": True, "farms": [{}, {}]}):
            with self.subTest(obs=obs):
                self.assertIs(apply_public_supply_order(obs, parent), parent)


if __name__ == "__main__":
    unittest.main()
