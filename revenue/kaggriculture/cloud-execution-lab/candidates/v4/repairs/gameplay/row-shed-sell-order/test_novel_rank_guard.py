# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import copy
import unittest

from novel_rank_guard import NovelRankGuard


def action(rows, farmer=None):
    return {
        "farmer": ["PASS"] if farmer is None else farmer,
        "hands": [],
        "market": copy.deepcopy(rows),
    }


class NovelRankGuardTests(unittest.TestCase):
    def test_duplicate_pressure_rank_returns_parent_identity(self):
        base = action([["SELL", "WOOL", 5], ["SELL", "MILK", 4], ["HIRE"]])
        ranked = action([["SELL", "MILK", 4], ["SELL", "WOOL", 5], ["HIRE"]])
        guard = NovelRankGuard()
        self.assertEqual(guard.choose(base, ranked, ranked), base)
        self.assertEqual(guard.diagnostics["reason"], "redundant_with_pressure_rank")

    def test_distinct_rank_keeps_row_shed_candidate(self):
        base = action([
            ["SELL", "WOOL", 5], ["SELL", "MILK", 4],
            ["SELL", "EGG", 3], ["HIRE"],
        ])
        row = action([
            ["SELL", "MILK", 4], ["SELL", "WOOL", 5],
            ["SELL", "EGG", 3], ["HIRE"],
        ])
        pressure = action([
            ["SELL", "EGG", 3], ["SELL", "WOOL", 5],
            ["SELL", "MILK", 4], ["HIRE"],
        ])
        guard = NovelRankGuard()
        self.assertEqual(guard.choose(base, row, pressure), row)
        self.assertEqual(guard.diagnostics["status"], "applied")
        self.assertEqual(guard.diagnostics["reason"], "novel_vs_pressure_rank")

    def test_pressure_identity_still_proves_row_rank_is_novel(self):
        base = action([["SELL", "WOOL", 5], ["SELL", "MILK", 4], ["HIRE"]])
        row = action([["SELL", "MILK", 4], ["SELL", "WOOL", 5], ["HIRE"]])
        self.assertEqual(NovelRankGuard().choose(base, row, base), row)

    def test_missing_pressure_fails_closed(self):
        base = action([["SELL", "WOOL", 5], ["SELL", "MILK", 4]])
        row = action([["SELL", "MILK", 4], ["SELL", "WOOL", 5]])
        guard = NovelRankGuard()
        self.assertEqual(guard.choose(base, row, None), base)
        self.assertIn("missing", guard.diagnostics["reason"])

    def test_pressure_suffix_mutation_fails_closed(self):
        base = action([["SELL", "WOOL", 5], ["SELL", "MILK", 4], ["HIRE"]])
        row = action([["SELL", "MILK", 4], ["SELL", "WOOL", 5], ["HIRE"]])
        pressure = action([
            ["SELL", "WOOL", 5], ["SELL", "MILK", 4], ["BUY_SEED", "WHEAT", 1],
        ])
        self.assertEqual(NovelRankGuard().choose(base, row, pressure), base)

    def test_pressure_non_market_mutation_fails_closed(self):
        base = action([["SELL", "WOOL", 5], ["SELL", "MILK", 4]])
        row = action([["SELL", "MILK", 4], ["SELL", "WOOL", 5]])
        pressure = action(
            [["SELL", "WOOL", 5], ["SELL", "MILK", 4]], farmer=["LEFT"]
        )
        self.assertEqual(NovelRankGuard().choose(base, row, pressure), base)

    def test_candidate_multiset_change_fails_closed(self):
        base = action([["SELL", "WOOL", 5], ["SELL", "MILK", 4]])
        row = action([["SELL", "MILK", 5], ["SELL", "WOOL", 5]])
        self.assertEqual(NovelRankGuard().choose(base, row, copy.deepcopy(base)), base)

    def test_duplicate_rows_are_compared_with_multiplicity(self):
        base = action([
            ["SELL", "WOOL", 5], ["SELL", "WOOL", 5],
            ["SELL", "MILK", 4], ["HIRE"],
        ])
        row = action([
            ["SELL", "MILK", 4], ["SELL", "WOOL", 5],
            ["SELL", "WOOL", 5], ["HIRE"],
        ])
        pressure = action([
            ["SELL", "WOOL", 5], ["SELL", "MILK", 4],
            ["SELL", "WOOL", 5], ["HIRE"],
        ])
        self.assertEqual(NovelRankGuard().choose(base, row, pressure), row)

    def test_falsey_barrier_is_immutable(self):
        base = action([["SELL", "WOOL", 5], [], ["SELL", "MILK", 4]])
        guard = NovelRankGuard()
        self.assertEqual(guard.choose(base, copy.deepcopy(base), copy.deepcopy(base)), base)
        self.assertEqual(guard.diagnostics["reason"], "leading_sell_block_lt_2")

    def test_inputs_are_never_mutated(self):
        base = action([["SELL", "WOOL", 5], ["SELL", "MILK", 4], ["HIRE"]])
        row = action([["SELL", "MILK", 4], ["SELL", "WOOL", 5], ["HIRE"]])
        pressure = copy.deepcopy(base)
        snapshots = tuple(copy.deepcopy(value) for value in (base, row, pressure))
        NovelRankGuard().choose(base, row, pressure)
        self.assertEqual((base, row, pressure), snapshots)

    def test_truthy_malformed_parent_fails_closed(self):
        base = action([["SELL", "WOOL", 5], ["SELL", "MILK", 4]])
        base["market"].append(1)
        self.assertEqual(
            NovelRankGuard().choose(base, copy.deepcopy(base), copy.deepcopy(base)), base
        )


if __name__ == "__main__":
    unittest.main()
