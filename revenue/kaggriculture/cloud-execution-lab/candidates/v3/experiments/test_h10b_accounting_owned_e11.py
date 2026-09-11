# SPDX-License-Identifier: Apache-2.0
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
import sys
import unittest

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import h10b_accounting_owned_e11 as h


def state(**kwargs):
    values = {"sale_window_debts": {}, "advanced_sales": {}, "sale_due_step": -1}
    values.update(kwargs)
    return SimpleNamespace(**values)


def obs(step=10, player=0):
    return {"step": step, "player": player, "market": {"prices": {"MILK": 10}}, "town": {"unlocked_shops": []}}


def action(rows):
    return {"farmer": ["PASS"], "hands": [["PASS"]], "market": deepcopy(rows)}


def absorption(*_args):
    return 1


def fake_defer(items):
    def apply(_obs, parent_action, _history, _cfg, _absorption, *, enabled):
        return parent_action, {"enabled": enabled, "changed": True, "deferred": list(items), "reason": "TEST"}
    return apply


class H10BTests(unittest.TestCase):
    def test_disabled_exact_identity_and_no_state_read(self):
        st = state(); parent_action = action([["SELL", "MILK", 3]])
        def forbidden(_obs):
            raise AssertionError("disabled path must not read state")
        wrapped = h.wrap_r04_agent(lambda *_: parent_action, absorption, enabled=False, state_getter=forbidden)
        self.assertIs(wrapped(obs(), {}), parent_action)

    def test_inherited_sell_without_booking_is_untouched(self):
        st = state(); parent_action = action([["SELL", "MILK", 99]])
        wrapped = h.wrap_r04_agent(lambda *_: parent_action, absorption, enabled=True,
                                   state_getter=lambda _obs: st, e11_apply=fake_defer(["MILK"]))
        self.assertIs(wrapped(obs(), {}), parent_action)
        self.assertEqual(st.sale_window_debts, {})

    def test_only_unique_exact_accounting_owned_row_is_blank(self):
        st = state(); parent_action = action([["SELL", "MILK", 99], ["SELL", "MILK", 3]])
        def parent(*_):
            st.sale_window_debts = {12: {"MILK": 3}}
            return parent_action
        wrapped = h.wrap_r04_agent(parent, absorption, enabled=True,
                                   state_getter=lambda _obs: st, e11_apply=fake_defer(["MILK"]))
        out = wrapped(obs(10), {})
        self.assertEqual(out["market"], [["SELL", "MILK", 99], []])
        self.assertEqual(st.sale_window_debts, {})

    def test_ambiguous_exact_rows_fail_open(self):
        st = state(); parent_action = action([["SELL", "MILK", 3], ["SELL", "MILK", 3]])
        def parent(*_):
            st.sale_window_debts = {12: {"MILK": 3}}
            return parent_action
        wrapped = h.wrap_r04_agent(parent, absorption, enabled=True,
                                   state_getter=lambda _obs: st, e11_apply=fake_defer(["MILK"]))
        self.assertIs(wrapped(obs(10), {}), parent_action)
        self.assertEqual(st.sale_window_debts, {12: {"MILK": 3}})

    def test_no_exact_row_fail_open(self):
        st = state(); parent_action = action([["SELL", "MILK", 4]])
        def parent(*_):
            st.sale_window_debts = {12: {"MILK": 3}}
            return parent_action
        wrapped = h.wrap_r04_agent(parent, absorption, enabled=True,
                                   state_getter=lambda _obs: st, e11_apply=fake_defer(["MILK"]))
        self.assertIs(wrapped(obs(10), {}), parent_action)
        self.assertEqual(st.sale_window_debts, {12: {"MILK": 3}})

    def test_unknown_predecessor_accounting_fails_open(self):
        st = state(); parent_action = action([["SELL", "MILK", 3]]); calls = {"n": 0}
        def getter(_obs):
            calls["n"] += 1
            if calls["n"] == 1:
                raise RuntimeError("no pre-state")
            return st
        def parent(*_):
            st.sale_window_debts = {12: {"MILK": 3}}
            return parent_action
        wrapped = h.wrap_r04_agent(parent, absorption, enabled=True,
                                   state_getter=getter, e11_apply=fake_defer(["MILK"]))
        self.assertIs(wrapped(obs(10), {}), parent_action)
        self.assertEqual(st.sale_window_debts, {12: {"MILK": 3}})

    def test_combined_native_and_e184_exact_booking_refunds_atomically(self):
        st = state(); parent_action = action([["SELL", "MILK", 6]])
        def parent(*_):
            st.advanced_sales = {"MILK": 3}; st.sale_due_step = 11
            st.sale_window_debts = {12: {"MILK": 3}}
            return parent_action
        wrapped = h.wrap_r04_agent(parent, absorption, enabled=True,
                                   state_getter=lambda _obs: st, e11_apply=fake_defer(["MILK"]))
        out = wrapped(obs(10), {})
        self.assertEqual(out["market"], [[]])
        self.assertEqual(st.advanced_sales, {})
        self.assertEqual(st.sale_due_step, -1)
        self.assertEqual(st.sale_window_debts, {})

    def test_unrelated_accounting_survives(self):
        st = state(); parent_action = action([["SELL", "MILK", 3], ["SELL", "FERTILIZER", 5]])
        def parent(*_):
            st.sale_window_debts = {12: {"MILK": 3, "FERTILIZER": 5}}
            return parent_action
        wrapped = h.wrap_r04_agent(parent, absorption, enabled=True,
                                   state_getter=lambda _obs: st, e11_apply=fake_defer(["MILK"]))
        out = wrapped(obs(10), {})
        self.assertEqual(out["market"], [[], ["SELL", "FERTILIZER", 5]])
        self.assertEqual(st.sale_window_debts, {12: {"FERTILIZER": 5}})


if __name__ == "__main__":
    unittest.main(verbosity=2)
