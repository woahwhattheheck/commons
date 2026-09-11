#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Source-safety predecessors for the fert-daily donor.

These tests are intentionally evaluator-free. They pin the theorem that a new
PASS->DROP may not consume shed capacity needed by parent DROP cargo and may not
create overflow/discard. PASS->COLLECT remains independent of shed capacity.
"""
from __future__ import annotations

import unittest

import donor


def tiles():
    return [[None for _ in range(10)] for _ in range(10)]


def observation(*, position=(4, 4), hands=None, inventories=None, shed=None, board=None):
    board = tiles() if board is None else board
    hands = [] if hands is None else list(hands)
    inventories = [{}] if inventories is None else inventories
    shed = {} if shed is None else shed
    return {
        "step": 100,
        "player": 0,
        "farms": [{"tiles": board, "farmer": list(position), "hands": hands}],
        "private": {"inventories": inventories, "shed": shed},
    }


def parent(*, hands=None):
    return {"farmer": ["PASS"], "hands": [] if hands is None else hands, "market": []}


TAPE = [{} for _ in range(719)]


class FertDailySafety(unittest.TestCase):
    def setUp(self):
        donor.reset()

    def test_collect_does_not_need_shed_capacity_evidence(self):
        board = tiles()
        board[2][2] = {"animal": "COW", "fertilizer_available": True}
        obs = observation(position=(2, 2), inventories=[{}], shed={"WHEAT": "poison"}, board=board)
        action = parent()
        result = donor.apply_fert_daily_sweep(obs, action, TAPE)
        self.assertEqual(result["farmer"], ["COLLECT_FERTILIZER"])
        self.assertEqual(result["hands"], [])

    def test_drop_allowed_when_all_parent_and_new_cargo_exactly_fits(self):
        obs = observation(inventories=[{"FERTILIZER": 2}], shed={"WHEAT": 98})
        result = donor.apply_fert_daily_sweep(obs, parent(), TAPE)
        self.assertEqual(result["farmer"], ["DROP"])
        self.assertEqual(donor.get_report()["dropped"], 1)

    def test_drop_vetoed_when_new_cargo_would_overflow(self):
        action = parent()
        obs = observation(inventories=[{"FERTILIZER": 2}], shed={"WHEAT": 99})
        result = donor.apply_fert_daily_sweep(obs, action, TAPE)
        self.assertIs(result, action)
        self.assertEqual(result["farmer"], ["PASS"])
        self.assertEqual(donor.get_report()["dropped"], 0)
        self.assertEqual(donor.get_report()["drop_skipped_guard"], 1)

    def test_new_drop_cannot_steal_capacity_from_parent_drop(self):
        action = parent(hands=[["DROP"]])
        obs = observation(
            hands=[[4, 5]],
            inventories=[{"FERTILIZER": 2}, {"WHEAT": 99}],
            shed={},
        )
        result = donor.apply_fert_daily_sweep(obs, action, TAPE)
        self.assertIs(result, action)
        self.assertEqual(result["farmer"], ["PASS"])
        self.assertEqual(result["hands"], [["DROP"]])
        self.assertEqual(donor.get_report()["dropped"], 0)

    def test_exact_fit_includes_parent_drop_cargo(self):
        action = parent(hands=[["DROP"]])
        obs = observation(
            hands=[[4, 5]],
            inventories=[{"FERTILIZER": 2}, {"WHEAT": 98}],
            shed={},
        )
        result = donor.apply_fert_daily_sweep(obs, action, TAPE)
        self.assertEqual(result["farmer"], ["DROP"])
        self.assertEqual(result["hands"], [["DROP"]])

    def test_malformed_shed_capacity_evidence_vetoes_new_drop(self):
        for bad in (True, 99.0, "99", -1):
            with self.subTest(bad=bad):
                donor.reset()
                action = parent()
                obs = observation(inventories=[{"FERTILIZER": 1}], shed={"WHEAT": bad})
                result = donor.apply_fert_daily_sweep(obs, action, TAPE)
                self.assertIs(result, action)
                self.assertEqual(result["farmer"], ["PASS"])

    def test_malformed_other_cargo_vetoes_new_drop(self):
        for bad in (True, 1.0, "1", -1):
            with self.subTest(bad=bad):
                donor.reset()
                action = parent()
                obs = observation(inventories=[{"FERTILIZER": 1, "WHEAT": bad}], shed={})
                result = donor.apply_fert_daily_sweep(obs, action, TAPE)
                self.assertIs(result, action)
                self.assertEqual(result["farmer"], ["PASS"])


if __name__ == "__main__":
    unittest.main()
