# SPDX-License-Identifier: Apache-2.0
"""Focused checks for the H5 terminal animal-capital ROI experiment."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import h5_capital_roi as h5  # noqa: E402


def obs(step):
    return {"step": step}


def action(market=None):
    return {
        "farmer": ["WATER"],
        "hands": [["HARVEST"], ["WEST"]],
        "market": deepcopy(market or []),
    }


class H5CapitalRoiTests(unittest.TestCase):
    def test_disabled_is_object_identity(self):
        original = action([["BUY_ANIMAL", "COW", 2]])
        out, report = h5.apply_capital_roi_guard(obs(700), original, enabled=False)
        self.assertIs(out, original)
        self.assertFalse(report["changed"])
        self.assertEqual(report["reason"], "OFF")

    def test_before_r04_final_plan_is_untouched(self):
        original = action([["BUY_ANIMAL", "GOOSE", 1]])
        out, report = h5.apply_capital_roi_guard(obs(647), original, enabled=True)
        self.assertIs(out, original)
        self.assertEqual(report["reason"], "BEFORE_FINAL_PLAN")

    def test_all_animals_are_provably_dead_at_step_648(self):
        original = action([
            ["SELL", "WOOL", 2],
            ["BUY_ANIMAL", "GOOSE", 1],
            ["BUY_ANIMAL", "SHEEP", 2],
            ["BUY_ANIMAL", "COW", 3],
            ["HIRE"],
            ["BUY_LAND"],
        ])
        out, report = h5.apply_capital_roi_guard(obs(648), original, enabled=True)
        self.assertEqual(out["market"], [
            ["SELL", "WOOL", 2], [], [], [], ["HIRE"], ["BUY_LAND"],
        ])
        self.assertEqual(report["dropped_indices"], [1, 2, 3])
        self.assertEqual(report["dropped_units"], {"GOOSE": 1, "SHEEP": 2, "COW": 3})

    def test_worker_actions_never_change(self):
        original = action([["BUY_ANIMAL", "COW", 1]])
        out, _ = h5.apply_capital_roi_guard(obs(700), original, enabled=True)
        self.assertEqual(out["farmer"], original["farmer"])
        self.assertEqual(out["hands"], original["hands"])

    def test_market_positions_are_preserved(self):
        original = action([
            ["SELL", "MILK", 5],
            ["BUY_ANIMAL", "COW", 1],
            ["BUY_PRODUCT", "WHEAT", 2],
        ])
        out, _ = h5.apply_capital_roi_guard(obs(700), original, enabled=True)
        self.assertEqual(len(out["market"]), len(original["market"]))
        self.assertEqual(out["market"][0], original["market"][0])
        self.assertEqual(out["market"][1], [])
        self.assertEqual(out["market"][2], original["market"][2])

    def test_hires_land_products_and_seeds_are_out_of_scope(self):
        market = [["HIRE"], ["BUY_LAND"], ["BUY_PRODUCT", "WHEAT", 2],
                  ["BUY_SEED", "STRAWBERRY", 3]]
        original = action(market)
        out, report = h5.apply_capital_roi_guard(obs(700), original, enabled=True)
        self.assertIs(out, original)
        self.assertEqual(report["reason"], "NO_PROVABLY_DEAD_ANIMAL_CAPITAL")

    def test_longer_episode_does_not_suppress_if_yield_can_arrive(self):
        original = action([["BUY_ANIMAL", "GOOSE", 1]])
        out, report = h5.apply_capital_roi_guard(
            obs(648), original, {"episodeSteps": 900}, enabled=True
        )
        self.assertIs(out, original)
        self.assertEqual(report["remaining_turns"], 250)
        self.assertEqual(report["reason"], "NO_PROVABLY_DEAD_ANIMAL_CAPITAL")

    def test_unknown_animal_is_left_alone(self):
        original = action([["BUY_ANIMAL", "ALPACA", 1]])
        out, _ = h5.apply_capital_roi_guard(obs(700), original, enabled=True)
        self.assertIs(out, original)

    def test_wrapper_is_r04_callable_compatible(self):
        original = action([["BUY_ANIMAL", "COW", 1], ["SELL", "WOOL", 4]])
        def parent(observation, configuration=None):
            return deepcopy(original)
        guarded = h5.wrap_agent(parent, enabled=True)
        out = guarded(obs(700), {"episodeSteps": 720})
        self.assertEqual(out["market"], [[], ["SELL", "WOOL", 4]])


if __name__ == "__main__":
    unittest.main(verbosity=2)
