#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Focused fail-closed contracts for safe_consume.py."""
from __future__ import annotations

import copy
import unittest

from safe_consume import apply_fert_daily_sweep_safe

SIZE = 10


def make_obs(step=100, positions=None, inventories=None, shed=None, tiles=None):
    positions = positions or [[4, 4]]
    board = tiles or [[{"kind": "SOIL"} for _ in range(SIZE)] for _ in range(SIZE)]
    invs = [dict(value) for value in (inventories or [])]
    invs += [{} for _ in range(len(positions) - len(invs))]
    return {
        "step": step,
        "player": 0,
        "farms": [{
            "tiles": board,
            "farmer": list(positions[0]),
            "hands": [list(value) for value in positions[1:]],
        }],
        "private": {
            "inventories": invs,
            "shed": dict(shed or {}),
        },
    }


def make_action(commands, market=None):
    return {
        "farmer": list(commands[0]),
        "hands": [list(value) for value in commands[1:]],
        "market": copy.deepcopy(market or []),
    }


def blank_tape(length=719):
    return [{"farmer": ["PASS"], "hands": [], "market": []} for _ in range(length)]


class SafeConsume(unittest.TestCase):
    def test_strict_collection_survives_without_capacity(self):
        tiles = [[{"kind": "SOIL"} for _ in range(SIZE)] for _ in range(SIZE)]
        tiles[2][2] = {"kind": "PASTURE", "animal": "COW", "fertilizer_available": True}
        action = make_action([["PASS"]])
        out = apply_fert_daily_sweep_safe(
            make_obs(positions=[[2, 2]], tiles=tiles), action, blank_tape(), None
        )
        self.assertEqual(out["farmer"], ["COLLECT_FERTILIZER"])

    def test_truthy_fertilizer_alias_does_not_authorize_collection(self):
        for value in (1, "yes", [], {}):
            tiles = [[{"kind": "SOIL"} for _ in range(SIZE)] for _ in range(SIZE)]
            tiles[2][2] = {"kind": "PASTURE", "animal": "COW", "fertilizer_available": value}
            action = make_action([["PASS"]])
            with self.subTest(value=value):
                self.assertIs(
                    apply_fert_daily_sweep_safe(
                        make_obs(positions=[[2, 2]], tiles=tiles), action, blank_tape(), 100
                    ),
                    action,
                )

    def test_drop_requires_full_payload_room_and_explicit_exact_capacity(self):
        for capacity in (None, True, 100.0, "100"):
            action = make_action([["PASS"]])
            with self.subTest(capacity=capacity):
                self.assertIs(
                    apply_fert_daily_sweep_safe(
                        make_obs(inventories=[{"FERTILIZER": 2}]), action, blank_tape(), capacity
                    ),
                    action,
                )

        action = make_action([["PASS"]])
        out = apply_fert_daily_sweep_safe(
            make_obs(inventories=[{"FERTILIZER": 2, "WHEAT": 3}], shed={"WOOL": 94}),
            action,
            blank_tape(),
            100,
        )
        self.assertEqual(out["farmer"], ["DROP"])

        action = make_action([["PASS"]])
        self.assertIs(
            apply_fert_daily_sweep_safe(
                make_obs(inventories=[{"FERTILIZER": 2, "WHEAT": 3}], shed={"WOOL": 96}),
                action,
                blank_tape(),
                100,
            ),
            action,
        )

    def test_full_shed_same_step_sell_cannot_authorize_drop(self):
        market = [["SELL", "WOOL", 50], ["SELL", "FERTILIZER", 10]]
        action = make_action([["PASS"]], market)
        out = apply_fert_daily_sweep_safe(
            make_obs(inventories=[{"FERTILIZER": 1}], shed={"WOOL": 100}),
            action,
            blank_tape(),
            100,
        )
        self.assertIs(out, action)
        self.assertEqual(out["market"], market)

    def test_two_wrapper_drops_reserve_room_in_worker_execution_order(self):
        obs = make_obs(
            positions=[[4, 4], [5, 4]],
            inventories=[{"FERTILIZER": 3}, {"FERTILIZER": 3}],
            shed={"WOOL": 95},
        )
        action = make_action([["PASS"], ["PASS"]])
        out = apply_fert_daily_sweep_safe(obs, action, blank_tape(), 100)
        self.assertEqual(out["farmer"], ["DROP"])
        self.assertEqual(out["hands"], [["PASS"]])

    def test_unknown_earlier_unit_action_blocks_later_synthetic_drop(self):
        obs = make_obs(
            positions=[[1, 1], [4, 4]],
            inventories=[{}, {"FERTILIZER": 1}],
            shed={"WOOL": 10},
        )
        action = make_action([["HARVEST"], ["PASS"]])
        self.assertIs(apply_fert_daily_sweep_safe(obs, action, blank_tape(), 100), action)

    def test_later_inventory_work_and_animal_cargo_block_drop(self):
        tape = blank_tape()
        tape[105] = {"farmer": ["FERTILIZE"], "hands": [], "market": []}
        action = make_action([["PASS"]])
        self.assertIs(
            apply_fert_daily_sweep_safe(
                make_obs(inventories=[{"FERTILIZER": 1}]), action, tape, 100
            ),
            action,
        )

        animal_action = make_action([["PASS"]])
        self.assertIs(
            apply_fert_daily_sweep_safe(
                make_obs(inventories=[{"FERTILIZER": 1, "COW": 1}]),
                animal_action,
                blank_tape(),
                100,
            ),
            animal_action,
        )

    def test_malformed_shed_or_inventory_fails_closed(self):
        action = make_action([["PASS"]])
        bad_shed = make_obs(inventories=[{"FERTILIZER": 1}])
        bad_shed["private"]["shed"] = {"WOOL": True}
        self.assertIs(apply_fert_daily_sweep_safe(bad_shed, action, blank_tape(), 100), action)

        for inventory in ({"FERTILIZER": True}, {"FERTILIZER": -1}, {"FERTILIZER": 1.0}):
            with self.subTest(inventory=inventory):
                candidate = make_action([["PASS"]])
                self.assertIs(
                    apply_fert_daily_sweep_safe(
                        make_obs(inventories=[inventory]), candidate, blank_tape(), 100
                    ),
                    candidate,
                )

    def test_duplicate_collection_tile_claimed_once_and_market_untouched(self):
        tiles = [[{"kind": "SOIL"} for _ in range(SIZE)] for _ in range(SIZE)]
        tiles[2][2] = {"kind": "COOP", "animal": "GOOSE", "fertilizer_available": True}
        market = [["SELL", "WHEAT", 2]]
        action = make_action([["PASS"], ["PASS"]], market)
        out = apply_fert_daily_sweep_safe(
            make_obs(positions=[[2, 2], [2, 2]], inventories=[{}, {}], tiles=tiles),
            action,
            blank_tape(),
            100,
        )
        self.assertEqual(out["farmer"], ["COLLECT_FERTILIZER"])
        self.assertEqual(out["hands"], [["PASS"]])
        self.assertEqual(out["market"], market)


if __name__ == "__main__":
    unittest.main(verbosity=2)
