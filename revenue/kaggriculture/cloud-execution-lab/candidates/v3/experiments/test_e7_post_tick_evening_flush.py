#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
import copy
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
V3 = HERE.parent
OVERLAY = V3 / "overlay"
for path in (HERE, OVERLAY):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import r04_full_router as r04  # noqa: E402
from e7_post_tick_evening_flush import install  # noqa: E402


class Parent:
    def __init__(self, actions=None):
        self.actions = actions or {}

    def __call__(self, observation, configuration=None):
        step = observation["step"]
        action = self.actions.get(step, {"farmer": ["PASS"], "hands": [], "market": []})
        return copy.deepcopy(action)


def config(**patch):
    value = {
        "turnsPerDay": 24,
        "shedCapacity": 100,
        "maxMarketOrdersPerTurn": 10,
        "townCenterSellInterval": 24,
    }
    value.update(patch)
    return value


def obs(step, shed=None, milk_price=10, inventories=None):
    inventories = [{}] if inventories is None else copy.deepcopy(inventories)
    hands = [[1 + idx, 0] for idx in range(max(0, len(inventories) - 1))]
    return {
        "step": step,
        "player": 0,
        "farms": [{
            "tiles": [[None for _ in range(10)] for _ in range(10)],
            "farmer": [0, 0],
            "hands": hands,
        }],
        "private": {
            "shed": copy.deepcopy(shed or {"MILK": 5}),
            "inventories": inventories,
        },
        "market": {"prices": {"MILK": milk_price}},
        "town": {"unlocked_shops": []},
    }


