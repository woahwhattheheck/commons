# SPDX-License-Identifier: Apache-2.0
"""Focused current-ABI regression contract for V3.1 row-shed semantics."""
from __future__ import annotations

import copy
import importlib.util
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parent
LAB = HERE.parents[4]
if str(LAB) not in sys.path:
    sys.path.insert(0, str(LAB))

_spec = importlib.util.spec_from_file_location("v4_row_shed_sell_order", HERE / "row_shed_sell_order.py")
row_shed = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(row_shed)

OBS = {"market": {"inventory": {"WOOL": 10000, "MILK": 10000, "EGG": 10000}}}


def action(rows):
    return {"farmer": ["PASS"], "hands": [], "market": copy.deepcopy(rows)}


class RowShedSellOrderTests(unittest.TestCase):
    def test_official_price_shape_uses_fillable_units(self):
        raw = action([["SELL", "WOOL", 1000], ["SELL", "MILK", 6], ["HIRE"]])
        got = row_shed.RowShedSellOrder().transform(
            OBS, {}, raw, post_unit_shed={"WOOL": 1, "MILK": 6})
        self.assertEqual(got["market"], [
            ["SELL", "MILK", 6], ["SELL", "WOOL", 1000], ["HIRE"]])

    def test_raw_slots_falsey_barrier_and_tail_are_preserved(self):
        raw = action([["SELL", "WOOL", 1000], [], ["SELL", "MILK", 6], ["HIRE"]])
        got = row_shed.RowShedSellOrder().transform(
            OBS, {}, raw, post_unit_shed={"WOOL": 1})
        self.assertEqual(got, raw)

    def test_reorder_never_changes_rows_or_input(self):
        rows = [["SELL", "WOOL", 1000], ["SELL", "MILK", 6],
                ["SELL", "EGG", 3], ["HIRE"]]
        raw = action(rows)
        snapshot = copy.deepcopy(raw)
        got = row_shed.RowShedSellOrder().transform(
            OBS, {}, raw, post_unit_shed={"WOOL": 0, "MILK": 6, "EGG": 3})
        self.assertEqual(sorted(map(tuple, got["market"][:3])), sorted(map(tuple, rows[:3])))
        self.assertEqual(got["market"][3:], rows[3:])
        self.assertEqual(raw, snapshot)

    def test_incomplete_projection_fails_closed(self):
        raw = action([["SELL", "WOOL", 1000], ["SELL", "MILK", 6], ["HIRE"]])
        got = row_shed.RowShedSellOrder().transform(
            OBS, {}, raw, post_unit_shed={"MILK": 6})
        self.assertEqual(got, raw)

    def test_projection_poison_fails_closed(self):
        raw = action([["SELL", "WOOL", 1000], ["SELL", "MILK", 6], ["HIRE"]])
        for bad in (True, 1.0, "1", -1):
            with self.subTest(bad=bad):
                got = row_shed.RowShedSellOrder().transform(
                    OBS, {}, raw, post_unit_shed={"WOOL": bad, "MILK": 6})
                self.assertEqual(got, raw)

    def test_quantity_poison_fails_closed(self):
        for bad in (True, 6.0, "6", -1):
            with self.subTest(bad=bad):
                raw = action([["SELL", "WOOL", bad], ["SELL", "MILK", 6], ["HIRE"]])
                got = row_shed.RowShedSellOrder().transform(
                    OBS, {}, raw, post_unit_shed={"WOOL": 1, "MILK": 6})
                self.assertEqual(got, raw)

    def test_truthy_malformed_row_anywhere_fails_closed(self):
        raw = action([["SELL", "WOOL", 1000], ["SELL", "MILK", 6], 1])
        got = row_shed.RowShedSellOrder().transform(
            OBS, {}, raw, post_unit_shed={"WOOL": 1, "MILK": 6})
        self.assertEqual(got, raw)

    def test_equal_scores_are_stable(self):
        def flat_price(_item, _level, _params):
            return 10
        raw = action([["SELL", "WOOL", 2], ["SELL", "MILK", 3], ["HIRE"]])
        got = row_shed.RowShedSellOrder(flat_price).transform(
            OBS, {}, raw, post_unit_shed={"WOOL": 2, "MILK": 3})
        self.assertEqual(got, raw)

    def test_malformed_envelope_returns_explicit_fallback(self):
        selected = action([["SELL", "WOOL", 1000], ["SELL", "MILK", 6]])
        fallback = action([["HIRE"]])
        got = row_shed.RowShedSellOrder().transform(
            OBS, "bad", selected,
            post_unit_shed={"WOOL": 1, "MILK": 6}, fallback_action=fallback)
        self.assertEqual(got, fallback)

    def test_missing_projection_is_parent_identity(self):
        raw = action([["SELL", "WOOL", 1000], ["SELL", "MILK", 6]])
        got = row_shed.RowShedSellOrder().transform(OBS, {}, raw)
        self.assertEqual(got, raw)


if __name__ == "__main__":
    unittest.main()
