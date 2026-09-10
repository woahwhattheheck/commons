# SPDX-License-Identifier: Apache-2.0
"""Current-runtime contracts for conservative strict-dominance SELL ordering."""
from __future__ import annotations

from copy import deepcopy
import unittest

import mechanics
from titan_runtime import Features, HERE, TitanAgent, load


def pressure_module():
    source = (HERE if (HERE / "pressure_priority.py").is_file() else
              HERE.parent / "cloud-opponent-league/lark-responsive")
    load("sell_priority", source / "sell_priority.py", cache=True)
    return load("_strict_dominance_runtime_contract", source / "pressure_priority.py")


class StrictDominanceRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.obs = {
            "player": 0,
            "step": 100,
            "market": {
                "inventory": {
                    "WHEAT": 10000,
                    "FERTILIZER": 10000,
                    "WOOL": 10000,
                    "MILK": 10000,
                },
                "prices": {
                    "WHEAT": 25,
                    "FERTILIZER": 100,
                    "WOOL": 200,
                    "MILK": 160,
                },
            },
        }
        self.cfg = {"maxMarketOrdersPerTurn": 10}

    def test_omitted_flag_retains_historical_full_pressure_sort(self):
        action = {
            "farmer": ["PASS"],
            "hands": [],
            "market": [
                ["SELL", "WHEAT", 2],
                ["SELL", "FERTILIZER", 3],
            ],
        }
        before = deepcopy(action)
        result = pressure_module().transform(
            action,
            self.obs,
            self.cfg,
            quote=mechanics.market_price,
        )
        self.assertEqual(
            result["market"],
            [["SELL", "FERTILIZER", 3], ["SELL", "WHEAT", 2]],
        )
        self.assertEqual(action, before)

    def test_canonical_enabled_path_preserves_two_exposed_lots(self):
        action = {
            "farmer": ["PASS"],
            "hands": [],
            "market": [
                ["SELL", "WHEAT", 2],
                ["SELL", "FERTILIZER", 3],
            ],
        }
        before = deepcopy(action)
        agent = TitanAgent(Features(market_pressure=True))
        result = agent._market_pressure_selected(self.obs, self.cfg, action)
        self.assertEqual(result, before)
        self.assertEqual(action, before)
        self.assertEqual(
            agent.diagnostics["market_pressure"],
            {"enabled": True, "changed": False},
        )

    def test_canonical_enabled_path_crosses_positive_over_zero_only(self):
        action = {
            "farmer": ["PASS"],
            "hands": [],
            "market": [
                ["SELL", "WOOL", 1],
                ["SELL", "MILK", 2],
            ],
        }
        before = deepcopy(action)
        agent = TitanAgent(Features(market_pressure=True))
        result = agent._market_pressure_selected(self.obs, self.cfg, action)
        self.assertEqual(
            result["market"],
            [["SELL", "MILK", 2], ["SELL", "WOOL", 1]],
        )
        self.assertEqual(action, before)
        self.assertEqual(
            agent.diagnostics["market_pressure"],
            {"enabled": True, "changed": True},
        )

    def test_disabled_runtime_remains_exact_identity(self):
        action = {
            "farmer": ["PASS"],
            "hands": [],
            "market": [["SELL", "FERTILIZER", 3]],
        }
        agent = TitanAgent(Features(market_pressure=False))
        self.assertIs(agent._market_pressure_selected(self.obs, self.cfg, action), action)


if __name__ == "__main__":
    unittest.main(verbosity=2)
