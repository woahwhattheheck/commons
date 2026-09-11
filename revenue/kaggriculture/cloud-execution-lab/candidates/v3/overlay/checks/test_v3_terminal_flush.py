# SPDX-License-Identifier: Apache-2.0
"""Focused invariants for the default-off R04 terminal-flush candidate."""
from __future__ import annotations

import copy
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import r04_full_router as r04  # noqa: E402
import r04_terminal_flush as terminal  # noqa: E402

CONFIG = {
    "episodeSteps": 720,
    "turnsPerDay": 24,
    "boardSize": 10,
    "shedCapacity": 100,
    "maxMarketOrdersPerTurn": 10,
}


def observation(step, shed=None, inventory=None, prices=None):
    size = 10
    tiles = [[{"kind": "SOIL"} for _ in range(size)] for _ in range(size)]
    farm = {
        "tiles": tiles,
        "farmer": [4, 4],
        "hands": [],
        "money": 1000,
        "unlocked_quadrants": ["NW"],
        "hires_today": 0,
    }
    market_prices = {item: 10 for item in r04.PRODUCTS}
    market_prices.update(prices or {})
    return {
        "step": step,
        "day": step // 24,
        "hour": step % 24,
        "player": 0,
        "farms": [farm, copy.deepcopy(farm)],
        "private": {
            "inventories": [dict(inventory or {})],
            "shed": dict(shed or {}),
        },
        "market": {"prices": market_prices},
        "town": {"unlocked_shops": ["BAKERY", "YARN_STORE"]},
    }


def action(farmer=None, market=None):
    return {
        "farmer": list(farmer or ["PASS"]),
        "hands": [],
        "market": [list(row) for row in (market or [])],
    }


class TerminalFlushTests(unittest.TestCase):
    def test_identity_before_bounded_window(self):
        original = action(["WATER"], [["HIRE"]])
        self.assertIs(terminal.terminal_flush(observation(697, {"STRAWBERRY": 17}), original), original)

    def test_step701_flushes_high_value_shed_stock_without_touching_worker(self):
        original = action(["WATER"], [["HIRE"]])
        got = terminal.terminal_flush(
            observation(701, {"STRAWBERRY": 17, "WOOL": 3, "WHEAT": 9}),
            original,
        )
        self.assertEqual(got["farmer"], ["WATER"])
        self.assertEqual(got["hands"], [])
        self.assertEqual(
            got["market"],
            [["SELL", "STRAWBERRY", 17], ["SELL", "WOOL", 3], ["HIRE"]],
        )

    def test_projected_same_turn_drop_can_be_sold(self):
        original = action(["DROP"])
        got = terminal.terminal_flush(
            observation(701, {}, inventory={"STRAWBERRY": 6}),
            original,
        )
        self.assertEqual(got["farmer"], ["DROP"])
        self.assertEqual(got["market"], [["SELL", "STRAWBERRY", 6]])

    def test_existing_sell_is_not_doubled(self):
        original = action(market=[["SELL", "STRAWBERRY", 5]])
        got = terminal.terminal_flush(
            observation(701, {"STRAWBERRY": 17}),
            original,
        )
        self.assertEqual(got["market"], [["SELL", "STRAWBERRY", 12], ["SELL", "STRAWBERRY", 5]])

    def test_order_cap_is_never_exceeded(self):
        full = [["HIRE"] for _ in range(r04.MAX_ORDERS)]
        original = action(market=full)
        self.assertIs(
            terminal.terminal_flush(observation(701, {"STRAWBERRY": 17}), original),
            original,
        )

    def test_low_quote_is_not_flushed(self):
        original = action()
        self.assertIs(
            terminal.terminal_flush(
                observation(701, {"STRAWBERRY": 17}, prices={"STRAWBERRY": 1}),
                original,
            ),
            original,
        )

    def test_last_step_remains_owned_by_r04_liquidation(self):
        original = action(["DROP"], [["SELL", "WHEAT", 3]])
        self.assertIs(
            terminal.terminal_flush(
                observation(r04.LAST_STEP, {"STRAWBERRY": 17}),
                original,
            ),
            original,
        )

    def test_install_is_explicit_and_preserves_parent_off_window(self):
        calls = []

        def host(obs, cfg=None):
            calls.append((obs["step"], cfg))
            return action(["WATER"], [["HIRE"]])

        wrapped = terminal.install(host)
        before = wrapped(observation(697, {"STRAWBERRY": 17}), CONFIG)
        live = wrapped(observation(701, {"STRAWBERRY": 17}), CONFIG)
        self.assertEqual(before, action(["WATER"], [["HIRE"]]))
        self.assertEqual(live["farmer"], ["WATER"])
        self.assertEqual(live["market"], [["SELL", "STRAWBERRY", 17], ["HIRE"]])
        self.assertEqual([row[0] for row in calls], [697, 701])

    def test_invalid_activation_boundary_is_rejected(self):
        with self.assertRaises(ValueError):
            terminal.install(lambda *_: action(), start=r04.LAST_STEP)


if __name__ == "__main__":
    unittest.main()
