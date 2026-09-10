# SPDX-License-Identifier: Apache-2.0
"""Exact chronology and cumulative seed-row contracts for early capital."""
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


EARLY_CAPITAL_PATH = Path("early_capital.py")
EARLY_CAPITAL_BLOB = "45a978ca1da32417b1090502cb446fb6b24b1916"


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


def with_one_hand(observation: dict, *, position=(3, 4)) -> dict:
    result = copy.deepcopy(observation)
    result["farms"][0]["hands"] = [list(position)]
    result["private"]["inventories"] = [{}, {}]
    return result


def run_official_interpreter(
    own_action: dict,
    *,
    money: int = 750,
    seeds: dict | None = None,
    shed: dict | None = None,
    first_tile=None,
    hand_position=(3, 4),
) -> tuple[dict, dict, dict]:
    """Execute one full official interpreter turn from a controlled live state."""
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
            player=0,
            step=1,
            day=0,
            hour=1,
            farms=farms,
            private=privates[0],
            market=market,
            town=town,
        ),
        types.SimpleNamespace(
            player=1,
            step=1,
            day=0,
            hour=1,
            farms=farms,
            private=privates[1],
            market=market,
            town=town,
        ),
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


class SeedCapitalChronologyContracts(unittest.TestCase):
    def test_source_blob_is_exact(self):
        self.assertEqual(
            git_blob(EARLY_CAPITAL_PATH.read_bytes()),
            EARLY_CAPITAL_BLOB,
        )

    def test_executed_current_plant_is_not_future_seed_demand(self):
        selected = action(
            [
                ["BUY_LAND"],
                ["BUY_SEED", "WHEAT", 1],
                ["SELL", "MELON", 1],
            ],
            farmer_action=["PLANT", "WHEAT"],
        )
        fixed, report = order_early_capital(
            m,
            obs(
                step=1,
                shed={"MELON": 1},
                seeds={"WHEAT": 1},
                money=750,
            ),
            config(3),
            selected,
            route_with(),
        )

        self.assertEqual(report["operating_seed_rows"], [])
        self.assertEqual(report["certified_funding_rows"], [2])
        self.assertEqual(
            fixed["market"],
            [
                ["SELL", "MELON", 1],
                ["BUY_LAND"],
                ["BUY_SEED", "WHEAT", 1],
            ],
        )

    def test_real_future_plant_preserves_seed_priority(self):
        selected = action(
            [
                ["BUY_LAND"],
                ["BUY_SEED", "WHEAT", 1],
                ["SELL", "MELON", 1],
            ]
        )
        fixed, report = order_early_capital(
            m,
            obs(
                step=1,
                shed={"MELON": 1},
                seeds={"WHEAT": 0},
                money=750,
            ),
            config(3),
            selected,
            route_with((2, "WHEAT")),
        )

        self.assertEqual(report["operating_seed_rows"], [1])
        self.assertEqual(
            fixed["market"],
            [
                ["SELL", "MELON", 1],
                ["BUY_SEED", "WHEAT", 1],
                ["BUY_LAND"],
            ],
        )

    def test_atomic_two_requests_one_seed_matches_full_interpreter(self):
        selected = action(
            [],
            farmer_action=["PLANT", "WHEAT"],
            hands=[["PLANT", "WHEAT"]],
        )
        observation = with_one_hand(
            obs(step=1, seeds={"WHEAT": 1}, money=750)
        )
        projected = _project_post_unit_private(
            m, observation, config(3), selected, 1
        )
        self.assertIsNotNone(projected)
        self.assertEqual(projected["seeds"]["WHEAT"], 1)

        farm, private, _ = run_official_interpreter(
            selected,
            seeds={"WHEAT": 1},
        )
        self.assertEqual(private["seeds"]["WHEAT"], 1)
        self.assertIsNone(farm["tiles"][4][4])
        self.assertIsNone(farm["tiles"][4][3])

    def test_atomic_block_precedes_tile_validity(self):
        selected = action(
            [],
            farmer_action=["PLANT", "WHEAT"],
            hands=[["PLANT", "WHEAT"]],
        )
        observation = with_one_hand(
            obs(step=1, seeds={"WHEAT": 1}, money=750)
        )
        observation["farms"][0]["tiles"][4][4] = {"kind": "WEED"}
        projected = _project_post_unit_private(
            m, observation, config(3), selected, 1
        )
        self.assertIsNotNone(projected)
        self.assertEqual(projected["seeds"]["WHEAT"], 1)

        farm, private, _ = run_official_interpreter(
            selected,
            seeds={"WHEAT": 1},
            first_tile={"kind": "WEED"},
        )
        self.assertEqual(private["seeds"]["WHEAT"], 1)
        self.assertEqual(farm["tiles"][4][4], {"kind": "WEED"})
        self.assertIsNone(farm["tiles"][4][3])

    def test_atomic_projection_decides_exact_land_unlock(self):
        selected = action(
            [
                ["BUY_LAND"],
                ["BUY_SEED", "WHEAT", 1],
                ["SELL", "MELON", 1],
            ],
            farmer_action=["PLANT", "WHEAT"],
            hands=[["PLANT", "WHEAT"]],
        )
        observation = with_one_hand(
            obs(
                step=1,
                shed={"MELON": 1},
                seeds={"WHEAT": 1},
                money=750,
            )
        )
        fixed, report = order_early_capital(
            m,
            observation,
            config(3),
            selected,
            route_with((2, "WHEAT")),
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
            [
                ["SELL", "MELON", 1],
                ["BUY_LAND"],
                ["BUY_SEED", "WHEAT", 1],
            ],
        )

        fixed_farm, fixed_private, fixed_market = run_official_interpreter(
            fixed,
            money=750,
            seeds={"WHEAT": 1},
            shed={"MELON": 1},
        )
        old_farm, old_private, old_market = run_official_interpreter(
            predecessor,
            money=750,
            seeds={"WHEAT": 1},
            shed={"MELON": 1},
        )

        self.assertEqual(fixed_farm["unlocked_quadrants"], ["NW", "NE"])
        self.assertEqual(fixed_farm["money"], 0.0)
        self.assertEqual(fixed_private["seeds"]["WHEAT"], 1)
        self.assertEqual(old_farm["unlocked_quadrants"], ["NW"])
        self.assertEqual(old_farm["money"], 990.0)
        self.assertEqual(old_private["seeds"]["WHEAT"], 2)
        self.assertEqual(fixed_market["inventory"]["MELON"], 10001)
        self.assertEqual(old_market["inventory"]["MELON"], 10001)


