#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import copy
import unittest

import b3_bonus_window_watering as b3


def observation(step, tile, *, hands=None):
    size = 10
    tiles = [[None for _ in range(size)] for _ in range(size)]
    tiles[4][4] = copy.deepcopy(tile)
    hand_positions = list(hands or [])
    farm = {
        "tiles": tiles,
        "farmer": [4, 4],
        "hands": hand_positions,
        "money": 3000,
        "unlocked_quadrants": ["NW"],
        "hires_today": 0,
    }
    return {
        "step": step,
        "player": 0,
        "farms": [farm, copy.deepcopy(farm)],
        "private": {"inventories": [{} for _ in range(1 + len(hand_positions))], "shed": {}},
        "market": {"prices": {}},
        "town": {"unlocked_shops": []},
    }


def plant(crop, planted_day, *, dry=0, watered=False, units=1, fertilized=-1):
    return {
        "kind": "PLANT",
        "crop": crop,
        "planted_day": planted_day,
        "watered_today": watered,
        "consecutive_unwatered": dry,
        "yield_units": units,
        "fertilized_until_day": fertilized,
        "max_lifespan_step": -1,
    }


def water_action():
    return {"farmer": ["WATER"], "hands": [], "market": [["SELL", "MILK", 1]]}


def refresh_dry(dry, watered):
    """Exact drought-counter transition used by the official daily plant refresh."""
    return 0 if watered else dry + 1


class BonusWaterTests(unittest.TestCase):
    def setUp(self):
        b3.telemetry.clear()

    def test_disabled_is_exact_identity(self):
        obs = observation(11 * 24, plant("STRAWBERRY", 0, units=1))
        action = water_action()
        self.assertIs(b3.transform(obs, action, enabled=False), action)

    def test_second_dry_day_keeps_survival_water(self):
        obs = observation(11 * 24, plant("STRAWBERRY", 0, dry=1, units=1))
        action = water_action()
        self.assertIs(b3.transform(obs, action, enabled=True), action)
        self.assertEqual(b3.telemetry["kept_survival_water"], 1)

    def test_nonongoing_yield_window_keeps_productive_water(self):
        obs = observation(2 * 24, plant("CARROT", 0, dry=0, units=1))
        action = water_action()
        self.assertIs(b3.transform(obs, action, enabled=True), action)
        self.assertEqual(b3.telemetry["kept_yield_water"], 1)

    def test_nonongoing_at_yield_cap_harvests_instead(self):
        obs = observation(2 * 24, plant("CARROT", 0, dry=0, units=4))
        action = water_action()
        out = b3.transform(obs, action, enabled=True)
        self.assertEqual(out["farmer"], ["HARVEST"])
        self.assertEqual(out["market"], action["market"])
        self.assertEqual(action["farmer"], ["WATER"])

    def test_ongoing_fertilized_production_day_keeps_water(self):
        obs = observation(9 * 24, plant("STRAWBERRY", 0, dry=0, units=1, fertilized=9))
        action = water_action()
        self.assertIs(b3.transform(obs, action, enabled=True), action)
        self.assertEqual(b3.telemetry["kept_yield_water"], 1)

    def test_ongoing_unwatered_crop_keeps_water_without_future_rescue_proof(self):
        obs = observation(11 * 24, plant("STRAWBERRY", 0, dry=0, units=1, fertilized=-1))
        action = water_action()
        self.assertIs(b3.transform(obs, action, enabled=True), action)
        self.assertEqual(b3.telemetry["kept_ongoing_survival_water"], 1)

    def test_ongoing_guard_closes_two_day_drought_gap(self):
        tile = plant("STRAWBERRY", 0, dry=0, units=1, fertilized=-1)
        obs = observation(11 * 24, tile)
        action = water_action()
        self.assertIs(b3.transform(obs, action, enabled=True), action)

        # Parent WATER today resets to 0, so one missed WATER tomorrow only reaches 1.
        control_after_today = refresh_dry(tile["consecutive_unwatered"], watered=True)
        control_after_tomorrow = refresh_dry(control_after_today, watered=False)
        self.assertEqual(control_after_tomorrow, 1)

        # The rejected old substitution skipped today's WATER: 0->1, then 1->2 (weed).
        old_candidate_after_today = refresh_dry(tile["consecutive_unwatered"], watered=False)
        old_candidate_after_tomorrow = refresh_dry(old_candidate_after_today, watered=False)
        self.assertEqual(old_candidate_after_tomorrow, 2)

    def test_already_watered_duplicate_can_harvest(self):
        obs = observation(11 * 24, plant("STRAWBERRY", 0, dry=1, watered=True, units=1))
        action = water_action()
        out = b3.transform(obs, action, enabled=True)
        self.assertEqual(out["farmer"], ["HARVEST"])

    def test_safe_nonongoing_skip_without_harvest_keeps_parent(self):
        obs = observation(4 * 24, plant("CARROT", 0, dry=0, units=0))
        action = water_action()
        self.assertIs(b3.transform(obs, action, enabled=True), action)
        self.assertEqual(b3.telemetry["no_productive_replacement"], 1)

    def test_missing_fertilizer_state_fails_closed(self):
        bad = plant("CARROT", 0, units=4)
        del bad["fertilized_until_day"]
        obs = observation(2 * 24, bad)
        action = water_action()
        self.assertIs(b3.transform(obs, action, enabled=True), action)
        self.assertEqual(b3.telemetry["water_unknown_tile"], 1)

    def test_malformed_public_state_fails_closed(self):
        bad = plant("CARROT", 0, units=4)
        bad["watered_today"] = 0
        obs = observation(2 * 24, bad)
        action = water_action()
        self.assertIs(b3.transform(obs, action, enabled=True), action)

    def test_nonstandard_turns_per_day_fails_closed(self):
        obs = observation(11 * 24, plant("STRAWBERRY", 0, units=1))
        action = water_action()
        self.assertIs(b3.transform(obs, action, {"turnsPerDay": 12}, enabled=True), action)
        self.assertEqual(b3.telemetry["nonstandard_configuration"], 1)

    def test_wrapper_disabled_preserves_parent_result_identity(self):
        action = water_action()

        def parent(observation, configuration=None):
            return action

        wrapped = b3.install(parent, enabled=False)
        obs = observation(11 * 24, plant("STRAWBERRY", 0, units=1))
        self.assertIs(wrapped(obs, None), action)


if __name__ == "__main__":
    unittest.main()
