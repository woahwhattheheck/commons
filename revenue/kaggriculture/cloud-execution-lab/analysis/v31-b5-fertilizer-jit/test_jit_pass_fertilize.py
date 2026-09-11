# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations
import copy
import unittest
import jit_pass_fertilize as jit


def fixture():
    tiles = [[None for _ in range(3)] for _ in range(3)]
    tiles[1][1] = {
        "kind": "PLANT", "crop": "WHEAT", "planted_day": 16,
        "yield_units": 1, "watered_today": False,
        "fertilized_until_day": -1, "consecutive_unwatered": 0,
    }
    obs = {
        "step": 454, "player": 0,
        "farms": [{"farmer": [0, 0], "hands": [[1, 1]], "tiles": tiles}],
        "private": {"inventories": [{}, {"FERTILIZER": 3}]},
    }
    action = {"farmer": ["PASS"], "hands": [["PASS"]], "market": []}
    nxt = {"farmer": ["PASS"], "hands": [["WATER"]], "market": []}
    return obs, action, nxt


class JitPassFertilizeTests(unittest.TestCase):
    def test_positive_hand_replaces_only_literal_pass(self):
        obs, action, nxt = fixture(); frozen = copy.deepcopy(action)
        out, rows = jit.apply_jit_pass_fertilize(action, obs, nxt, enabled=True)
        self.assertEqual(action, frozen)
        self.assertIsNot(out, action)
        self.assertEqual(out["farmer"], ["PASS"])
        self.assertEqual(out["hands"], [["FERTILIZE"]])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["worker"], 1)
        self.assertEqual(rows[0]["crop"], "WHEAT")

    def test_flag_off_is_exact_object_identity(self):
        obs, action, nxt = fixture()
        out, rows = jit.apply_jit_pass_fertilize(action, obs, nxt, enabled=False)
        self.assertIs(out, action); self.assertEqual(rows, ())

    def test_no_fertilizer_fails_closed(self):
        obs, action, nxt = fixture(); obs["private"]["inventories"][1] = {}
        out, rows = jit.apply_jit_pass_fertilize(action, obs, nxt, enabled=True)
        self.assertIs(out, action); self.assertEqual(rows, ())

    def test_existing_coverage_fails_closed(self):
        obs, action, nxt = fixture(); obs["farms"][0]["tiles"][1][1]["fertilized_until_day"] = 18
        out, _ = jit.apply_jit_pass_fertilize(action, obs, nxt, enabled=True)
        self.assertIs(out, action)

    def test_ongoing_crop_fails_closed(self):
        obs, action, nxt = fixture(); tile=obs["farms"][0]["tiles"][1][1]
        tile.update(crop="STRAWBERRY", planted_day=8)
        out, _ = jit.apply_jit_pass_fertilize(action, obs, nxt, enabled=True)
        self.assertIs(out, action)

    def test_wrong_next_op_fails_closed(self):
        obs, action, nxt = fixture(); nxt["hands"][0] = ["HARVEST"]
        out, _ = jit.apply_jit_pass_fertilize(action, obs, nxt, enabled=True)
        self.assertIs(out, action)

    def test_yield_cap_fails_closed(self):
        obs, action, nxt = fixture(); obs["farms"][0]["tiles"][1][1]["yield_units"] = 6
        out, _ = jit.apply_jit_pass_fertilize(action, obs, nxt, enabled=True)
        self.assertIs(out, action)

    def test_wheat_max_minus_one_has_zero_marginal_yield(self):
        obs, action, nxt = fixture(); obs["farms"][0]["tiles"][1][1]["yield_units"] = 5
        out, rows = jit.apply_jit_pass_fertilize(action, obs, nxt, enabled=True)
        self.assertIs(out, action); self.assertEqual(rows, ())

    def test_carrot_max_minus_one_has_zero_marginal_yield(self):
        obs, action, nxt = fixture(); tile = obs["farms"][0]["tiles"][1][1]
        tile.update(crop="CARROT", planted_day=16, yield_units=3)
        out, rows = jit.apply_jit_pass_fertilize(action, obs, nxt, enabled=True)
        self.assertIs(out, action); self.assertEqual(rows, ())

    def test_melon_max_minus_one_has_zero_marginal_yield(self):
        obs, action, nxt = fixture(); tile = obs["farms"][0]["tiles"][1][1]
        tile.update(crop="MELON", planted_day=8, yield_units=5)
        out, rows = jit.apply_jit_pass_fertilize(action, obs, nxt, enabled=True)
        self.assertIs(out, action); self.assertEqual(rows, ())

    def test_two_units_headroom_still_qualifies(self):
        obs, action, nxt = fixture(); obs["farms"][0]["tiles"][1][1]["yield_units"] = 4
        out, rows = jit.apply_jit_pass_fertilize(action, obs, nxt, enabled=True)
        self.assertIsNot(out, action); self.assertEqual(len(rows), 1)

    def test_same_tile_multi_worker_matches_fail_closed(self):
        obs, action, nxt = fixture()
        obs["farms"][0]["hands"] = [[1, 1], [1, 1]]
        obs["private"]["inventories"] = [{}, {"FERTILIZER": 3}, {"FERTILIZER": 2}]
        action["hands"] = [["PASS"], ["PASS"]]
        nxt["hands"] = [["WATER"], ["WATER"]]
        frozen = copy.deepcopy(action)
        out, rows = jit.apply_jit_pass_fertilize(action, obs, nxt, enabled=True)
        self.assertIs(out, action)
        self.assertEqual(action, frozen)
        self.assertEqual(rows, ())

    def test_watered_same_day_fails_closed(self):
        obs, action, nxt = fixture(); obs["farms"][0]["tiles"][1][1]["watered_today"] = True
        out, _ = jit.apply_jit_pass_fertilize(action, obs, nxt, enabled=True)
        self.assertIs(out, action)

    def test_day_boundary_fails_closed(self):
        obs, action, nxt = fixture(); obs["step"] = 455
        out, _ = jit.apply_jit_pass_fertilize(action, obs, nxt, enabled=True)
        self.assertIs(out, action)

    def test_malformed_state_fails_closed(self):
        obs, action, nxt = fixture(); obs["farms"][0]["tiles"][1][1]["watered_today"] = 0
        out, _ = jit.apply_jit_pass_fertilize(action, obs, nxt, enabled=True)
        self.assertIs(out, action)


if __name__ == '__main__': unittest.main()
