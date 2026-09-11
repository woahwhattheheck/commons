#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import copy
import unittest

import a5_melon_jit_fertilize as a5


def fixture(*, step=250, crop="MELON", planted_day=4, fertilizer=2, yield_units=2):
    tiles = [[None for _ in range(3)] for _ in range(3)]
    tiles[1][1] = {
        "kind": "PLANT",
        "crop": crop,
        "planted_day": planted_day,
        "yield_units": yield_units,
        "watered_today": False,
        "fertilized_until_day": -1,
    }
    obs = {
        "step": step,
        "player": 0,
        "farms": [{"farmer": [0, 0], "hands": [[1, 1]], "tiles": tiles}],
        "private": {"inventories": [{}, {"FERTILIZER": fertilizer}]},
    }
    action = {"farmer": ["PASS"], "hands": [["PASS"]], "market": [["SELL", "MILK", 2]]}
    nxt = {"farmer": ["PASS"], "hands": [["WATER"]], "market": []}
    return obs, action, nxt


class A5MelonJitTests(unittest.TestCase):
    def test_positive_changes_only_literal_pass_and_preserves_market(self):
        obs, action, nxt = fixture()
        frozen = copy.deepcopy(action)
        out, rows = a5.apply_melon_jit_fertilize(action, obs, nxt, enabled=True)
        self.assertEqual(action, frozen)
        self.assertIsNot(out, action)
        self.assertEqual(out["farmer"], ["PASS"])
        self.assertEqual(out["hands"], [["FERTILIZE"]])
        self.assertEqual(out["market"], frozen["market"])
        self.assertEqual(rows[0]["crop"], "MELON")
        self.assertEqual(rows[0]["authored_water_step"], obs["step"] + 1)

    def test_disabled_is_exact_identity(self):
        obs, action, nxt = fixture()
        out, rows = a5.apply_melon_jit_fertilize(action, obs, nxt, enabled=False)
        self.assertIs(out, action)
        self.assertEqual(rows, ())

    def test_only_melon_is_eligible(self):
        for crop in ("WHEAT", "CARROT", "STRAWBERRY", "TOMATO"):
            with self.subTest(crop=crop):
                obs, action, nxt = fixture(crop=crop)
                out, rows = a5.apply_melon_jit_fertilize(action, obs, nxt, enabled=True)
                self.assertIs(out, action)
                self.assertEqual(rows, ())

    def test_requires_next_authored_same_worker_water(self):
        obs, action, nxt = fixture()
        nxt["hands"][0] = ["HARVEST"]
        out, rows = a5.apply_melon_jit_fertilize(action, obs, nxt, enabled=True)
        self.assertIs(out, action)
        self.assertEqual(rows, ())

    def test_blocked_repair_worker_fails_closed(self):
        obs, action, nxt = fixture()
        out, rows = a5.apply_melon_jit_fertilize(action, obs, nxt, blocked_workers=(1,), enabled=True)
        self.assertIs(out, action)
        self.assertEqual(rows, ())

    def test_day_boundary_fails_closed(self):
        obs, action, nxt = fixture(step=263, planted_day=4)
        out, rows = a5.apply_melon_jit_fertilize(action, obs, nxt, enabled=True)
        self.assertIs(out, action)
        self.assertEqual(rows, ())

    def test_outside_yield_window_fails_closed(self):
        # day 10, planted day 5 -> age 5, before MELON's age-6 yield window.
        obs, action, nxt = fixture(step=250, planted_day=5)
        out, rows = a5.apply_melon_jit_fertilize(action, obs, nxt, enabled=True)
        self.assertIs(out, action)
        self.assertEqual(rows, ())

    def test_existing_coverage_and_yield_cap_fail_closed(self):
        obs, action, nxt = fixture()
        tile = obs["farms"][0]["tiles"][1][1]
        tile["fertilized_until_day"] = obs["step"] // 24
        self.assertIs(a5.apply_melon_jit_fertilize(action, obs, nxt, enabled=True)[0], action)
        tile["fertilized_until_day"] = -1
        tile["yield_units"] = a5.MELON_MAX_YIELD
        self.assertIs(a5.apply_melon_jit_fertilize(action, obs, nxt, enabled=True)[0], action)

    def test_max_minus_one_has_zero_marginal_yield(self):
        obs, action, nxt = fixture(yield_units=a5.MELON_MAX_YIELD - 1)
        frozen = copy.deepcopy(action)
        out, rows = a5.apply_melon_jit_fertilize(action, obs, nxt, enabled=True)
        self.assertIs(out, action)
        self.assertEqual(action, frozen)
        self.assertEqual(rows, ())

    def test_two_units_headroom_remains_eligible(self):
        obs, action, nxt = fixture(yield_units=a5.MELON_MAX_YIELD - 2)
        out, rows = a5.apply_melon_jit_fertilize(action, obs, nxt, enabled=True)
        self.assertIsNot(out, action)
        self.assertEqual(out["hands"], [["FERTILIZE"]])
        self.assertEqual(len(rows), 1)

    def test_bool_and_string_quantities_do_not_coerce(self):
        for bad in (True, "2", 2.0):
            with self.subTest(bad=bad):
                obs, action, nxt = fixture()
                obs["private"]["inventories"][1]["FERTILIZER"] = bad
                out, rows = a5.apply_melon_jit_fertilize(action, obs, nxt, enabled=True)
                self.assertIs(out, action)
                self.assertEqual(rows, ())

    def test_same_tile_workers_are_deduped(self):
        obs, action, nxt = fixture()
        obs["farms"][0]["hands"].append([1, 1])
        obs["private"]["inventories"].append({"FERTILIZER": 2})
        action["hands"].append(["PASS"])
        nxt["hands"].append(["WATER"])
        out, rows = a5.apply_melon_jit_fertilize(action, obs, nxt, enabled=True)
        self.assertEqual(len(rows), 1)
        self.assertEqual(out["hands"].count(["FERTILIZE"]), 1)


if __name__ == "__main__":
    unittest.main()
