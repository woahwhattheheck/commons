#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
import copy
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
OVERLAY = HERE.parent / "overlay"
for path in (HERE, OVERLAY):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from e7_post_tick_evening_flush import PostTickEveningFlush, install  # noqa: E402


class Parent:
    def __init__(self, actions=None):
        self.actions = actions or {}

    def __call__(self, observation, configuration=None):
        action = self.actions.get(
            observation["step"],
            {"farmer": ["PASS"], "hands": [], "market": []},
        )
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


def obs(step, milk_price=10):
    return {
        "step": step,
        "player": 0,
        "farms": [{
            "tiles": [[None for _ in range(10)] for _ in range(10)],
            "farmer": [0, 0],
            "hands": [],
        }],
        "private": {
            "shed": {"MILK": 5},
            "inventories": [{}],
        },
        "market": {"prices": {"MILK": milk_price}},
        "town": {"unlocked_shops": []},
    }


class E7FailClosedTests(unittest.TestCase):
    def test_only_literal_true_activates(self):
        for enabled in (False, 0, 1, "true", [True], object()):
            with self.subTest(enabled=repr(enabled)):
                parent = Parent()
                self.assertIs(parent, install(parent, enabled=enabled))

        parent = Parent()
        self.assertIsInstance(install(parent, enabled=True), PostTickEveningFlush)

    def test_truthy_poison_never_validates_parent(self):
        for enabled in (1, "enabled", {"enabled": True}):
            with self.subTest(enabled=repr(enabled)):
                self.assertIsNone(install(None, enabled=enabled))
        with self.assertRaises(TypeError):
            install(None, enabled=True)

    def test_zero_quantity_sell_is_release_barrier(self):
        parent = Parent({
            49: {
                "farmer": ["PASS"],
                "hands": [],
                "market": [["SELL", "MILK", 0]],
            }
        })
        agent = install(parent, enabled=True)

        self.assertEqual([], agent(obs(47, milk_price=10), config())["market"])
        self.assertEqual([], agent(obs(48, milk_price=11), config())["market"])

        released = agent(obs(49, milk_price=12), config())
        self.assertEqual([["SELL", "MILK", 0]], released["market"])
        self.assertEqual(1, agent.telemetry["release_malformed_sell"])
        self.assertEqual(0, agent.telemetry["released_units"])


if __name__ == "__main__":
    unittest.main()