class CumulativeSeedRowContracts(unittest.TestCase):
    @staticmethod
    def observation(*, seeds=None, money=760):
        return obs(
            step=1,
            shed={"MELON": 1},
            seeds=seeds or {},
            money=money,
        )

    def test_one_future_seed_allocates_only_first_matching_row(self):
        selected = action(
            [
                ["BUY_LAND"],
                ["BUY_SEED", "WHEAT", 1],
                ["BUY_SEED", "WHEAT", 1],
                ["SELL", "MELON", 1],
            ]
        )
        fixed, report = order_early_capital(
            m,
            self.observation(),
            config(4),
            selected,
            route_with((2, "WHEAT")),
        )

        self.assertEqual(report["operating_seed_rows"], [1])
        self.assertEqual(
            report["seed_allocations"],
            [
                {
                    "index": 1,
                    "crop": "WHEAT",
                    "requested": 1,
                    "allocated": 1,
                }
            ],
        )
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

    def test_cumulative_allocation_decides_exact_land_unlock(self):
        selected = action(
            [
                ["BUY_LAND"],
                ["BUY_SEED", "WHEAT", 1],
                ["BUY_SEED", "WHEAT", 1],
                ["SELL", "MELON", 1],
            ]
        )
        fixed, _ = order_early_capital(
            m,
            self.observation(),
            config(4),
            selected,
            route_with((2, "WHEAT")),
        )
        predecessor = action(
            [
                ["SELL", "MELON", 1],
                ["BUY_SEED", "WHEAT", 1],
                ["BUY_SEED", "WHEAT", 1],
                ["BUY_LAND"],
            ]
        )

        fixed_farm, fixed_private, fixed_market = run_official_interpreter(
            fixed,
            money=760,
            shed={"MELON": 1},
        )
        old_farm, old_private, old_market = run_official_interpreter(
            predecessor,
            money=760,
            shed={"MELON": 1},
        )

        self.assertEqual(fixed_farm["unlocked_quadrants"], ["NW", "NE"])
        self.assertEqual(fixed_farm["money"], 0.0)
        self.assertEqual(fixed_private["seeds"]["WHEAT"], 1)
        self.assertEqual(old_farm["unlocked_quadrants"], ["NW"])
        self.assertEqual(old_farm["money"], 990.0)
        self.assertEqual(old_private["seeds"]["WHEAT"], 2)
        self.assertEqual(fixed_market["inventory"]["MELON"], 10001)
        self.assertEqual(old_market["inventory"]["MELON"], 10001)

    def test_two_future_plants_allocate_two_one_unit_rows(self):
        selected = action(
            [
                ["BUY_LAND"],
                ["BUY_SEED", "WHEAT", 1],
                ["BUY_SEED", "WHEAT", 1],
                ["SELL", "MELON", 1],
            ]
        )
        fixed, report = order_early_capital(
            m,
            self.observation(),
            config(4),
            selected,
            route_with((2, "WHEAT"), (3, "WHEAT")),
        )

        self.assertEqual(report["operating_seed_rows"], [1, 2])
        self.assertEqual(
            [row["allocated"] for row in report["seed_allocations"]],
            [1, 1],
        )
        self.assertEqual(
            fixed["market"],
            [
                ["SELL", "MELON", 1],
                ["BUY_SEED", "WHEAT", 1],
                ["BUY_SEED", "WHEAT", 1],
                ["BUY_LAND"],
            ],
        )

    def test_residual_seed_reduces_row_allocation(self):
        selected = action(
            [
                ["BUY_LAND"],
                ["BUY_SEED", "WHEAT", 1],
                ["BUY_SEED", "WHEAT", 1],
                ["SELL", "MELON", 1],
            ]
        )
        fixed, report = order_early_capital(
            m,
            self.observation(seeds={"WHEAT": 1}),
            config(4),
            selected,
            route_with((2, "WHEAT"), (3, "WHEAT")),
        )

        self.assertEqual(report["operating_seed_rows"], [1])
        self.assertEqual(
            fixed["market"][1:3],
            [["BUY_SEED", "WHEAT", 1], ["BUY_LAND"]],
        )

    def test_zero_and_negative_rows_cannot_claim_priority(self):
        selected = action(
            [
                ["BUY_LAND"],
                ["BUY_SEED", "WHEAT", 0],
                ["BUY_SEED", "WHEAT", -4],
                ["BUY_SEED", "WHEAT", 1],
                ["SELL", "MELON", 1],
            ]
        )
        fixed, report = order_early_capital(
            m,
            self.observation(),
            config(5),
            selected,
            route_with((2, "WHEAT")),
        )

        self.assertEqual(report["operating_seed_rows"], [3])
        self.assertEqual(
            fixed["market"],
            [
                ["SELL", "MELON", 1],
                ["BUY_SEED", "WHEAT", 1],
                ["BUY_LAND"],
                ["BUY_SEED", "WHEAT", 0],
                ["BUY_SEED", "WHEAT", -4],
            ],
        )

    def test_one_row_can_cover_multi_unit_future_demand(self):
        selected = action(
            [
                ["BUY_LAND"],
                ["BUY_SEED", "WHEAT", 2],
                ["BUY_SEED", "WHEAT", 1],
                ["SELL", "MELON", 1],
            ]
        )
        fixed, report = order_early_capital(
            m,
            self.observation(),
            config(4),
            selected,
            route_with((2, "WHEAT"), (3, "WHEAT")),
        )

        self.assertEqual(report["operating_seed_rows"], [1])
        self.assertEqual(report["seed_allocations"][0]["allocated"], 2)
        self.assertEqual(
            fixed["market"][1:3],
            [["BUY_SEED", "WHEAT", 2], ["BUY_LAND"]],
        )

    def test_crop_deficits_allocate_independently(self):
        selected = action(
            [
                ["BUY_LAND"],
                ["BUY_SEED", "WHEAT", 1],
                ["BUY_SEED", "WHEAT", 1],
                ["BUY_SEED", "CARROT", 1],
                ["BUY_SEED", "CARROT", 1],
                ["SELL", "MELON", 1],
            ]
        )
        fixed, report = order_early_capital(
            m,
            self.observation(),
            config(6),
            selected,
            route_with((2, "WHEAT"), (3, "CARROT")),
        )

        self.assertEqual(report["operating_seed_rows"], [1, 3])
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

    def test_unmet_deficit_is_reported_without_inventing_rows(self):
        selected = action(
            [
                ["BUY_LAND"],
                ["BUY_SEED", "WHEAT", 1],
                ["SELL", "MELON", 1],
            ]
        )
        fixed, report = order_early_capital(
            m,
            self.observation(),
            config(3),
            selected,
            route_with((2, "WHEAT"), (3, "WHEAT")),
        )

        self.assertEqual(report["operating_seed_rows"], [1])
        self.assertEqual(report["unmet_seed_demand"], {"WHEAT": 1})
        self.assertEqual(
            sorted(fixed["market"], key=repr),
            sorted(selected["market"], key=repr),
        )


if __name__ == "__main__":
    unittest.main()
