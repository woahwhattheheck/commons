# SPDX-License-Identifier: Apache-2.0
"""Focused checks for V4 D4 ``r04_d4_strawberry_timing``."""
from __future__ import annotations

import copy
import inspect
import json
import pathlib
import sys
import unittest
from types import SimpleNamespace

HERE = pathlib.Path(__file__).resolve().parent
OVERLAY = HERE.parent
if str(OVERLAY) not in sys.path:
    sys.path.insert(0, str(OVERLAY))

import r04_full_router as r04  # noqa: E402
import r04_d4_strawberry_timing as d4  # noqa: E402
from titan_runtime import Features, TitanAgent  # noqa: E402

CONFIG = {"episodeSteps": 720, "turnsPerDay": 24, "boardSize": 10,
          "shedCapacity": 100, "maxMarketOrdersPerTurn": 10,
          "farmHandCostMult": 1}


class View:
    def __init__(self, stock=12, price=200):
        self.shed = {item: 0 for item in r04.PRODUCTS}
        self.shed["STRAWBERRY"] = stock
        self.prices = {item: 10 for item in r04.PRODUCTS}
        self.prices["STRAWBERRY"] = price
        self.positions = []
        self.inventories = []

    def inventory(self, actor):
        return {}

    def beside_shed(self, pos):
        return False


def observation(step=369, *, stock=12, price=200):
    tiles = [[None] * 10 for _ in range(10)]
    farm = {"tiles": tiles, "farmer": [4, 4], "hands": [],
            "money": 1000, "unlocked_quadrants": ["NW"], "hires_today": 0}
    prices = {item: 10 for item in r04.PRODUCTS}
    prices["STRAWBERRY"] = price
    return {"step": step, "day": step // 24, "hour": step % 24, "player": 0,
            "farms": [farm, copy.deepcopy(farm)],
            "private": {"inventories": [{}], "shed": {"STRAWBERRY": stock}},
            "market": {"prices": prices},
            "town": {"unlocked_shops": ["BAKERY", "YARN_STORE"]}}


def action(market=None):
    return {"farmer": ["PASS"], "hands": [], "market": list(market or [])}


def tape_with(step, qty=1000, pickup_step=None):
    tape = [{"farmer": ["PASS"], "hands": [], "market": []}
            for _ in range(r04.LAST_STEP + 1)]
    tape[step]["market"] = [["SELL", "STRAWBERRY", qty]]
    if pickup_step is not None:
        tape[pickup_step]["farmer"] = ["PICKUP", "STRAWBERRY", 1]
    return tape


