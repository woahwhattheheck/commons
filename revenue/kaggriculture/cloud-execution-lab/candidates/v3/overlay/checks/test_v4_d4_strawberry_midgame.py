# SPDX-License-Identifier: Apache-2.0
"""Focused checks for V4 ``r04_d4_strawberry_midgame``.

Run in a materialised candidate package:

    python -B -m unittest -v checks/test_v4_d4_strawberry_midgame.py
"""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import r04_d4_strawberry_midgame as lane  # noqa: E402
import r04_full_router as r04  # noqa: E402
from titan_runtime import Features, TitanAgent  # noqa: E402

CONFIG = {"episodeSteps": 720, "turnsPerDay": 24, "boardSize": 10,
          "shedCapacity": 100, "maxMarketOrdersPerTurn": 10,
          "farmHandCostMult": 1}


class View:
    def __init__(self, stock=12, price=200):
        self.shed = {item: 0 for item in r04.PRODUCTS}
        self.shed["STRAWBERRY"] = stock
        self.prices = {"STRAWBERRY": price}
        self.positions = []
        self.inventories = []

    def inventory(self, actor):
        return {}

    def beside_shed(self, position):
        return False


def action(market=None):
    return {"farmer": ["PASS"], "hands": [], "market": list(market or [])}


def state(debts=None):
    return SimpleNamespace(queues={}, sale_window_debts={} if debts is None else debts)


def tape_with(step, qty=1000, pickup_step=None):
    tape = [{"farmer": ["PASS"], "hands": [], "market": []}
            for _ in range(r04.LAST_STEP + 1)]
    tape[step]["market"] = [["SELL", "STRAWBERRY", qty]]
    if pickup_step is not None:
        tape[pickup_step]["farmer"] = ["PICKUP", "STRAWBERRY", 1]
    return tape


