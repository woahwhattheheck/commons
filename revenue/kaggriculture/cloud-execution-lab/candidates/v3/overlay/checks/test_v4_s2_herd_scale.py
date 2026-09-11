# SPDX-License-Identifier: Apache-2.0
"""Focused checks for the V4 S2 V233 herd-scale profile."""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import r04_full_router as r04  # noqa: E402
import r04_s2_herd_scale as s2  # noqa: E402
from titan_runtime import Features  # noqa: E402


def _grid(fill=None):
    return [[fill for _ in range(10)] for _ in range(10)]


def _obs(step=288, *, hands=0, money=100_000, tiles=None):
    if tiles is None:
        tiles = _grid(None)
    farm = {
        "tiles": tiles,
        "farmer": [4, 4],
        "hands": [[4, 4] for _ in range(hands)],
        "money": money,
        "unlocked_quadrants": ["NW", "NE", "SW"],
        "hires_today": 0,
    }
    return {
        "step": step,
        "day": step // 24,
        "hour": step % 24,
        "player": 0,
        "farms": [farm, dict(farm)],
        "private": {
            "shed": {},
            "inventories": [{} for _ in range(hands + 1)],
        },
        "market": {
            "prices": {"WHEAT": 25, "WOOL": 220},
            "inventory": {},
        },
        "town": {"unlocked_shops": ["YARN_STORE", "YARN_STORE"]},
    }


def _action(hands=0):
    return {"farmer": ["PASS"], "hands": [["PASS"] for _ in range(hands)], "market": []}


class S2HerdScaleTests(unittest.TestCase):
    def tearDown(self):
        r04.install(s2_herd_scale=False)

    def test_key_ships_off_and_features_accept_it(self):
        data = json.loads((ROOT / "TITAN-CONFIG.json").read_text(encoding="utf-8"))
        self.assertIs(data["r04_s2_herd_scale"], False)
        self.assertIs(Features(**data).r04_s2_herd_scale, False)

    def test_profile_off_is_exact_published_v233_shape(self):
        r04.install(s2_herd_scale=False)
        self.assertEqual(
            r04._v4_s2_profile(),
            {"sheep": 6, "workers": 2, "targets": s2.BASE_TARGETS},
        )
        self.assertEqual(s2.initial_fixed_cost(r04._v4_s2_profile()), 7000)

    def test_profile_on_scales_animals_without_changing_hire_footprint(self):
        r04.install(s2_herd_scale=True)
        profile = r04._v4_s2_profile()
        self.assertEqual(profile["sheep"], 8)
        self.assertEqual(profile["workers"], 2)
        self.assertEqual(profile["targets"], s2.SCALED_TARGETS)
        self.assertEqual(s2.initial_fixed_cost(profile), 8000)
        self.assertEqual(len(profile["targets"][0]), 4)
        self.assertEqual(len(profile["targets"][1]), 4)

    def test_initial_request_scales_sheep_and_grain_but_not_hires(self):
        original_eligible = r04._v233_eligible
        original_native_day = r04._v219_native_day
        r04._v233_eligible = lambda obs, native: True
        r04._v219_native_day = lambda native, day: [
            {"farmer": ["PASS"], "hands": [], "market": []} for _ in range(24)
        ]
        try:
            for enabled, sheep, targets in (
                (False, 6, s2.BASE_TARGETS),
                (True, 8, s2.SCALED_TARGETS),
            ):
                with self.subTest(enabled=enabled):
                    r04.install(s2_herd_scale=enabled)
                    state = {}
                    result = r04._v233_request(_obs(), _action(), state, object())
                    self.assertEqual(
                        result["market"],
                        [["BUY_LAND"], ["BUY_ANIMAL", "SHEEP", sheep],
                         ["BUY_PRODUCT", "WHEAT", sheep], ["HIRE"], ["HIRE"]],
                    )
                    self.assertEqual(state["pending"]["sheep"], sheep)
                    self.assertEqual(state["pending"]["workers"], 2)
                    self.assertEqual(state["pending"]["targets"], targets)
        finally:
            r04._v233_eligible = original_eligible
            r04._v219_native_day = original_native_day

    def test_scaled_eligibility_requires_only_added_target_cells_to_be_pristine(self):
        original_native_day = r04._v219_native_day
        r04._v219_native_day = lambda native, day: [
            {"farmer": ["PASS"], "hands": [], "market": []}
        ]
        try:
            tiles = _grid(None)
            for group in s2.SCALED_TARGETS:
                for x, y in group:
                    tiles[y][x] = "LOCKED"
            tiles[7][5] = None
            observation = _obs(tiles=tiles)

            r04.install(s2_herd_scale=False)
            self.assertTrue(r04._v233_eligible(observation, object()))
            r04.install(s2_herd_scale=True)
            self.assertFalse(r04._v233_eligible(observation, object()))
        finally:
            r04._v219_native_day = original_native_day

    def test_rescue_cap_tracks_eight_active_target_cells(self):
        tiles = _grid(None)
        targets = {1: list(s2.SCALED_TARGETS[0]), 2: list(s2.SCALED_TARGETS[1])}
        for group in targets.values():
            for x, y in group:
                tiles[y][x] = {"kind": "PASTURE", "animal": "SHEEP", "fed_today": False}

        observation = _obs(step=300, hands=2, tiles=tiles)
        observation["private"]["inventories"] = [{}, {}, {}]
        state = {"workers": targets, "rescue_today": 0}
        result = r04._v234_rescue(observation, _action(hands=2), state)
        self.assertEqual(result["market"], [["BUY_PRODUCT", "WHEAT", 8]])
        self.assertEqual(state["rescue_today"], 8)

    def test_profile_helper_rejects_target_count_drift(self):
        original = dict(s2.SCALED_PROFILE)
        try:
            s2.SCALED_PROFILE["sheep"] = 7
            with self.assertRaises(ValueError):
                s2.v233_profile(True)
        finally:
            s2.SCALED_PROFILE.clear()
            s2.SCALED_PROFILE.update(original)


if __name__ == "__main__":
    unittest.main()
