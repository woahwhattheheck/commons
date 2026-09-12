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
    def test_raw_rank_difference_erased_by_downstream_pressure_returns_parent(self):
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
        # Existing selected-action economics may leave the two pressure inputs
        # distinct, while unique pressure scores sort both to the same final action.
        guard = NovelRankGuard()
        self.assertEqual(guard.choose(base, row, base, base, row, base), base)
        self.assertEqual(
            guard.diagnostics["reason"], "redundant_after_downstream_pressure"
        )
        self.assertTrue(guard.diagnostics["final_pressure_equal"])

    def test_pressure_tie_preserves_row_shed_final_difference(self):
        base = action([["SELL", "WOOL", 5], ["SELL", "MILK", 4], ["HIRE"]])
        row = action([["SELL", "MILK", 4], ["SELL", "WOOL", 5], ["HIRE"]])
        # Stable equal-pressure ties preserve each pressure input's order.
        guard = NovelRankGuard()
        self.assertEqual(guard.choose(base, row, base, base, row, row), row)
        self.assertEqual(guard.diagnostics["status"], "applied")
        self.assertEqual(guard.diagnostics["reason"], "survives_downstream_pressure")
        self.assertFalse(guard.diagnostics["final_pressure_equal"])

    def test_intervening_sell_economics_can_change_pressure_inputs(self):
        base = action([
            ["SELL", "WOOL", 5], ["SELL", "MILK", 4],
            ["SELL", "EGG", 3], ["HIRE"],
        ])
        row = action([
            ["SELL", "MILK", 4], ["SELL", "WOOL", 5],
            ["SELL", "EGG", 3], ["HIRE"],
        ])
        parent_input = action([
            ["SELL", "WOOL", 4], ["SELL", "MILK", 3],
            ["SELL", "EGG", 2], ["HIRE"],
        ])
        row_input = action([
            ["SELL", "MILK", 3], ["SELL", "WOOL", 4],
            ["SELL", "EGG", 2], ["HIRE"],
        ])
        parent_output = action([
            ["SELL", "EGG", 2], ["SELL", "WOOL", 4],
            ["SELL", "MILK", 3], ["HIRE"],
        ])
        row_output = action([
            ["SELL", "EGG", 2], ["SELL", "MILK", 3],
            ["SELL", "WOOL", 4], ["HIRE"],
        ])
        self.assertEqual(
            NovelRankGuard().choose(
                base, row, parent_input, parent_output, row_input, row_output
            ),
            row,
        )

    def test_incomplete_old_rank_evidence_fails_closed(self):
        base = action([["SELL", "WOOL", 5], ["SELL", "MILK", 4]])
        row = action([["SELL", "MILK", 4], ["SELL", "WOOL", 5]])
        guard = NovelRankGuard()
        self.assertEqual(guard.choose(base, row, base), base)
        self.assertIn("complete downstream pressure", guard.diagnostics["reason"])

    def test_identical_pressure_inputs_with_different_outputs_are_invalid(self):
        base = action([["SELL", "WOOL", 5], ["SELL", "MILK", 4]])
        row = action([["SELL", "MILK", 4], ["SELL", "WOOL", 5]])
        guard = NovelRankGuard()
        self.assertEqual(guard.choose(base, row, base, base, base, row), base)
        self.assertIn("inconsistent postimages", guard.diagnostics["reason"])

    def test_pressure_postimage_multiset_mutation_fails_closed(self):
        base = action([["SELL", "WOOL", 5], ["SELL", "MILK", 4], ["HIRE"]])
        row = action([["SELL", "MILK", 4], ["SELL", "WOOL", 5], ["HIRE"]])
        bad = action([
            ["SELL", "MILK", 4],
            ["SELL", "WOOL", 5],
            ["BUY_SEED", "WHEAT", 1],
        ])
        guard = NovelRankGuard()
        self.assertEqual(guard.choose(base, row, base, base, row, bad), base)
        self.assertIn("multiset", guard.diagnostics["reason"])

    def test_pressure_non_market_mutation_fails_closed(self):
        base = action([["SELL", "WOOL", 5], ["SELL", "MILK", 4]])
        row = action([["SELL", "MILK", 4], ["SELL", "WOOL", 5]])
        bad = action(
            [["SELL", "MILK", 4], ["SELL", "WOOL", 5]], farmer=["LEFT"]
        )
        guard = NovelRankGuard()
        self.assertEqual(guard.choose(base, row, base, base, row, bad), base)
        self.assertIn("non-market", guard.diagnostics["reason"])

    def test_pressure_path_non_market_disagreement_fails_closed(self):
        base = action([["SELL", "WOOL", 5], ["SELL", "MILK", 4]])
        row = action([["SELL", "MILK", 4], ["SELL", "WOOL", 5]])
        row_input = action(row["market"], farmer=["LEFT"])
        guard = NovelRankGuard()
        self.assertEqual(
            guard.choose(base, row, base, base, row_input, row_input), base
        )
        self.assertIn("non-market action surface", guard.diagnostics["reason"])

    def test_row_shed_multiset_change_fails_closed(self):
        base = action([["SELL", "WOOL", 5], ["SELL", "MILK", 4]])
        row = action([["SELL", "MILK", 5], ["SELL", "WOOL", 5]])
        self.assertEqual(
            NovelRankGuard().choose(base, row, base, base, row, row), base
        )

    def test_duplicate_rows_are_preserved_with_multiplicity(self):
        base = action([
            ["SELL", "WOOL", 5], ["SELL", "WOOL", 5],
            ["SELL", "MILK", 4], ["HIRE"],
        ])
        row = action([
            ["SELL", "MILK", 4], ["SELL", "WOOL", 5],
            ["SELL", "WOOL", 5], ["HIRE"],
        ])
        parent_output = action([
            ["SELL", "WOOL", 5], ["SELL", "MILK", 4],
            ["SELL", "WOOL", 5], ["HIRE"],
        ])
        row_output = action([
            ["SELL", "MILK", 4], ["SELL", "WOOL", 5],
            ["SELL", "WOOL", 5], ["HIRE"],
        ])
        self.assertEqual(
            NovelRankGuard().choose(base, row, base, parent_output, row, row_output),
            row,
        )

    def test_falsey_barrier_is_immutable(self):
        base = action([["SELL", "WOOL", 5], [], ["SELL", "MILK", 4]])
        guard = NovelRankGuard()
        self.assertEqual(
            guard.choose(base, copy.deepcopy(base)),
            base,
        )
        self.assertEqual(guard.diagnostics["reason"], "leading_sell_block_lt_2")

    def test_inputs_are_never_mutated(self):
        base = action([["SELL", "WOOL", 5], ["SELL", "MILK", 4], ["HIRE"]])
        row = action([["SELL", "MILK", 4], ["SELL", "WOOL", 5], ["HIRE"]])
        parent_input = copy.deepcopy(base)
        parent_output = copy.deepcopy(base)
        row_input = copy.deepcopy(row)
        row_output = copy.deepcopy(row)
        values = (base, row, parent_input, parent_output, row_input, row_output)
        snapshots = tuple(copy.deepcopy(value) for value in values)
        NovelRankGuard().choose(*values)
        self.assertEqual(values, snapshots)

    def test_truthy_malformed_parent_fails_closed(self):
        base = action([["SELL", "WOOL", 5], ["SELL", "MILK", 4]])
        base["market"].append(1)
        self.assertEqual(
            NovelRankGuard().choose(base, copy.deepcopy(base)),
            base,
        )


if __name__ == "__main__":
    unittest.main()
