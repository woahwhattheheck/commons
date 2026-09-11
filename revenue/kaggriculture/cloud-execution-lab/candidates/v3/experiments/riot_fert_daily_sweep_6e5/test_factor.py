#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Focused compatibility contract for the Riot fert-daily-sweep donor.

This intentionally does NOT wire the factor into production R04.  The branch is a
repaired-P0 donor while #12565 owns the production router.  These tests preserve
the factor's command-level theorem and assert that the 6e5 parent still carries
the shipped stack that a future post-L3 consumer must preserve.
"""
from __future__ import annotations

import json
from pathlib import Path
import unittest

import r04_fert_daily_sweep as sweep

HERE = Path(__file__).resolve().parent
V3 = HERE.parents[1]
SIZE = 10


def animal_tile(available=True):
    return {
        "kind": "PASTURE",
        "animal": "COW",
        "placed_day": 3,
        "fertilizer_available": available,
    }


def make_obs(step=100, positions=None, tile_overrides=None, inventories=None):
    positions = positions or [[0, 0]]
    tiles = [[{"kind": "SOIL"} for _ in range(SIZE)] for _ in range(SIZE)]
    for (x, y), tile in (tile_overrides or {}).items():
        tiles[y][x] = tile
    farm = {
        "tiles": tiles,
        "farmer": list(positions[0]),
        "hands": [list(p) for p in positions[1:]],
    }
    invs = [dict(v) for v in (inventories or [])]
    invs += [{} for _ in range(len(positions) - len(invs))]
    return {
        "step": step,
        "player": 0,
        "farms": [farm, json.loads(json.dumps(farm))],
        "private": {"inventories": invs, "shed": {}},
    }


def make_action(commands, market=None):
    return {
        "farmer": list(commands[0]),
        "hands": [list(c) for c in commands[1:]],
        "market": [list(row) for row in (market or [])],
    }


def blank_tape(length=719):
    return [
        {"farmer": ["PASS"], "hands": [], "market": []}
        for _ in range(length)
    ]


class FactorContract(unittest.TestCase):
    def tearDown(self):
        sweep.reset()

    def test_collects_free_fertilizer_only_from_idle_worker(self):
        obs = make_obs(
            positions=[[2, 2]],
            tile_overrides={(2, 2): animal_tile(True)},
        )
        out = sweep.apply_fert_daily_sweep(
            obs, make_action([["PASS"]]), blank_tape()
        )
        self.assertEqual(out["farmer"], ["COLLECT_FERTILIZER"])
        self.assertEqual(sweep.get_report()["collected"], 1)

        real = make_action([["HARVEST"]])
        self.assertIs(
            sweep.apply_fert_daily_sweep(obs, real, blank_tape()),
            real,
        )

    def test_duplicate_tile_is_claimed_once(self):
        obs = make_obs(
            positions=[[2, 2], [2, 2]],
            tile_overrides={(2, 2): animal_tile(True)},
            inventories=[{}, {}],
        )
        out = sweep.apply_fert_daily_sweep(
            obs, make_action([["PASS"], ["PASS"]]), blank_tape()
        )
        self.assertEqual(out["farmer"], ["COLLECT_FERTILIZER"])
        self.assertEqual(out["hands"], [["PASS"]])
        self.assertEqual(sweep.get_report()["collect_skipped_claimed"], 1)

    def test_malformed_positions_fail_closed(self):
        for position in ([True, 0], [-1, 0], [0, -1], [999, 0], [0, 999]):
            action = make_action([["PASS"]])
            obs = make_obs(positions=[position])
            self.assertIs(
                sweep.apply_fert_daily_sweep(obs, action, blank_tape()),
                action,
                position,
            )

    def test_drop_requires_safe_same_day_inventory_path(self):
        obs = make_obs(
            positions=[[4, 4]],
            inventories=[{"FERTILIZER": 2}],
        )
        out = sweep.apply_fert_daily_sweep(
            obs, make_action([["PASS"]]), blank_tape()
        )
        self.assertEqual(out["farmer"], ["DROP"])

        tape = blank_tape()
        tape[105] = {"farmer": ["FERTILIZE"], "hands": [], "market": []}
        action = make_action([["PASS"]])
        self.assertIs(
            sweep.apply_fert_daily_sweep(obs, action, tape),
            action,
        )

        animal_obs = make_obs(
            positions=[[4, 4]],
            inventories=[{"FERTILIZER": 2, "COW": 1}],
        )
        animal_action = make_action([["PASS"]])
        self.assertIs(
            sweep.apply_fert_daily_sweep(animal_obs, animal_action, blank_tape()),
            animal_action,
        )

    def test_no_tape_means_collection_only(self):
        obs = make_obs(
            positions=[[4, 4]],
            inventories=[{"FERTILIZER": 1}],
        )
        action = make_action([["PASS"]])
        self.assertIs(sweep.apply_fert_daily_sweep(obs, action, None), action)

    def test_market_rows_are_never_changed(self):
        obs = make_obs(
            positions=[[2, 2]],
            tile_overrides={(2, 2): animal_tile(True)},
        )
        market = [["SELL", "WHEAT", 5], ["BUY", "COW", 1]]
        out = sweep.apply_fert_daily_sweep(
            obs, make_action([["PASS"]], market), blank_tape()
        )
        self.assertEqual(out["market"], market)


class CurrentRootCustody(unittest.TestCase):
    def test_donor_does_not_replace_production_router(self):
        manifest_text = (V3 / "V3-MANIFEST.json").read_text(encoding="utf-8")
        apply_text = (V3 / "apply_v3.py").read_text(encoding="utf-8")
        router_text = (V3 / "overlay" / "r04_full_router.py").read_text(encoding="utf-8")

        # This donor branch must leave the live production router unmodified.
        self.assertNotIn("r04_fert_daily_sweep", manifest_text)
        self.assertNotIn("FERT_DAILY_SWEEP", router_text)

        # The repaired-P0 parent still carries the stack a future consumer must
        # preserve rather than silently replacing with Riot's stale parent.
        for key in (
            "r04_b5_carrot_fertilizer",
            "r04_b5_jit_fertilize",
            "r04_strawberry_topup",
            "r04_no_late_sale_advance",
            "r04_sale_fertilizer",
            "r04_cattle_early",
        ):
            with self.subTest(key=key):
                self.assertTrue(
                    key in manifest_text or key in apply_text or key in router_text,
                    f"missing shipped-stack marker {key}",
                )


if __name__ == "__main__":
    unittest.main(verbosity=2)
