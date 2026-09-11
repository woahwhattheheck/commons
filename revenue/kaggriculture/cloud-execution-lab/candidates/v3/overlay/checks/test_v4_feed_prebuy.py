# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import r04_feed_prebuy as lane
import r04_full_router as r04


def _tile_grid():
    tiles = [[None for _ in range(10)] for _ in range(10)]
    tiles[4][6] = {
        "animal": "GOOSE",
        "fed_today": False,
        "consecutive_unfed": 1,
    }
    return tiles


def _observation(wheat=0, money=5000, wheat_price=30, egg_price=100):
    return {
        "step": 39,
        "player": 0,
        "farms": [{
            "money": money,
            "farmer": [4, 4],
            "hands": [],
            "tiles": _tile_grid(),
        }],
        "private": {
            "shed": {"WHEAT": wheat},
            "inventories": [{}],
        },
        "market": {
            "prices": {
                "WHEAT": wheat_price,
                "EGG": egg_price,
                "MILK": 100,
                "WOOL": 100,
                "FERTILIZER": 10,
                "CARROT": 50,
                "TOMATO": 50,
                "STRAWBERRY": 50,
                "MELON": 50,
            }
        },
    }


def _action():
    return {"farmer": ["PASS"], "hands": [], "market": []}


class FeedPrebuyTests(unittest.TestCase):
    def setUp(self):
        self.old_policy = r04._POLICY
        tape = [{"farmer": ["PASS"], "hands": [], "market": []} for _ in range(719)]
        state = SimpleNamespace(
            plan=0,
            last_step=39,
            day=1,
            queues={},
            v217_used=0,
            v217_task=None,
        )
        r04._POLICY = SimpleNamespace(players={0: state}, tapes=[tape])

    def tearDown(self):
        r04._POLICY = self.old_policy

    def test_disabled_returns_exact_parent(self):
        parent = _action()
        self.assertIs(lane.apply_feed_prebuy(_observation(), parent, enabled=False), parent)

    def test_two_wheat_prebuy_unlocks_literal_v217_rescue(self):
        parent = _action()
        out = lane.apply_feed_prebuy(_observation(wheat=0), parent, enabled=True)
        self.assertIsNot(out, parent)
        self.assertEqual(out["market"], [["BUY_PRODUCT", "WHEAT", 2]])
        self.assertEqual(parent["market"], [])

    def test_one_wheat_prebuy_is_minimal_when_one_is_already_stored(self):
        out = lane.apply_feed_prebuy(_observation(wheat=1), _action(), enabled=True)
        self.assertEqual(out["market"], [["BUY_PRODUCT", "WHEAT", 1]])

    def test_does_not_buy_when_v217_is_already_funded(self):
        parent = _action()
        self.assertIs(lane.apply_feed_prebuy(_observation(wheat=2), parent, enabled=True), parent)

    def test_existing_market_order_is_a_hard_barrier(self):
        parent = _action()
        parent["market"] = [["SELL", "CARROT", 1]]
        self.assertIs(lane.apply_feed_prebuy(_observation(), parent, enabled=True), parent)

    def test_nonpass_unit_action_is_a_hard_barrier(self):
        parent = _action()
        parent["farmer"] = ["EAST"]
        self.assertIs(lane.apply_feed_prebuy(_observation(), parent, enabled=True), parent)

    def test_low_output_value_rejects_purchase(self):
        parent = _action()
        self.assertIs(
            lane.apply_feed_prebuy(_observation(wheat_price=40, egg_price=50), parent, enabled=True),
            parent,
        )

    def test_cash_reserve_rejects_purchase(self):
        parent = _action()
        self.assertIs(lane.apply_feed_prebuy(_observation(money=1050), parent, enabled=True), parent)

    def test_capacity_rejects_purchase(self):
        obs = _observation()
        obs["private"]["shed"] = {"WHEAT": 0, "CARROT": 99}
        parent = _action()
        self.assertIs(lane.apply_feed_prebuy(obs, parent, enabled=True), parent)

    def test_wrong_hour_returns_exact_parent(self):
        obs = _observation()
        obs["step"] = 38
        r04._POLICY.players[0].last_step = 38
        parent = _action()
        self.assertIs(lane.apply_feed_prebuy(obs, parent, enabled=True), parent)

    def test_parent_and_observation_are_not_mutated(self):
        obs = _observation()
        parent = _action()
        before_obs = copy.deepcopy(obs)
        before_parent = copy.deepcopy(parent)
        lane.apply_feed_prebuy(obs, parent, enabled=True)
        self.assertEqual(obs, before_obs)
        self.assertEqual(parent, before_parent)


if __name__ == "__main__":
    unittest.main()
