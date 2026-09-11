# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import copy
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import h3c_goose_eod_cap_rescue as h3c  # noqa: E402


STEP = 18 * 24 + 23
CONFIG = {
    "boardSize": 10,
    "turnsPerDay": 24,
    "shedCapacity": 100,
    "maxMarketOrdersPerTurn": 10,
}


def goose(*, units=4, placed=12, fed=True, cared=True, fertilizer=True, bonus=1):
    return {
        "kind": "COOP",
        "animal": "GOOSE",
        "placed_day": placed,
        "yield_units": units,
        "consecutive_unfed": 0,
        "fed_today": fed,
        "cared_today": cared,
        "fertilizer_available": fertilizer,
        "pending_care_bonus": bonus,
    }


def fixture(*, step=STEP, shed=None, inventory=None, market=None):
    tiles0 = [[None for _ in range(10)] for _ in range(10)]
    tiles1 = [[None for _ in range(10)] for _ in range(10)]
    tiles0[2][2] = goose()
    action = {
        "farmer": ["PASS"],
        "hands": [["COLLECT_FERTILIZER"]],
        "market": list(market or []),
    }
    observation = {
        "step": step,
        "player": 0,
        "farms": [
            {"farmer": [0, 0], "hands": [[2, 2]], "tiles": tiles0},
            {"farmer": [0, 0], "hands": [], "tiles": tiles1},
        ],
        "private": {
            "inventories": [{}, dict(inventory or {})],
            "shed": dict(shed or {}),
        },
    }
    return observation, action


