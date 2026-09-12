# SPDX-License-Identifier: Apache-2.0
"""Activation-custody regressions for the canonical dead-feed/CARE-bank seam."""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
import unittest

import dead_feed_care as lane


CFG = {"boardSize": 10, "turnsPerDay": 24, "episodeSteps": 720}
POISONS = ("false", 1, 1.0, [True], {"enabled": False})


def _farms(tile):
    tiles = [[None for _ in range(10)] for __ in range(10)]
    tiles[4][2] = tile
    own = {"farmer": [2, 4], "hands": [], "tiles": tiles}
    other = {
        "farmer": [4, 4],
        "hands": [],
        "tiles": [[None for _ in range(10)] for __ in range(10)],
    }
    return [own, other]


def dead_feed_fixture():
    tile = {
        "kind": "PASTURE",
        "animal": "COW",
        "placed_day": 0,
        "yield_units": 0,
        "consecutive_unfed": 0,
        "fed_today": True,
        "cared_today": False,
        "fertilizer_available": True,
        "pending_care_bonus": 0,
    }
    observation = {
        "step": 240,
        "player": 0,
        "farms": _farms(tile),
        "private": {"inventories": [{"WHEAT": 0}], "shed": {}, "seeds": {}},
    }
    action = {"farmer": ["FEED"], "hands": [], "market": []}
    return observation, action


def carebank_fixture():
    tile = {
        "kind": "PASTURE",
        "animal": "COW",
        "placed_day": 21,
        "yield_units": 0,
        "consecutive_unfed": 0,
        "fed_today": False,
        "cared_today": True,
        "fertilizer_available": True,
        "pending_care_bonus": 2,
    }
    observation = {
        "step": 690,
        "player": 0,
        "farms": _farms(tile),
        "private": {"inventories": [{"WHEAT": 4}], "shed": {}, "seeds": {}},
    }
    action = {"farmer": ["COLLECT_FERTILIZER"], "hands": [], "market": []}
    route = [{"farmer": ["PASS"], "hands": [], "market": []} for _ in range(720)]
    return observation, action, route


class StrictEnableCustody(unittest.TestCase):
    def setUp(self):
        lane.telemetry.clear()

    def test_dead_feed_truthy_nonbools_preserve_identity_and_telemetry(self):
        for poison in POISONS:
            with self.subTest(poison=repr(poison)):
                obs, action = dead_feed_fixture()
                before_action = deepcopy(action)
                before_telemetry = Counter(lane.telemetry)
                result = lane.apply_dead_feed_care(
                    action, obs, CFG, enabled=poison
                )
                self.assertIs(result, action)
                self.assertEqual(action, before_action)
                self.assertEqual(lane.telemetry, before_telemetry)

    def test_carebank_truthy_nonbools_preserve_identity_and_telemetry(self):
        for poison in POISONS:
            with self.subTest(poison=repr(poison)):
                obs, action, route = carebank_fixture()
                before_action = deepcopy(action)
                before_telemetry = Counter(lane.telemetry)
                result = lane.apply_carebank_feed_swap(
                    action, obs, CFG, route, enabled=poison
                )
                self.assertIs(result, action)
                self.assertEqual(action, before_action)
                self.assertEqual(lane.telemetry, before_telemetry)

    def test_literal_true_still_arms_dead_feed_rewrite(self):
        obs, action = dead_feed_fixture()
        result = lane.apply_dead_feed_care(action, obs, CFG, enabled=True)
        self.assertIsNot(result, action)
        self.assertEqual(result["farmer"], ["CARE"])
        self.assertEqual(action["farmer"], ["FEED"])
        self.assertEqual(lane.telemetry["rewrites"], 1)

    def test_literal_true_still_arms_carebank_rewrite(self):
        obs, action, route = carebank_fixture()
        result = lane.apply_carebank_feed_swap(
            action, obs, CFG, route, enabled=True
        )
        self.assertIsNot(result, action)
        self.assertEqual(result["farmer"], ["FEED"])
        self.assertEqual(action["farmer"], ["COLLECT_FERTILIZER"])
        self.assertEqual(lane.telemetry["carebank_feed_swaps"], 1)


if __name__ == "__main__":
    unittest.main()
