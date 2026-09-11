#!/usr/bin/env python3
import ast
import copy
from pathlib import Path
import unittest

import h1_terminal_harvest as h1


def tile(**changes):
    value = {
        "kind": "PLANT",
        "crop": "WHEAT",
        "planted_day": 20,
        "yield_units": 3,
        "max_lifespan_step": 672,
    }
    value.update(changes)
    return value


def obs(current_tile=None, *, step=672, hands=None):
    grid = [[current_tile if current_tile is not None else tile(), None], [None, None]]
    farm = {"farmer": [0, 0], "hands": list(hands or []), "tiles": grid}
    return {"step": step, "player": 0, "farms": [farm]}


def official_decay_plants():
    """Load only `_decay_plants` from the committed official-engine source via AST."""
    engine = Path(__file__).resolve().parents[3] / "reference" / "engine" / "kaggriculture.py"
    tree = ast.parse(engine.read_text(encoding="utf-8"), filename=str(engine))
    fn = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "_decay_plants")
    module = ast.Module(body=[fn], type_ignores=[])
    ast.fix_missing_locations(module)
    namespace = {}
    exec(compile(module, str(engine), "exec"), namespace)
    return namespace["_decay_plants"]


class H1Test(unittest.TestCase):
    def setUp(self):
        h1.telemetry.clear()

    def action(self):
        return {"farmer": ["WATER"], "hands": [], "market": [["SELL", "MILK", 2]]}

    def test_disabled_exact_identity(self):
        action = self.action()
        self.assertIs(h1.transform(obs(), action, {"turnsPerDay": 24}, False), action)

    def test_exact_first_decay_mature_annual_harvests(self):
        action = self.action()
        result = h1.transform(obs(), action, {"turnsPerDay": 24}, True)
        self.assertEqual(result["farmer"], ["HARVEST"])
        self.assertEqual(result["market"], action["market"])
        self.assertEqual(action["farmer"], ["WATER"])

    def test_official_equality_is_first_decay_not_final_life(self):
        decay = official_decay_plants()
        farm = {"tiles": [[copy.deepcopy(tile())]]}
        decay(farm, 672)
        self.assertEqual(farm["tiles"][0][0]["yield_units"], 2)
        self.assertEqual(farm["tiles"][0][0]["kind"], "PLANT")
        decay(farm, 674)
        self.assertEqual(farm["tiles"][0][0]["yield_units"], 1)
        decay(farm, 676)
        self.assertEqual(farm["tiles"][0][0], {"kind": "WEED"})

    def test_future_lifespan_kept(self):
        action = self.action()
        self.assertIs(
            h1.transform(obs(tile(max_lifespan_step=696)), action, {"turnsPerDay": 24}, True),
            action,
        )

    def test_later_decay_state_conservatively_kept(self):
        action = self.action()
        self.assertIs(
            h1.transform(obs(tile(max_lifespan_step=670)), action, {"turnsPerDay": 24}, True),
            action,
        )

    def test_no_yield_kept(self):
        action = self.action()
        self.assertIs(
            h1.transform(obs(tile(yield_units=0)), action, {"turnsPerDay": 24}, True),
            action,
        )

    def test_immature_kept(self):
        action = self.action()
        self.assertIs(
            h1.transform(obs(tile(crop="MELON", planted_day=28)), action, {"turnsPerDay": 24}, True),
            action,
        )

    def test_ongoing_kept(self):
        action = self.action()
        self.assertIs(
            h1.transform(obs(tile(crop="TOMATO", planted_day=10)), action, {"turnsPerDay": 24}, True),
            action,
        )

    def test_non_water_kept(self):
        action = {"farmer": ["HARVEST"], "hands": [], "market": []}
        self.assertIs(h1.transform(obs(), action, {"turnsPerDay": 24}, True), action)

    def test_nonstandard_config_is_type_strict(self):
        for bad in (24.0, "24", True, None):
            with self.subTest(bad=bad):
                action = self.action()
                self.assertIs(h1.transform(obs(), action, {"turnsPerDay": bad}, True), action)

    def test_malformed_state_kept(self):
        for key, bad in (
            ("yield_units", True),
            ("planted_day", "20"),
            ("max_lifespan_step", 672.0),
        ):
            with self.subTest(key=key, bad=bad):
                action = self.action()
                self.assertIs(
                    h1.transform(obs(tile(**{key: bad})), action, {"turnsPerDay": 24}, True),
                    action,
                )

    def test_multiple_workers_only_rescues_qualifying(self):
        first = tile()
        second = tile(crop="CARROT", yield_units=0)
        grid = [[first, second], [None, None]]
        observation = {
            "step": 672,
            "player": 0,
            "farms": [{"farmer": [0, 0], "hands": [[1, 0]], "tiles": grid}],
        }
        action = {"farmer": ["WATER"], "hands": [["WATER"]], "market": []}
        result = h1.transform(observation, action, {"turnsPerDay": 24}, True)
        self.assertEqual(result["farmer"], ["HARVEST"])
        self.assertEqual(result["hands"], [["WATER"]])
        self.assertEqual(action["farmer"], ["WATER"])

    def test_install_disabled_preserves_parent_object(self):
        action = self.action()

        def parent(_observation, _configuration=None):
            return action

        self.assertIs(h1.install(parent, False)(obs(), {"turnsPerDay": 24}), action)


if __name__ == "__main__":
    unittest.main()
