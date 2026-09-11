# SPDX-License-Identifier: Apache-2.0
"""Focused checks for the H8 evening-flush internal row-arbitration experiment."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parent
OVERLAY = HERE.parent / "overlay"
for path in (HERE, OVERLAY):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import h8_flush_row_order as h8  # noqa: E402


def obs(inventory=None):
    return {"market": {"inventory": dict(inventory or {})}}


def action(market):
    return {
        "farmer": ["PASS"],
        "hands": [["PASS"]],
        "market": deepcopy(market),
    }


class H8FlushRowOrderTests(unittest.TestCase):
    def test_disabled_is_exact_post_action_identity(self):
        pre = action([["SELL", "FERTILIZER", 3]])
        post = action([["SELL", "WOOL", 2], ["SELL", "MILK", 3], ["SELL", "FERTILIZER", 3]])
        out, report = h8.apply_flush_internal_row_order(obs(), pre, post, enabled=False)
        self.assertIs(out, post)
        self.assertFalse(report["changed"])
        self.assertEqual(report["reason"], "OFF")

    def test_custom_market_params_fail_closed_like_r04_row_order(self):
        pre = action([])
        post = action([["SELL", "WOOL", 2], ["SELL", "MILK", 3]])
        out, report = h8.apply_flush_internal_row_order(
            obs(), pre, post, {"marketParams": {"custom": True}}, enabled=True,
            sorter=lambda rows, inventory: list(reversed(rows)),
        )
        self.assertIs(out, post)
        self.assertEqual(report["reason"], "CUSTOM_MARKET_PARAMS")

    def test_reorders_only_demonstrable_flush_prefix(self):
        suffix = [["SELL", "FERTILIZER", 3], ["BUY_PRODUCT", "WHEAT", 1]]
        prefix = [["SELL", "WOOL", 2], ["SELL", "MILK", 3]]
        pre = action(suffix)
        post = action(prefix + suffix)

        def reverse(rows, inventory):
            self.assertEqual(inventory, {"WOOL": 10000})
            return list(reversed(rows))

        out, report = h8.apply_flush_internal_row_order(
            obs({"WOOL": 10000}), pre, post, enabled=True, sorter=reverse,
        )
        self.assertEqual(out["market"], list(reversed(prefix)) + suffix)
        self.assertEqual(out["farmer"], post["farmer"])
        self.assertEqual(out["hands"], post["hands"])
        self.assertEqual(report["reason"], "REORDER_FLUSH_PREFIX")
        self.assertTrue(report["changed"])
        self.assertEqual(report["flush_prefix_rows"], 2)

    def test_preexisting_suffix_order_is_never_arbitrated(self):
        suffix = [["SELL", "MILK", 99], ["SELL", "WOOL", 99], ["HIRE"]]
        prefix = [["SELL", "STRAWBERRY", 1], ["SELL", "MELON", 1]]
        pre = action(suffix)
        post = action(prefix + suffix)
        out, _ = h8.apply_flush_internal_row_order(
            obs(), pre, post, enabled=True,
            sorter=lambda rows, inventory: list(reversed(rows)),
        )
        self.assertEqual(out["market"][:2], list(reversed(prefix)))
        self.assertEqual(out["market"][2:], suffix)

    def test_suffix_mismatch_fails_closed(self):
        pre = action([["SELL", "FERTILIZER", 3]])
        post = action([["SELL", "WOOL", 2], ["SELL", "MILK", 3], ["SELL", "FERTILIZER", 4]])
        out, report = h8.apply_flush_internal_row_order(
            obs(), pre, post, enabled=True,
            sorter=lambda rows, inventory: list(reversed(rows)),
        )
        self.assertIs(out, post)
        self.assertEqual(report["reason"], "SUFFIX_MISMATCH")

    def test_non_flush_prefix_fails_closed(self):
        pre = action([])
        post = action([["SELL", "WHEAT", 2], ["SELL", "MILK", 3]])
        out, report = h8.apply_flush_internal_row_order(
            obs(), pre, post, enabled=True,
            sorter=lambda rows, inventory: list(reversed(rows)),
        )
        self.assertIs(out, post)
        self.assertEqual(report["reason"], "NON_FLUSH_PREFIX")

    def test_single_flush_row_is_identity(self):
        pre = action([["HIRE"]])
        post = action([["SELL", "WOOL", 2], ["HIRE"]])
        out, report = h8.apply_flush_internal_row_order(obs(), pre, post, enabled=True)
        self.assertIs(out, post)
        self.assertEqual(report["reason"], "SINGLE_FLUSH_ROW")

    def test_no_inserted_prefix_is_identity(self):
        pre = action([["SELL", "WOOL", 2]])
        post = deepcopy(pre)
        out, report = h8.apply_flush_internal_row_order(obs(), pre, post, enabled=True)
        self.assertIs(out, post)
        self.assertEqual(report["reason"], "NO_FLUSH_PREFIX")

    def test_default_sorter_is_exact_live_r04_order_sells(self):
        # Bind the candidate to the existing R04 competitive metric rather than a copy.
        import r04_full_router as r04
        inventory = {"WOOL": 10000, "MILK": 10000, "STRAWBERRY": 10000, "MELON": 10000}
        prefix = [
            ["SELL", "STRAWBERRY", 17],
            ["SELL", "WOOL", 8],
            ["SELL", "MILK", 5],
            ["SELL", "MELON", 2],
        ]
        pre = action([["SELL", "FERTILIZER", 3]])
        post = action(prefix + pre["market"])
        expected = r04.order_sells(deepcopy(prefix), inventory)
        out, report = h8.apply_flush_internal_row_order(
            obs(inventory), pre, post, enabled=True,
        )
        self.assertEqual(out["market"][:len(prefix)], expected)
        self.assertEqual(out["market"][len(prefix):], pre["market"])
        self.assertEqual(report["changed"], expected != prefix)
        self.assertIn(report["reason"], {"REORDER_FLUSH_PREFIX", "ALREADY_ORDERED"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
