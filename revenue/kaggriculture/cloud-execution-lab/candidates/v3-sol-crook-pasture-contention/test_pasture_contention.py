# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
LAB = HERE.parents[1]
if (LAB / "mechanics.py").is_file() and str(LAB) not in sys.path:
    sys.path.insert(0, str(LAB))

import mechanics as m
from pasture_contention import repair_selected


def animal_tile(animal="COW", *, fed=True, cared=False, yield_units=3):
    return {
        "kind": "PASTURE",
        "animal": animal,
        "placed_day": 0,
        "yield_units": yield_units,
        "consecutive_unfed": 0,
        "fed_today": fed,
        "cared_today": cared,
        "fertilizer_available": False,
        "pending_care_bonus": 0,
    }


def fixture(*, tile=None, positions=None, actions=None):
    tiles = [[None for _ in range(10)] for _ in range(10)]
    tiles[2][2] = tile if tile is not None else animal_tile()
    positions = positions or [[2, 2], [2, 2]]
    actions = actions or [["HARVEST"], ["HARVEST"]]
    farm = {
        "farmer": list(positions[0]),
        "hands": [list(p) for p in positions[1:]],
        "tiles": tiles,
        "money": 0,
        "hires_today": 0,
        "unlocked_quadrants": ["NW"],
    }
    private = {
        "inventories": [{} for _ in positions],
        "shed": {},
        "seeds": {},
    }
    obs = {"step": 190, "player": 0, "farms": [farm, copy.deepcopy(farm)],
           "private": private}
    selected = {"farmer": list(actions[0]),
                "hands": [list(a) for a in actions[1:]],
                "market": [["SELL", "MILK", 1], [], ["BUY_SEED", "WHEAT", 1]]}
    return obs, selected


def execute(obs, selected, *, day=7):
    farm = copy.deepcopy(obs["farms"][0])
    private = copy.deepcopy(obs["private"])
    acts = [selected["farmer"], *selected["hands"]]
    for index, action in enumerate(acts):
        m._apply_unit_action(farm, private, index, action, 10, day, 24, 100)
    return farm, private


class PastureContentionTests(unittest.TestCase):
    def test_exact_engine_salvages_wasted_second_harvest_as_future_yield(self):
        obs, selected = fixture()
        original = copy.deepcopy(selected)
        repaired, report = repair_selected(obs, selected)

        self.assertIsNot(repaired, selected)
        self.assertEqual(selected, original)
        self.assertEqual(repaired["farmer"], ["HARVEST"])
        self.assertEqual(repaired["hands"], [["CARE"]])
        self.assertEqual(repaired["market"], selected["market"])
        self.assertEqual(report["changed_actions"], 1)
        self.assertEqual(report["events"][0]["product"], "MILK")

        base_farm, base_private = execute(obs, selected)
        new_farm, new_private = execute(obs, repaired)
        self.assertEqual(base_private["inventories"][0], {"MILK": 3})
        self.assertEqual(new_private["inventories"][0], {"MILK": 3})
        self.assertEqual(base_private["inventories"][1], {})
        self.assertEqual(new_private["inventories"][1], {})
        self.assertFalse(base_farm["tiles"][2][2]["cared_today"])
        self.assertTrue(new_farm["tiles"][2][2]["cared_today"])

        # Day 7 -> day 8 is a COW production boundary. CARE is banked after
        # this production and is consumed on the following fed boundary.
        m._daily_refresh_animals(base_farm, 7)
        m._daily_refresh_animals(new_farm, 7)
        self.assertEqual(base_farm["tiles"][2][2]["pending_care_bonus"], 0)
        self.assertEqual(new_farm["tiles"][2][2]["pending_care_bonus"], 1)
        for farm in (base_farm, new_farm):
            farm["tiles"][2][2]["fed_today"] = True
        m._daily_refresh_animals(base_farm, 8)
        m._daily_refresh_animals(new_farm, 8)
        for farm in (base_farm, new_farm):
            farm["tiles"][2][2]["fed_today"] = True
        m._daily_refresh_animals(base_farm, 9)
        m._daily_refresh_animals(new_farm, 9)
        self.assertEqual(new_farm["tiles"][2][2]["yield_units"],
                         base_farm["tiles"][2][2]["yield_units"] + 1)

    def test_sheep_path_reports_and_harvests_wool(self):
        obs, selected = fixture(tile=animal_tile("SHEEP"))
        repaired, report = repair_selected(obs, selected)
        farm, private = execute(obs, repaired, day=7)
        self.assertEqual(report["events"][0]["product"], "WOOL")
        self.assertEqual(private["inventories"][0], {"WOOL": 3})
        self.assertTrue(farm["tiles"][2][2]["cared_today"])

    def test_unfed_duplicate_is_identity(self):
        obs, selected = fixture(tile=animal_tile(fed=False))
        repaired, report = repair_selected(obs, selected)
        self.assertIs(repaired, selected)
        self.assertFalse(report["changed"])

    def test_existing_care_on_tile_blocks_replacement(self):
        obs, selected = fixture(positions=[[2, 2], [2, 2], [2, 2]],
                                actions=[["HARVEST"], ["HARVEST"], ["CARE"]])
        repaired, report = repair_selected(obs, selected)
        self.assertIs(repaired, selected)
        self.assertEqual(report["duplicate_groups"], 1)
        self.assertEqual(report["eligible_groups"], 0)

    def test_three_harvesters_change_only_the_first_wasted_action(self):
        obs, selected = fixture(positions=[[2, 2], [2, 2], [2, 2]],
                                actions=[["HARVEST"], ["HARVEST"], ["HARVEST"]])
        repaired, report = repair_selected(obs, selected)
        self.assertEqual(repaired["farmer"], ["HARVEST"])
        self.assertEqual(repaired["hands"], [["CARE"], ["HARVEST"]])
        self.assertEqual(report["changed_actions"], 1)

    def test_crop_and_coop_duplicates_are_identity(self):
        plant = {"kind": "PLANT", "crop": "MELON", "yield_units": 3}
        obs, selected = fixture(tile=plant)
        repaired, _ = repair_selected(obs, selected)
        self.assertIs(repaired, selected)
        obs, selected = fixture(tile=animal_tile("GOOSE"))
        obs["farms"][0]["tiles"][2][2]["kind"] = "COOP"
        repaired, _ = repair_selected(obs, selected)
        self.assertIs(repaired, selected)

    def test_nonduplicate_actions_and_market_rows_are_exact(self):
        obs, selected = fixture(positions=[[2, 2], [2, 2], [4, 4]],
                                actions=[["HARVEST"], ["HARVEST"], ["DROP"]])
        repaired, report = repair_selected(obs, selected)
        self.assertTrue(report["changed"])
        self.assertEqual(repaired["hands"][1], ["DROP"])
        self.assertEqual(repaired["market"], selected["market"])

    def test_malformed_observation_fails_closed(self):
        selected = {"farmer": ["HARVEST"], "hands": [["HARVEST"]], "market": []}
        repaired, report = repair_selected({}, selected)
        self.assertIs(repaired, selected)
        self.assertEqual(report["reason"], "observation_shape")


if __name__ == "__main__":
    unittest.main()
