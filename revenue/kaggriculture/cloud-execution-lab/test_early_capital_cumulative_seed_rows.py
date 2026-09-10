# SPDX-License-Identifier: Apache-2.0
# These tests exercise only the Kaggle Kaggriculture simulation game.
"""Exact unit chronology and whole-row seed allocation contracts."""
from __future__ import annotations

import copy
import hashlib
from pathlib import Path
import types
import unittest

import mechanics as m
from early_capital import _project_post_unit_private, order_early_capital
from test_early_capital_executable_prefix import (
    CFG,
    action,
    load_official_engine,
    obs,
)


SOURCE = Path("early_capital.py")
SOURCE_BLOB = "ac464f49934d9cd0547e4c4f772a7758f47db6e7"


def git_blob(data: bytes) -> str:
    return hashlib.sha1(
        b"blob " + str(len(data)).encode() + b"\0" + data
    ).hexdigest()


def config(limit: int) -> dict:
    return dict(CFG, maxMarketOrdersPerTurn=limit)


def route_with(*entries: tuple[int, str]) -> list[dict]:
    route = [
        {"farmer": ["PASS"], "hands": [], "market": []}
        for _ in range(32)
    ]
    for step, crop in entries:
        route[step] = {
            "farmer": ["PLANT", crop],
            "hands": [],
            "market": [],
        }
    return route


def with_one_hand(observation: dict, position=(3, 4)) -> dict:
    result = copy.deepcopy(observation)
    result["farms"][0]["hands"] = [list(position)]
    result["private"]["inventories"] = [{}, {}]
    return result


def run_official(
    own_action: dict,
    *,
    money: int,
    seeds: dict | None = None,
    shed: dict | None = None,
    first_tile=None,
    hand_position=(3, 4),
) -> tuple[dict, dict, dict]:
    """Execute one complete turn through the pinned official interpreter."""
    engine = load_official_engine()
    board = 10
    farms = [engine._new_farm(board, money), engine._new_farm(board, 0)]
    privates = [engine._new_private(), engine._new_private()]

    hands = own_action.get("hands", []) if isinstance(own_action, dict) else []
    if isinstance(hands, list) and hands:
        farms[0]["hands"].append(list(hand_position))
        privates[0]["inventories"].append({})
    for crop, quantity in (seeds or {}).items():
        privates[0]["seeds"][crop] = quantity
    for item, quantity in (shed or {}).items():
        privates[0]["shed"][item] = quantity
    if first_tile is not None:
        farms[0]["tiles"][4][4] = copy.deepcopy(first_tile)

    market = engine._new_market()
    market["inventory"]["MELON"] = 10000
    engine._refresh_prices(market)
    town = engine._new_town()
    observations = [
        types.SimpleNamespace(
            player=index,
            step=1,
            day=0,
            hour=1,
            farms=farms,
            private=privates[index],
            market=market,
            town=town,
        )
        for index in range(2)
    ]
    states = [
        types.SimpleNamespace(
            observation=observations[0],
            action=copy.deepcopy(own_action),
            status="ACTIVE",
            reward=0.0,
        ),
        types.SimpleNamespace(
            observation=observations[1],
            action={"farmer": ["PASS"], "hands": [], "market": []},
            status="ACTIVE",
            reward=0.0,
        ),
    ]
    env = types.SimpleNamespace(
        configuration=types.SimpleNamespace(
            boardSize=board,
            startingMoney=3000,
            turnsPerDay=24,
            episodeSteps=720,
            maxMarketOrdersPerTurn=10,
            farmHandCostMult=1,
            shedCapacity=100,
            townShopSellInterval=4,
            townCenterSellInterval=24,
            townShopUnlockInterval=3,
            weedSpawnChance=0.0,
            marketParams=None,
        ),
        done=False,
        info={"seed": 0},
    )
    engine.interpreter(states, env)
    return farms[0], privates[0], market


def assert_market_outcome(
    case: unittest.TestCase,
    fixed: dict,
    predecessor: dict,
    *,
    money: int,
    seeds: dict | None = None,
) -> None:
    fixed_farm, fixed_private, fixed_market = run_official(
        fixed,
        money=money,
        seeds=seeds,
        shed={"MELON": 1},
    )
    old_farm, old_private, old_market = run_official(
        predecessor,
        money=money,
        seeds=seeds,
        shed={"MELON": 1},
    )
    case.assertEqual(fixed_farm["unlocked_quadrants"], ["NW", "NE"])
    case.assertEqual(fixed_farm["money"], 0.0)
    case.assertEqual(old_farm["unlocked_quadrants"], ["NW"])
    case.assertEqual(old_farm["money"], 990.0)
    case.assertEqual(fixed_market["inventory"]["MELON"], 10001)
    case.assertEqual(old_market["inventory"]["MELON"], 10001)
    case.assertIsInstance(fixed_private["seeds"], dict)
    case.assertIsInstance(old_private["seeds"], dict)