class H3cContracts(unittest.TestCase):
    def apply(self, observation, action, *, config=CONFIG, enabled=True):
        return h3c.apply_goose_eod_cap_rescue(action, observation, config, enabled=enabled)

    def test_disabled_is_exact_parent_identity(self):
        observation, action = fixture()
        self.assertIs(self.apply(observation, action, enabled=False), action)

    def test_positive_hour23_hand_swaps_only_collect_to_harvest(self):
        observation, action = fixture(market=[["SELL", "WHEAT", 1]])
        frozen = copy.deepcopy(action)
        result = self.apply(observation, action)
        self.assertIsNot(result, action)
        self.assertEqual(action, frozen)
        self.assertEqual(result["farmer"], ["PASS"])
        self.assertEqual(result["hands"], [["HARVEST"]])
        self.assertEqual(result["market"], frozen["market"])

    def test_positive_main_farmer_is_supported(self):
        observation, action = fixture()
        observation["farms"][0]["farmer"] = [2, 2]
        observation["farms"][0]["hands"] = []
        observation["private"]["inventories"] = [{}]
        action["farmer"] = ["COLLECT_FERTILIZER"]
        action["hands"] = []
        result = self.apply(observation, action)
        self.assertEqual(result["farmer"], ["HARVEST"])
        self.assertEqual(result["hands"], [])

    def test_only_hour23_is_eligible(self):
        for hour in (0, 1, 22):
            with self.subTest(hour=hour):
                observation, action = fixture(step=18 * 24 + hour)
                self.assertIs(self.apply(observation, action), action)

    def test_no_overflow_is_identity(self):
        observation, action = fixture()
        observation["farms"][0]["tiles"][2][2]["yield_units"] = 2
        self.assertIs(self.apply(observation, action), action)

    def test_existing_one_unit_overflow_boundary_activates(self):
        observation, action = fixture()
        tile = observation["farms"][0]["tiles"][2][2]
        tile["yield_units"] = 3
        tile["pending_care_bonus"] = 1
        self.assertEqual(self.apply(observation, action)["hands"][0], ["HARVEST"])

    def test_feed_care_and_fertilizer_legality_are_required(self):
        for field in ("fed_today", "cared_today", "fertilizer_available"):
            with self.subTest(field=field):
                observation, action = fixture()
                observation["farms"][0]["tiles"][2][2][field] = False
                self.assertIs(self.apply(observation, action), action)

    def test_immature_goose_is_identity(self):
        observation, action = fixture()
        observation["farms"][0]["tiles"][2][2]["placed_day"] = 18
        self.assertIs(self.apply(observation, action), action)

    def test_non_goose_is_identity(self):
        observation, action = fixture()
        tile = observation["farms"][0]["tiles"][2][2]
        tile["animal"] = "SHEEP"
        tile["kind"] = "PASTURE"
        self.assertIs(self.apply(observation, action), action)

    def test_tile_scalar_type_poison_fails_closed(self):
        mutations = (
            ("placed_day", "12"),
            ("yield_units", True),
            ("yield_units", 4.0),
            ("consecutive_unfed", False),
            ("fed_today", 1),
            ("cared_today", 1),
            ("fertilizer_available", 1),
            ("pending_care_bonus", 1.0),
        )
        for field, value in mutations:
            with self.subTest(field=field, value=value):
                observation, action = fixture()
                observation["farms"][0]["tiles"][2][2][field] = value
                self.assertIs(self.apply(observation, action), action)

    def test_configuration_requires_exact_present_integer_tuple(self):
        configs = (
            None,
            {},
            {"turnsPerDay": 24},
            {**CONFIG, "turnsPerDay": "24"},
            {**CONFIG, "turnsPerDay": 24.0},
            {**CONFIG, "turnsPerDay": True},
            {**CONFIG, "shedCapacity": 99},
        )
        for config in configs:
            with self.subTest(config=config):
                observation, action = fixture()
                self.assertIs(self.apply(observation, action, config=config), action)

    def test_same_tile_duplicate_qualifiers_fail_closed(self):
        observation, action = fixture()
        observation["farms"][0]["hands"] = [[2, 2], [2, 2]]
        observation["private"]["inventories"] = [{}, {}, {}]
        action["hands"] = [["COLLECT_FERTILIZER"], ["COLLECT_FERTILIZER"]]
        self.assertIs(self.apply(observation, action), action)

    def test_same_tile_existing_harvest_blocks_redundant_swap(self):
        observation, action = fixture()
        observation["farms"][0]["farmer"] = [2, 2]
        action["farmer"] = ["HARVEST"]
        self.assertIs(self.apply(observation, action), action)

    def test_same_tile_other_active_service_blocks_action_order_ambiguity(self):
        observation, action = fixture()
        observation["farms"][0]["farmer"] = [2, 2]
        action["farmer"] = ["CARE"]
        self.assertIs(self.apply(observation, action), action)

    def test_same_tile_pass_does_not_block(self):
        observation, action = fixture()
        observation["farms"][0]["farmer"] = [2, 2]
        action["farmer"] = ["PASS"]
        self.assertEqual(self.apply(observation, action)["hands"][0], ["HARVEST"])

    def test_capacity_guard_accounts_for_candidate_egg_units(self):
        observation, action = fixture(shed={"WHEAT": 97})
        self.assertIs(self.apply(observation, action), action)
        observation, action = fixture(shed={"WHEAT": 96})
        self.assertEqual(self.apply(observation, action)["hands"][0], ["HARVEST"])

    def test_capacity_guard_accounts_for_other_current_harvest(self):
        observation, action = fixture(shed={"WHEAT": 94})
        observation["farms"][0]["farmer"] = [1, 1]
        observation["farms"][0]["tiles"][1][1] = {
            "kind": "PLANT", "crop": "WHEAT", "planted_day": 10,
            "yield_units": 3, "watered_today": True, "fertilized_until_day": -1,
        }
        action["farmer"] = ["HARVEST"]
        self.assertIs(self.apply(observation, action), action)

    def test_capacity_guard_accounts_for_other_fertilizer_collect(self):
        observation, action = fixture(shed={"WHEAT": 96})
        observation["farms"][0]["farmer"] = [1, 1]
        observation["farms"][0]["tiles"][1][1] = goose(units=0)
        action["farmer"] = ["COLLECT_FERTILIZER"]
        self.assertIs(self.apply(observation, action), action)

    def test_market_stock_inflows_block_but_sell_does_not(self):
        for row in (["BUY_PRODUCT", "WHEAT", 1], ["BUY_ANIMAL", "GOOSE", 1]):
            with self.subTest(row=row):
                observation, action = fixture(market=[row])
                self.assertIs(self.apply(observation, action), action)
        observation, action = fixture(market=[["SELL", "WHEAT", 1]])
        self.assertEqual(self.apply(observation, action)["hands"][0], ["HARVEST"])

    def test_malformed_unrelated_worker_shape_blocks_atomically(self):
        observation, action = fixture()
        observation["farms"][0]["hands"].append([3, 3])
        observation["private"]["inventories"].append({})
        action["hands"].append("bad")
        self.assertIs(self.apply(observation, action), action)

    def test_position_inventory_and_player_type_poison_fail_closed(self):
        mutations = ("position", "inventory", "player", "farms")
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                observation, action = fixture()
                if mutation == "position":
                    observation["farms"][0]["hands"][0] = [2, 2, 9]
                elif mutation == "inventory":
                    observation["private"]["inventories"][1] = {"WHEAT": True}
                elif mutation == "player":
                    observation["player"] = True
                else:
                    observation["farms"] = observation["farms"][:1]
                self.assertIs(self.apply(observation, action), action)

    def test_non_literal_collect_command_is_identity(self):
        observation, action = fixture()
        action["hands"][0] = ["COLLECT_FERTILIZER", 1]
        self.assertIs(self.apply(observation, action), action)


if __name__ == "__main__":
    unittest.main()
