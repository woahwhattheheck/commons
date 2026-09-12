#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Exact-engine witness for the broader annual HARVEST->PLANT->WATER seam.

This deliberately does *not* widen UNITPIPE's reorder helper. HARVEST transfers
cargo into the executing actor's private inventory, so moving a HARVEST row
between actor slots would change custody even when the shared tile transition is
otherwise legal. The tests below preserve that boundary while proving the
source-real same-callback relay for already-correct actor ordering.
"""
from __future__ import annotations

from copy import deepcopy
import unittest

from test_unit_pipeline import load_engine, observation
from unit_pipeline import reorder_unit_pipeline

ANNUALS = ("WHEAT", "CARROT", "MELON")


def apply_rows_at_day(engine, obs, selected, day):
    farm = obs["farms"][0]
    private = obs["private"]
    rows = [selected["farmer"], *selected.get("hands", [])]
    for idx, row in enumerate(rows):
        engine._apply_unit_action(farm, private, idx, row, 10, day, 24, 100)


class AnnualRelayWitnessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = load_engine()

    def mature_annual_observation(self, old_crop, new_crop, *, day=12):
        first = self.engine.CROPS[old_crop]["first_yield_day"]
        plant = self.engine._new_plant(old_crop, day - first, 24)
        plant["yield_units"] = min(3, self.engine.CROPS[old_crop]["max_yield"])
        plant["watered_today"] = True
        plant["consecutive_unwatered"] = 0
        obs = observation(plant, hands=2, seeds={new_crop: 1})
        return obs, plant["yield_units"]

    def test_all_annual_old_to_new_relays_survive_end_of_day(self):
        day = 12
        for old_crop in ANNUALS:
            for new_crop in ANNUALS:
                with self.subTest(old_crop=old_crop, new_crop=new_crop):
                    obs, source_units = self.mature_annual_observation(old_crop, new_crop, day=day)
                    action = {
                        "farmer": ["HARVEST"],
                        "hands": [["PLANT", new_crop], ["WATER"]],
                        "market": [],
                    }
                    apply_rows_at_day(self.engine, obs, action, day)

                    farm = obs["farms"][0]
                    private = obs["private"]
                    tile = farm["tiles"][4][4]
                    self.assertEqual(source_units, private["inventories"][0].get(old_crop))
                    self.assertNotIn(old_crop, private["inventories"][1])
                    self.assertNotIn(old_crop, private["inventories"][2])
                    self.assertEqual(0, private["seeds"].get(new_crop))
                    self.assertEqual("PLANT", tile["kind"])
                    self.assertEqual(new_crop, tile["crop"])
                    self.assertEqual(day, tile["planted_day"])
                    self.assertTrue(tile["watered_today"])
                    self.assertEqual(1, tile["consecutive_unwatered"])

                    self.engine._daily_refresh_plants(farm, day, 24)
                    tile = farm["tiles"][4][4]
                    self.assertEqual("PLANT", tile["kind"])
                    self.assertEqual(new_crop, tile["crop"])
                    self.assertEqual(0, tile["consecutive_unwatered"])
                    self.assertFalse(tile["watered_today"])

    def test_reversed_water_then_plant_dies_at_end_of_day(self):
        day = 12
        obs, _ = self.mature_annual_observation("WHEAT", "CARROT", day=day)
        action = {
            "farmer": ["HARVEST"],
            "hands": [["WATER"], ["PLANT", "CARROT"]],
            "market": [],
        }
        apply_rows_at_day(self.engine, obs, action, day)
        farm = obs["farms"][0]
        tile = farm["tiles"][4][4]
        self.assertEqual("PLANT", tile["kind"])
        self.assertFalse(tile["watered_today"])
        self.assertEqual(1, tile["consecutive_unwatered"])

        self.engine._daily_refresh_plants(farm, day, 24)
        self.assertEqual({"kind": "WEED"}, farm["tiles"][4][4])

    def test_unitpipe_keeps_harvest_actor_custody_out_of_reorder_scope(self):
        day = 12
        obs, _ = self.mature_annual_observation("WHEAT", "CARROT", day=day)
        action = {
            "farmer": ["HARVEST"],
            "hands": [["PLANT", "CARROT"], ["WATER"]],
            "market": [],
        }
        before = deepcopy(action)
        got, report = reorder_unit_pipeline(obs, action, enabled=True)
        self.assertEqual(before, got)
        self.assertFalse(report["changed"])
        self.assertEqual(1, report["refusals"].get("noncanonical_or_impure_row"))


if __name__ == "__main__":
    unittest.main()
