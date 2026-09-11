# SPDX-License-Identifier: Apache-2.0
"""Focused checks for V4 ``r04_dead_water_harvest``.

Run in a materialised candidate package:

    python -B -m unittest -v checks/test_v4_dead_water_harvest.py
"""
from __future__ import annotations

import unittest

import r04_dead_water_harvest as lane


def _tile(crop="WHEAT", planted_day=26, yield_units=3,
          watered_today=True, max_lifespan_step=696):
    return {
        "kind": "PLANT",
        "crop": crop,
        "planted_day": planted_day,
        "yield_units": yield_units,
        "watered_today": watered_today,
        "max_lifespan_step": max_lifespan_step,
    }


def _obs(tile, step=680, day=28):
    farm = {
        "farmer": [0, 0],
        "hands": [],
        "tiles": [[tile]],
    }
    return {
        "step": step,
        "day": day,
        "player": 0,
        "farms": [farm],
    }


def _action(command=None):
    return {"farmer": command or ["WATER"], "hands": [], "market": []}


class DeadWaterHarvestTest(unittest.TestCase):
    def setUp(self):
        lane.reset()

    def test_already_watered_mature_plant_recovers_harvest(self):
        out = lane.apply_dead_water_harvest(_obs(_tile()), _action())
        self.assertEqual(out["farmer"], ["HARVEST"])
        self.assertEqual(lane.get_report()["recovered"], 1)

    def test_expiring_unwatered_mature_plant_recovers_harvest(self):
        tile = _tile(crop="CARROT", planted_day=25, yield_units=4,
                     watered_today=False, max_lifespan_step=680)
        out = lane.apply_dead_water_harvest(_obs(tile), _action())
        self.assertEqual(out["farmer"], ["HARVEST"])
        self.assertEqual(lane.get_report()["expiring"], 1)

    def test_annual_yield_units_before_maturity_fails_closed(self):
        # Official engine initializes non-ongoing crops with yield_units == 1.
        tile = _tile(crop="WHEAT", planted_day=28, yield_units=1,
                     watered_today=True, max_lifespan_step=696)
        action = _action()
        out = lane.apply_dead_water_harvest(_obs(tile), action)
        self.assertIs(out, action)
        self.assertEqual(lane.get_report()["not_harvestable"], 1)

    def test_productive_water_is_untouched(self):
        tile = _tile(watered_today=False, max_lifespan_step=696)
        action = _action()
        self.assertIs(lane.apply_dead_water_harvest(_obs(tile), action), action)

    def test_zero_yield_ongoing_crop_is_untouched(self):
        tile = _tile(crop="TOMATO", planted_day=18, yield_units=0,
                     watered_today=True, max_lifespan_step=-1)
        action = _action()
        self.assertIs(lane.apply_dead_water_harvest(_obs(tile), action), action)

    def test_outside_window_and_disabled_are_identity(self):
        action = _action()
        self.assertIs(
            lane.apply_dead_water_harvest(_obs(_tile(), step=671, day=27), action),
            action,
        )
        self.assertIs(
            lane.apply_dead_water_harvest(_obs(_tile()), action, enabled=False),
            action,
        )

    def test_unknown_position_and_non_water_fail_closed(self):
        observation = _obs(_tile())
        observation["farms"][0]["farmer"] = [-1, 0]
        action = _action()
        self.assertIs(lane.apply_dead_water_harvest(observation, action), action)
        pass_action = _action(["PASS"])
        self.assertIs(
            lane.apply_dead_water_harvest(_obs(_tile()), pass_action),
            pass_action,
        )


if __name__ == "__main__":
    unittest.main()
