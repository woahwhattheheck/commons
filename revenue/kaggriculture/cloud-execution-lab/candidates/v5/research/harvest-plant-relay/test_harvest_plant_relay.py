# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parent
LAB = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(LAB))

import mechanics as m
from harvest_plant_relay import transform


def plant(crop="CARROT", *, planted_day=3, yield_units=4):
    return {
        "kind": "PLANT",
        "crop": crop,
        "planted_day": planted_day,
        "yield_units": yield_units,
        "watered_today": True,
        "consecutive_unwatered": 0,
        "fertilized_until_day": -1,
        "max_lifespan_step": -1,
    }


def farm(*, crop="CARROT", farmer=None, hands=None, planted_day=3, yield_units=4):
    tiles = [[None for _ in range(10)] for _ in range(10)]
    fx, fy = farmer or [4, 4]
    tiles[fy][fx] = plant(crop, planted_day=planted_day, yield_units=yield_units)
    return {
        "farmer": list(farmer or [4, 4]),
        "hands": deepcopy(hands or [[4, 4]]),
        "tiles": tiles,
        "money": 10000,
        "unlocked_quadrants": ["NW"],
        "hires_today": len(hands or [[4, 4]]),
    }


def observation(*, crop="CARROT", seeds=1, hands=None, planted_day=3,
                yield_units=4, step=120, player=0):
    own = farm(
        crop=crop,
        hands=hands,
        planted_day=planted_day,
        yield_units=yield_units,
    )
    other = farm(crop="CARROT", farmer=[4, 4], hands=[])
    seed_map = {name: 0 for name in m.CROPS}
    seed_map[crop] = seeds
    return {
        "step": step,
        "player": player,
        "farms": [own, other] if player == 0 else [other, own],
        "private": {
            "shed": {item: 0 for item in [*m.PRODUCTS, *m.ANIMALS]},
            "seeds": seed_map,
            "inventories": [{} for _ in range(1 + len(own["hands"]))],
        },
        "market": {"inventory": {}, "prices": {}},
    }


def selected(*, hands=None, market=None, farmer=None):
    return {
        "farmer": deepcopy(farmer or ["HARVEST"]),
        "hands": deepcopy(hands or [["PASS"]]),
        "market": deepcopy(market or []),
    }


def apply_units(observation, action):
    farm_state = deepcopy(observation["farms"][observation["player"]])
    private = deepcopy(observation["private"])
    day = observation["step"] // 24
    actions = [action["farmer"], *action["hands"]]
    for idx, unit_action in enumerate(actions):
        m._apply_unit_action(farm_state, private, idx, unit_action, 10, day, 24, 100)
    return farm_state, private


