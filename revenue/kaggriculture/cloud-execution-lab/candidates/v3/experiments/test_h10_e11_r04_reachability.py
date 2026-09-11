# SPDX-License-Identifier: Apache-2.0
"""Focused checks for H10 E11 reachability + R04 sale-debt atomicity."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
import sys
import unittest

HERE = Path(__file__).resolve().parent
OVERLAY = HERE.parent / "overlay"
for path in (HERE, OVERLAY):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import h10_e11_r04_reachability as h10  # noqa: E402


def obs(step, price, *, player=0):
    return {
        "step": step,
        "player": player,
        "market": {"prices": {"MILK": price}, "inventory": {"MILK": 10000}},
        "town": {"unlocked_shops": ["ICE_CREAM_SHOP"]},
    }


def action(quantity=5):
    return {
        "farmer": ["PASS"],
        "hands": [["PASS"]],
        "market": [["SELL", "MILK", quantity]],
    }


def absorb_one(_item, _step, _shops, _config):
    return 1


CFG = {
    "episodeSteps": 20,
    "rival_dump_price_drop": 15.0,
    "rival_dump_lookback_steps": 8,
    "e11_min_future_absorption": 2,
}


class H10E11R04Tests(unittest.TestCase):
    def test_disabled_returns_exact_parent_action_and_never_reads_state(self):
        parent_action = action()
        def parent(_observation, _configuration=None):
            return parent_action
        def forbidden_getter(_observation):
            raise AssertionError("disabled adapter must not read R04 state")

        wrapped = h10.wrap_r04_agent(
            parent, absorb_one, enabled=False, state_getter=forbidden_getter,
        )
        out = wrapped(obs(5, 40), CFG)
        self.assertIs(out, parent_action)
        self.assertEqual(wrapped.telemetry["calls"], 0)

    def test_live_e11_becomes_reachable_after_price_drop(self):
        state = SimpleNamespace(sale_window_debts={})
        parent_actions = []
        def parent(_observation, _configuration=None):
            item = action(4)
            parent_actions.append(item)
            return item
        wrapped = h10.wrap_r04_agent(
            parent, absorb_one, enabled=True, state_getter=lambda _obs: state,
        )

        first = wrapped(obs(5, 40), CFG)
        second = wrapped(obs(6, 10), CFG)
        self.assertIs(first, parent_actions[0])
        self.assertEqual(second["market"], [[]])
        self.assertEqual(wrapped.telemetry["changed"], 1)
        self.assertEqual(
            wrapped.telemetry["last_by_player"][0]["reason"],
            "PUBLIC_PRICE_DROP_DEFER_MILK",
        )

    def test_new_e184_debt_is_refunded_but_preexisting_debt_survives(self):
        state = SimpleNamespace(sale_window_debts={8: {"MILK": 2}, 9: {"WOOL": 1}})
        def parent(observation, _configuration=None):
            if observation["step"] == 6:
                state.sale_window_debts = {
                    8: {"MILK": 5},
                    9: {"WOOL": 1, "MILK": 2},
                }
            return action(5)

        wrapped = h10.wrap_r04_agent(
            parent, absorb_one, enabled=True, state_getter=lambda _obs: state,
        )
        wrapped(obs(5, 40), CFG)  # establish E11 price history
        out = wrapped(obs(6, 10), CFG)
        self.assertEqual(out["market"], [[]])
        self.assertEqual(state.sale_window_debts, {8: {"MILK": 2}, 9: {"WOOL": 1}})
        report = wrapped.telemetry["last_by_player"][0]
        self.assertEqual(report["new_debt_qty"]["MILK"], 5)
        self.assertEqual(report["refunded_new_debt"]["MILK"], 5)

    def test_debt_consumed_at_current_step_is_not_recreated(self):
        state = SimpleNamespace(sale_window_debts={6: {"MILK": 2}})
        def parent(observation, _configuration=None):
            if observation["step"] == 6:
                state.sale_window_debts = {}  # parent consumed the due debt this step
            return action(3)

        wrapped = h10.wrap_r04_agent(
            parent, absorb_one, enabled=True, state_getter=lambda _obs: state,
        )
        wrapped(obs(5, 40), CFG)
        out = wrapped(obs(6, 10), CFG)
        self.assertEqual(out["market"], [[]])
        self.assertEqual(state.sale_window_debts, {})
        self.assertEqual(wrapped.telemetry["last_by_player"][0]["refunded_new_debt"], {})

    def test_existing_future_debt_is_untouched_when_parent_books_nothing(self):
        state = SimpleNamespace(sale_window_debts={8: {"MILK": 2}})
        wrapped = h10.wrap_r04_agent(
            lambda _obs, _cfg=None: action(3), absorb_one,
            enabled=True, state_getter=lambda _obs: state,
        )
        wrapped(obs(5, 40), CFG)
        out = wrapped(obs(6, 10), CFG)
        self.assertEqual(out["market"], [[]])
        self.assertEqual(state.sale_window_debts, {8: {"MILK": 2}})

    def test_parent_debt_larger_than_removed_sell_fails_closed(self):
        state = SimpleNamespace(sale_window_debts={})
        produced = []
        def parent(observation, _configuration=None):
            item = action(5)
            produced.append(item)
            if observation["step"] == 6:
                state.sale_window_debts = {8: {"MILK": 6}}
            return item

        wrapped = h10.wrap_r04_agent(
            parent, absorb_one, enabled=True, state_getter=lambda _obs: state,
        )
        wrapped(obs(5, 40), CFG)
        out = wrapped(obs(6, 10), CFG)
        self.assertIs(out, produced[1])
        self.assertEqual(out["market"], [["SELL", "MILK", 5]])
        self.assertEqual(state.sale_window_debts, {8: {"MILK": 6}})
        self.assertEqual(
            wrapped.telemetry["last_by_player"][0]["reason"],
            "FAIL_CLOSED_DEBT_EXCEEDS_DEFERRED_SELL",
        )

    def test_non_row_stable_e11_result_fails_closed_without_debt_mutation(self):
        state = SimpleNamespace(sale_window_debts={8: {"MILK": 1}})
        produced = []
        def parent(_observation, _configuration=None):
            item = action(5)
            produced.append(item)
            return item
        def bad_apply(_obs, parent_action, _history, _cfg, _absorb, *, enabled):
            self.assertTrue(enabled)
            out = deepcopy(parent_action)
            out["market"] = []  # illegal shape change for canonical E11
            return out, {"enabled": True, "changed": True, "deferred": ["MILK"]}

        wrapped = h10.wrap_r04_agent(
            parent, absorb_one, enabled=True, state_getter=lambda _obs: state,
            e11_apply=bad_apply,
        )
        out = wrapped(obs(5, 10), CFG)
        self.assertIs(out, produced[0])
        self.assertEqual(state.sale_window_debts, {8: {"MILK": 1}})
        self.assertEqual(
            wrapped.telemetry["last_by_player"][0]["reason"],
            "FAIL_CLOSED_NON_ROW_STABLE_E11",
        )

    def test_fractional_absorption_keeps_exact_parent_action(self):
        state = SimpleNamespace(sale_window_debts={})
        produced = []
        def parent(_observation, _configuration=None):
            item = action(4)
            produced.append(item)
            return item
        wrapped = h10.wrap_r04_agent(
            parent, lambda *_args: 1.5, enabled=True,
            state_getter=lambda _obs: state,
        )
        wrapped(obs(5, 40), CFG)
        out = wrapped(obs(6, 10), CFG)
        self.assertIs(out, produced[1])
        self.assertEqual(
            wrapped.telemetry["last_by_player"][0]["reason"],
            "NO_OP_NONINTEGER_OR_NEGATIVE_ABSORPTION",
        )

    def test_price_history_is_isolated_per_player(self):
        states = {
            0: SimpleNamespace(sale_window_debts={}),
            1: SimpleNamespace(sale_window_debts={}),
        }
        wrapped = h10.wrap_r04_agent(
            lambda _obs, _cfg=None: action(4), absorb_one, enabled=True,
            state_getter=lambda observation: states[int(observation["player"])],
        )
        wrapped(obs(5, 40, player=0), CFG)
        p1 = wrapped(obs(5, 10, player=1), CFG)
        p0 = wrapped(obs(6, 10, player=0), CFG)
        self.assertEqual(p1["market"], [["SELL", "MILK", 4]])
        self.assertEqual(p0["market"], [[]])

    def test_step_rewind_resets_player_price_history(self):
        state = SimpleNamespace(sale_window_debts={})
        wrapped = h10.wrap_r04_agent(
            lambda _obs, _cfg=None: action(4), absorb_one, enabled=True,
            state_getter=lambda _obs: state,
        )
        wrapped(obs(5, 40), CFG)
        out = wrapped(obs(4, 10), CFG)  # new/reset episode for same player
        self.assertEqual(out["market"], [["SELL", "MILK", 4]])
        self.assertEqual(wrapped.telemetry["last_by_player"][0]["reason"], "NO_OP_FLAT_MARKET")

    def test_worker_actions_survive_real_e11_deferral(self):
        state = SimpleNamespace(sale_window_debts={})
        wrapped = h10.wrap_r04_agent(
            lambda _obs, _cfg=None: action(4), absorb_one, enabled=True,
            state_getter=lambda _obs: state,
        )
        wrapped(obs(5, 40), CFG)
        out = wrapped(obs(6, 10), CFG)
        self.assertEqual(out["farmer"], ["PASS"])
        self.assertEqual(out["hands"], [["PASS"]])


if __name__ == "__main__":
    unittest.main(verbosity=2)