class D4StrawberryMidgame(unittest.TestCase):
    def tearDown(self):
        if hasattr(r04, "D4_STRAWBERRY_MIDGAME"):
            r04.D4_STRAWBERRY_MIDGAME = False

    def test_key_ships_off_and_features_accept_it(self):
        data = json.loads((ROOT / "TITAN-CONFIG.json").read_text(encoding="utf-8"))
        self.assertIs(data["r04_d4_strawberry_midgame"], False)
        self.assertIs(Features(**data).r04_d4_strawberry_midgame, False)

    def test_disabled_wrapper_is_exact_parent_object(self):
        parent = action()
        self.assertIs(lane.apply_d4(parent, {}, dict(CONFIG), enabled=False), parent)

    def test_advances_authored_sale_before_next_flush(self):
        old_horizon, old_flush = r04.SALE_HORIZON, r04.EVENING_FLUSH
        r04.SALE_HORIZON = 8
        r04.EVENING_FLUSH = True
        try:
            parent = action()
            memory = state()
            out, added, reservations = lane.advance_midgame_strawberry(
                parent, View(stock=12, price=200), memory, tape_with(380), 369,
                min_price=180)
            self.assertIsNot(out, parent)
            self.assertEqual(12, added)
            self.assertEqual(((380, 12),), reservations)
            self.assertEqual([["SELL", "STRAWBERRY", 12]], out["market"])
            self.assertEqual({380: {"STRAWBERRY": 12}}, memory.sale_window_debts)
        finally:
            r04.SALE_HORIZON, r04.EVENING_FLUSH = old_horizon, old_flush

    def test_evening_flush_owns_later_h22_row(self):
        old_horizon, old_flush = r04.SALE_HORIZON, r04.EVENING_FLUSH
        r04.SALE_HORIZON = 8
        r04.EVENING_FLUSH = True
        try:
            parent = action()
            memory = state()
            out, added, reservations = lane.advance_midgame_strawberry(
                parent, View(stock=12, price=200), memory, tape_with(382), 373,
                min_price=180)
            self.assertIs(out, parent)
            self.assertEqual((0, ()), (added, reservations))
            self.assertEqual({}, memory.sale_window_debts)
        finally:
            r04.SALE_HORIZON, r04.EVENING_FLUSH = old_horizon, old_flush

    def test_parent_horizon_remains_parent_owned(self):
        parent = action()
        memory = state()
        out, added, reservations = lane.advance_midgame_strawberry(
            parent, View(), memory, tape_with(390), 384, min_price=180)
        self.assertIs(out, parent)
        self.assertEqual((0, ()), (added, reservations))
        self.assertEqual({}, memory.sale_window_debts)

    def test_current_strawberry_sell_is_h4_owned(self):
        parent = action([["SELL", "STRAWBERRY", 2]])
        out, added, _ = lane.advance_midgame_strawberry(
            parent, View(), state(), tape_with(402), 384, min_price=180)
        self.assertIs(out, parent)
        self.assertEqual(0, added)

    def test_future_pickup_blocks_before_due(self):
        parent = action()
        out, added, _ = lane.advance_midgame_strawberry(
            parent, View(), state(), tape_with(402, pickup_step=398), 384,
            min_price=180)
        self.assertIs(out, parent)
        self.assertEqual(0, added)

    def test_existing_debt_is_subtracted_exactly(self):
        memory = state({402: {"STRAWBERRY": 8}})
        out, added, reservations = lane.advance_midgame_strawberry(
            action(), View(stock=5), memory, tape_with(402, qty=10), 384,
            min_price=180)
        self.assertEqual(2, added)
        self.assertEqual(((402, 2),), reservations)
        self.assertEqual(10, memory.sale_window_debts[402]["STRAWBERRY"])
        self.assertEqual([["SELL", "STRAWBERRY", 2]], out["market"])

    def test_full_inherited_debt_map_is_fail_closed(self):
        malformed = (
            {True: {"STRAWBERRY": 1}},
            {"402": {"STRAWBERRY": 1}},
            {720: {"STRAWBERRY": 1}},
            {402: []},
            {402: {"STRAWBERRY": True}},
            {402: {"STRAWBERRY": 1.0}},
            {402: {"STRAWBERRY": "1"}},
            {402: {"STRAWBERRY": -1}},
            {402: {"NOT_A_PRODUCT": 1}},
        )
        old_flush = r04.EVENING_FLUSH
        r04.EVENING_FLUSH = False
        try:
            for debts in malformed:
                with self.subTest(debts=debts):
                    parent = action()
                    memory = state(debts)
                    out, added, reservations = lane.advance_midgame_strawberry(
                        parent, View(stock=5), memory, tape_with(402, qty=10), 384,
                        min_price=180)
                    self.assertIs(out, parent)
                    self.assertEqual((0, ()), (added, reservations))
                    self.assertIs(memory.sale_window_debts, debts)
        finally:
            r04.EVENING_FLUSH = old_flush

    def test_price_threshold_is_identity(self):
        parent = action()
        out, added, _ = lane.advance_midgame_strawberry(
            parent, View(price=179), state(), tape_with(402), 384, min_price=180)
        self.assertIs(out, parent)
        self.assertEqual(0, added)

    def test_order_cap_blocks_without_mutation(self):
        parent = action([["SELL", "WHEAT", 1] for _ in range(r04.MAX_ORDERS)])
        out, added, _ = lane.advance_midgame_strawberry(
            parent, View(), state(), tape_with(402), 384, min_price=180)
        self.assertIs(out, parent)
        self.assertEqual(0, added)

    def test_nonstandard_configuration_fails_closed(self):
        parent = action()
        bad = dict(CONFIG)
        bad["maxMarketOrdersPerTurn"] = 9
        self.assertIs(lane.apply_d4(parent, {}, bad, enabled=True), parent)

    def test_install_and_titan_diagnostics_carry_key(self):
        r04.install(d4_strawberry_midgame=True)
        self.assertIs(r04.D4_STRAWBERRY_MIDGAME, True)
        r04.install(d4_strawberry_midgame=False)
        self.assertIs(r04.D4_STRAWBERRY_MIDGAME, False)

        agent = TitanAgent(Features(r04_sale_window=True, r04_d4_strawberry_midgame=True))
        # Step 0 is outside D4's timing window; this test exercises plumbing only.
        agent.act({"step": 0, "day": 0, "hour": 0, "player": 0,
                   "farms": [{"tiles": [[None] * 10 for _ in range(10)], "farmer": [4, 4],
                               "hands": [], "money": 1000, "unlocked_quadrants": ["NW"],
                               "hires_today": 0}] * 2,
                   "private": {"inventories": [{}], "shed": {}},
                   "market": {"prices": {product: 10 for product in r04.PRODUCTS}},
                   "town": {"unlocked_shops": []}}, dict(CONFIG))
        self.assertIs(r04.D4_STRAWBERRY_MIDGAME, True)
        self.assertIs(agent.diagnostics["d4_strawberry_midgame"], True)


if __name__ == "__main__":
    unittest.main()
