# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parent
OVERLAY = HERE.parent / "overlay"
for path in (HERE, OVERLAY):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import h8_terminal_sell_viability_order as h8  # noqa: E402


def obs(*, step=700, shed=None, inventory=None, prices=None):
    return {
        "step": step,
        "player": 0,
        "farms": [
            {"tiles": [[None]], "farmer": [0, 0], "hands": []},
            {"tiles": [[None]], "farmer": [0, 0], "hands": []},
        ],
        "private": {
            "inventories": [dict(inventory or {})],
            "shed": dict(shed or {}),
        },
        "market": {
            "prices": dict(prices or {"WOOL": 200, "STRAWBERRY": 120, "MILK": 160}),
            "inventory": {"WOOL": 50, "STRAWBERRY": 50, "MILK": 50},
        },
    }


def parent_with(action):
    def parent(_observation, _configuration=None):
        return action
    return parent


class H8TerminalSellViabilityOrderTests(unittest.TestCase):
    def test_disabled_is_exact_parent_output_identity(self):
        action = {"farmer": ["PASS"], "hands": [], "market": [["SELL", "WOOL", 4], ["SELL", "STRAWBERRY", 4]]}
        arm = h8.install(parent_with(action), enabled=False)
        self.assertIs(arm(obs(shed={"STRAWBERRY": 4}), {}), action)
        self.assertEqual(arm.telemetry["changed"], 0)
        self.assertEqual(arm.telemetry["reasons"]["OFF"], 1)

    def test_before_window_is_exact_parent_output_identity(self):
        action = {"farmer": ["PASS"], "hands": [], "market": [["SELL", "WOOL", 4], ["SELL", "STRAWBERRY", 4]]}
        arm = h8.install(parent_with(action), enabled=True, first_step=648)
        self.assertIs(arm(obs(step=647, shed={"STRAWBERRY": 4}), {}), action)
        self.assertEqual(arm.telemetry["changed"], 0)
        self.assertEqual(arm.telemetry["reasons"]["BEFORE_WINDOW"], 1)

    def test_zero_stock_leading_sell_moves_behind_executable_sell(self):
        action = {
            "farmer": ["PASS"],
            "hands": [],
            "market": [["SELL", "WOOL", 5], ["SELL", "STRAWBERRY", 4], ["HIRE"]],
        }
        before = deepcopy(action)
        arm = h8.install(parent_with(action), enabled=True)
        out = arm(obs(shed={"WOOL": 0, "STRAWBERRY": 4}), {"maxMarketOrdersPerTurn": 10})
        self.assertEqual(action, before)
        self.assertEqual(out["market"], [["SELL", "STRAWBERRY", 4], ["SELL", "WOOL", 5], ["HIRE"]])
        self.assertEqual(arm.telemetry["changed"], 1)
        self.assertEqual(arm.telemetry["live_rows"], 1)
        self.assertEqual(arm.telemetry["dead_rows"], 1)

    def test_never_moves_sell_across_non_sell_boundary(self):
        action = {
            "farmer": ["PASS"],
            "hands": [],
            "market": [["SELL", "WOOL", 3], ["HIRE"], ["SELL", "STRAWBERRY", 4]],
        }
        arm = h8.install(parent_with(action), enabled=True)
        out = arm(obs(shed={"STRAWBERRY": 4}), {})
        self.assertIs(out, action)
        self.assertEqual(out["market"], action["market"])
        self.assertEqual(arm.telemetry["reasons"]["LEADING_SELL_LT_2"], 1)

    def test_partial_first_sale_stays_live_and_exhausts_same_item(self):
        action = {
            "farmer": ["PASS"],
            "hands": [],
            "market": [
                ["SELL", "WOOL", 9],
                ["SELL", "WOOL", 2],
                ["SELL", "STRAWBERRY", 1],
            ],
        }
        arm = h8.install(parent_with(action), enabled=True)
        out = arm(obs(shed={"WOOL": 3, "STRAWBERRY": 1}), {})
        self.assertEqual(out["market"], [
            ["SELL", "WOOL", 9],
            ["SELL", "STRAWBERRY", 1],
            ["SELL", "WOOL", 2],
        ])
        self.assertEqual(len(out["market"]), len(action["market"]))
        self.assertEqual(arm.telemetry["changed"], 1)

    def test_drop_projection_can_make_sell_executable(self):
        action = {
            "farmer": ["DROP"],
            "hands": [],
            "market": [["SELL", "WOOL", 2], ["SELL", "STRAWBERRY", 1]],
        }
        arm = h8.install(parent_with(action), enabled=True)
        out = arm(obs(shed={"STRAWBERRY": 1}, inventory={"WOOL": 2}), {})
        self.assertIs(out, action)
        self.assertEqual(arm.telemetry["reasons"]["ALREADY_VIABLE_FIRST"], 1)
        self.assertEqual(arm.telemetry["dead_rows"], 0)

    def test_full_ten_row_queue_keeps_exact_row_multiset_and_count(self):
        rows = [
            ["SELL", "WOOL", 1],
            ["SELL", "MILK", 1],
            ["SELL", "STRAWBERRY", 1],
            ["SELL", "WOOL", 2],
            ["SELL", "MILK", 2],
            ["SELL", "STRAWBERRY", 2],
            ["SELL", "WOOL", 3],
            ["SELL", "MILK", 3],
            ["SELL", "STRAWBERRY", 3],
            ["HIRE"],
        ]
        action = {"farmer": ["PASS"], "hands": [], "market": deepcopy(rows)}
        arm = h8.install(parent_with(action), enabled=True)
        out = arm(obs(shed={"WOOL": 0, "MILK": 1, "STRAWBERRY": 3}), {"maxMarketOrdersPerTurn": 10})
        self.assertEqual(len(out["market"]), 10)
        self.assertEqual(out["market"][-1], ["HIRE"])
        self.assertCountEqual(map(tuple, out["market"]), map(tuple, rows))
        self.assertEqual(sum(1 for row in out["market"] if row[0] == "SELL"), 9)
        self.assertEqual(arm.telemetry["changed"], 1)


if __name__ == "__main__":
    unittest.main()
