"""Engine-equivalence regressions for scarce shared seed during unit actions.

The scheduler projects the current unit stage before it evaluates future shed
capacity and seed demand.  That projection must preserve the official
interpreter's actor order: farmer first, then hands, all consuming one shared
seed ledger.  Synthetic fixtures below are mechanics certificates, not policy
or leaderboard evidence.
"""
from __future__ import annotations

import copy
from pathlib import Path
import unittest

import scheduler as s
import test_engine_semantics as semantics
from titan_runtime import load


HERE = Path(__file__).resolve().parent


class SchedulerSeedPrefixTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        semantics.EngineSemantics.setUpClass()
        cls.helper = semantics.EngineSemantics()
        cls.engine = cls.helper.engine

    def assert_matches_engine(self, actions, seeds, *, occupied=()):
        """Compare ``post_units`` with one pinned-interpreter transition."""
        state, env = self.helper.fixture(step=1)
        obs = state[0].observation
        farm = obs.farms[0]
        private = obs.private
        positions = [(3, 3), (4, 3), (3, 4)]
        self.assertLessEqual(len(actions), len(positions))

        farm["farmer"] = list(positions[0])
        farm["hands"] = [list(pos) for pos in positions[1:len(actions)]]
        private["inventories"] = [{} for _ in actions]
        for x, y in positions[:len(actions)]:
            farm["tiles"][y][x] = None
        for actor_index, crop in occupied:
            x, y = positions[actor_index]
            farm["tiles"][y][x] = s.m._new_plant(crop, 0, 24)
        for crop in s.m.CROPS:
            private["seeds"][crop] = int(seeds.get(crop, 0))

        action = {
            "farmer": copy.deepcopy(actions[0]),
            "hands": copy.deepcopy(actions[1:]),
            "market": [],
        }
        before_obs = copy.deepcopy(obs)
        projected_farm, projected_private = s.post_units(
            obs, action, env.configuration)
        self.assertEqual(obs, before_obs, "Projection mutated the live observation")

        state[0].action = copy.deepcopy(action)
        state[1].action = semantics.pass_agent({})
        self.engine.interpreter(state, env)
        self.assertEqual(projected_farm, state[0].observation.farms[0])
        self.assertEqual(projected_private, state[0].observation.private)
        return projected_farm, projected_private, positions

    def test_one_seed_executes_only_the_first_legal_planter(self):
        farm, private, positions = self.assert_matches_engine(
            [["PLANT", "WHEAT"], ["PLANT", "WHEAT"]],
            {"WHEAT": 1},
        )
        first_x, first_y = positions[0]
        second_x, second_y = positions[1]
        self.assertEqual(farm["tiles"][first_y][first_x]["crop"], "WHEAT")
        self.assertIsNone(farm["tiles"][second_y][second_x])
        self.assertEqual(private["seeds"]["WHEAT"], 0)

    def test_illegal_first_planter_leaves_seed_for_later_hand(self):
        farm, private, positions = self.assert_matches_engine(
            [["PLANT", "WHEAT"], ["PLANT", "WHEAT"]],
            {"WHEAT": 1},
            occupied=((0, "CARROT"),),
        )
        first_x, first_y = positions[0]
        second_x, second_y = positions[1]
        self.assertEqual(farm["tiles"][first_y][first_x]["crop"], "CARROT")
        self.assertEqual(farm["tiles"][second_y][second_x]["crop"], "WHEAT")
        self.assertEqual(private["seeds"]["WHEAT"], 0)

    def test_each_crop_has_an_independent_ordered_seed_prefix(self):
        farm, private, positions = self.assert_matches_engine(
            [["PLANT", "WHEAT"], ["PLANT", "WHEAT"], ["PLANT", "CARROT"]],
            {"WHEAT": 1, "CARROT": 1},
        )
        crops = []
        for x, y in positions:
            tile = farm["tiles"][y][x]
            crops.append(None if tile is None else tile["crop"])
        self.assertEqual(crops, ["WHEAT", None, "CARROT"])
        self.assertEqual(private["seeds"]["WHEAT"], 0)
        self.assertEqual(private["seeds"]["CARROT"], 0)

    def test_actor_order_not_aggregate_demand_selects_the_legal_prefix(self):
        cases = (
            (["WHEAT", "CARROT", "WHEAT"], ["WHEAT", "CARROT", None]),
            (["CARROT", "WHEAT", "CARROT"], ["CARROT", "WHEAT", None]),
        )
        for requested, expected in cases:
            with self.subTest(requested=requested):
                actions = [["PLANT", crop] for crop in requested]
                farm, private, positions = self.assert_matches_engine(
                    actions, {"WHEAT": 1, "CARROT": 1})
                actual = []
                for x, y in positions:
                    tile = farm["tiles"][y][x]
                    actual.append(None if tile is None else tile["crop"])
                self.assertEqual(actual, expected)
                self.assertEqual(private["seeds"]["WHEAT"], 0)
                self.assertEqual(private["seeds"]["CARROT"], 0)

    def test_consumed_prefix_preserves_needed_future_seed_purchase(self):
        """A legal current PLANT must not be mistaken for retained stock."""
        actions = [["PLANT", "WHEAT"], ["PLANT", "WHEAT"]]
        _farm, private, _positions = self.assert_matches_engine(
            actions, {"WHEAT": 1})
        self.assertEqual(private["seeds"]["WHEAT"], 0)

        route = [semantics.pass_agent({}) for _ in range(4)]
        route[2] = {
            "farmer": ["PLANT", "WHEAT"],
            "hands": [],
            "market": [],
        }
        budget_module = load(
            "_test_seed_prefix_budget",
            HERE / "reference/integrated-selected/alder/seed_budget.py",
        )
        budget = budget_module.SeedBudget({"fixture": route})
        selected = {
            "farmer": copy.deepcopy(actions[0]),
            "hands": copy.deepcopy(actions[1:]),
            "market": [["BUY_SEED", "WHEAT", 1]],
        }
        retained = budget.apply(
            selected, private["seeds"], 1, "fixture", max_orders=10)
        self.assertEqual(retained["market"], [["BUY_SEED", "WHEAT", 1]])
        self.assertEqual(budget.events, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
