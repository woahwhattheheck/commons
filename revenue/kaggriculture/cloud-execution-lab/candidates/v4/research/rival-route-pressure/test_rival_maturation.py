#!/usr/bin/env python3
import copy
import unittest

import rival_maturation as r
from rival_route_pressure import UnsupportedEvidence


def plant(crop, *, planted_day=0, yield_units=0, watered_today=False, consecutive_unwatered=0):
    return {
        "kind": "PLANT",
        "crop": crop,
        "planted_day": planted_day,
        "yield_units": yield_units,
        "watered_today": watered_today,
        "consecutive_unwatered": consecutive_unwatered,
    }


def obs(*rival_tiles):
    return {
        "player": 0,
        "farms": [
            {"tiles": [[None]]},
            {"tiles": [list(rival_tiles)]},
        ],
    }


class RivalMaturationTests(unittest.TestCase):
    def test_melon_day9_to_day10_upper_bound(self):
        report = r.public_rival_maturation(
            obs(plant("MELON", yield_units=1)), {"turnsPerDay": 24}, start=216, horizon=25
        )
        melon = report["products"]["MELON"]
        self.assertEqual(melon["visible_sources"], 1)
        self.assertEqual(melon["harvestable_now_units"], 0)
        self.assertEqual(melon["single_harvest_burst_ceiling_by_end_units"], 5)
        self.assertEqual(melon["incremental_maturing_units"], 5)
        self.assertEqual(melon["earliest_maturity_step"], 240)

    def test_melon_before_maturity_is_not_harvestable(self):
        report = r.public_rival_maturation(
            obs(plant("MELON", yield_units=1)), {"turnsPerDay": 24}, start=216, horizon=24
        )
        melon = report["products"]["MELON"]
        self.assertEqual(report["end"], 239)
        self.assertEqual(melon["single_harvest_burst_ceiling_by_end_units"], 0)
        self.assertEqual(melon["incremental_maturing_units"], 0)

    def test_strawberry_first_production_eod_is_counted(self):
        report = r.public_rival_maturation(
            obs(plant("STRAWBERRY")), {"turnsPerDay": 24}, start=216, horizon=25
        )
        berry = report["products"]["STRAWBERRY"]
        self.assertEqual(berry["harvestable_now_units"], 0)
        self.assertEqual(berry["single_harvest_burst_ceiling_by_end_units"], 2)
        self.assertEqual(berry["incremental_maturing_units"], 2)
        self.assertEqual(berry["earliest_maturity_step"], 240)

    def test_already_watered_annual_does_not_double_count_current_day(self):
        report = r.public_rival_maturation(
            obs(plant("MELON", yield_units=3, watered_today=True)),
            {"turnsPerDay": 24},
            start=216,
            horizon=25,
        )
        self.assertEqual(
            report["products"]["MELON"]["single_harvest_burst_ceiling_by_end_units"], 5
        )

    def test_mature_melon_reports_now_and_incremental_headroom(self):
        report = r.public_rival_maturation(
            obs(plant("MELON", yield_units=3)), {"turnsPerDay": 24}, start=240, horizon=1
        )
        melon = report["products"]["MELON"]
        self.assertEqual(melon["harvestable_now_units"], 3)
        self.assertEqual(melon["single_harvest_burst_ceiling_by_end_units"], 5)
        self.assertEqual(melon["incremental_maturing_units"], 2)

    def test_default_scope_ignores_other_crops(self):
        report = r.public_rival_maturation(
            obs(plant("CARROT", planted_day=8, yield_units=2)),
            {"turnsPerDay": 24},
            start=240,
            horizon=24,
        )
        self.assertEqual(report["products"]["STRAWBERRY"]["visible_sources"], 0)
        self.assertEqual(report["products"]["MELON"]["visible_sources"], 0)
        self.assertEqual(report["tiles"], [])

    def test_explicit_scope_can_include_all_crops(self):
        report = r.public_rival_maturation(
            obs(plant("CARROT", planted_day=8, yield_units=2)),
            {"turnsPerDay": 24},
            start=240,
            horizon=1,
            products=("CARROT",),
        )
        self.assertEqual(report["products"]["CARROT"]["harvestable_now_units"], 2)

    def test_private_rival_payload_is_not_used(self):
        a = obs(plant("STRAWBERRY"))
        b = copy.deepcopy(a)
        a["private"] = {"shed": {"STRAWBERRY": 999999}}
        b["private"] = {"shed": {"STRAWBERRY": 0}}
        self.assertEqual(
            r.public_rival_maturation(a, {"turnsPerDay": 24}, start=216, horizon=25),
            r.public_rival_maturation(b, {"turnsPerDay": 24}, start=216, horizon=25),
        )

    def test_output_never_claims_decision_authority(self):
        report = r.public_rival_maturation(
            obs(plant("STRAWBERRY")), {"turnsPerDay": 24}, start=216, horizon=25
        )
        self.assertFalse(report["decision_authority"])
        self.assertFalse(report["sale_timing_authority"])
        self.assertFalse(report["opponent_identity_used"])
        self.assertFalse(report["private_rival_state_used"])

    def test_malformed_public_state_fails_closed(self):
        bad = obs(plant("MELON", yield_units=7))
        with self.assertRaises(UnsupportedEvidence):
            r.public_rival_maturation(bad, {"turnsPerDay": 24}, start=240)
        bad = obs(plant("MELON", consecutive_unwatered=2))
        with self.assertRaises(UnsupportedEvidence):
            r.public_rival_maturation(bad, {"turnsPerDay": 24}, start=240)
        with self.assertRaises(UnsupportedEvidence):
            r.public_rival_maturation(obs(), {"turnsPerDay": True}, start=0)
        with self.assertRaises(UnsupportedEvidence):
            r.public_rival_maturation(obs(), {"turnsPerDay": 24}, start=0, horizon=0)


if __name__ == "__main__":
    unittest.main()
