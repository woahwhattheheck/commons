# SPDX-License-Identifier: Apache-2.0
"""Focused source checks for the parked V4 S5 crop-mix lane."""
from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import v4_s5_crop_mix as lane  # noqa: E402

CONFIG = {"episodeSteps": 720, "turnsPerDay": 24, "boardSize": 10}


def _tiles(wheat_tiles=0, carrot_tiles=0):
    if wheat_tiles < 0 or carrot_tiles < 0 or wheat_tiles + carrot_tiles > 100:
        raise ValueError("bad census")
    cells = []
    cells.extend({"kind": "PLANT", "crop": "WHEAT"} for _ in range(wheat_tiles))
    cells.extend({"kind": "PLANT", "crop": "CARROT"} for _ in range(carrot_tiles))
    cells.extend(None for _ in range(100 - len(cells)))
    return [cells[i:i + 10] for i in range(0, 100, 10)]


def observation(day=25, wheat=3, carrot=3, wheat_tiles=37, carrot_tiles=4):
    own = {"tiles": _tiles(wheat_tiles, carrot_tiles)}
    rival = {"tiles": _tiles()}
    return {
        "step": day * 24,
        "day": day,
        "player": 0,
        "farms": [own, rival],
        "private": {"seeds": {"WHEAT": wheat, "CARROT": carrot}},
    }


def action(farmer=None, hands=None, market=None):
    return {
        "farmer": farmer if farmer is not None else ["PASS"],
        "hands": hands if hands is not None else [],
        "market": market if market is not None else [],
    }