class UnitChronologyContracts(unittest.TestCase):
    def test_source_blob_is_exact(self):
        self.assertEqual(git_blob(SOURCE.read_bytes()), SOURCE_BLOB)

    def test_current_plant_is_not_counted_again_as_future_demand(self):
        selected = action(
            [["BUY_LAND"], ["BUY_SEED", "WHEAT", 1], ["SELL", "MELON", 1]],
            farmer_action=["PLANT", "WHEAT"],
        )
        fixed, report = order_early_capital(
            m,
            obs(step=1, shed={"MELON": 1}, seeds={"WHEAT": 1}, money=750),
            config(3),
            selected,
            route_with(),
        )
        self.assertEqual(report["operating_seed_rows"], [])
        self.assertEqual(
            fixed["market"],
            [["SELL", "MELON", 1], ["BUY_LAND"], ["BUY_SEED", "WHEAT", 1]],
        )

    def test_real_future_plant_keeps_one_seed_row_operating(self):
        selected = action(
            [["BUY_LAND"], ["BUY_SEED", "WHEAT", 1], ["SELL", "MELON", 1]]
        )
        fixed, report = order_early_capital(
            m,
            obs(step=1, shed={"MELON": 1}, seeds={"WHEAT": 0}, money=750),
            config(3),
            selected,
            route_with((2, "WHEAT")),
        )
        self.assertEqual(report["operating_seed_rows"], [1])
        self.assertEqual(
            fixed["market"],
            [["SELL", "MELON", 1], ["BUY_SEED", "WHEAT", 1], ["BUY_LAND"]],
        )

    def test_atomic_plant_gate_matches_full_interpreter(self):
        selected = action(
            [],
            farmer_action=["PLANT", "WHEAT"],
            hands=[["PLANT", "WHEAT"]],
        )
        observation = with_one_hand(obs(step=1, seeds={"WHEAT": 1}, money=750))
        projected = _project_post_unit_private(m, observation, config(3), selected, 1)
        farm, private, _ = run_official(selected, money=750, seeds={"WHEAT": 1})
        self.assertEqual(projected["seeds"]["WHEAT"], 1)
        self.assertEqual(private["seeds"]["WHEAT"], 1)
        self.assertIsNone(farm["tiles"][4][4])
        self.assertIsNone(farm["tiles"][4][3])

    def test_atomic_gate_precedes_first_tile_validity(self):
        selected = action(
            [],
            farmer_action=["PLANT", "WHEAT"],
            hands=[["PLANT", "WHEAT"]],
        )
        observation = with_one_hand(obs(step=1, seeds={"WHEAT": 1}, money=750))
        observation["farms"][0]["tiles"][4][4] = {"kind": "WEED"}
        projected = _project_post_unit_private(m, observation, config(3), selected, 1)
        farm, private, _ = run_official(
            selected,
            money=750,
            seeds={"WHEAT": 1},
            first_tile={"kind": "WEED"},
        )
        self.assertEqual(projected["seeds"]["WHEAT"], 1)
        self.assertEqual(private["seeds"]["WHEAT"], 1)
        self.assertEqual(farm["tiles"][4][4], {"kind": "WEED"})
        self.assertIsNone(farm["tiles"][4][3])

    def test_atomic_projection_decides_exact_land_unlock(self):
        selected = action(
            [["BUY_LAND"], ["BUY_SEED", "WHEAT", 1], ["SELL", "MELON", 1]],
            farmer_action=["PLANT", "WHEAT"],
            hands=[["PLANT", "WHEAT"]],
        )
        observation = with_one_hand(
            obs(step=1, shed={"MELON": 1}, seeds={"WHEAT": 1}, money=750)
        )
        fixed, report = order_early_capital(
            m, observation, config(3), selected, route_with((2, "WHEAT"))
        )
        predecessor = copy.deepcopy(selected)
        predecessor["market"] = [
            ["SELL", "MELON", 1],
            ["BUY_SEED", "WHEAT", 1],
            ["BUY_LAND"],
        ]
        self.assertEqual(report["operating_seed_rows"], [])
        self.assertEqual(
            fixed["market"],
            [["SELL", "MELON", 1], ["BUY_LAND"], ["BUY_SEED", "WHEAT", 1]],
        )
        assert_market_outcome(self, fixed, predecessor, money=750, seeds={"WHEAT": 1})
        _, fixed_private, _ = run_official(
            fixed, money=750, seeds={"WHEAT": 1}, shed={"MELON": 1}
        )
        _, old_private, _ = run_official(
            predecessor, money=750, seeds={"WHEAT": 1}, shed={"MELON": 1}
        )
        self.assertEqual(fixed_private["seeds"]["WHEAT"], 1)
        self.assertEqual(old_private["seeds"]["WHEAT"], 2)


