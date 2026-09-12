# SPDX-License-Identifier: Apache-2.0
"""F2 public-stock boundary: official BUY_PRODUCT does not gate on market stock.

The pinned Kaggriculture engine checks buyer cash and shed capacity, then
commits BUY_PRODUCT even when public inventory is zero or would become
negative. F2 must therefore treat public market inventory as non-authoritative
for admission while preserving both-seat identity and nonmutation guarantees.
No planner mock is used.
"""
from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
CHECKS = Path(__file__).resolve().parent
for directory in (ROOT, CHECKS):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))

import r04_feed_prebuy as lane
import r04_full_router as r04
import test_v4_feed_prebuy as fixtures


class StockIntSubclass(int):
    pass


class FeedPrebuyStockBoundaryTests(unittest.TestCase):
    def setUp(self):
        tape = [fixtures._action() for _ in range(719)]
        players = {
            seat: SimpleNamespace(
                plan=0, last_step=39, day=1, queues={},
                v217_used=0, v217_task=None,
            )
            for seat in (0, 1)
        }
        self.policy = SimpleNamespace(players=players, tapes=[tape])
        patcher = mock.patch.object(r04, "_POLICY", self.policy)
        patcher.start()
        self.addCleanup(patcher.stop)

    def probe(self, wheat, public_inventory, seat=0, enabled=True):
        observation = fixtures._observation(wheat=wheat)
        observation["farms"].append(copy.deepcopy(observation["farms"][0]))
        observation["player"] = seat
        observation["market"]["inventory"] = public_inventory
        parent = fixtures._action()
        before_observation = copy.deepcopy(observation)
        before_parent = copy.deepcopy(parent)
        before_policy = copy.deepcopy(self.policy)
        out = lane.apply_feed_prebuy(
            observation, parent,
            configuration=fixtures._standard_config(), enabled=enabled,
        )
        self.assertEqual(observation, before_observation)
        self.assertEqual(parent, before_parent)
        self.assertEqual(self.policy, before_policy)
        return parent, out

    def test_public_stock_value_does_not_suppress_engine_legal_one_unit_buy(self):
        stock_values = (
            True, False, 1.0, StockIntSubclass(1), 1, 0, -1, "1", None,
        )
        for seat in (0, 1):
            for stock in stock_values:
                with self.subTest(seat=seat, stock=stock, kind=type(stock).__name__):
                    parent, out = self.probe(1, {"WHEAT": stock}, seat=seat)
                    self.assertIsNot(out, parent)
                    self.assertEqual(out["market"], [["BUY_PRODUCT", "WHEAT", 1]])

    def test_public_stock_below_requested_quantity_does_not_suppress_two_unit_buy(self):
        for seat in (0, 1):
            for inventory in ({"WHEAT": 0}, {"WHEAT": 1}, {}, None, [], 1, "1", True):
                with self.subTest(seat=seat, inventory=inventory):
                    parent, out = self.probe(0, inventory, seat=seat)
                    self.assertIsNot(out, parent)
                    self.assertEqual(out["market"], [["BUY_PRODUCT", "WHEAT", 2]])
                    self.assertEqual(out["farmer"], parent["farmer"])
                    self.assertEqual(out["hands"], parent["hands"])

    def test_disabled_returns_parent_independent_of_public_stock(self):
        for seat in (0, 1):
            with self.subTest(seat=seat):
                parent, out = self.probe(1, {"WHEAT": 0}, seat=seat, enabled=False)
                self.assertIs(out, parent)


if __name__ == "__main__":
    unittest.main()
