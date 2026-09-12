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
    def test_raw_rank_difference_erased_by_pressure_returns_parent(self):
        """Predecessor killer: different raw ranks can have one final postimage."""
        base = action([
            ["SELL", "WOOL", 5],
            ["SELL", "MILK", 4],
            ["SELL", "EGG", 3],
            ["HIRE"],
        ])
        row = action([
            ["SELL", "MILK", 4],
            ["SELL", "WOOL", 5],
            ["SELL", "EGG", 3],
            ["HIRE"],
        ])
        # Unique downstream pressure scores can deterministically restore both
        # paths to the incumbent order even though the raw row-shed rank differs.
        guard = NovelRankGuard()
        self.assertEqual(guard.choose(base, row, base, copy.deepcopy(base)), base)
        self.assertEqual(guard.diagnostics["reason"], "redundant_after_pressure")
        self.assertTrue(guard.diagnostics["final_pressure_equal"])

    def test_pressure_tie_preserves_row_shed_final_difference(self):
        base = action([["SELL", "WOOL", 5], ["SELL", "MILK", 4], ["HIRE"]])
        row = action([["SELL", "MILK", 4], ["SELL", "WOOL", 5], ["HIRE"]])
        # Equal pressure scores are stable: each path retains its own input order.
        guard = NovelRankGuard()
        self.assertEqual(guard.choose(base, row, base, row), row)
        self.assertEqual(guard.diagnostics["status"], "applied")
        self.assertEqual(guard.diagnostics["reason"], "survives_pressure_postimage")
        self.assertFalse(guard.diagnostics["final_pressure_equal"])

    def test_distinct_pressure_postimages_keep_row_shed_candidate(self):
        base = action([
            ["SELL", "WOOL", 5], ["SELL", "MILK", 4],
            ["SELL", "EGG", 3], ["HIRE"],
        ])
        row = action([
            ["SELL", "MILK", 4], ["SELL", "WOOL", 5],
            ["SELL", "EGG", 3], ["HIRE"],
        ])
        pressure_parent = action([
            ["SELL", "EGG", 3], ["SELL", "WOOL", 5],
            ["SELL", "MILK", 4], ["HIRE"],
        ])
        pressure_row = action([
            ["SELL", "EGG", 3], ["SELL", "MILK", 4],
            ["SELL", "WOOL", 5], ["HIRE"],
        ])
        self.assertEqual(
            NovelRankGuard().choose(base, row, pressure_parent, pressure_row), row
        )

    def test_old_three_argument_rank_evidence_fails_closed(self):
        base = action([["SELL", "WOOL", 5], ["SELL", "MILK", 4]])
        row = action([["SELL", "MILK", 4], ["SELL", "WOOL", 5]])
        guard = NovelRankGuard()
        self.assertEqual(guard.choose(base, row, base), base)
        self.assertIn("both downstream pressure postimages", guard.diagnostics["reason"])

    def test_missing_parent_pressure_fails_closed(self):
        base = action([["SELL", "WOOL", 5], ["SELL", "MILK", 4]])
        row = action([["SELL", "MILK", 4], ["SELL", "WOOL", 5]])
        self.assertEqual(NovelRankGuard().choose(base, row, None, row), base)

    def test_pressure_row_multiset_mutation_fails_closed(self):
        base = action([["SELL", "WOOL", 5], ["SELL", "MILK", 4], ["HIRE"]])
        row = action([["SELL", "MILK", 4], ["SELL", "WOOL", 5], ["HIRE"]])
        bad = action([
            ["SELL", "MILK", 4],
            ["SELL", "WOOL", 5],
            ["BUY_SEED", "WHEAT", 1],
        ])
        guard = NovelRankGuard()
        self.assertEqual(guard.choose(base, row, base, bad), base)
        self.assertIn("multiset", guard.diagnostics["reason"])

    def test_pressure_non_market_mutation_fails_closed(self):
        base = action([["SELL", "WOOL", 5], ["SELL", "MILK", 4]])
        row = action([["SELL", "MILK", 4], ["SELL", "WOOL", 5]])
        bad = action(
            [["SELL", "MILK", 4], ["SELL", "WOOL", 5]], farmer=["LEFT"]
        )
        guard = NovelRankGuard()
        self.assertEqual(guard.choose(base, row, base, bad), base)
        self.assertIn("non-market", guard.diagnostics["reason"])

    def test_row_shed_multiset_change_fails_closed(self):
        base = action([["SELL", "WOOL", 5], ["SELL", "MILK", 4]])
        row = action([["SELL", "MILK", 5], ["SELL", "WOOL", 5]])
        self.assertEqual(NovelRankGuard().choose(base, row, base, row), base)

    def test_duplicate_rows_are_preserved_with_multiplicity(self):
        base = action([
            ["SELL", "WOOL", 5], ["SELL", "WOOL", 5],
            ["SELL", "MILK", 4], ["HIRE"],
        ])
        row = action([
            ["SELL", "MILK", 4], ["SELL", "WOOL", 5],
            ["SELL", "WOOL", 5], ["HIRE"],
        ])
        pressure_parent = action([
            ["SELL", "WOOL", 5], ["SELL", "MILK", 4],
            ["SELL", "WOOL", 5], ["HIRE"],
        ])
        pressure_row = action([
            ["SELL", "MILK", 4], ["SELL", "WOOL", 5],
            ["SELL", "WOOL", 5], ["HIRE"],
        ])
        self.assertEqual(
            NovelRankGuard().choose(base, row, pressure_parent, pressure_row), row
        )

    def test_falsey_barrier_is_immutable(self):
        base = action([["SELL", "WOOL", 5], [], ["SELL", "MILK", 4]])
        guard = NovelRankGuard()
        self.assertEqual(
            guard.choose(base, copy.deepcopy(base), copy.deepcopy(base), copy.deepcopy(base)),
            base,
        )
        self.assertEqual(guard.diagnostics["reason"], "leading_sell_block_lt_2")

    def test_inputs_are_never_mutated(self):
        base = action([["SELL", "WOOL", 5], ["SELL", "MILK", 4], ["HIRE"]])
        row = action([["SELL", "MILK", 4], ["SELL", "WOOL", 5], ["HIRE"]])
        pressure_parent = copy.deepcopy(base)
        pressure_row = copy.deepcopy(row)
        values = (base, row, pressure_parent, pressure_row)
        snapshots = tuple(copy.deepcopy(value) for value in values)
        NovelRankGuard().choose(*values)
        self.assertEqual(values, snapshots)

    def test_truthy_malformed_parent_fails_closed(self):
        base = action([["SELL", "WOOL", 5], ["SELL", "MILK", 4]])
        base["market"].append(1)
        self.assertEqual(
            NovelRankGuard().choose(
                base,
                copy.deepcopy(base),
                copy.deepcopy(base),
                copy.deepcopy(base),
            ),
            base,
        )


if __name__ == "__main__":
    unittest.main()
