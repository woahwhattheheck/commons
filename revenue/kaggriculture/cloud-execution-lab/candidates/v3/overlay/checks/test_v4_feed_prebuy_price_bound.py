# SPDX-License-Identifier: Apache-2.0
"""Regression: F2 uses the proven +25 same-turn WHEAT funding bound."""
from __future__ import annotations

import copy
import unittest
from unittest import mock

import r04_feed_prebuy as lane
import r04_full_router as r04


CONFIG = {
    "episodeSteps": 720,
    "boardSize": 10,
    "turnsPerDay": 24,
    "shedCapacity": 100,
    "maxMarketOrdersPerTurn": 10,
    "marketParams": {},
}


def observation(money):
    tiles = [[None for _ in range(10)] for _ in range(10)]
    tiles[4][6] = {
        "animal": "GOOSE",
        "fed_today": False,
        "consecutive_unfed": 1,
    }
    return {
        "step": 39,
        "player": 0,
        "farms": [{
            "money": money,
            "farmer": [4, 4],
            "hands": [],
            "tiles": tiles,
        }],
        "private": {"shed": {"WHEAT": 0}, "inventories": [{}]},
        "market": {
            "inventory": {"WHEAT": 2},
            "prices": {
                "WHEAT": 30,
                "EGG": 100,
                "MILK": 100,
                "WOOL": 100,
                "FERTILIZER": 10,
                "CARROT": 50,
                "TOMATO": 50,
                "STRAWBERRY": 50,
                "MELON": 50,
            },
        },
    }


def parent_action():
    return {"farmer": ["PASS"], "hands": [], "market": []}


def planner_probe(_observation, _action, quantity, _r04, configuration=None):
    if quantity < 2:
        return None
    return {"target": [6, 4]}


class F2SameTurnWheatFundingTests(unittest.TestCase):
    def probe(self, money):
        obs = observation(money)
        parent = parent_action()
        before = copy.deepcopy(parent)
        config = dict(CONFIG)
        with mock.patch.object(lane, "_next_v217_task", side_effect=planner_probe) as planner, \
             mock.patch.object(lane, "_remaining_day_cash_spend_free", return_value=True):
            quantity = lane._purchase_quantity(obs, parent, config, r04)
        self.assertEqual(planner.call_count, 3)
        for call in planner.call_args_list:
            self.assertIs(call.kwargs["configuration"], config)
        self.assertEqual(parent, before)
        return quantity

    def test_price_pad_matches_proven_m1_same_turn_bound(self):
        self.assertEqual(lane._PRICE_PAD, 25)

    def test_stale_plus10_budget_is_rejected(self):
        # q=2, quote=$30: stale +10 required $1080 and would admit $1090.
        # Proven +25 bound requires $1110, so $1090 must fail closed.
        self.assertIsNone(self.probe(1090.0))

    def test_exact_plus25_budget_still_admits_the_same_two_unit_witness(self):
        self.assertEqual(self.probe(1110.0), 2)


if __name__ == "__main__":
    unittest.main()
