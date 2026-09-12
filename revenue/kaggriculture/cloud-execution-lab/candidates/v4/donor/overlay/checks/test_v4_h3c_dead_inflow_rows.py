# SPDX-License-Identifier: Apache-2.0
"""Focused parser-boundary regressions for H3c market inflow vetoes."""
from __future__ import annotations

import copy
import unittest

import h3c_goose_eod_cap_rescue as h3c


def fixture():
    tiles = [[{"kind": "EMPTY"} for _ in range(10)] for _ in range(10)]
    tiles[1][1] = {
        "kind": "COOP", "animal": "GOOSE", "placed_day": 0,
        "yield_units": 4, "consecutive_unfed": 0, "fed_today": True,
        "cared_today": True, "fertilizer_available": True,
        "pending_care_bonus": 1,
    }
    farm = {"farmer": [1, 1], "hands": [], "tiles": tiles}
    observation = {
        "step": 239,
        "player": 0,
        "farms": [copy.deepcopy(farm), copy.deepcopy(farm)],
        "private": {"inventories": [{}], "shed": {"WHEAT": 0}},
    }
    action = {"farmer": ["COLLECT_FERTILIZER"], "hands": [], "market": []}
    return action, observation, dict(h3c.STANDARD_CONFIG, episodeSteps=720)


class TestH3cDeadMarketInflows(unittest.TestCase):
    def setUp(self):
        h3c.telemetry.clear()

    def rescue(self, order):
        action, observation, configuration = fixture()
        action["market"] = [[] for _ in range(9)] + [order]
        result = h3c.apply_goose_eod_cap_rescue(
            action, observation, configuration, enabled=True)
        return action, result

    def test_zero_buy_product_is_proven_dead(self):
        parent, result = self.rescue(["BUY_PRODUCT", "WHEAT", 0])
        self.assertIsNot(result, parent)
        self.assertEqual(result["farmer"], ["HARVEST"])
        self.assertEqual(h3c.telemetry["market_inflow_block"], 0)

    def test_nonpositive_buy_animal_is_proven_dead(self):
        for quantity in (0, -1, -99):
            with self.subTest(quantity=quantity):
                h3c.telemetry.clear()
                parent, result = self.rescue(["BUY_ANIMAL", "GOOSE", quantity])
                self.assertIsNot(result, parent)
                self.assertEqual(result["farmer"], ["HARVEST"])
                self.assertEqual(h3c.telemetry["market_inflow_block"], 0)

    def test_positive_buy_still_blocks(self):
        for order in (["BUY_PRODUCT", "WHEAT", 1], ["BUY_ANIMAL", "GOOSE", 1]):
            with self.subTest(order=order):
                h3c.telemetry.clear()
                parent, result = self.rescue(order)
                self.assertIs(result, parent)
                self.assertEqual(h3c.telemetry["market_inflow_block"], 1)

    def test_coerced_nonpositive_buy_remains_fail_closed(self):
        for quantity in (False, 0.0, "0"):
            with self.subTest(quantity=quantity):
                h3c.telemetry.clear()
                parent, result = self.rescue(["BUY_PRODUCT", "WHEAT", quantity])
                self.assertIs(result, parent)
                self.assertEqual(h3c.telemetry["market_inflow_block"], 1)


if __name__ == "__main__":
    unittest.main()