class HarvestPlantRelayTests(unittest.TestCase):
    def test_engine_farmer_harvest_then_hand_replants_same_tick(self):
        obs = observation(crop="CARROT", seeds=1, step=120, planted_day=3)
        base = selected(market=[["SELL", "WOOL", 1]])
        before = deepcopy((obs, base))

        candidate, report = transform(base, obs, {})
        self.assertTrue(report["changed"])
        self.assertEqual(candidate["farmer"], ["HARVEST"])
        self.assertEqual(candidate["hands"], [["PLANT", "CARROT"]])
        self.assertEqual(candidate["market"], base["market"])
        self.assertEqual((obs, base), before)

        base_farm, base_private = apply_units(obs, base)
        cand_farm, cand_private = apply_units(obs, candidate)

        self.assertIsNone(base_farm["tiles"][4][4])
        replanted = cand_farm["tiles"][4][4]
        self.assertEqual(replanted["kind"], "PLANT")
        self.assertEqual(replanted["crop"], "CARROT")
        self.assertEqual(replanted["planted_day"], 5)
        self.assertEqual(base_private["inventories"], cand_private["inventories"])
        self.assertEqual(base_private["inventories"][0].get("CARROT"), 4)
        self.assertEqual(base_private["seeds"]["CARROT"], 1)
        self.assertEqual(cand_private["seeds"]["CARROT"], 0)

        base_without_target = deepcopy(base_farm)
        cand_without_target = deepcopy(cand_farm)
        base_without_target["tiles"][4][4] = None
        cand_without_target["tiles"][4][4] = None
        self.assertEqual(base_without_target, cand_without_target)

    def test_spare_seed_is_beyond_existing_atomic_plant_demand(self):
        obs = observation(
            crop="CARROT",
            seeds=1,
            hands=[[4, 4], [0, 0]],
        )
        action = selected(hands=[["PASS"], ["PLANT", "CARROT"]])
        result, report = transform(action, obs, {})
        self.assertIs(result, action)
        self.assertEqual(report["reason"], "no_spare_preexisting_seed")
        self.assertEqual(report["existing_plant_demand"], 1)

        obs["private"]["seeds"]["CARROT"] = 2
        result, report = transform(action, obs, {})
        self.assertTrue(report["changed"])
        self.assertEqual(result["hands"][0], ["PLANT", "CARROT"])
        self.assertEqual(result["hands"][1], ["PLANT", "CARROT"])

    def test_ongoing_crop_is_identity(self):
        obs = observation(crop="TOMATO", seeds=3, step=300, planted_day=0)
        action = selected()
        result, report = transform(action, obs, {})
        self.assertIs(result, action)
        self.assertEqual(report["reason"], "ongoing_or_unknown_crop")

    def test_immature_or_empty_crop_is_identity(self):
        action = selected()
        immature = observation(crop="MELON", seeds=1, step=24, planted_day=0, yield_units=1)
        result, report = transform(action, immature, {})
        self.assertIs(result, action)
        self.assertEqual(report["reason"], "immature_crop")

        empty = observation(crop="CARROT", seeds=1, yield_units=0)
        result, report = transform(action, empty, {})
        self.assertIs(result, action)
        self.assertEqual(report["reason"], "not_harvestable")

    def test_colocated_hand_must_be_unique_and_idle(self):
        action = selected(hands=[["PASS"], ["PASS"]])
        two = observation(crop="CARROT", seeds=2, hands=[[4, 4], [4, 4]])
        result, report = transform(action, two, {})
        self.assertIs(result, action)
        self.assertEqual(report["reason"], "ambiguous_colocated_hands")

        busy = observation(crop="CARROT", seeds=2, hands=[[4, 4]])
        action = selected(hands=[["WATER"]])
        result, report = transform(action, busy, {})
        self.assertIs(result, action)
        self.assertEqual(report["reason"], "colocated_hand_not_pass")

    def test_noncolocated_hand_and_reversed_order_are_identity(self):
        obs = observation(crop="CARROT", seeds=2, hands=[[3, 4]])
        action = selected()
        result, report = transform(action, obs, {})
        self.assertIs(result, action)
        self.assertEqual(report["reason"], "ambiguous_colocated_hands")

        obs = observation(crop="CARROT", seeds=2, hands=[[4, 4]])
        action = selected(farmer=["PASS"], hands=[["HARVEST"]])
        result, report = transform(action, obs, {})
        self.assertIs(result, action)
        self.assertEqual(report["reason"], "selected_shape_or_farmer_action")

    def test_market_and_other_hand_actions_are_preserved(self):
        obs = observation(
            crop="WHEAT",
            seeds=2,
            hands=[[0, 0], [4, 4], [9, 9]],
            step=120,
            planted_day=3,
            yield_units=6,
        )
        action = selected(
            hands=[["EAST"], ["PASS"], ["WEST"]],
            market=[["BUY_SEED", "WHEAT", 2], ["SELL", "WOOL", 3]],
        )
        result, report = transform(action, obs, {})
        self.assertTrue(report["changed"])
        self.assertEqual(result["hands"], [["EAST"], ["PLANT", "WHEAT"], ["WEST"]])
        self.assertEqual(result["market"], action["market"])
        self.assertEqual(report["hand_index"], 1)

    def test_exact_public_and_standard_config_boundary(self):
        obs = observation(crop="CARROT", seeds=1)
        action = selected()
        for player, step in ((True, 120), (0, True), (2, 120), (0, -1), ("0", 120)):
            with self.subTest(player=player, step=step):
                changed = deepcopy(obs)
                changed["player"] = player
                changed["step"] = step
                result, report = transform(action, changed, {})
                self.assertIs(result, action)
                self.assertEqual(report["reason"], "malformed_public_identity")

        for cfg in ({"boardSize": 8}, {"turnsPerDay": 12}, [], False):
            with self.subTest(cfg=cfg):
                result, report = transform(action, obs, cfg)
                self.assertIs(result, action)
                self.assertIn(report["reason"], {"outside_standard_config", "malformed_input"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