class S5CropMix(unittest.TestCase):
    def test_off_is_exact_parent_object(self):
        parent = action(["PLANT", "CARROT"], [], [["BUY_SEED", "CARROT", 4]])
        self.assertIs(lane.apply_crop_mix(observation(), parent, "off", CONFIG), parent)

    def test_requires_explicit_standard_contract(self):
        parent = action(["PLANT", "CARROT"], [], [["BUY_SEED", "CARROT", 4]])
        bad_configs = (
            None,
            {"episodeSteps": 719, "turnsPerDay": 24, "boardSize": 10},
            {"episodeSteps": 720, "turnsPerDay": 12, "boardSize": 10},
            {"episodeSteps": 720, "turnsPerDay": 24, "boardSize": 12},
            {"episodeSteps": True, "turnsPerDay": 24, "boardSize": 10},
        )
        for configuration in bad_configs:
            with self.subTest(configuration=configuration):
                self.assertIs(
                    lane.apply_crop_mix(observation(), parent, "retain_wheat", configuration),
                    parent,
                )

    def test_attribute_configuration_is_supported(self):
        parent = action(["PASS"], [], [["BUY_SEED", "CARROT", 4]])
        out = lane.apply_crop_mix(
            observation(wheat_tiles=37), parent, "retain_wheat", SimpleNamespace(**CONFIG)
        )
        self.assertEqual(out["market"], [["BUY_SEED", "WHEAT", 4]])

    def test_only_days_24_and_25_activate(self):
        parent = action(["PASS"], [], [["BUY_SEED", "CARROT", 1]])
        for day in (0, 23, 26, 29):
            with self.subTest(day=day):
                self.assertIs(
                    lane.apply_crop_mix(observation(day=day, wheat_tiles=0), parent, "retain_wheat", CONFIG),
                    parent,
                )

    def test_exact_replay_start_census_does_not_blanket_convert(self):
        # 107953186 starts d24 at WHEAT38 while the winner starts at 37.
        parent = action(
            ["PLANT", "CARROT"],
            [["PLANT", "CARROT"]],
            [["BUY_SEED", "CARROT", 2]],
        )
        self.assertIs(
            lane.apply_crop_mix(
                observation(day=24, wheat=10, carrot=10, wheat_tiles=38, carrot_tiles=0),
                parent,
                "retain_wheat",
                CONFIG,
            ),
            parent,
        )

    def test_day24_floor_allows_only_observed_deficit(self):
        parent = action(["PLANT", "CARROT"], [["PLANT", "CARROT"]], [])
        out = lane.apply_crop_mix(
            observation(day=24, wheat=2, carrot=2, wheat_tiles=36),
            parent,
            "retain_wheat",
            CONFIG,
        )
        self.assertEqual(out["farmer"], ["PLANT", "WHEAT"])
        self.assertEqual(out["hands"], [["PLANT", "CARROT"]])

    def test_day25_uses_winner_start_floor_and_caps_plant_swaps(self):
        # W37 vs winner W41 => deficit four. Six authored CARROT plants must not
        # all be converted merely because seed is available.
        parent = action(
            ["PLANT", "CARROT"],
            [["PLANT", "CARROT"] for _ in range(5)],
            [],
        )
        out = lane.apply_crop_mix(
            observation(day=25, wheat=10, carrot=10, wheat_tiles=37),
            parent,
            "retain_wheat",
            CONFIG,
        )
        commands = [out["farmer"], *out["hands"]]
        self.assertEqual(commands.count(["PLANT", "WHEAT"]), 4)
        self.assertEqual(commands.count(["PLANT", "CARROT"]), 2)

    def test_seed_proof_bounds_current_plant_rewrites(self):
        parent = action(
            ["PLANT", "WHEAT"],
            [["PLANT", "CARROT"], ["PLANT", "CARROT"]],
            [],
        )
        # W37 => deficit4, but only one WHEAT seed remains beyond the parent's
        # authored WHEAT plant, so exactly one CARROT command may be rewritten.
        out = lane.apply_crop_mix(
            observation(day=25, wheat=2, carrot=2, wheat_tiles=37),
            parent,
            "retain_wheat",
            CONFIG,
        )
        self.assertEqual(out["farmer"], ["PLANT", "WHEAT"])
        self.assertEqual(out["hands"], [["PLANT", "WHEAT"], ["PLANT", "CARROT"]])

    def test_parent_carrot_plants_must_be_seed_backed(self):
        parent = action(["PLANT", "CARROT"], [], [])
        self.assertIs(
            lane.apply_crop_mix(
                observation(wheat=10, carrot=0, wheat_tiles=37),
                parent,
                "retain_wheat",
                CONFIG,
            ),
            parent,
        )

    def test_residual_deficit_can_rewrite_equal_quantity_seed_row(self):
        # W37 => deficit4. One current plant consumes one unit of deficit, so a
        # q3 final seed row may supply exactly the residual without row splitting.
        parent = action(
            ["PLANT", "CARROT"],
            [],
            [["SELL", "MILK", 1], ["BUY_SEED", "CARROT", 3], ["SELL", "WOOL", 2]],
        )
        original = copy.deepcopy(parent)
        out = lane.apply_crop_mix(
            observation(wheat=1, carrot=1, wheat_tiles=37),
            parent,
            "retain_wheat",
            CONFIG,
        )
        self.assertEqual(out["farmer"], ["PLANT", "WHEAT"])
        self.assertEqual(
            out["market"],
            [["SELL", "MILK", 1], ["BUY_SEED", "WHEAT", 3], ["SELL", "WOOL", 2]],
        )
        self.assertEqual(out["market"][1][2], parent["market"][1][2])
        self.assertLess(lane.WHEAT_SEED_COST, lane.CARROT_SEED_COST)
        self.assertEqual(parent, original)

    def test_seed_row_larger_than_residual_is_not_split(self):
        parent = action(["PLANT", "CARROT"], [], [["BUY_SEED", "CARROT", 4]])
        # deficit4 minus one plant => residual3; q4 must remain CARROT.
        out = lane.apply_crop_mix(
            observation(wheat=1, carrot=1, wheat_tiles=37),
            parent,
            "retain_wheat",
            CONFIG,
        )
        self.assertEqual(out["farmer"], ["PLANT", "WHEAT"])
        self.assertEqual(out["market"], [["BUY_SEED", "CARROT", 4]])

    def test_saved_seed_cash_cannot_enable_later_purchase(self):
        parents = (
            action(["PASS"], [], [["BUY_SEED", "CARROT", 4], ["HIRE"]]),
            action(["PASS"], [], [["BUY_SEED", "CARROT", 4], ["BUY_LAND"]]),
            action(["PASS"], [], [["BUY_SEED", "CARROT", 4], ["BUY_PRODUCT", "WHEAT", 1]]),
            action(["PASS"], [], [["BUY_SEED", "CARROT", 4], ["BUY_SEED", "WHEAT", 1]]),
            action(["PASS"], [], [["BUY_SEED", "CARROT", 4], ["BUY_ANIMAL", "COW", 1]]),
        )
        for parent in parents:
            with self.subTest(market=parent["market"]):
                self.assertIs(
                    lane.apply_crop_mix(
                        observation(wheat_tiles=37), parent, "retain_wheat", CONFIG
                    ),
                    parent,
                )

    def test_malformed_or_nonliteral_market_rows_fail_closed(self):
        parents = (
            action(["PASS"], [], [("BUY_SEED", "CARROT", 4)]),
            action(["PASS"], [], [["BUY_SEED", "CARROT", True]]),
            action(["PASS"], [], [["BUY_SEED", "CARROT", "4"]]),
            action(["PASS"], [], [["BUY_SEED", "CARROT", 0]]),
            action(["PASS"], [], [["BUY_SEED", "CARROT", 4], ["MYSTERY"]]),
        )
        for parent in parents:
            with self.subTest(market=parent["market"]):
                self.assertIs(
                    lane.apply_crop_mix(
                        observation(wheat_tiles=37), parent, "retain_wheat", CONFIG
                    ),
                    parent,
                )

    def test_malformed_census_or_player_fails_closed(self):
        parent = action(["PLANT", "CARROT"], [], [])
        cases = []
        bad = observation(wheat=10, carrot=10, wheat_tiles=37)
        bad["player"] = True
        cases.append(bad)
        bad = observation(wheat=10, carrot=10, wheat_tiles=37)
        bad["farms"][0]["tiles"] = bad["farms"][0]["tiles"][:-1]
        cases.append(bad)
        bad = observation(wheat=10, carrot=10, wheat_tiles=37)
        bad["farms"][0]["tiles"][0] = tuple(bad["farms"][0]["tiles"][0])
        cases.append(bad)
        for obs in cases:
            self.assertIs(lane.apply_crop_mix(obs, parent, "retain_wheat", CONFIG), parent)

    def test_inconsistent_step_day_fails_closed(self):
        parent = action(["PASS"], [], [["BUY_SEED", "CARROT", 1]])
        obs = observation(day=25, wheat_tiles=37)
        obs["day"] = 24
        self.assertIs(lane.apply_crop_mix(obs, parent, "retain_wheat", CONFIG), parent)


if __name__ == "__main__":
    unittest.main()
