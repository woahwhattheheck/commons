from __future__ import annotations

import copy
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from b1_alternate_feed import install


def observation(*, unfed=0, fed=False, wheat=(1,), cared=False, step=100, positions=None):
    positions = positions or [[1, 1]]
    hands = positions[1:]
    inventories = [{"WHEAT": amount} for amount in wheat]
    return {
        "step": step,
        "player": 0,
        "farms": [{
            "farmer": positions[0],
            "hands": hands,
            "tiles": [
                [None, None, None],
                [None, {"kind": "PASTURE", "animal": "SHEEP",
                        "fed_today": fed, "cared_today": cared,
                        "consecutive_unfed": unfed}, None],
                [None, None, None],
            ],
        }],
        "private": {"inventories": inventories},
    }


class Parent:
    def __init__(self, action):
        self.action = action

    def __call__(self, observation, configuration=None):
        return self.action


class AlternateFeedTests(unittest.TestCase):
    def test_disabled_is_exact_identity(self):
        action = {"farmer": ["FEED"], "hands": [], "market": [["BUY_PRODUCT", "WHEAT", 3]]}
        agent = install(Parent(action), enabled=False)
        out = agent(observation())
        self.assertIs(out, action)
        self.assertEqual(agent.telemetry["commands_suppressed"], 0)

    def test_safe_first_miss_suppresses_feed_without_touching_market_or_parent(self):
        action = {"farmer": ["FEED"], "hands": [], "market": [["SELL", "WOOL", 2]]}
        original = copy.deepcopy(action)
        agent = install(Parent(action), enabled=True)
        out = agent(observation(unfed=0, wheat=(1,)))
        self.assertEqual(out["farmer"], ["PASS"])
        self.assertEqual(out["market"], original["market"])
        self.assertEqual(action, original)
        self.assertEqual(agent.telemetry["feed_units_saved"], 1)

    def test_second_consecutive_miss_is_protected(self):
        action = {"farmer": ["FEED"], "hands": [], "market": []}
        agent = install(Parent(action), enabled=True)
        out = agent(observation(unfed=1, wheat=(1,)))
        self.assertIs(out, action)
        self.assertEqual(out["farmer"], ["FEED"])
        self.assertEqual(agent.telemetry["protected_second_miss"], 1)

    def test_no_wheat_never_changes_noop_feed_bytes(self):
        action = {"farmer": ["FEED"], "hands": [], "market": []}
        agent = install(Parent(action), enabled=True)
        self.assertIs(agent(observation(wheat=(0,))), action)

    def test_already_fed_never_changes_parent_bytes(self):
        action = {"farmer": ["FEED"], "hands": [], "market": []}
        agent = install(Parent(action), enabled=True)
        self.assertIs(agent(observation(fed=True)), action)

    def test_two_workers_same_animal_are_both_suppressed_but_save_one_unit(self):
        action = {"farmer": ["FEED"], "hands": [["FEED"]], "market": []}
        agent = install(Parent(action), enabled=True)
        obs = observation(wheat=(1, 1), positions=[[1, 1], [1, 1]])
        out = agent(obs)
        self.assertEqual(out["farmer"], ["PASS"])
        self.assertEqual(out["hands"], [["PASS"]])
        self.assertEqual(agent.telemetry["commands_suppressed"], 2)
        self.assertEqual(agent.telemetry["feed_units_saved"], 1)

    def test_repeated_safe_feed_same_animal_day_does_not_double_count_saved_unit(self):
        action = {"farmer": ["FEED"], "hands": [], "market": []}
        agent = install(Parent(action), enabled=True)
        first = observation(step=100)
        second = observation(step=101)
        self.assertEqual(agent(first)["farmer"], ["PASS"])
        self.assertEqual(agent(second)["farmer"], ["PASS"])
        self.assertEqual(agent.telemetry["feed_units_saved"], 1)

    def test_new_day_with_unfed_one_passes_feed_through(self):
        action = {"farmer": ["FEED"], "hands": [], "market": []}
        agent = install(Parent(action), enabled=True)
        self.assertEqual(agent(observation(step=119, unfed=0))["farmer"], ["PASS"])
        parent_out = agent(observation(step=120, unfed=1))
        self.assertIs(parent_out, action)
        self.assertEqual(parent_out["farmer"], ["FEED"])

    def test_cared_tile_telemetry_marks_bonus_risk_without_changing_guard(self):
        action = {"farmer": ["FEED"], "hands": [], "market": []}
        agent = install(Parent(action), enabled=True)
        out = agent(observation(cared=True))
        self.assertEqual(out["farmer"], ["PASS"])
        self.assertEqual(agent.telemetry["suppressed_on_cared_tile"], 1)


if __name__ == "__main__":
    unittest.main()
