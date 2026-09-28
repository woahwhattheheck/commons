# SPDX-License-Identifier: Apache-2.0
"""Exact preserved-engine contracts for the market-carry overlay."""
from __future__ import annotations

import copy
from pathlib import Path
import sys
import unittest


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import mechanics
import scheduler
import test_engine_semantics as semantics
from market_carry import MarketCarry


class OfficialEngineContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        semantics.EngineSemantics.setUpClass()
        cls.helper = semantics.EngineSemantics()
        cls.engine = cls.helper.engine

    def test_predicted_worst_profit_is_realized_without_rival_flow(self):
        state, env = self.helper.fixture(
            item="STRAWBERRY",
            stock=(0, 0),
            inventory=10_000,
            step=120,
            shops=["SMOOTHIE_SHOP"] * 4,
            cash=10_000,
        )
        obs = state[0].observation
        selected = {"farmer": ["PASS"], "hands": [], "market": []}
        overlay = MarketCarry(mechanics, post_units=scheduler.post_units)
        candidate, report = overlay.transform(obs, env.configuration, selected)
        self.assertTrue(report["changed"], report)
        order = candidate["market"][-1]
        self.assertEqual(order[:2], ["BUY_PRODUCT", "STRAWBERRY"])
        quantity = int(order[2])
        start_cash = int(obs.farms[0]["money"])

        state[0].action = copy.deepcopy(candidate)
        state[1].action = semantics.pass_agent({})
        self.engine._process_market(state, env)
        after_buy_cash = int(obs.farms[0]["money"])
        self.engine._town_consume(env, state, 120)
        state[0].action = {
            "farmer": ["PASS"],
            "hands": [],
            "market": [["SELL", "STRAWBERRY", quantity]],
        }
        state[1].action = semantics.pass_agent({})
        self.engine._process_market(state, env)
        final_cash = int(obs.farms[0]["money"])

        self.assertLess(after_buy_cash, start_cash)
        self.assertGreater(final_cash, start_cash)
        self.assertGreaterEqual(
            final_cash - start_cash,
            report["entry"]["worst_profit"],
        )
        self.assertEqual(obs.private["shed"].get("STRAWBERRY", 0), 0)

    def test_actual_post_unit_drop_capacity_is_respected(self):
        state, env = self.helper.fixture(
            item="MILK",
            stock=(90, 0),
            inventory=10_000,
            step=120,
            shops=["SMOOTHIE_SHOP"] * 4,
            cash=10_000,
        )
        obs = state[0].observation
        obs.private["inventories"] = [{"MILK": 20}]
        selected = {"farmer": ["DROP"], "hands": [], "market": []}
        overlay = MarketCarry(mechanics, post_units=scheduler.post_units)
        candidate, report = overlay.transform(obs, env.configuration, selected)
        self.assertIs(candidate, selected)
        self.assertEqual(report["reason"], "no_post_unit_capacity")

    def test_append_does_not_change_inherited_market_fills(self):
        kwargs = dict(
            item="STRAWBERRY",
            stock=(0, 0),
            inventory=10_000,
            step=120,
            shops=["SMOOTHIE_SHOP"] * 4,
            cash=10_000,
        )
        control, control_env = self.helper.fixture(**kwargs)
        treatment, treatment_env = self.helper.fixture(**kwargs)
        for state in (control, treatment):
            state[0].observation.private["shed"]["WHEAT"] = 2
        selected = {
            "farmer": ["PASS"],
            "hands": [],
            "market": [["SELL", "WHEAT", 2]],
        }
        overlay = MarketCarry(mechanics, post_units=scheduler.post_units)
        candidate, report = overlay.transform(
            treatment[0].observation, treatment_env.configuration, selected
        )
        self.assertTrue(report["changed"], report)
        self.assertEqual(candidate["market"][:-1], selected["market"])

        control[0].action = copy.deepcopy(selected)
        treatment[0].action = copy.deepcopy(candidate)
        control[1].action = treatment[1].action = semantics.pass_agent({})
        self.engine._process_market(control, control_env)
        self.engine._process_market(treatment, treatment_env)
        self.assertEqual(
            control[0].observation.private["shed"].get("WHEAT", 0),
            treatment[0].observation.private["shed"].get("WHEAT", 0),
        )
        actual_cost = (
            int(control[0].observation.farms[0]["money"])
            - int(treatment[0].observation.farms[0]["money"])
        )
        self.assertGreater(actual_cost, 0)
        self.assertLessEqual(actual_cost, report["entry"]["worst_cost"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
