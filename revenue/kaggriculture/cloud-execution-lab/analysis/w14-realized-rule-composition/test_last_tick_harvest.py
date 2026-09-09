#!/usr/bin/env python3
from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from last_tick_harvest import rewrite_last_tick_crop_harvest


EMPTY_COUNTS = {
    "CARROT": 0,
    "COW": 0,
    "EGG": 0,
    "FERTILIZER": 0,
    "GOOSE": 0,
    "MELON": 0,
    "MILK": 0,
    "SHEEP": 0,
    "STRAWBERRY": 0,
    "TOMATO": 0,
    "WHEAT": 0,
    "WOOL": 0,
}


def crop(yield_units: int = 2, name: str = "WHEAT") -> dict:
    return {
        "kind": "PLANT",
        "crop": name,
        "planted_day": 0,
        "yield_units": yield_units,
        "watered_today": True,
        "consecutive_unwatered": 0,
        "fertilized_until_day": -1,
        "max_lifespan_step": 120,
    }


def animal(yield_units: int = 2) -> dict:
    return {
        "kind": "PASTURE",
        "animal": "COW",
        "placed_day": 0,
        "yield_units": yield_units,
        "fed_today": True,
        "cared_today": True,
        "consecutive_unfed": 0,
        "pending_care_bonus": 1,
        "fertilizer_available": True,
    }


def fixture(
    *,
    farmer=(0, 0),
    hands=(),
    tiles=None,
    shed=None,
    inventories=None,
    hour=23,
    action=None,
):
    if tiles is None:
        tiles = [[crop(), None], [None, None]]
    if shed is None:
        shed = copy.deepcopy(EMPTY_COUNTS)
    if inventories is None:
        inventories = [{} for _ in range(1 + len(hands))]
    observation = {
        "player": 0,
        "step": hour,
        "hour": hour,
        "farms": [
            {
                "farmer": list(farmer),
                "hands": [list(value) for value in hands],
                "tiles": copy.deepcopy(tiles),
                "money": 1000,
            }
        ],
        "private": {
            "shed": copy.deepcopy(shed),
            "inventories": copy.deepcopy(inventories),
            "seeds": {},
        },
    }
    if action is None:
        action = {
            "farmer": ["PASS"],
            "hands": [["PASS"] for _ in hands],
            "market": [],
        }
    return observation, action


