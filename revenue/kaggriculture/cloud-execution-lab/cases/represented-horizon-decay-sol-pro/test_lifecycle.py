#!/usr/bin/env python3
"""Full official-lifecycle reachability for the represented-decay predecessor."""
from __future__ import annotations

import ast
import copy
import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path
from types import ModuleType

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import repair


def repository_root() -> Path:
    for candidate in (HERE, *HERE.parents):
        if (candidate / repair.SOURCE_REL).is_file():
            return candidate
    raise RuntimeError("repository root not found")


REPO = repository_root()


def load_module(name: str, source: bytes, temp: tempfile.TemporaryDirectory[str]) -> ModuleType:
    path = Path(temp.name) / f"{name}.py"
    path.write_bytes(source)
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def function_ast(source: bytes, name: str) -> str:
    tree = ast.parse(source.decode("utf-8"))
    matches = [
        node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name
    ]
    if len(matches) != 1:
        raise AssertionError(f"expected one top-level {name}, observed {len(matches)}")
    return ast.dump(matches[0], annotate_fields=True, include_attributes=False)


def empty_world(module: ModuleType):
    board_size = 10
    farm = {
        "tiles": [[None] * board_size for _ in range(board_size)],
        "farmer": [4, 4],
        "hands": [],
        "money": 0,
        "hires_today": 0,
        "unlocked_quadrants": ["NW"],
    }
    private = {
        "shed": {item: 0 for item in [*module.PRODUCTS, *module.ANIMALS]},
        "seeds": {crop: 0 for crop in module.CROPS},
        "inventories": [{}],
    }
    private["seeds"]["CARROT"] = 1
    return farm, private


class RepresentedDecayLifecycleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        built = repair.build(REPO)
        cls.engine_source = built[1]
        cls.mechanics_source = built[2]
        cls.temp = tempfile.TemporaryDirectory(prefix="titan-decay-lifecycle-")
        cls.m = load_module("bound_production_mechanics", cls.mechanics_source, cls.temp)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_lifecycle_functions_are_official_engine_identical(self):
        for name in (
            "_new_plant",
            "_apply_unit_action",
            "_decay_plants",
            "_daily_refresh_plants",
        ):
            with self.subTest(name=name):
                self.assertEqual(
                    function_ast(self.mechanics_source, name),
                    function_ast(self.engine_source, name),
                )

    def test_carrot_yield_three_lifespan_120_is_full_season_reachable(self):
        m = self.m
        farm, private = empty_world(m)
        board_size = 10
        turns_per_day = 24

        # A legal day-1 PLANT followed by a later same-day WATER starts the
        # crop's survival chain without increasing yield at age zero.
        m._apply_unit_action(
            farm,
            private,
            0,
            ["PLANT", "CARROT"],
            board_size,
            1,
            turns_per_day,
            100,
        )
        planted = farm["tiles"][4][4]
        self.assertEqual(planted["yield_units"], 1)
        self.assertEqual(planted["consecutive_unwatered"], 1)
        self.assertEqual(planted["max_lifespan_step"], 120)

        for day in (1, 2, 3, 4):
            m._apply_unit_action(
                farm,
                private,
                0,
                ["WATER"],
                board_size,
                day,
                turns_per_day,
                100,
            )
            # This is the exact official EOD transition after steps 47, 71,
            # 95, and 119.  Age-2 and age-3 water add one unit each.
            m._daily_refresh_plants(farm, day, turns_per_day)

        expected = {
            "kind": "PLANT",
            "crop": "CARROT",
            "planted_day": 1,
            "watered_today": False,
            "consecutive_unwatered": 0,
            "yield_units": 3,
            "max_lifespan_step": 120,
            "fertilized_until_day": -1,
        }
        self.assertEqual(farm["tiles"][4][4], expected)
        self.assertEqual(private["seeds"]["CARROT"], 0)

    def test_reachable_crop_dies_before_represented_harvest_drop(self):
        m = self.m
        farm, private = empty_world(m)
        for action, day in ((["PLANT", "CARROT"], 1), (["WATER"], 1)):
            m._apply_unit_action(farm, private, 0, action, 10, day, 24, 100)
        m._daily_refresh_plants(farm, 1, 24)
        for day in (2, 3, 4):
            m._apply_unit_action(farm, private, 0, ["WATER"], 10, day, 24, 100)
            m._daily_refresh_plants(farm, day, 24)

        trace = []
        for step in range(120, 125):
            m._decay_plants(farm, step)
            tile = copy.deepcopy(farm["tiles"][4][4])
            trace.append(
                tile.get("yield_units") if isinstance(tile, dict) and tile.get("kind") == "PLANT" else tile
            )
        self.assertEqual(trace, [2, 2, 1, 1, {"kind": "WEED"}])

        before_private = copy.deepcopy(private)
        m._apply_unit_action(farm, private, 0, ["HARVEST"], 10, 5, 24, 100)
        m._apply_unit_action(farm, private, 0, ["DROP"], 10, 5, 24, 100)
        self.assertEqual(private, before_private)
        self.assertEqual(farm["tiles"][4][4], {"kind": "WEED"})


if __name__ == "__main__":
    unittest.main()
