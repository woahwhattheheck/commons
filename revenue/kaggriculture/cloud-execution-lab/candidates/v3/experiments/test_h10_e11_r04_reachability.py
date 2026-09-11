# SPDX-License-Identifier: Apache-2.0
"""Focused checks for H10 E11 reachability + R04 sale-accounting atomicity."""
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


def state(**kwargs):
    values = {
        "sale_window_debts": {},
        "advanced_sales": {},
        "sale_due_step": -1,
    }
    values.update(kwargs)
    return SimpleNamespace(**values)


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
        st = state()
        parent_actions = []
        def parent(_observation, _configuration=None):
            item = action(4)
            parent_actions.append(item)
            return item
        wrapped = h10.wrap_r04_agent(
            parent, absorb_one, enabled=True, state_getter=lambda _obs: st,
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
        st = state(sale_window_debts={8: {"MILK": 2}, 9: {"WOOL": 1}})
        def parent(observation, _configuration=None):
            if observation["step"] == 6:
                st.sale_window_debts = {
                    8: {"MILK": 5},
                    9: {"WOOL": 1, "MILK": 2},
                }
            return action(5)

        wrapped = h10.wrap_r04_agent(
            parent, absorb_one, enabled=True, state_getter=lambda _obs: st,
        )
        wrapped(obs(5, 40), CFG)
        out = wrapped(obs(6, 10), CFG)
        self.assertEqual(out["market"], [[]])
        self.assertEqual(st.sale_window_debts, {8: {"MILK": 2}, 9: {"WOOL": 1}})
        report = wrapped.telemetry["last_by_player"][0]
        self.assertEqual(report["new_debt_qty"]["MILK"], 5)
        self.assertEqual(report["refunded_new_debt"]["MILK"], 5)

    def test_native_advance_is_refunded_and_next_turn_sale_is_not_phantom_subtracted(self):
        st = state()
        produced = []
        def parent(observation, _configuration=None):
            step = int(observation["step"])
            if step == 6:
                st.advanced_sales = {"MILK": 4}
                st.sale_due_step = 7
                item = action(4)
            elif step == 7:
                quantity = 4
                if st.sale_due_step == 7:
                    quantity -= min(quantity, int(st.advanced_sales.get("MILK", 0)))
                st.advanced_sales = {}
                st.sale_due_step = -1
                item = action(quantity)
            else:
                item = action(4)
            produced.append(item)
            return item

        wrapped = h10.wrap_r04_agent(
            parent, absorb_one, enabled=True, state_getter=lambda _obs: st,
        )
        wrapped(obs(5, 40), CFG)
        deferred = wrapped(obs(6, 10), CFG)
        self.assertEqual(deferred["market"], [[]])
        self.assertEqual(st.advanced_sales, {})
        self.assertEqual(st.sale_due_step, -1)
        report = wrapped.telemetry["last_by_player"][0]
        self.assertEqual(report["new_native_advance_qty"], {"MILK": 4})
        self.assertEqual(report["refunded_new_native_advance"], {"MILK": 4})

        next_turn = wrapped(obs(7, 40), CFG)
        self.assertEqual(next_turn["market"], [["SELL", "MILK", 4]])
        self.assertEqual(produced[-1]["market"], [["SELL", "MILK", 4]])

    def test_debt_consumed_at_current_step_is_not_recreated(self):
        st = state(sale_window_debts={6: {"MILK": 2}})
        def parent(observation, _configuration=None):
            if observation["step"] == 6:
                st.sale_window_debts = {}
            return action(3)

        wrapped = h10.wrap_r04_agent(
            parent, absorb_one, enabled=True, state_getter=lambda _obs: st,
        )
        wrapped(obs(5, 40), CFG)
        out = wrapped(obs(6, 10), CFG)
        self.assertEqual(out["market"], [[]])
        self.assertEqual(st.sale_window_debts, {})
        self.assertEqual(wrapped.telemetry["last_by_player"][0]["refunded_new_debt"], {})

    def test_existing_future_debt_is_untouched_when_parent_books_nothing(self):
        st = state(sale_window_debts={8: {"MILK": 2}})
        wrapped = h10.wrap_r04_agent(
            lambda _obs, _cfg=None: action(3), absorb_one,
            enabled=True, state_getter=lambda _obs: st,
        )
        wrapped(obs(5, 40), CFG)
        out = wrapped(obs(6, 10), CFG)
        self.assertEqual(out["market"], [[]])
        self.assertEqual(st.sale_window_debts, {8: {"MILK": 2}})

    def test_unknown_predecessor_accounting_fails_closed_without_refund(self):
        st = state(sale_window_debts={8: {"MILK": 2}})
        calls = {"n": 0}
        produced = []
        def getter(_observation):
            calls["n"] += 1
            if calls["n"] == 3:
                raise RuntimeError("pre-state unavailable")
            return st
        def parent(_observation, _configuration=None):
            item = action(4)
            produced.append(item)
            return item

        wrapped = h10.wrap_r04_agent(
            parent, absorb_one, enabled=True, state_getter=getter,
        )
        wrapped(obs(5, 40), CFG)
        out = wrapped(obs(6, 10), CFG)
        self.assertIs(out, produced[1])
        self.assertEqual(st.sale_window_debts, {8: {"MILK": 2}})
        self.assertEqual(
            wrapped.telemetry["last_by_player"][0]["reason"],
            "FAIL_CLOSED_UNKNOWN_PREDECESSOR_SALE_ACCOUNTING",
        )

    def test_unknown_predecessor_native_accounting_fails_closed_without_refund(self):
        st = state()
        calls = {"n": 0}
        produced = []
        def getter(_observation):
            calls["n"] += 1
            if calls["n"] == 3:
                raise RuntimeError("pre-state unavailable")
            return st
        def parent(observation, _configuration=None):
            item = action(4)
            produced.append(item)
            if int(observation["step"]) == 6:
                st.advanced_sales = {"MILK": 2}
                st.sale_due_step = 7
            return item

        wrapped = h10.wrap_r04_agent(
            parent, absorb_one, enabled=True, state_getter=getter,
        )
        wrapped(obs(5, 40), CFG)
        out = wrapped(obs(6, 10), CFG)
        self.assertIs(out, produced[1])
        self.assertEqual(st.advanced_sales, {"MILK": 2})
        self.assertEqual(st.sale_due_step, 7)
        self.assertEqual(
            wrapped.telemetry["last_by_player"][0]["reason"],
            "FAIL_CLOSED_UNKNOWN_PREDECESSOR_SALE_ACCOUNTING",
        )

    def test_booked_quantity_larger_than_removed_sell_fails_closed(self):
        st = state()
        produced = []
        def parent(observation, _configuration=None):
            item = action(5)
            produced.append(item)
            if observation["step"] == 6:
                st.sale_window_debts = {8: {"MILK": 6}}
            return item

        wrapped = h10.wrap_r04_agent(
            parent, absorb_one, enabled=True, state_getter=lambda _obs: st,
        )
        wrapped(obs(5, 40), CFG)
        out = wrapped(obs(6, 10), CFG)
        self.assertIs(out, produced[1])
        self.assertEqual(out["market"], [["SELL", "MILK", 5]])
        self.assertEqual(st.sale_window_debts, {8: {"MILK": 6}})
        self.assertEqual(
            wrapped.telemetry["last_by_player"][0]["reason"],
            "FAIL_CLOSED_BOOKED_QTY_EXCEEDS_DEFERRED_SELL",
        )

    def test_combined_native_and_e184_overbook_fails_closed(self):
        st = state()
        produced = []
        def parent(observation, _configuration=None):
            item = action(5)
            produced.append(item)
            if int(observation["step"]) == 6:
                st.advanced_sales = {"MILK": 3}
                st.sale_due_step = 7
                st.sale_window_debts = {8: {"MILK": 3}}
            return item

        wrapped = h10.wrap_r04_agent(
            parent, absorb_one, enabled=True, state_getter=lambda _obs: st,
        )
        wrapped(obs(5, 40), CFG)
        out = wrapped(obs(6, 10), CFG)
        self.assertIs(out, produced[1])
        self.assertEqual(st.advanced_sales, {"MILK": 3})
        self.assertEqual(st.sale_due_step, 7)
        self.assertEqual(st.sale_window_debts, {8: {"MILK": 3}})
        report = wrapped.telemetry["last_by_player"][0]
        self.assertEqual(report["reason"], "FAIL_CLOSED_BOOKED_QTY_EXCEEDS_DEFERRED_SELL")
        self.assertEqual(report["booked_sale_qty"], {"MILK": 6})
        self.assertEqual(report["removed_sell_qty"], {"MILK": 5})

    def test_non_row_stable_e11_result_fails_closed_without_accounting_mutation(self):
        st = state(sale_window_debts={8: {"MILK": 1}})
        produced = []
        def parent(_observation, _configuration=None):
            item = action(5)
            produced.append(item)
            return item
        def bad_apply(_obs, parent_action, _history, _cfg, _absorb, *, enabled):
            self.assertTrue(enabled)
            out = deepcopy(parent_action)
            out["market"] = []
            return out, {"enabled": True, "changed": True, "deferred": ["MILK"]}

        wrapped = h10.wrap_r04_agent(
            parent, absorb_one, enabled=True, state_getter=lambda _obs: st,
            e11_apply=bad_apply,
        )
        out = wrapped(obs(5, 10), CFG)
        self.assertIs(out, produced[0])
        self.assertEqual(st.sale_window_debts, {8: {"MILK": 1}})
        self.assertEqual(
            wrapped.telemetry["last_by_player"][0]["reason"],
            "FAIL_CLOSED_NON_ROW_STABLE_E11",
        )

    def test_fractional_absorption_keeps_exact_parent_action(self):
        st = state()
        produced = []
        def parent(_observation, _configuration=None):
            item = action(4)
            produced.append(item)
            return item
        wrapped = h10.wrap_r04_agent(
            parent, lambda *_args: 1.5, enabled=True,
            state_getter=lambda _obs: st,
        )
        wrapped(obs(5, 40), CFG)
        out = wrapped(obs(6, 10), CFG)
        self.assertIs(out, produced[1])
        self.assertEqual(
            wrapped.telemetry["last_by_player"][0]["reason"],
            "NO_OP_NONINTEGER_OR_NEGATIVE_ABSORPTION",
        )

    def test_price_history_is_isolated_per_player(self):
        states = {0: state(), 1: state()}
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
        st = state()
        wrapped = h10.wrap_r04_agent(
            lambda _obs, _cfg=None: action(4), absorb_one, enabled=True,
            state_getter=lambda _obs: st,
        )
        wrapped(obs(5, 40), CFG)
        out = wrapped(obs(4, 10), CFG)
        self.assertEqual(out["market"], [["SELL", "MILK", 4]])
        self.assertEqual(wrapped.telemetry["last_by_player"][0]["reason"], "NO_OP_FLAT_MARKET")

    def test_worker_actions_survive_real_e11_deferral(self):
        st = state()
        wrapped = h10.wrap_r04_agent(
            lambda _obs, _cfg=None: action(4), absorb_one, enabled=True,
            state_getter=lambda _obs: st,
        )
        wrapped(obs(5, 40), CFG)
        out = wrapped(obs(6, 10), CFG)
        self.assertEqual(out["farmer"], ["PASS"])
        self.assertEqual(out["hands"], [["PASS"]])


if __name__ == "__main__":
    unittest.main(verbosity=2)