class LastTickHarvestContracts(unittest.TestCase):
    def apply(self, observation, action, **configuration):
        return rewrite_last_tick_crop_harvest(
            observation,
            action,
            {"turnsPerDay": 24, "shedCapacity": 100, **configuration},
        )

    def test_pass_on_yielded_crop_harvests(self):
        observation, action = fixture()
        output, info = self.apply(observation, action)
        self.assertEqual(output["farmer"], ["HARVEST"])
        self.assertTrue(info["applied"])
        self.assertEqual(info["activations"][0]["visible_yield"], 2)
        self.assertEqual(info["activations"][0]["crop"], "WHEAT")

    def test_last_tick_move_harvests_current_not_destination_tile(self):
        observation, action = fixture(
            action={"farmer": ["MOVE", 1, 0], "hands": [], "market": []}
        )
        output, info = self.apply(observation, action)
        self.assertEqual(output["farmer"], ["HARVEST"])
        self.assertEqual(info["activations"][0]["position"], [0, 0])
        self.assertEqual(info["activations"][0]["selected_action"], ["MOVE", 1, 0])

    def test_nonfinal_tick_is_unchanged(self):
        observation, action = fixture(hour=22)
        output, info = self.apply(observation, action)
        self.assertEqual(output, action)
        self.assertFalse(info["applied"])
        self.assertIn("not-last-tick", info["reason"])

    def test_zero_yield_is_unchanged(self):
        observation, action = fixture(tiles=[[crop(0), None], [None, None]])
        output, info = self.apply(observation, action)
        self.assertEqual(output, action)
        self.assertFalse(info["applied"])

    def test_animal_harvest_is_out_of_scope(self):
        observation, action = fixture(tiles=[[animal(), None], [None, None]])
        output, info = self.apply(observation, action)
        self.assertEqual(output, action)
        self.assertFalse(info["applied"])

    def test_full_shed_declines(self):
        shed = copy.deepcopy(EMPTY_COUNTS)
        shed["WHEAT"] = 100
        observation, action = fixture(shed=shed)
        output, info = self.apply(observation, action)
        self.assertEqual(output, action)
        self.assertFalse(info["applied"])

    def test_exact_capacity_admits(self):
        shed = copy.deepcopy(EMPTY_COUNTS)
        shed["WHEAT"] = 98
        observation, action = fixture(shed=shed)
        output, info = self.apply(observation, action)
        self.assertEqual(output["farmer"], ["HARVEST"])
        self.assertEqual(info["worst_case_total_after"], 100)

    def test_carried_stock_is_charged(self):
        shed = copy.deepcopy(EMPTY_COUNTS)
        shed["WHEAT"] = 97
        observation, action = fixture(
            shed=shed,
            inventories=[{"FERTILIZER": 2}],
        )
        output, info = self.apply(observation, action)
        self.assertEqual(output, action)
        self.assertFalse(info["applied"])

    def test_selected_other_harvest_is_charged(self):
        shed = copy.deepcopy(EMPTY_COUNTS)
        shed["WHEAT"] = 96
        observation, action = fixture(
            hands=((1, 0),),
            tiles=[[crop(2), crop(3)], [None, None]],
            shed=shed,
            action={
                "farmer": ["PASS"],
                "hands": [["HARVEST"]],
                "market": [],
            },
        )
        output, info = self.apply(observation, action)
        self.assertEqual(output["farmer"], ["PASS"])
        self.assertEqual(output["hands"], [["HARVEST"]])
        self.assertFalse(info["applied"])
        self.assertEqual(info["selected_generation_upper"], 3)

    def test_selected_collect_fertilizer_is_charged(self):
        shed = copy.deepcopy(EMPTY_COUNTS)
        shed["WHEAT"] = 98
        observation, action = fixture(
            hands=((1, 0),),
            tiles=[[crop(2), animal(0)], [None, None]],
            shed=shed,
            action={
                "farmer": ["PASS"],
                "hands": [["COLLECT_FERTILIZER"]],
                "market": [],
            },
        )
        output, info = self.apply(observation, action)
        self.assertEqual(output["farmer"], ["PASS"])
        self.assertFalse(info["applied"])
        self.assertEqual(info["selected_generation_upper"], 1)

    def test_buy_product_upper_bound_is_charged_without_sale_credit(self):
        shed = copy.deepcopy(EMPTY_COUNTS)
        shed["WHEAT"] = 95
        observation, action = fixture(
            shed=shed,
            action={
                "farmer": ["PASS"],
                "hands": [],
                "market": [
                    ["SELL", "WHEAT", 50],
                    ["BUY_PRODUCT", "MILK", 4],
                ],
            },
        )
        output, info = self.apply(observation, action)
        self.assertEqual(output["farmer"], ["PASS"])
        self.assertFalse(info["applied"])
        self.assertEqual(info["market_buy_upper"], 4)

    def test_buy_animal_upper_bound_is_charged(self):
        shed = copy.deepcopy(EMPTY_COUNTS)
        shed["WHEAT"] = 98
        observation, action = fixture(
            shed=shed,
            action={
                "farmer": ["PASS"],
                "hands": [],
                "market": [["BUY_ANIMAL", "COW"]],
            },
        )
        output, info = self.apply(observation, action)
        self.assertEqual(output, action)
        self.assertFalse(info["applied"])
        self.assertEqual(info["market_buy_upper"], 1)

    def test_stateful_colocated_worker_blocks_rewrite(self):
        observation, action = fixture(
            hands=((0, 0),),
            action={
                "farmer": ["PASS"],
                "hands": [["WATER"]],
                "market": [],
            },
        )
        output, info = self.apply(observation, action)
        self.assertEqual(output, action)
        self.assertFalse(info["applied"])

    def test_two_colocated_passes_produce_one_harvest(self):
        observation, action = fixture(hands=((0, 0),))
        output, info = self.apply(observation, action)
        self.assertEqual(output["farmer"], ["HARVEST"])
        self.assertEqual(output["hands"], [["PASS"]])
        self.assertEqual(len(info["activations"]), 1)

    def test_two_distinct_tiles_can_both_harvest_with_cumulative_bound(self):
        observation, action = fixture(
            hands=((1, 0),),
            tiles=[[crop(2), crop(3)], [None, None]],
        )
        output, info = self.apply(observation, action)
        self.assertEqual(output["farmer"], ["HARVEST"])
        self.assertEqual(output["hands"], [["HARVEST"]])
        self.assertEqual([row["visible_yield"] for row in info["activations"]], [2, 3])

    def test_missing_hand_action_is_extended_deterministically(self):
        observation, action = fixture(
            farmer=(1, 1),
            hands=((0, 0),),
            action={"farmer": ["PASS"], "hands": [], "market": []},
        )
        output, info = self.apply(observation, action)
        self.assertEqual(output["farmer"], ["PASS"])
        self.assertEqual(output["hands"], [["HARVEST"]])
        self.assertTrue(info["applied"])

    def test_unknown_market_operation_fails_closed(self):
        observation, action = fixture(
            action={
                "farmer": ["PASS"],
                "hands": [],
                "market": [["FUTURE_STOCK_SOURCE", "WHEAT", 1]],
            }
        )
        output, info = self.apply(observation, action)
        self.assertEqual(output, action)
        self.assertFalse(info["applied"])
        self.assertIn("unsupported-op", info["reason"])

    def test_boolean_numeric_fields_fail_closed(self):
        observation, action = fixture()
        observation["player"] = False
        output, info = self.apply(observation, action)
        self.assertEqual(output, action)
        self.assertFalse(info["applied"])
        self.assertIn("player-not-integer", info["reason"])

    def test_inputs_are_not_mutated_and_receipt_is_deterministic(self):
        observation, action = fixture(hands=((1, 0),), tiles=[[crop(2), crop(3)], [None, None]])
        before_observation = copy.deepcopy(observation)
        before_action = copy.deepcopy(action)
        first = self.apply(observation, action)
        second = self.apply(observation, action)
        self.assertEqual(first, second)
        self.assertEqual(observation, before_observation)
        self.assertEqual(action, before_action)
        json.dumps(first, sort_keys=True, allow_nan=False)


if __name__ == "__main__":
    unittest.main()
