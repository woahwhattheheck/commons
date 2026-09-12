#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from copy import deepcopy
import hashlib
import importlib.util
from pathlib import Path
import sys
import types
import unittest

HERE = Path(__file__).resolve().parent
LAB = HERE.parents[4]
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from unit_pipeline import ENGINE_GIT_BLOB, reorder_unit_pipeline

ENGINE = LAB / "reference" / "engine" / "kaggriculture.py"


def git_blob(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def load_engine():
    pkg = types.ModuleType("kaggle_environments")
    utils = types.ModuleType("kaggle_environments.utils")
    utils.resolve_episode_seed = lambda env: 0
    old_pkg = sys.modules.get("kaggle_environments")
    old_utils = sys.modules.get("kaggle_environments.utils")
    sys.modules["kaggle_environments"] = pkg
    sys.modules["kaggle_environments.utils"] = utils
    try:
        spec = importlib.util.spec_from_file_location("_unitpipe_engine", ENGINE)
        module = importlib.util.module_from_spec(spec)
        sys.modules["_unitpipe_engine"] = module
        assert spec.loader is not None
        spec.loader.exec_module(module)
        return module
    finally:
        if old_pkg is None:
            sys.modules.pop("kaggle_environments", None)
        else:
            sys.modules["kaggle_environments"] = old_pkg
        if old_utils is None:
            sys.modules.pop("kaggle_environments.utils", None)
        else:
            sys.modules["kaggle_environments.utils"] = old_utils


def observation(tile, *, hands=1, seeds=None, positions=None):
    board = [[None for _ in range(10)] for _ in range(10)]
    board[4][4] = deepcopy(tile)
    if positions is None:
        positions = [[4, 4] for _ in range(hands + 1)]
    farm = {
        "money": 3000.0,
        "tiles": board,
        "farmer": list(positions[0]),
        "hands": [list(p) for p in positions[1:]],
        "unlocked_quadrants": ["NW"],
        "hires_today": 0,
    }
    private = {
        "shed": {},
        "seeds": dict(seeds or {}),
        "inventories": [{} for _ in range(hands + 1)],
    }
    return {"player": 0, "farms": [farm], "private": private}


def apply_rows(engine, obs, selected):
    farm = obs["farms"][0]
    private = obs["private"]
    rows = [selected["farmer"], *selected.get("hands", [])]
    for idx, row in enumerate(rows):
        engine._apply_unit_action(farm, private, idx, row, 10, 0, 24, 100)


class UnitPipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = load_engine()

    def test_engine_pin(self):
        self.assertEqual(ENGINE_GIT_BLOB, git_blob(ENGINE))

    def test_disabled_is_exact_identity(self):
        obs = observation(None, hands=1, seeds={"STRAWBERRY": 1})
        action = {"farmer": ["WATER"], "hands": [["PLANT", "STRAWBERRY"]], "market": [["HIRE"]]}
        got, report = reorder_unit_pipeline(obs, action, enabled=False)
        self.assertEqual(action, got)
        self.assertFalse(report["changed"])
        self.assertEqual(1, report["refusals"]["disabled"])

    def test_empty_tile_reorders_plant_then_water(self):
        obs = observation(None, hands=1, seeds={"STRAWBERRY": 1})
        action = {"farmer": ["WATER"], "hands": [["PLANT", "STRAWBERRY"]], "market": []}
        got, report = reorder_unit_pipeline(obs, action, enabled=True)
        self.assertEqual(["PLANT", "STRAWBERRY"], got["farmer"])
        self.assertEqual([["WATER"]], got["hands"])
        self.assertTrue(report["changed"])
        self.assertEqual(action["market"], got["market"])

    def test_engine_witness_new_ongoing_crop_is_watered(self):
        base = observation(None, hands=1, seeds={"STRAWBERRY": 1})
        cand = deepcopy(base)
        action = {"farmer": ["WATER"], "hands": [["PLANT", "STRAWBERRY"]], "market": []}
        got, _ = reorder_unit_pipeline(cand, action, enabled=True)
        apply_rows(self.engine, base, action)
        apply_rows(self.engine, cand, got)
        self.assertEqual("PLANT", base["farms"][0]["tiles"][4][4]["kind"])
        self.assertFalse(base["farms"][0]["tiles"][4][4]["watered_today"])
        self.assertTrue(cand["farms"][0]["tiles"][4][4]["watered_today"])
        self.assertEqual(base["private"]["seeds"], cand["private"]["seeds"])

    def test_weed_chain_reorders_dig_plant_water(self):
        weed = {"kind": "WEED"}
        obs = observation(weed, hands=2, seeds={"TOMATO": 1})
        action = {
            "farmer": ["WATER"],
            "hands": [["PLANT", "TOMATO"], ["DIG"]],
            "market": [["BUY_SEED", "TOMATO", 1]],
        }
        got, report = reorder_unit_pipeline(obs, action, enabled=True)
        self.assertEqual(["DIG"], got["farmer"])
        self.assertEqual([["PLANT", "TOMATO"], ["WATER"]], got["hands"])
        self.assertEqual(action["market"], got["market"])
        self.assertTrue(report["changed"])

    def test_engine_witness_weed_chain_changes_noop_to_live_crop(self):
        weed = {"kind": "WEED"}
        base = observation(weed, hands=2, seeds={"TOMATO": 1})
        cand = deepcopy(base)
        action = {"farmer": ["WATER"], "hands": [["PLANT", "TOMATO"], ["DIG"]], "market": []}
        got, _ = reorder_unit_pipeline(cand, action, enabled=True)
        apply_rows(self.engine, base, action)
        apply_rows(self.engine, cand, got)
        self.assertIsNone(base["farms"][0]["tiles"][4][4])
        tile = cand["farms"][0]["tiles"][4][4]
        self.assertEqual("PLANT", tile["kind"])
        self.assertEqual("TOMATO", tile["crop"])
        self.assertTrue(tile["watered_today"])

    def test_different_positions_refuse(self):
        obs = observation(None, hands=1, seeds={"WHEAT": 1}, positions=[[4, 4], [3, 4]])
        action = {"farmer": ["WATER"], "hands": [["PLANT", "WHEAT"]], "market": []}
        got, report = reorder_unit_pipeline(obs, action, enabled=True)
        self.assertEqual(action, got)
        self.assertFalse(report["changed"])

    def test_existing_plant_is_not_destroyed(self):
        plant = {
            "kind": "PLANT", "crop": "WHEAT", "planted_day": 0,
            "watered_today": False, "consecutive_unwatered": 0,
            "yield_units": 6, "max_lifespan_step": 200, "fertilized_until_day": -1,
        }
        obs = observation(plant, hands=1, seeds={"WHEAT": 1})
        action = {"farmer": ["PLANT", "WHEAT"], "hands": [["DIG"]], "market": []}
        got, report = reorder_unit_pipeline(obs, action, enabled=True)
        self.assertEqual(action, got)
        self.assertFalse(report["changed"])
        self.assertEqual(1, report["refusals"]["tile_not_safe_for_pipeline"])

    def test_seed_unavailable_refuses(self):
        obs = observation(None, hands=1, seeds={"WHEAT": 0})
        action = {"farmer": ["WATER"], "hands": [["PLANT", "WHEAT"]], "market": []}
        got, report = reorder_unit_pipeline(obs, action, enabled=True)
        self.assertEqual(action, got)
        self.assertEqual(1, report["refusals"]["seed_not_observed_available"])

    def test_impure_group_refuses(self):
        obs = observation(None, hands=2, seeds={"WHEAT": 1})
        action = {"farmer": ["WATER"], "hands": [["PLANT", "WHEAT"], ["FEED"]], "market": []}
        got, report = reorder_unit_pipeline(obs, action, enabled=True)
        self.assertEqual(action, got)
        self.assertEqual(1, report["refusals"]["noncanonical_or_impure_row"])

    def test_atomic_plant_demand_multiset_is_preserved(self):
        weed = {"kind": "WEED"}
        obs = observation(weed, hands=2, seeds={"CARROT": 1})
        action = {"farmer": ["PLANT", "CARROT"], "hands": [["DIG"], ["WATER"]], "market": []}
        got, _ = reorder_unit_pipeline(obs, action, enabled=True)

        def plants(a):
            rows = [a["farmer"], *a["hands"]]
            return sorted(tuple(row) for row in rows if row and row[0] == "PLANT")

        self.assertEqual(plants(action), plants(got))
        self.assertEqual(len(action["hands"]), len(got["hands"]))

    def test_already_ordered_is_eligible_but_unchanged(self):
        obs = observation(None, hands=1, seeds={"WHEAT": 1})
        action = {"farmer": ["PLANT", "WHEAT"], "hands": [["WATER"]], "market": []}
        got, report = reorder_unit_pipeline(obs, action, enabled=True)
        self.assertEqual(action, got)
        self.assertEqual(1, report["eligible_groups"])
        self.assertFalse(report["changed"])


if __name__ == "__main__":
    unittest.main()
