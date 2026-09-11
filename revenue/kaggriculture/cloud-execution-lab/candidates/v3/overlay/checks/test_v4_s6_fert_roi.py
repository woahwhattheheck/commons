# SPDX-License-Identifier: Apache-2.0
"""Focused checks for V4 ``r04_s6_fert_roi``.

Run in a materialised candidate package:

    python -B -m unittest -v checks/test_v4_s6_fert_roi.py
"""
from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import r04_fert_hand as fert_hand  # noqa: E402
import r04_full_router as r04  # noqa: E402
import r04_s6_fert_roi as lane  # noqa: E402
from titan_runtime import Features  # noqa: E402

STANDARD_CONFIG = {"episodeSteps": 720, "turnsPerDay": 24, "boardSize": 10}


def plant(crop, *, planted_day, yield_units=1, watered_today=False, covered=-1):
    return {
        "kind": "PLANT",
        "crop": crop,
        "planted_day": planted_day,
        "yield_units": yield_units,
        "watered_today": watered_today,
        "fertilized_until_day": covered,
        "max_lifespan_step": -1,
    }


def observation(*, step=24 * 24, tomato_watered=True, tomato_yield=1,
                tomato_covered=-1, prices=None):
    tiles = [[None for _ in range(10)] for _ in range(10)]
    tiles[2][2] = plant("CARROT", planted_day=22)
    tiles[2][3] = plant(
        "TOMATO",
        planted_day=16,
        yield_units=tomato_yield,
        watered_today=tomato_watered,
        covered=tomato_covered,
    )
    farm = {
        "tiles": tiles,
        "farmer": [0, 0],
        "hands": [[2, 2]],
        "money": 1000,
        "unlocked_quadrants": ["NW"],
        "hires_today": 0,
    }
    market_prices = {"WHEAT": 25, "CARROT": 35, "TOMATO": 200, "FERTILIZER": 100}
    market_prices.update(prices or {})
    return {
        "step": step,
        "day": step // 24,
        "hour": step % 24,
        "player": 0,
        "farms": [farm, copy.deepcopy(farm)],
        "private": {
            "inventories": [{}, {"FERTILIZER": 1}],
            "shed": {"FERTILIZER": 0},
            "seeds": {},
        },
        "market": {"prices": market_prices},
        "town": {"unlocked_shops": ["PIZZA_SHOP"]},
    }


def clear_incumbent_carrot(obs):
    obs["farms"][0]["tiles"][2][2] = None
    return obs


def tape_with_later_carrot(step):
    tape = [
        {"farmer": ["PASS"], "hands": [], "market": []}
        for _ in range(720)
    ]
    tape[step + 2]["farmer"] = ["PLANT", "CARROT"]
    return tape


