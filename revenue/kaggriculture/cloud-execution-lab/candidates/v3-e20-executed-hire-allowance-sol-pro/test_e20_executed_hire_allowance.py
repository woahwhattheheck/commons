# SPDX-License-Identifier: Apache-2.0
"""Predecessor killers for E20 executed-HIRE allowance custody."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import e20_hire_guard as e20  # noqa: E402


def plant(watered=True):
    return {"kind": "PLANT", "crop": "WHEAT", "watered_today": watered}


def observation(*, money=3000, hires_today=0, step=10, tiles=None):
    return {
        "step": step,
        "player": 0,
        "farms": [
            {
                "money": money,
                "hires_today": hires_today,
                "tiles": tiles if tiles is not None else [[plant(True)]],
            }
        ],
    }


def fib(n):
    a, b = 1, 1
    for _ in range(n):
        a, b = b, a + b
    return a


def execute_hire_sell_subset(
    action, *, money, hires_today, wheat=0, price=10, mult=1, limit=10
):
    """Official market subset: literal row order, HIRE, then quantity SELL."""
    for order in list(action.get("market", []))[: max(1, int(limit))]:
        if not isinstance(order, list) or not order:
            continue
        if order[0] == "HIRE":
            cost = mult * fib(hires_today)
            if money >= cost:
                money -= cost
                hires_today += 1
        elif order[0] == "SELL" and len(order) >= 3 and order[1] == "WHEAT":
            try:
                quantity = int(order[2])
            except (TypeError, ValueError):
                continue
            quantity = min(max(0, quantity), wheat)
            money += quantity * price
            wheat -= quantity
    return {"money": money, "hires_today": hires_today, "wheat": wheat}


class ExecutedHireAllowanceTests(unittest.TestCase):
    def test_unfunded_first_hire_does_not_authorize_deleting_later_funded_hire(self):
        action = {"market": [["HIRE"], ["SELL", "WHEAT", 1], ["HIRE"]]}
        cfg = {
            "maxMarketOrdersPerTurn": 3,
            "e20_max_hires_per_day": 3,
            "e20_min_unwatered_crops": 3,
            "farmHandCostMult": 1,
        }
        out, report = e20.apply_hire_guard(
            observation(money=0, hires_today=2), action, cfg, enabled=True
        )
        self.assertIs(out, action)
        self.assertEqual(report["reason"], "UNCERTAIN_ALLOWED_HIRE_EXECUTION")
        self.assertEqual(
            report["uncertainty"], "UNFUNDED_HIRE_MAY_BE_FUNDED_LATER"
        )
        state = execute_hire_sell_subset(
            out, money=0, hires_today=2, wheat=1, limit=3
        )
        self.assertEqual(state["hires_today"], 3)

    def test_front_loaded_funded_allowance_preserves_prior_intended_behavior(self):
        action = {
            "market": [
                ["HIRE"],
                ["BUY_SEED", "WHEAT", 1],
                ["HIRE"],
                ["HIRE"],
                ["SELL", "WHEAT", 1],
            ]
        }
        original = deepcopy(action)
        out, report = e20.apply_hire_guard(
            observation(money=3000, hires_today=2),
            action,
            {"maxMarketOrdersPerTurn": 10, "e20_max_hires_per_day": 3},
            enabled=True,
        )
        self.assertEqual(action, original)
        self.assertEqual(
            out["market"],
            [
                ["HIRE"],
                ["BUY_SEED", "WHEAT", 1],
                [],
                [],
                ["SELL", "WHEAT", 1],
            ],
        )
        self.assertEqual(report["certified_hire_indices"], [0])
        self.assertEqual(report["dropped_indices"], [2, 3])

    def test_money_changing_row_before_allowed_hire_is_fail_closed(self):
        action = {"market": [["SELL", "WHEAT", 1], ["HIRE"], ["HIRE"]]}
        out, report = e20.apply_hire_guard(
            observation(money=3000, hires_today=2),
            action,
            {"maxMarketOrdersPerTurn": 3, "e20_max_hires_per_day": 3},
            enabled=True,
        )
        self.assertIs(out, action)
        self.assertEqual(report["uncertainty"], "PRECEDING_MONEY_CHANGING_ORDER")

    def test_at_cap_drops_only_interpreter_visible_hires(self):
        action = {
            "market": [["HIRE"], ["SELL", "WHEAT", 1], ["HIRE"], ["HIRE"]]
        }
        out, report = e20.apply_hire_guard(
            observation(hires_today=3),
            action,
            {"maxMarketOrdersPerTurn": 3, "e20_max_hires_per_day": 3},
            enabled=True,
        )
        self.assertEqual(
            out["market"], [[], ["SELL", "WHEAT", 1], [], ["HIRE"]]
        )
        self.assertEqual(report["dropped_indices"], [0, 2])
        self.assertEqual(report["inert_suffix_hire_indices"], [3])

    def test_suffix_only_excess_is_exact_identity(self):
        action = {"market": [["HIRE"], ["SELL", "WHEAT", 1], ["HIRE"]]}
        out, report = e20.apply_hire_guard(
            observation(money=10, hires_today=2),
            action,
            {"maxMarketOrdersPerTurn": 2, "e20_max_hires_per_day": 3},
            enabled=True,
        )
        self.assertIs(out, action)
        self.assertEqual(report["reason"], "HIRES_WITHIN_LOW_DEMAND_ALLOWANCE")
        self.assertEqual(report["inert_suffix_hire_indices"], [2])

    def test_fibonacci_multiplier_controls_certification(self):
        action = {"market": [["HIRE"], ["HIRE"]]}
        cfg = {"e20_max_hires_per_day": 3, "farmHandCostMult": 2}
        out, report = e20.apply_hire_guard(
            observation(money=3, hires_today=2), action, cfg, enabled=True
        )
        self.assertIs(out, action)
        self.assertEqual(report["required_cost"], 4)
        out, report = e20.apply_hire_guard(
            observation(money=4, hires_today=2), action, cfg, enabled=True
        )
        self.assertEqual(out["market"], [["HIRE"], []])
        self.assertEqual(report["certified_hire_indices"], [0])

    def test_two_front_loaded_successes_are_certified_sequentially(self):
        action = {"market": [["HIRE"], ["HIRE"], ["HIRE"]]}
        out, report = e20.apply_hire_guard(
            observation(money=3, hires_today=1),
            action,
            {"e20_max_hires_per_day": 3},
            enabled=True,
        )
        self.assertEqual(out["market"], [["HIRE"], ["HIRE"], []])
        self.assertEqual(report["certified_hire_indices"], [0, 1])

    def test_bad_state_and_configuration_are_identity(self):
        action = {"market": [["HIRE"], ["HIRE"]]}
        cases = [
            (observation(hires_today=True), {}),
            (observation(money=float("nan")), {}),
            (observation(), {"maxMarketOrdersPerTurn": "bad"}),
            (observation(), {"farmHandCostMult": 0}),
            (observation(), {"e20_max_hires_per_day": -1}),
        ]
        for obs, cfg in cases:
            with self.subTest(cfg=cfg):
                out, report = e20.apply_hire_guard(obs, action, cfg, enabled=True)
                self.assertIs(out, action)
                self.assertFalse(report["changed"])

    def test_high_demand_and_terminal_are_identity(self):
        action = {"market": [["HIRE"], ["HIRE"]]}
        high = observation(tiles=[[plant(False), plant(False), plant(False)]])
        out, report = e20.apply_hire_guard(high, action, {}, enabled=True)
        self.assertIs(out, action)
        self.assertEqual(report["reason"], "DEMAND_JUSTIFIES_HIRES")
        out, report = e20.apply_hire_guard(
            observation(step=718), action, {}, enabled=True
        )
        self.assertIs(out, action)
        self.assertEqual(report["reason"], "NO_EDIT_TERMINAL_STEP")

    def test_idempotent_and_input_nonmutating(self):
        action = {
            "farmer": ["PASS"],
            "opaque": {"x": 1},
            "market": [["HIRE"], ["HIRE"]],
        }
        original = deepcopy(action)
        first, first_report = e20.apply_hire_guard(
            observation(money=10, hires_today=2),
            action,
            {"e20_max_hires_per_day": 3},
            enabled=True,
        )
        second, second_report = e20.apply_hire_guard(
            observation(money=10, hires_today=2),
            first,
            {"e20_max_hires_per_day": 3},
            enabled=True,
        )
        self.assertEqual(action, original)
        self.assertTrue(first_report["changed"])
        self.assertIs(second, first)
        self.assertFalse(second_report["changed"])
        self.assertEqual(first["farmer"], action["farmer"])
        self.assertEqual(first["opaque"], action["opaque"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
