#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parent
V3 = HERE.parents[1]
C4 = V3 / "experiments" / "c4_town_demand_boundary"
if str(C4) not in sys.path:
    sys.path.insert(0, str(C4))

import candidate as c4  # noqa: E402
import test_candidate as parent_tests  # noqa: E402


class C4PreDebtRepairTests(unittest.TestCase):
    def setUp(self):
        c4.telemetry.clear()
        self.standard = {"townShopSellInterval": 4, "townCenterSellInterval": 24}

    def rollback(self, act, obs, st, before):
        return c4.rollback_cross_tick_advances(
            act, obs, st, before, self.standard, enabled=True
        )

    def test_malformed_current_due_cannot_hide_behind_valid_new_future_debt(self):
        act = parent_tests.action([["SELL", "CARROT", 3]])
        st = parent_tests.state({301: {"CARROT": 3}})
        debts = st.sale_window_debts
        before = {300: {"MILK": True}}
        out = self.rollback(act, parent_tests.observation(300, ["PET_CAFE"]), st, before)
        self.assertIs(out, act)
        self.assertIs(st.sale_window_debts, debts)
        self.assertEqual(c4.telemetry["malformed"], 1)

    def test_stale_predebt_cannot_hide_behind_valid_new_future_debt(self):
        act = parent_tests.action([["SELL", "CARROT", 3]])
        st = parent_tests.state({301: {"CARROT": 3}})
        debts = st.sale_window_debts
        before = {299: {"MILK": 1}}
        out = self.rollback(act, parent_tests.observation(300, ["PET_CAFE"]), st, before)
        self.assertIs(out, act)
        self.assertIs(st.sale_window_debts, debts)
        self.assertEqual(c4.telemetry["malformed"], 1)

    def test_missing_future_predebt_fails_closed_even_with_new_cross_tick_debt(self):
        act = parent_tests.action([["SELL", "CARROT", 2]])
        st = parent_tests.state({301: {"CARROT": 2}})
        debts = st.sale_window_debts
        before = {302: {"MILK": 1}}
        out = self.rollback(act, parent_tests.observation(300, ["PET_CAFE"]), st, before)
        self.assertIs(out, act)
        self.assertIs(st.sale_window_debts, debts)
        self.assertEqual(c4.telemetry["malformed"], 1)

    def test_valid_current_due_may_disappear_while_new_future_debt_rolls_back(self):
        act = parent_tests.action([["SELL", "CARROT", 2]])
        st = parent_tests.state({301: {"CARROT": 2}})
        before = {300: {"MILK": 1}}
        out = self.rollback(act, parent_tests.observation(300, ["PET_CAFE"]), st, before)
        self.assertEqual(out["market"], [[]])
        self.assertEqual(st.sale_window_debts, {})
        self.assertEqual(c4.telemetry["units_rolled_back"], 2)


if __name__ == "__main__":
    unittest.main()