class E7PostTickTests(unittest.TestCase):
    def test_disabled_install_is_exact_parent_identity(self):
        parent = Parent()
        self.assertIs(parent, install(parent, enabled=False))

    def test_hours_21_and_22_are_incumbent_evening_flush(self):
        parent = Parent()
        agent = install(parent, enabled=True)
        for step in (21, 22, 45, 46):
            with self.subTest(step=step):
                observation = obs(step)
                parent_action = parent(observation, config())
                expected = r04.evening_flush(observation, parent_action)
                actual = agent(observation, config())
                self.assertEqual(expected, actual)

    def test_hour23_flush_extra_moves_to_next_day_hour1(self):
        parent = Parent()
        agent = install(parent, enabled=True)
        a23 = agent(obs(23, milk_price=10), config())
        self.assertEqual([], a23["market"])
        a24 = agent(obs(24, milk_price=11), config())
        self.assertEqual([], a24["market"])
        a25 = agent(obs(25, milk_price=12), config())
        self.assertEqual([["SELL", "MILK", 5]], a25["market"])
        self.assertEqual(5, agent.telemetry["withheld_units"])
        self.assertEqual(5, agent.telemetry["released_units"])
        self.assertEqual(10, agent.telemetry["quote_uplift_units"])
        self.assertEqual("withhold", agent.events[0]["kind"])
        self.assertEqual("release", agent.events[1]["kind"])

    def test_nonempty_worker_inventory_preserves_incumbent_hour23_flush(self):
        parent = Parent()
        agent = install(parent, enabled=True)
        observation = obs(23, inventories=[{"MILK": 1}])
        expected = r04.evening_flush(observation, parent(observation, config()))
        self.assertEqual(expected, agent(observation, config()))
        self.assertEqual(1, agent.telemetry["capacity_reject"])

    def test_inventory_producing_worker_action_preserves_incumbent_flush(self):
        parent = Parent({23: {"farmer": ["HARVEST"], "hands": [], "market": []}})
        agent = install(parent, enabled=True)
        observation = obs(23)
        expected = r04.evening_flush(observation, parent(observation, config()))
        self.assertEqual(expected, agent(observation, config()))
        self.assertEqual(1, agent.telemetry["capacity_reject"])

    def test_shed_adding_market_buy_preserves_incumbent_flush(self):
        action = {"farmer": ["PASS"], "hands": [], "market": [["BUY_PRODUCT", "WHEAT", 1]]}
        parent = Parent({23: action})
        agent = install(parent, enabled=True)
        observation = obs(23)
        expected = r04.evening_flush(observation, parent(observation, config()))
        self.assertEqual(expected, agent(observation, config()))
        self.assertEqual(1, agent.telemetry["capacity_reject"])

    def test_nonstandard_clock_type_fails_closed_to_incumbent_flush(self):
        parent = Parent()
        agent = install(parent, enabled=True)
        observation = obs(23)
        expected = r04.evening_flush(observation, parent(observation, config()))
        self.assertEqual(expected, agent(observation, config(turnsPerDay="24")))
        self.assertEqual(1, agent.telemetry["config_reject"])

    def test_falsey_non_mapping_market_params_fail_closed(self):
        parent = Parent()
        agent = install(parent, enabled=True)
        observation = obs(23)
        expected = r04.evening_flush(observation, parent(observation, config()))
        for value in ([], 0, False, ""):
            with self.subTest(value=value):
                self.assertEqual(expected, agent(observation, config(marketParams=value)))
        self.assertEqual(4, agent.telemetry["config_reject"])

    def test_release_tops_up_existing_same_item_sell_without_new_row(self):
        parent = Parent({25: {"farmer": ["PASS"], "hands": [], "market": [["SELL", "MILK", 2]]}})
        agent = install(parent, enabled=True)
        self.assertEqual([], agent(obs(23), config())["market"])
        agent(obs(24), config())
        released = agent(obs(25, milk_price=12), config())
        self.assertEqual([["SELL", "MILK", 5]], released["market"])

    def test_release_topup_preserves_raw_placeholder_indices(self):
        market = [["HIRE"], [], ["SELL", "MILK", 2], ["HIRE"]]
        parent = Parent({25: {"farmer": ["PASS"], "hands": [], "market": market}})
        agent = install(parent, enabled=True)
        agent(obs(23), config())
        agent(obs(24), config())
        released = agent(obs(25, milk_price=12), config())
        self.assertEqual(["HIRE"], released["market"][0])
        self.assertEqual([], released["market"][1])
        self.assertEqual(["SELL", "MILK", 5], released["market"][2])
        self.assertEqual(["HIRE"], released["market"][3])
        self.assertEqual(4, len(released["market"]))

    def test_release_appends_after_raw_placeholder_without_reindexing(self):
        market = [["HIRE"], [], ["HIRE"]]
        parent = Parent({25: {"farmer": ["PASS"], "hands": [], "market": market}})
        agent = install(parent, enabled=True)
        agent(obs(23), config())
        agent(obs(24), config())
        released = agent(obs(25, milk_price=12), config())
        self.assertEqual(market, released["market"][:3])
        self.assertEqual(["SELL", "MILK", 5], released["market"][3])
        self.assertEqual(4, len(released["market"]))

    def test_release_market_full_records_shortfall_and_does_not_displace_parent(self):
        full = [["HIRE"] for _ in range(10)]
        parent = Parent({25: {"farmer": ["PASS"], "hands": [], "market": full}})
        agent = install(parent, enabled=True)
        agent(obs(23), config())
        agent(obs(24), config())
        released = agent(obs(25, milk_price=12), config())
        self.assertEqual(full, released["market"])
        self.assertEqual(5, agent.telemetry["release_shortfall_units"])

    def test_release_full_raw_market_with_placeholder_does_not_compact(self):
        full = [["HIRE"] for _ in range(10)]
        full[4] = []
        parent = Parent({25: {"farmer": ["PASS"], "hands": [], "market": full}})
        agent = install(parent, enabled=True)
        agent(obs(23), config())
        agent(obs(24), config())
        released = agent(obs(25, milk_price=12), config())
        self.assertEqual(full, released["market"])
        self.assertEqual([], released["market"][4])
        self.assertEqual(5, agent.telemetry["release_shortfall_units"])

    def test_bool_shed_quantity_is_not_coerced_into_capacity_proof(self):
        parent = Parent()
        agent = install(parent, enabled=True)
        observation = obs(23, shed={"MILK": True})
        expected = r04.evening_flush(observation, parent(observation, config()))
        self.assertEqual(expected, agent(observation, config()))
        self.assertEqual(1, agent.telemetry["capacity_reject"])


if __name__ == "__main__":
    unittest.main()