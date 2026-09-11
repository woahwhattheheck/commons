# SPDX-License-Identifier: Apache-2.0
"""Focused checks for V4 F1 ``r04_fert_mix``.

Run in a materialised candidate package:

    python -B -m unittest -v checks/test_v4_fert_mix.py
"""
from __future__ import annotations

import copy
import json
import sys
import types
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import r04_fert_hand as fert  # noqa: E402
import r04_fert_mix as lane  # noqa: E402
import r04_full_router as r04  # noqa: E402
from titan_runtime import Features  # noqa: E402


def _tape():
    return [{"farmer": ["PASS"], "hands": [], "market": []} for _ in range(719)]


def observation(step=586, position=(1, 1), wheat=(1, 1), wheat_price=100,
                fertilizer_price=10, fertilizer=1, carrot=None):
    tiles = [[None for _ in range(10)] for _ in range(10)]
    if wheat is not None:
        x, y = wheat
        tiles[y][x] = {"kind": "PLANT", "crop": "WHEAT", "planted_day": 22,
                       "fertilized_until_day": -1, "yield_units": 1,
                       "watered_today": False}
    if carrot is not None:
        x, y = carrot
        tiles[y][x] = {"kind": "PLANT", "crop": "CARROT", "planted_day": 23,
                       "fertilized_until_day": -1, "yield_units": 1,
                       "watered_today": False}
    farm = {"tiles": tiles, "farmer": [4, 4], "hands": [list(position)],
            "money": 1000, "unlocked_quadrants": ["NW"], "hires_today": 1}
    return {
        "step": step, "day": step // 24, "hour": step % 24, "player": 0,
        "farms": [farm, copy.deepcopy(farm)],
        "private": {"inventories": [{}, {"FERTILIZER": fertilizer}],
                    "shed": {"FERTILIZER": 0}},
        "market": {"prices": {"WHEAT": wheat_price, "FERTILIZER": fertilizer_price}},
        "town": {"unlocked_shops": ["BAKERY", "YARN_STORE"]},
    }


def action(command=None):
    return {"farmer": ["PASS"], "hands": [command or ["PASS"]],
            "market": [["SELL", "WHEAT", 1]]}


class FertMix(unittest.TestCase):
    def setUp(self):
        fert.FERT_HAND = True
        fert._STATE.clear()
        for key in lane.REPORT:
            lane.REPORT[key] = 0
        fert._STATE[0] = types.SimpleNamespace(index=0, want=1)

    def tearDown(self):
        fert._STATE.clear()
        fert.FERT_HAND = False
        if hasattr(r04, "FERT_MIX"):
            r04.FERT_MIX = False

    def _run(self, obs, parent, tape=None):
        with mock.patch.object(r04, "_policy_tape", return_value=tape or _tape()):
            return lane.apply_fert_mix(obs, parent, enabled=True)

    def test_key_ships_off_and_features_accept_it(self):
        data = json.loads((ROOT / "TITAN-CONFIG.json").read_text(encoding="utf-8"))
        self.assertIs(data["r04_fert_mix"], False)
        self.assertIs(Features(**data).r04_fert_mix, False)
        r04.install(fert_mix=True)
        self.assertIs(r04.FERT_MIX, True)
        r04.install(fert_mix=False)
        self.assertIs(r04.FERT_MIX, False)

    def test_disabled_returns_exact_parent_object(self):
        parent = action()
        self.assertIs(lane.apply_fert_mix(observation(), parent, enabled=False), parent)

    def test_nonpass_existing_hand_work_is_never_replaced(self):
        parent = action(["WEST"])
        self.assertIs(self._run(observation(), parent), parent)

    def test_no_fertilizer_returns_exact_parent(self):
        parent = action()
        self.assertIs(self._run(observation(fertilizer=0), parent), parent)
        self.assertEqual(lane.REPORT["declined_no_fertilizer"], 1)

    def test_current_carrot_target_reserves_fertilizer(self):
        parent = action()
        obs = observation(carrot=(3, 3))
        self.assertIs(self._run(obs, parent), parent)
        self.assertEqual(lane.REPORT["declined_carrot_reserve"], 1)

    def test_future_carrot_planting_reserves_fertilizer(self):
        parent = action()
        tape = _tape()
        tape[587]["farmer"] = ["PLANT", "CARROT"]
        self.assertIs(self._run(observation(), parent, tape=tape), parent)
        self.assertEqual(lane.REPORT["declined_carrot_reserve"], 1)

    def test_idle_hand_fertilizes_profitable_wheat_underfoot(self):
        parent = action()
        out = self._run(observation(), parent)
        self.assertIsNot(out, parent)
        self.assertEqual(out["hands"], [["FERTILIZE"]])
        self.assertEqual(out["market"], parent["market"])
        self.assertEqual(len(out["hands"]), len(parent["hands"]))
        self.assertEqual(lane.REPORT["fertilized_wheat"], 1)

    def test_idle_hand_moves_toward_profitable_wheat(self):
        parent = action()
        out = self._run(observation(position=(0, 1), wheat=(2, 1)), parent)
        self.assertEqual(out["hands"], [["EAST"]])
        self.assertEqual(out["market"], parent["market"])
        self.assertEqual(lane.REPORT["moves_to_wheat"], 1)

    def test_low_roi_wheat_is_left_alone(self):
        parent = action()
        obs = observation(wheat_price=10, fertilizer_price=30)
        self.assertIs(self._run(obs, parent), parent)
        self.assertEqual(lane.REPORT["declined_no_roi"], 1)

    def test_last_hour_requires_wheat_underfoot(self):
        parent = action()
        obs = observation(step=599, position=(0, 1), wheat=(1, 1))
        self.assertIs(self._run(obs, parent), parent)
        obs2 = observation(step=599, position=(1, 1), wheat=(1, 1))
        out = self._run(obs2, parent)
        self.assertEqual(out["hands"], [["FERTILIZE"]])


if __name__ == "__main__":
    unittest.main()
