# SPDX-License-Identifier: Apache-2.0
"""F2 public-stock boundary: q=1 must not turn bool into executable inventory.

The two-unit witness alone cannot distinguish strict integer custody from
isinstance(value, int): True is already below two. Keep a live one-unit witness
alongside both-seat identity and nonmutation checks. No planner mock is used.
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

    def test_one_unit_stock_is_strict_not_bool_float_or_int_subclass(self):
        for seat in (0, 1):
            for stock in (True, False, 1.0, StockIntSubclass(1), 0, -1, "1", None):
                with self.subTest(seat=seat, stock=stock, kind=type(stock).__name__):
                    parent, out = self.probe(1, {"WHEAT": stock}, seat=seat)
                    self.assertIs(out, parent)

    def test_exact_one_and_two_unit_boundaries_activate_for_both_seats(self):
        for seat in (0, 1):
            for wheat, required in ((1, 1), (0, 2)):
                with self.subTest(seat=seat, wheat=wheat, required=required):
                    parent, out = self.probe(wheat, {"WHEAT": required}, seat=seat)
                    self.assertIsNot(out, parent)
                    self.assertEqual(out["market"], [["BUY_PRODUCT", "WHEAT", required]])
                    self.assertEqual(out["farmer"], parent["farmer"])
                    self.assertEqual(out["hands"], parent["hands"])

    def test_invalid_inventory_containers_preserve_exact_parent(self):
        for inventory in (None, [], 1, "1", True):
            with self.subTest(inventory=inventory):
                parent, out = self.probe(1, inventory)
                self.assertIs(out, parent)

    def test_disabled_returns_parent_even_when_stock_is_valid(self):
        for seat in (0, 1):
            with self.subTest(seat=seat):
                parent, out = self.probe(1, {"WHEAT": 1}, seat=seat, enabled=False)
                self.assertIs(out, parent)


if __name__ == "__main__":
    unittest.main()