class D4V4Tests(unittest.TestCase):
    def setUp(self):
        self.old_horizon = r04.SALE_HORIZON
        self.old_flush = r04.EVENING_FLUSH
        r04.SALE_HORIZON = 8
        r04.EVENING_FLUSH = True

    def tearDown(self):
        r04.SALE_HORIZON = self.old_horizon
        r04.EVENING_FLUSH = self.old_flush
        r04.D4_STRAWBERRY_TIMING = False
        r04.D4_STRAWBERRY_MIN_PRICE = 180

    def state(self, debts=None):
        return SimpleNamespace(queues={}, sale_window_debts={} if debts is None else debts)

    def test_key_ships_off_and_parameter_is_explicit(self):
        data = json.loads((OVERLAY / "TITAN-CONFIG.json").read_text(encoding="utf-8"))
        self.assertIs(data["r04_d4_strawberry_timing"], False)
        self.assertEqual(data["r04_d4_strawberry_min_price"], 180)
        features = Features(**data)
        self.assertIs(features.r04_d4_strawberry_timing, False)
        self.assertEqual(features.r04_d4_strawberry_min_price, 180)

    def test_feature_off_is_exact_identity(self):
        original = action()
        self.assertIs(
            d4.apply_d4_strawberry_timing(original, {}, enabled=False),
            original,
        )

    def test_preflush_authored_sale_can_advance(self):
        state = self.state()
        out, added, reservations = d4.advance_midgame_strawberry(
            action(), View(stock=12, price=200), state, tape_with(380), 369,
            min_price=180,
        )
        self.assertEqual(12, added)
        self.assertEqual(((380, 12),), reservations)
        self.assertEqual([["SELL", "STRAWBERRY", 12]], out["market"])
        self.assertEqual({380: {"STRAWBERRY": 12}}, state.sale_window_debts)

    def test_incumbent_flush_owns_later_h22_row(self):
        original = action()
        state = self.state()
        out, added, reservations = d4.advance_midgame_strawberry(
            original, View(stock=12, price=200), state, tape_with(382), 373,
            min_price=180,
        )
        self.assertIs(out, original)
        self.assertEqual((0, ()), (added, reservations))
        self.assertEqual({}, state.sale_window_debts)

    def test_price_parameter_is_strict_and_sweepable(self):
        original = action()
        state = self.state()
        out, added, _ = d4.advance_midgame_strawberry(
            original, View(stock=12, price=179), state, tape_with(380), 369,
            min_price=180,
        )
        self.assertIs(out, original)
        self.assertEqual(0, added)

        out, added, _ = d4.advance_midgame_strawberry(
            original, View(stock=12, price=179), state, tape_with(380), 369,
            min_price=150,
        )
        self.assertIsNot(out, original)
        self.assertEqual(12, added)

        out, added, _ = d4.advance_midgame_strawberry(
            original, View(stock=12, price=200), self.state(), tape_with(380), 369,
            min_price=True,
        )
        self.assertIs(out, original)
        self.assertEqual(0, added)

    def test_current_strawberry_trade_is_parent_owned(self):
        original = action([["SELL", "STRAWBERRY", 2]])
        state = self.state()
        out, added, _ = d4.advance_midgame_strawberry(
            original, View(), state, tape_with(380), 369, min_price=180,
        )
        self.assertIs(out, original)
        self.assertEqual(0, added)

    def test_existing_debt_is_subtracted_exactly(self):
        state = self.state({380: {"STRAWBERRY": 8}})
        out, added, reservations = d4.advance_midgame_strawberry(
            action(), View(stock=5), state, tape_with(380, qty=10), 369,
            min_price=180,
        )
        self.assertEqual(2, added)
        self.assertEqual(((380, 2),), reservations)
        self.assertEqual(10, state.sale_window_debts[380]["STRAWBERRY"])
        self.assertEqual([["SELL", "STRAWBERRY", 2]], out["market"])

    def test_full_inherited_debt_map_is_validated_before_mutation(self):
        malformed = (
            {True: {"STRAWBERRY": 1}},
            {"380": {"STRAWBERRY": 1}},
            {720: {"STRAWBERRY": 1}},
            {380: []},
            {380: {"STRAWBERRY": True}},
            {380: {"STRAWBERRY": 1.0}},
            {380: {"STRAWBERRY": "1"}},
            {380: {"STRAWBERRY": -1}},
            {380: {"NOT_A_PRODUCT": 1}},
        )
        for debts in malformed:
            with self.subTest(debts=debts):
                original = action()
                state = self.state(debts)
                out, added, reservations = d4.advance_midgame_strawberry(
                    original, View(stock=5), state, tape_with(380, qty=10), 369,
                    min_price=180,
                )
                self.assertIs(out, original)
                self.assertEqual((0, ()), (added, reservations))
                self.assertIs(state.sale_window_debts, debts)

    def test_order_cap_and_future_pickup_block(self):
        original = action([["SELL", "WHEAT", 1] for _ in range(r04.MAX_ORDERS)])
        state = self.state()
        out, added, _ = d4.advance_midgame_strawberry(
            original, View(), state, tape_with(380), 369, min_price=180,
        )
        self.assertIs(out, original)
        self.assertEqual(0, added)

        original = action()
        state = self.state()
        out, added, _ = d4.advance_midgame_strawberry(
            original, View(), state, tape_with(380, pickup_step=379), 369,
            min_price=180,
        )
        self.assertIs(out, original)
        self.assertEqual(0, added)

    def test_stack_seam_runs_after_h4_and_before_evening_flush(self):
        source = inspect.getsource(r04._v3_stack)
        self.assertLess(source.index("_strawberry_topup"),
                        source.index("apply_d4_strawberry_timing"))
        self.assertLess(source.index("apply_d4_strawberry_timing"),
                        source.index("evening_flush"))

    def test_install_and_titan_diagnostics_carry_key_and_parameter(self):
        r04.install(d4_strawberry_timing=True, d4_strawberry_min_price=222)
        self.assertIs(r04.D4_STRAWBERRY_TIMING, True)
        self.assertEqual(r04.D4_STRAWBERRY_MIN_PRICE, 222)
        with self.assertRaises(ValueError):
            r04.install(d4_strawberry_min_price=True)
        r04.install(d4_strawberry_timing=False, d4_strawberry_min_price=180)

        agent = TitanAgent(Features(r04_sale_window=True,
                                    r04_d4_strawberry_timing=True,
                                    r04_d4_strawberry_min_price=222))
        agent.act(observation(step=0, stock=0), dict(CONFIG))
        self.assertIs(r04.D4_STRAWBERRY_TIMING, True)
        self.assertEqual(r04.D4_STRAWBERRY_MIN_PRICE, 222)
        self.assertIs(agent.diagnostics["d4_strawberry_timing"], True)
        self.assertEqual(agent.diagnostics["d4_strawberry_min_price"], 222)


if __name__ == "__main__":
    unittest.main()
