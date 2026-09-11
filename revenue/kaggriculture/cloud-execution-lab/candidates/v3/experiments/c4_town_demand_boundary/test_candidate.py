#!/usr/bin/env python3
from __future__ import annotations

import copy
from pathlib import Path
import sys
import unittest
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import candidate as c4  # noqa: E402


def observation(step=300, shops=None):
    return {
        "step": step,
        "player": 0,
        "town": {"unlocked_shops": list(shops or [])},
        "market": {"inventory": {}},
    }


def action(rows=None):
    return {"farmer": ["PASS"], "hands": [], "market": copy.deepcopy(rows or [])}


def state(debts=None):
    return SimpleNamespace(sale_window_debts=copy.deepcopy(debts or {}))


class C4TownDemandBoundaryTests(unittest.TestCase):
    def setUp(self):
        c4.telemetry.clear()
        self.standard = {"townShopSellInterval": 4, "townCenterSellInterval": 24}

    def rollback(self, act, obs, st, before, *, enabled=True, config=None):
        return c4.rollback_cross_tick_advances(
            act, obs, st, before, self.standard if config is None else config, enabled=enabled
        )

    def test_disabled_is_exact_identity_and_state_identity(self):
        act = action([["SELL", "CARROT", 3]])
        st = state({301: {"CARROT": 3}})
        original_debts = st.sale_window_debts
        out = self.rollback(act, observation(300, ["PET_CAFE"]), st, {}, enabled=False)
        self.assertIs(out, act)
        self.assertIs(st.sale_window_debts, original_debts)

    def test_due_next_step_is_rolled_back_across_shop_tick(self):
        act = action([["BUY_SEED", "WHEAT", 1], ["SELL", "CARROT", 3]])
        st = state({301: {"CARROT": 3}})
        out = self.rollback(act, observation(300, ["PET_CAFE"]), st, {})
        self.assertEqual(out["market"], [["BUY_SEED", "WHEAT", 1], []])
        self.assertEqual(st.sale_window_debts, {})
        self.assertEqual(c4.telemetry["units_rolled_back"], 3)
        self.assertEqual(act["market"][1], ["SELL", "CARROT", 3])

    def test_tick_between_current_and_due_is_detected(self):
        act = action([["SELL", "CARROT", 2]])
        st = state({301: {"CARROT": 2}})
        out = self.rollback(act, observation(299, ["PET_CAFE"]), st, {})
        self.assertEqual(out["market"], [[]])
        self.assertEqual(st.sale_window_debts, {})

    def test_no_intervening_tick_keeps_parent_identity(self):
        act = action([["SELL", "CARROT", 2]])
        st = state({302: {"CARROT": 2}})
        out = self.rollback(act, observation(301, ["PET_CAFE"]), st, {})
        self.assertIs(out, act)
        self.assertEqual(st.sale_window_debts, {302: {"CARROT": 2}})

    def test_irrelevant_shop_keeps_item(self):
        act = action([["SELL", "CARROT", 2]])
        st = state({301: {"CARROT": 2}})
        out = self.rollback(act, observation(300, ["YARN_STORE"]), st, {})
        self.assertIs(out, act)

    def test_town_center_tick_covers_all_products_except_fertilizer(self):
        act = action([["SELL", "MELON", 2]])
        st = state({313: {"MELON": 2}})
        out = self.rollback(act, observation(312, []), st, {})
        self.assertEqual(out["market"], [[]])
        self.assertEqual(st.sale_window_debts, {})
        self.assertNotIn("FERTILIZER", c4.TOWN_CENTER_PRODUCTS)

    def test_only_new_debt_is_rolled_back(self):
        act = action([["SELL", "CARROT", 3]])
        before = {301: {"CARROT": 2}}
        st = state({301: {"CARROT": 5}})
        out = self.rollback(act, observation(300, ["PET_CAFE"]), st, before)
        self.assertEqual(out["market"], [[]])
        self.assertEqual(st.sale_window_debts, {301: {"CARROT": 2}})

    def test_crossing_and_non_crossing_due_cells_share_one_row(self):
        # From 301, due304 does not cross the 304 tick; due305 does.
        act = action([["SELL", "CARROT", 5]])
        st = state({304: {"CARROT": 2}, 305: {"CARROT": 3}})
        out = self.rollback(act, observation(301, ["PET_CAFE"]), st, {})
        self.assertEqual(out["market"], [["SELL", "CARROT", 2]])
        self.assertEqual(st.sale_window_debts, {304: {"CARROT": 2}})
        self.assertEqual(c4.telemetry["units_rolled_back"], 3)

    def test_multiple_products_rollback_independently(self):
        act = action([["SELL", "EGG", 2], ["SELL", "CARROT", 3]])
        st = state({301: {"EGG": 2, "CARROT": 3}})
        out = self.rollback(act, observation(300, ["BAKERY", "PET_CAFE"]), st, {})
        self.assertEqual(out["market"], [[], []])
        self.assertEqual(st.sale_window_debts, {})
        self.assertEqual(c4.telemetry["rows_rolled_back"], 2)

    def test_unknown_shop_fails_closed_without_state_mutation(self):
        act = action([["SELL", "CARROT", 2]])
        st = state({301: {"CARROT": 2}})
        debts = st.sale_window_debts
        out = self.rollback(act, observation(300, ["NOT_A_SHOP"]), st, {})
        self.assertIs(out, act)
        self.assertIs(st.sale_window_debts, debts)

    def test_nonstandard_or_type_loose_clock_fails_closed(self):
        bad_configs = (
            {"townShopSellInterval": 5, "townCenterSellInterval": 24},
            {"townShopSellInterval": 4.0, "townCenterSellInterval": 24},
            {"townShopSellInterval": True, "townCenterSellInterval": 24},
            {"townShopSellInterval": 4, "townCenterSellInterval": "24"},
        )
        for config in bad_configs:
            with self.subTest(config=config):
                act = action([["SELL", "CARROT", 2]])
                st = state({301: {"CARROT": 2}})
                debts = st.sale_window_debts
                out = self.rollback(act, observation(300, ["PET_CAFE"]), st, {}, config=config)
                self.assertIs(out, act)
                self.assertIs(st.sale_window_debts, debts)

    def test_bool_or_negative_debt_fails_closed(self):
        for bad in (True, -1):
            with self.subTest(bad=bad):
                act = action([["SELL", "CARROT", 2]])
                st = state({301: {"CARROT": bad}})
                debts = st.sale_window_debts
                out = self.rollback(act, observation(300, ["PET_CAFE"]), st, {})
                self.assertIs(out, act)
                self.assertIs(st.sale_window_debts, debts)

    def test_ambiguous_sell_rows_fail_closed_without_debt_rewrite(self):
        act = action([["SELL", "CARROT", 1], ["SELL", "CARROT", 1]])
        st = state({301: {"CARROT": 2}})
        debts = st.sale_window_debts
        out = self.rollback(act, observation(300, ["PET_CAFE"]), st, {})
        self.assertIs(out, act)
        self.assertIs(st.sale_window_debts, debts)
        self.assertEqual(c4.telemetry["ambiguous_sell_row"], 1)

    def test_existing_parent_rows_are_unchanged_when_advanced_row_is_reduced(self):
        rows = [["BUY_SEED", "WHEAT", 1], ["SELL", "MILK", 4], ["SELL", "CARROT", 5]]
        act = action(rows)
        # MILK is pre-existing parent sale: its debt did not grow. CARROT grew by 3.
        before = {301: {"MILK": 4}}
        st = state({301: {"MILK": 4, "CARROT": 3}, 302: {"CARROT": 2}})
        out = self.rollback(act, observation(300, ["PET_CAFE"]), st, before)
        self.assertEqual(out["market"][:2], rows[:2])
        self.assertEqual(out["market"][2], [])
        self.assertEqual(st.sale_window_debts, {301: {"MILK": 4}})


if __name__ == "__main__":
    unittest.main()