class WholeSeedRowContracts(unittest.TestCase):
    @staticmethod
    def observation(seeds=None, money=760):
        return obs(
            step=1,
            shed={"MELON": 1},
            seeds=seeds or {},
            money=money,
        )

    def order(self, rows, future, *, seeds=None, money=760):
        selected = action(rows)
        return selected, order_early_capital(
            m,
            self.observation(seeds=seeds, money=money),
            config(len(rows)),
            selected,
            route_with(*future),
        )

    def test_duplicate_rows_allocate_only_the_first_needed_unit(self):
        selected, (fixed, report) = self.order(
            [
                ["BUY_LAND"],
                ["BUY_SEED", "WHEAT", 1],
                ["BUY_SEED", "WHEAT", 1],
                ["SELL", "MELON", 1],
            ],
            ((2, "WHEAT"),),
        )
        self.assertEqual(report["operating_seed_rows"], [1])
        self.assertEqual(report["seed_allocations"][0]["allocated"], 1)
        self.assertEqual(report["unmet_seed_demand"], {})
        self.assertEqual(
            fixed["market"],
            [
                ["SELL", "MELON", 1],
                ["BUY_SEED", "WHEAT", 1],
                ["BUY_LAND"],
                ["BUY_SEED", "WHEAT", 1],
            ],
        )
        predecessor = action(
            [
                ["SELL", "MELON", 1],
                ["BUY_SEED", "WHEAT", 1],
                ["BUY_SEED", "WHEAT", 1],
                ["BUY_LAND"],
            ]
        )
        assert_market_outcome(self, fixed, predecessor, money=760)
        _, fixed_private, _ = run_official(fixed, money=760, shed={"MELON": 1})
        _, old_private, _ = run_official(predecessor, money=760, shed={"MELON": 1})
        self.assertEqual(fixed_private["seeds"]["WHEAT"], 1)
        self.assertEqual(old_private["seeds"]["WHEAT"], 2)
        self.assertEqual(
            sorted(fixed["market"], key=repr),
            sorted(selected["market"], key=repr),
        )

    def test_oversized_row_cannot_claim_partial_operating_priority(self):
        _, (fixed, report) = self.order(
            [["BUY_LAND"], ["BUY_SEED", "WHEAT", 2], ["SELL", "MELON", 1]],
            ((2, "WHEAT"),),
        )
        self.assertEqual(report["operating_seed_rows"], [])
        self.assertEqual(report["seed_allocations"], [])
        self.assertEqual(report["unmet_seed_demand"], {"WHEAT": 1})
        self.assertEqual(
            fixed["market"],
            [["SELL", "MELON", 1], ["BUY_LAND"], ["BUY_SEED", "WHEAT", 2]],
        )
        predecessor = action(
            [["SELL", "MELON", 1], ["BUY_SEED", "WHEAT", 2], ["BUY_LAND"]]
        )
        assert_market_outcome(self, fixed, predecessor, money=760)

    def test_later_exact_row_beats_earlier_oversized_row(self):
        _, (fixed, report) = self.order(
            [
                ["BUY_LAND"],
                ["BUY_SEED", "WHEAT", 2],
                ["BUY_SEED", "WHEAT", 1],
                ["SELL", "MELON", 1],
            ],
            ((2, "WHEAT"),),
        )
        self.assertEqual(report["operating_seed_rows"], [2])
        self.assertEqual(report["seed_allocations"][0]["requested"], 1)
        self.assertEqual(
            fixed["market"],
            [
                ["SELL", "MELON", 1],
                ["BUY_SEED", "WHEAT", 1],
                ["BUY_LAND"],
                ["BUY_SEED", "WHEAT", 2],
            ],
        )
        farm, private, _ = run_official(fixed, money=760, shed={"MELON": 1})
        self.assertEqual(farm["unlocked_quadrants"], ["NW", "NE"])
        self.assertEqual(private["seeds"]["WHEAT"], 1)

    def test_subset_search_prefers_complete_cover_over_greedy_prefix(self):
        _, (fixed, report) = self.order(
            [
                ["BUY_LAND"],
                ["BUY_SEED", "WHEAT", 1],
                ["BUY_SEED", "WHEAT", 2],
                ["SELL", "MELON", 1],
            ],
            ((2, "WHEAT"), (3, "WHEAT")),
            money=770,
        )
        self.assertEqual(report["operating_seed_rows"], [2])
        self.assertEqual(report["unmet_seed_demand"], {})
        self.assertEqual(
            fixed["market"],
            [
                ["SELL", "MELON", 1],
                ["BUY_SEED", "WHEAT", 2],
                ["BUY_LAND"],
                ["BUY_SEED", "WHEAT", 1],
            ],
        )
        farm, private, _ = run_official(fixed, money=770, shed={"MELON": 1})
        self.assertEqual(farm["unlocked_quadrants"], ["NW", "NE"])
        self.assertEqual(private["seeds"]["WHEAT"], 2)

    def test_two_one_unit_rows_cover_two_future_plants(self):
        _, (fixed, report) = self.order(
            [
                ["BUY_LAND"],
                ["BUY_SEED", "WHEAT", 1],
                ["BUY_SEED", "WHEAT", 1],
                ["SELL", "MELON", 1],
            ],
            ((2, "WHEAT"), (3, "WHEAT")),
        )
        self.assertEqual(report["operating_seed_rows"], [1, 2])
        self.assertEqual([row["allocated"] for row in report["seed_allocations"]], [1, 1])
        self.assertEqual(
            fixed["market"],
            [
                ["SELL", "MELON", 1],
                ["BUY_SEED", "WHEAT", 1],
                ["BUY_SEED", "WHEAT", 1],
                ["BUY_LAND"],
            ],
        )

    def test_held_seed_reduces_whole_row_deficit(self):
        _, (fixed, report) = self.order(
            [
                ["BUY_LAND"],
                ["BUY_SEED", "WHEAT", 1],
                ["BUY_SEED", "WHEAT", 1],
                ["SELL", "MELON", 1],
            ],
            ((2, "WHEAT"), (3, "WHEAT")),
            seeds={"WHEAT": 1},
        )
        self.assertEqual(report["operating_seed_rows"], [1])
        self.assertEqual(
            fixed["market"][1:3],
            [["BUY_SEED", "WHEAT", 1], ["BUY_LAND"]],
        )

    def test_zero_negative_and_malformed_quantities_do_not_claim_priority(self):
        _, (fixed, report) = self.order(
            [
                ["BUY_LAND"],
                ["BUY_SEED", "WHEAT", 0],
                ["BUY_SEED", "WHEAT", -4],
                ["BUY_SEED", "WHEAT", "bad"],
                ["BUY_SEED", "WHEAT", 1],
                ["SELL", "MELON", 1],
            ],
            ((2, "WHEAT"),),
        )
        self.assertEqual(report["operating_seed_rows"], [4])
        self.assertEqual(
            fixed["market"][:3],
            [["SELL", "MELON", 1], ["BUY_SEED", "WHEAT", 1], ["BUY_LAND"]],
        )

    def test_crop_deficits_are_independent_and_allocations_are_index_ordered(self):
        _, (fixed, report) = self.order(
            [
                ["BUY_LAND"],
                ["BUY_SEED", "WHEAT", 1],
                ["BUY_SEED", "WHEAT", 1],
                ["BUY_SEED", "CARROT", 1],
                ["BUY_SEED", "CARROT", 1],
                ["SELL", "MELON", 1],
            ],
            ((2, "WHEAT"), (3, "CARROT")),
        )
        self.assertEqual(report["operating_seed_rows"], [1, 3])
        self.assertEqual([row["index"] for row in report["seed_allocations"]], [1, 3])
        self.assertEqual(
            fixed["market"],
            [
                ["SELL", "MELON", 1],
                ["BUY_SEED", "WHEAT", 1],
                ["BUY_SEED", "CARROT", 1],
                ["BUY_LAND"],
                ["BUY_SEED", "WHEAT", 1],
                ["BUY_SEED", "CARROT", 1],
            ],
        )

    def test_unfillable_remainder_is_reported_without_order_invention(self):
        selected, (fixed, report) = self.order(
            [
                ["BUY_LAND"],
                ["BUY_SEED", "WHEAT", 2],
                ["BUY_SEED", "WHEAT", 2],
                ["SELL", "MELON", 1],
            ],
            ((2, "WHEAT"), (3, "WHEAT"), (4, "WHEAT")),
        )
        self.assertEqual(report["operating_seed_rows"], [1])
        self.assertEqual(report["unmet_seed_demand"], {"WHEAT": 1})
        self.assertEqual(
            sorted(fixed["market"], key=repr),
            sorted(selected["market"], key=repr),
        )


if __name__ == "__main__":
    unittest.main()