class S6FertRoiTest(unittest.TestCase):
    def test_s6_activation_requires_exact_standard_configuration(self):
        self.assertTrue(lane.standard_configuration(dict(STANDARD_CONFIG)))
        bad = (
            None,
            {"episodeSteps": 719, "turnsPerDay": 24, "boardSize": 10},
            {"episodeSteps": 720, "turnsPerDay": 12, "boardSize": 10},
            {"episodeSteps": 720, "turnsPerDay": 24, "boardSize": 9},
            {"episodeSteps": 720, "turnsPerDay": True, "boardSize": 10},
            {"episodeSteps": 720.0, "turnsPerDay": 24, "boardSize": 10},
        )
        for configuration in bad:
            with self.subTest(configuration=configuration):
                self.assertFalse(lane.standard_configuration(configuration))
        router_source = (ROOT / "r04_full_router.py").read_text(encoding="utf-8")
        self.assertIn(
            "s6_enabled = r04_s6_fert_roi.standard_configuration(configuration)",
            router_source,
        )

    def test_current_incumbent_carrot_blocks_tomato_reprioritization(self):
        target = lane.choose_fert_hand_target(observation(), (2, 2), ())
        self.assertIsNone(target)

    def test_zero_price_current_carrot_still_reserves_baseline(self):
        obs = observation(prices={"CARROT": 0, "TOMATO": 200})
        carrot = obs["farms"][0]["tiles"][2][2]
        self.assertGreater(fert_hand._gain(carrot, 24), 0)
        self.assertIsNone(lane.choose_fert_hand_target(obs, (2, 2), ()))

    def test_day28_carrot_reservation_mirrors_unclipped_incumbent(self):
        obs = observation(step=28 * 24, tomato_watered=True)
        carrot = plant("CARROT", planted_day=28)
        obs["farms"][0]["tiles"][2][2] = carrot
        obs["farms"][0]["tiles"][2][3] = plant(
            "TOMATO", planted_day=20, watered_today=True
        )
        self.assertGreater(fert_hand._gain(carrot, 28), 0)
        self.assertIsNone(lane.choose_fert_hand_target(obs, (2, 2), ()))

    def test_guaranteed_tomato_is_used_only_when_incumbent_is_idle(self):
        obs = clear_incumbent_carrot(observation())
        target = lane.choose_fert_hand_target(obs, (2, 2), ())
        self.assertIsNotNone(target)
        self.assertEqual(target["crop"], "TOMATO")
        self.assertEqual(target["position"], (3, 2))
        self.assertEqual(target["marginal_units"], 1)
        self.assertEqual(target["marginal_value"], 200)

    def test_unwatered_tomato_is_not_speculated(self):
        obs = clear_incumbent_carrot(observation(tomato_watered=False))
        self.assertIsNone(lane.choose_fert_hand_target(obs, (2, 2), ()))

    def test_existing_tomato_coverage_is_not_rebought(self):
        obs = clear_incumbent_carrot(observation(tomato_covered=24))
        self.assertIsNone(lane.choose_fert_hand_target(obs, (2, 2), ()))

    def test_cap_minus_one_tomato_has_zero_marginal_gain(self):
        obs = clear_incumbent_carrot(observation(tomato_yield=3))
        self.assertIsNone(lane.choose_fert_hand_target(obs, (2, 2), ()))

    def test_tomato_deadline_rejects_distance_one_at_hour_23(self):
        obs = clear_incumbent_carrot(observation(step=24 * 24 + 23))
        self.assertIsNone(lane.choose_fert_hand_target(obs, (2, 2), ()))

    def test_tomato_deadline_allows_distance_one_at_hour_22(self):
        obs = clear_incumbent_carrot(observation(step=24 * 24 + 22))
        target = lane.choose_fert_hand_target(obs, (2, 2), ())
        self.assertIsNotNone(target)
        self.assertEqual(target["crop"], "TOMATO")
        self.assertEqual(target["position"], (3, 2))

    def test_tomato_deadline_rejects_distance_two_at_hour_22(self):
        obs = clear_incumbent_carrot(observation(step=24 * 24 + 22))
        obs["farms"][0]["tiles"][2][4] = obs["farms"][0]["tiles"][2][3]
        obs["farms"][0]["tiles"][2][3] = None
        self.assertIsNone(lane.choose_fert_hand_target(obs, (2, 2), ()))

    def test_wheat_annual_gain_can_use_idle_hand(self):
        obs = clear_incumbent_carrot(
            observation(tomato_watered=False, prices={"WHEAT": 80, "CARROT": 35})
        )
        obs["farms"][0]["tiles"][2][3] = plant("WHEAT", planted_day=22)
        target = lane.choose_fert_hand_target(obs, (2, 2), ())
        self.assertIsNotNone(target)
        self.assertEqual(target["crop"], "WHEAT")
        self.assertEqual(target["position"], (3, 2))
        self.assertGreaterEqual(target["marginal_units"], 1)

    def test_unreachable_wheat_is_not_selected_late_day(self):
        obs = clear_incumbent_carrot(
            observation(
                step=24 * 24 + 23,
                tomato_watered=False,
                prices={"WHEAT": 10000, "CARROT": 35},
            )
        )
        obs["farms"][0]["tiles"][9][9] = plant("WHEAT", planted_day=22)
        self.assertIsNone(lane.choose_fert_hand_target(obs, (2, 2), ()))

    def test_day28_wheat_with_only_post_episode_water_is_not_productive(self):
        obs = clear_incumbent_carrot(
            observation(
                step=28 * 24,
                tomato_watered=False,
                prices={"WHEAT": 10000, "CARROT": 35},
            )
        )
        obs["farms"][0]["tiles"][2][3] = plant("WHEAT", planted_day=28)
        self.assertIsNone(lane.choose_fert_hand_target(obs, (2, 2), ()))

    def test_day28_wheat_with_day29_water_remains_productive(self):
        obs = clear_incumbent_carrot(
            observation(
                step=28 * 24,
                tomato_watered=False,
                prices={"WHEAT": 80, "CARROT": 35},
            )
        )
        obs["farms"][0]["tiles"][2][3] = plant("WHEAT", planted_day=27)
        target = lane.choose_fert_hand_target(obs, (2, 2), ())
        self.assertIsNotNone(target)
        self.assertEqual(target["crop"], "WHEAT")
        self.assertEqual(target["marginal_units"], 1)

    def test_upcoming_incumbent_carrot_reserves_hand(self):
        obs = clear_incumbent_carrot(observation())
        self.assertIsNone(
            lane.choose_fert_hand_target(obs, (1, 2), ((2, 2, 1),))
        )

    def test_same_position_upcoming_carrot_stays_pass(self):
        obs = clear_incumbent_carrot(observation(tomato_watered=False))
        upcoming = ((2, 2, 1),)
        self.assertIsNone(
            lane.choose_fert_hand_target(obs, (2, 2), upcoming)
        )
        state = fert_hand._Day(24)
        state.index = 0
        state.picked = True
        old = fert_hand.S6_FERT_ROI
        try:
            fert_hand.S6_FERT_ROI = True
            self.assertEqual(
                fert_hand._hand_command(obs, state, None, upcoming), ["PASS"]
            )
        finally:
            fert_hand.S6_FERT_ROI = old

    def test_later_today_carrot_reserves_budget_before_idle_s6(self):
        obs = clear_incumbent_carrot(observation())
        step = obs["step"]
        state = fert_hand._Day(24)
        state.index = 0
        state.picked = True
        old = fert_hand.S6_FERT_ROI
        try:
            fert_hand.S6_FERT_ROI = True
            self.assertEqual(
                fert_hand._hand_command(obs, state, tape_with_later_carrot(step), ()),
                ["PASS"],
            )
        finally:
            fert_hand.S6_FERT_ROI = old

    def test_malformed_price_fails_closed(self):
        obs = clear_incumbent_carrot(observation())
        obs["market"]["prices"]["TOMATO"] = True
        self.assertIsNone(lane.choose_fert_hand_target(obs, (2, 2), ()))

    def test_malformed_board_or_position_fails_closed(self):
        obs = clear_incumbent_carrot(observation())
        obs["farms"][0]["tiles"] = obs["farms"][0]["tiles"][:-1]
        self.assertIsNone(lane.choose_fert_hand_target(obs, (2, 2), ()))
        good = clear_incumbent_carrot(observation())
        self.assertIsNone(lane.choose_fert_hand_target(good, (-1, 2), ()))
        self.assertIsNone(lane.choose_fert_hand_target(good, (10, 2), ()))

    def test_actual_fert_hand_preserves_incumbent_carrot_when_s6_on(self):
        obs = observation()
        state = fert_hand._Day(24)
        state.index = 0
        state.picked = True
        old = fert_hand.S6_FERT_ROI
        try:
            fert_hand.S6_FERT_ROI = False
            incumbent = fert_hand._hand_command(obs, state, None, ())
            self.assertEqual(incumbent, ["FERTILIZE"])

            fert_hand.S6_FERT_ROI = True
            extended = fert_hand._hand_command(obs, state, None, ())
            self.assertEqual(extended, ["FERTILIZE"])
        finally:
            fert_hand.S6_FERT_ROI = old

    def test_actual_fert_hand_uses_tomato_only_when_incumbent_idle(self):
        obs = clear_incumbent_carrot(observation())
        state = fert_hand._Day(24)
        state.index = 0
        state.picked = True
        old = fert_hand.S6_FERT_ROI
        try:
            fert_hand.S6_FERT_ROI = False
            incumbent = fert_hand._hand_command(obs, state, None, ())
            self.assertEqual(incumbent, ["PASS"])

            fert_hand.S6_FERT_ROI = True
            extended = fert_hand._hand_command(obs, state, None, ())
            self.assertEqual(extended, ["EAST"])
        finally:
            fert_hand.S6_FERT_ROI = old

    def test_s6_never_changes_the_hire_selector_flag_surface(self):
        self.assertNotIn("S6_FERT_ROI", fert_hand._consider_hire.__code__.co_names)
        self.assertNotIn("r04_s6_fert_roi", fert_hand._consider_hire.__code__.co_names)

    def test_generated_key_contract_is_default_off(self):
        self.assertFalse(Features().r04_s6_fert_roi)
        self.assertFalse(fert_hand.S6_FERT_ROI)
        data = json.loads((ROOT / "TITAN-CONFIG.json").read_text(encoding="utf-8"))
        self.assertIs(data["r04_s6_fert_roi"], False)

    def test_install_flag_round_trip(self):
        old = r04.S6_FERT_ROI
        try:
            r04.install(s6_fert_roi=True)
            self.assertIs(r04.S6_FERT_ROI, True)
            r04.install(s6_fert_roi=False)
            self.assertIs(r04.S6_FERT_ROI, False)
        finally:
            r04.S6_FERT_ROI = old


if __name__ == "__main__":
    unittest.main()
