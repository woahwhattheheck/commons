# SPDX-License-Identifier: Apache-2.0
"""R04 key in the V3 tree: the R03 policy with the E184 sale window outermost.

    python -m unittest -v checks/test_v3_r04.py

Covers the E184 reservation rules on constructed tapes (horizon, per-due-step debts, the
72-step boundary, upcoming pickups, WHEAT/FERTILIZER exclusion), the horizon parameter,
the delegate seam (output identical to calling the published agent directly), precedence
over R03 and R01, and off-identity of the wiring. Standard library only.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import r04_full_router as r04  # noqa: E402
from r01_tapes import load_tapes  # noqa: E402
from titan_runtime import Features, TitanAgent  # noqa: E402

CONFIG = {"episodeSteps": 720, "turnsPerDay": 24, "boardSize": 10, "shedCapacity": 100,
          "maxMarketOrdersPerTurn": 10, "farmHandCostMult": 1}
DEFAULT_HORIZON = r04.SALE_HORIZON


def synthetic_observation(step, shed=None, shops=("BAKERY", "YARN_STORE"), player=0, money=1000):
    size = 10
    tiles = [["LOCKED"] * size for _ in range(size)]
    for y in range(3, 7):
        for x in range(3, 7):
            tiles[y][x] = {"kind": "SOIL"}
    farm = {"tiles": tiles, "farmer": [4, 4], "hands": [], "money": money,
            "unlocked_quadrants": ["NW"], "hires_today": 0}
    return {"step": step, "day": step // 24, "hour": step % 24, "player": player,
            "farms": [farm, copy.deepcopy(farm)],
            "private": {"inventories": [{}], "shed": dict(shed or {"WHEAT": 5})},
            "market": {"prices": {product: 10 for product in r04.PRODUCTS}},
            "town": {"unlocked_shops": list(shops)}}


def blank_tape():
    return [{"farmer": ["PASS"], "hands": [], "market": []} for _ in range(r04.LAST_STEP + 1)]


def empty_action():
    return {"farmer": ["PASS"], "hands": [], "market": []}


class Horizon(unittest.TestCase):
    def tearDown(self):
        r04.SALE_HORIZON = DEFAULT_HORIZON


class ModuleTests(Horizon):
    def test_inline_tapes_come_from_r01_tapes(self):
        self.assertEqual(r04._INLINE_TAPES, load_tapes())

    def test_e184_is_the_outermost_layer(self):
        self.assertEqual(r04.ADVANCE_START, 288)
        self.assertIs(r04.agent, r04.POLICY_AGENT)
        self.assertIs(r04._SALE_PARENT.telemetry, r04._V233_REPORT)
        self.assertIsNot(r04.advance_sales, r04._SALE_NATIVE_ADVANCE)
        self.assertIsNot(r04.subtract_advanced_sales, r04._SALE_NATIVE_SUBTRACT)
        for name in ("_V216_PARENT", "_V217_PARENT", "_V218_PARENT", "_V219_PARENT", "_V224_PARENT",
                     "_V226_PARENT", "_V231_PARENT", "_V233_PARENT", "_v234_rescue"):
            self.assertTrue(hasattr(r04, name), name)

    def test_install_sets_the_horizon(self):
        self.assertIs(r04.install(None, 5), r04.agent)
        self.assertEqual(r04.SALE_HORIZON, 5)
        with self.assertRaises(ValueError):
            r04.install(None, 0)

    def test_published_license_and_attribution_are_retained(self):
        source = (ROOT / "r04_full_router.py").read_text(encoding="utf-8")
        self.assertIn("Version 2.0, January 2004", source)
        self.assertIn("two-coins-one-sheep", source)
        self.assertIn("shop-router-0909", source)


class ReservationTests(Horizon):
    def reserve(self, tape, step, shed, action=None, horizon=3):
        r04.SALE_HORIZON = horizon
        action = action or empty_action()
        state = r04.DayState()
        view = r04.FarmView(synthetic_observation(step, shed=shed))
        r04.reserve_sales(action, view, state, tape, step)
        return action, state

    def test_sells_now_what_the_tape_sells_within_the_horizon(self):
        tape = blank_tape()
        tape[301]["market"] = [["SELL", "MILK", 4]]
        tape[303]["market"] = [["SELL", "MILK", 2]]
        tape[304]["market"] = [["SELL", "MILK", 9]]
        action, state = self.reserve(tape, 300, {"MILK": 10}, horizon=3)
        self.assertEqual(action["market"], [["SELL", "MILK", 6]])
        self.assertEqual(state.sale_window_debts, {301: {"MILK": 4}, 303: {"MILK": 2}})

    def test_reservation_is_bounded_by_stock(self):
        tape = blank_tape()
        tape[301]["market"] = [["SELL", "EGG", 7]]
        action, state = self.reserve(tape, 300, {"EGG": 3})
        self.assertEqual(action["market"], [["SELL", "EGG", 3]])
        self.assertEqual(state.sale_window_debts, {301: {"EGG": 3}})

    def test_debt_is_subtracted_once_at_the_due_step(self):
        tape = blank_tape()
        tape[301]["market"] = [["SELL", "MILK", 4]]
        _, state = self.reserve(tape, 300, {"MILK": 10})
        due = {"farmer": ["PASS"], "hands": [], "market": [["SELL", "MILK", 4], ["SELL", "EGG", 2]]}
        r04.subtract_advanced_sales(due, state, 301)
        self.assertEqual(due["market"], [["SELL", "MILK", 0], ["SELL", "EGG", 2]])
        self.assertEqual(state.sale_window_debts, {})

    def test_never_crosses_the_72_step_boundary(self):
        tape = blank_tape()
        tape[359]["market"] = [["SELL", "MILK", 2]]
        tape[360]["market"] = [["SELL", "MILK", 5]]
        action, state = self.reserve(tape, 358, {"MILK": 10}, horizon=3)
        self.assertEqual(action["market"], [["SELL", "MILK", 2]])
        self.assertEqual(state.sale_window_debts, {359: {"MILK": 2}})

    def test_upcoming_pickup_stops_the_window(self):
        tape = blank_tape()
        tape[301]["farmer"] = ["PICKUP", "MILK", 3]
        tape[302]["market"] = [["SELL", "MILK", 4]]
        action, _ = self.reserve(tape, 300, {"MILK": 10})
        self.assertEqual(action["market"], [])

    def test_wheat_and_fertilizer_are_never_advanced(self):
        tape = blank_tape()
        tape[301]["market"] = [["SELL", "WHEAT", 4], ["SELL", "FERTILIZER", 4]]
        action, _ = self.reserve(tape, 300, {"WHEAT": 10, "FERTILIZER": 10})
        self.assertEqual(action["market"], [])

    def test_item_already_sold_this_turn_is_not_advanced(self):
        tape = blank_tape()
        tape[301]["market"] = [["SELL", "MILK", 4]]
        action = empty_action()
        action["market"] = [["SELL", "MILK", 1]]
        action, _ = self.reserve(tape, 300, {"MILK": 10}, action=action)
        self.assertEqual(action["market"], [["SELL", "MILK", 1]])

    def test_horizon_one_reaches_only_the_next_action(self):
        tape = blank_tape()
        tape[301]["market"] = [["SELL", "MILK", 4]]
        tape[302]["market"] = [["SELL", "MILK", 4]]
        action, _ = self.reserve(tape, 300, {"MILK": 10}, horizon=1)
        self.assertEqual(action["market"], [["SELL", "MILK", 4]])


class WiringTests(Horizon):
    def play(self, callable_, steps):
        return [callable_(synthetic_observation(step), dict(CONFIG)) for step in steps]

    def test_keys_ship_off(self):
        data = json.loads((ROOT / "TITAN-CONFIG.json").read_text(encoding="utf-8"))
        self.assertIs(data["r04_sale_window"], False)
        self.assertEqual(data["r04_sale_horizon"], DEFAULT_HORIZON)
        features = Features(**data)
        self.assertIs(features.r04_sale_window, False)
        self.assertEqual(features.r04_sale_horizon, DEFAULT_HORIZON)
        self.assertFalse(TitanAgent(Features())._v3_active())
        self.assertTrue(TitanAgent(Features(r04_sale_window=True))._v3_active())

    def test_delegate_runs_before_any_canonical_state(self):
        agent = TitanAgent(Features(r04_sale_window=True))
        action = agent.act(synthetic_observation(0), dict(CONFIG))
        self.assertEqual(set(action), {"farmer", "hands", "market"})
        self.assertEqual(agent.diagnostics["status"], "completed")
        self.assertEqual(agent.diagnostics["route"], "r04_sale_window")
        self.assertEqual(agent.diagnostics["sale_horizon"], DEFAULT_HORIZON)
        self.assertFalse(agent.ready)
        self.assertIsNone(getattr(agent, "controller", None))

    def test_delegate_output_equals_the_published_agent(self):
        steps = list(range(0, 40)) + [143, 144, 145, 287, 288, 289, 300, 301, 647, 648, 700, 712, 717, r04.LAST_STEP]
        direct = self.play(r04.agent, steps)
        agent = TitanAgent(Features(r04_sale_window=True))
        delegated = self.play(lambda obs, cfg: agent.act(obs, cfg), steps)
        self.assertEqual(delegated, direct)

    def test_horizon_parameter_reaches_the_policy(self):
        agent = TitanAgent(Features(r04_sale_window=True, r04_sale_horizon=5))
        agent.act(synthetic_observation(0), dict(CONFIG))
        self.assertEqual(r04.SALE_HORIZON, 5)
        self.assertEqual(agent.diagnostics["sale_horizon"], 5)

    def test_r04_takes_precedence_over_r03_and_r01(self):
        agent = TitanAgent(Features(r01_shop_router=True, r03_full_router=True, r04_sale_window=True))
        agent.act(synthetic_observation(0), dict(CONFIG))
        self.assertEqual(agent.diagnostics["route"], "r04_sale_window")

    def test_notice_carries_attribution(self):
        notice = (ROOT / "NOTICE").read_text(encoding="utf-8")
        self.assertIn("r04_sale_window", notice)
        self.assertIn("two-coins-one-sheep", notice)


if __name__ == "__main__":
    unittest.main(verbosity=2)
