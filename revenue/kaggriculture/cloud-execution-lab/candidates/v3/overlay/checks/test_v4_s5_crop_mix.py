# SPDX-License-Identifier: Apache-2.0
"""Focused source checks for the parked V4 S5 crop-mix lane."""
from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import v4_s5_crop_mix as lane  # noqa: E402

CONFIG = {"episodeSteps": 720, "turnsPerDay": 24}


def observation(day=24, wheat=3, carrot=3):
    return {
        "step": day * 24,
        "day": day,
        "private": {"seeds": {"WHEAT": wheat, "CARROT": carrot}},
    }


def action(farmer=None, hands=None, market=None):
    return {
        "farmer": farmer if farmer is not None else ["PASS"],
        "hands": hands if hands is not None else [],
        "market": market if market is not None else [],
    }


class S5CropMix(unittest.TestCase):
    def test_off_is_exact_parent_object(self):
        parent = action(["PLANT", "CARROT"], [], [["BUY_SEED", "CARROT", 4]])
        self.assertIs(lane.apply_crop_mix(observation(), parent, "off", CONFIG), parent)

    def test_requires_explicit_standard_time_contract(self):
        parent = action(["PLANT", "CARROT"], [], [["BUY_SEED", "CARROT", 4]])
        bad_configs = (
            None,
            {"episodeSteps": 719, "turnsPerDay": 24},
            {"episodeSteps": 720, "turnsPerDay": 12},
            {"episodeSteps": True, "turnsPerDay": 24},
            {"episodeSteps": 720, "turnsPerDay": True},
        )
        for configuration in bad_configs:
            with self.subTest(configuration=configuration):
                self.assertIs(
                    lane.apply_crop_mix(
                        observation(), parent, "retain_wheat", configuration
                    ),
                    parent,
                )

    def test_attribute_configuration_is_supported(self):
        parent = action(["PASS"], [], [["BUY_SEED", "CARROT", 4]])
        out = lane.apply_crop_mix(
            observation(),
            parent,
            "retain_wheat",
            SimpleNamespace(**CONFIG),
        )
        self.assertEqual(out["market"], [["BUY_SEED", "WHEAT", 4]])

    def test_only_days_24_and_25_activate(self):
        parent = action(["PASS"], [], [["BUY_SEED", "CARROT", 4]])
        for day in (0, 23, 26, 29):
            with self.subTest(day=day):
                self.assertIs(
                    lane.apply_crop_mix(
                        observation(day=day), parent, "retain_wheat", CONFIG
                    ),
                    parent,
                )

    def test_quantity_preserving_carrot_buy_becomes_cheaper_wheat(self):
        parent = action(
            ["PASS"],
            [],
            [["SELL", "MILK", 1], ["BUY_SEED", "CARROT", 4], ["SELL", "WOOL", 2]],
        )
        original = copy.deepcopy(parent)
        out = lane.apply_crop_mix(observation(), parent, "retain_wheat", CONFIG)
        self.assertEqual(
            out["market"],
            [["SELL", "MILK", 1], ["BUY_SEED", "WHEAT", 4], ["SELL", "WOOL", 2]],
        )
        self.assertEqual(len(out["market"]), len(parent["market"]))
        self.assertEqual(out["market"][1][2], parent["market"][1][2])
        self.assertLess(lane.WHEAT_SEED_COST, lane.CARROT_SEED_COST)
        self.assertEqual(parent, original)

    def test_saved_seed_cash_cannot_enable_later_purchase(self):
        parents = (
            action(["PASS"], [], [["BUY_SEED", "CARROT", 4], ["HIRE"]]),
            action(["PASS"], [], [["BUY_SEED", "CARROT", 4], ["BUY_LAND"]]),
            action(["PASS"], [], [["BUY_SEED", "CARROT", 4], ["BUY_PRODUCT", "WHEAT", 1]]),
            action(["PASS"], [], [["BUY_SEED", "CARROT", 4], ["BUY_SEED", "WHEAT", 1]]),
            action(["PASS"], [], [["BUY_SEED", "CARROT", 4], ["BUY_ANIMAL", "COW", 1]]),
        )
        for parent in parents:
            with self.subTest(market=parent["market"]):
                self.assertIs(
                    lane.apply_crop_mix(observation(), parent, "retain_wheat", CONFIG),
                    parent,
                )

    def test_malformed_or_nonliteral_market_rows_fail_closed(self):
        parents = (
            action(["PASS"], [], [("BUY_SEED", "CARROT", 4)]),
            action(["PASS"], [], [["BUY_SEED", "CARROT", True]]),
            action(["PASS"], [], [["BUY_SEED", "CARROT", "4"]]),
            action(["PASS"], [], [["BUY_SEED", "CARROT", 0]]),
            action(["PASS"], [], [["BUY_SEED", "CARROT", 4], ["MYSTERY"]]),
        )
        for parent in parents:
            with self.subTest(market=parent["market"]):
                self.assertIs(
                    lane.apply_crop_mix(observation(), parent, "retain_wheat", CONFIG),
                    parent,
                )

    def test_current_carrot_plants_swap_only_with_full_seed_proof(self):
        parent = action(
            ["PLANT", "WHEAT"],
            [["PLANT", "CARROT"], ["PLANT", "CARROT"]],
            [],
        )
        # Parent has seed for its commands, but candidate cannot cover all three
        # WHEAT plants yet, so current occupancy must remain unchanged.
        self.assertIs(
            lane.apply_crop_mix(
                observation(wheat=2, carrot=2), parent, "retain_wheat", CONFIG
            ),
            parent,
        )
        out = lane.apply_crop_mix(
            observation(wheat=3, carrot=2), parent, "retain_wheat", CONFIG
        )
        self.assertEqual(out["farmer"], ["PLANT", "WHEAT"])
        self.assertEqual(out["hands"], [["PLANT", "WHEAT"], ["PLANT", "WHEAT"]])
        self.assertEqual(parent["hands"], [["PLANT", "CARROT"], ["PLANT", "CARROT"]])

    def test_parent_carrot_plants_must_be_seed_backed(self):
        parent = action(["PLANT", "CARROT"], [], [])
        self.assertIs(
            lane.apply_crop_mix(
                observation(wheat=10, carrot=0), parent, "retain_wheat", CONFIG
            ),
            parent,
        )

    def test_market_and_plant_rewrites_compose_copy_on_write(self):
        parent = action(
            ["PLANT", "CARROT"],
            [["PASS"], ["PLANT", "CARROT"]],
            [["BUY_SEED", "CARROT", 3], ["SELL", "MILK", 1]],
        )
        original = copy.deepcopy(parent)
        out = lane.apply_crop_mix(
            observation(wheat=2, carrot=2), parent, "retain_wheat", CONFIG
        )
        self.assertEqual(out["farmer"], ["PLANT", "WHEAT"])
        self.assertEqual(out["hands"], [["PASS"], ["PLANT", "WHEAT"]])
        self.assertEqual(
            out["market"], [["BUY_SEED", "WHEAT", 3], ["SELL", "MILK", 1]]
        )
        self.assertEqual(parent, original)

    def test_inconsistent_step_day_fails_closed(self):
        parent = action(["PASS"], [], [["BUY_SEED", "CARROT", 4]])
        obs = observation(day=24)
        obs["day"] = 25
        self.assertIs(lane.apply_crop_mix(obs, parent, "retain_wheat", CONFIG), parent)


if __name__ == "__main__":
    unittest.main()
