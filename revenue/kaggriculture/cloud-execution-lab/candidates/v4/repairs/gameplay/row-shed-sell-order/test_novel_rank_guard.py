# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import copy
import unittest

from novel_rank_guard import PressureNoveltyGuard


def action(rows, farmer=None):
    return {
        "farmer": ["PASS"] if farmer is None else farmer,
        "hands": [],
        "market": copy.deepcopy(rows),
    }


def quote(*_args):
    return 100


def stable_score_pressure(scores):
    """Small pressure-shaped callback: stable-sort the leading SELL block."""
    def transform(parent, observation, configuration, *, quote):
        del observation, configuration, quote
        result = copy.deepcopy(parent)
        rows = result["market"]
        stop = 0
        while stop < len(rows):
            row = rows[stop]
            if not row or not isinstance(row, list) or row[0] != "SELL":
                break
            stop += 1
        rows[:stop] = sorted(rows[:stop], key=lambda row: -scores[row[1]])
        return result
    return transform


class PressureNoveltyGuardTests(unittest.TestCase):
    def test_rank_difference_collapsed_by_downstream_pressure_returns_identity(self):
        base = action([
            ["SELL", "WOOL", 5], ["SELL", "MILK", 4],
            ["SELL", "EGG", 3], ["HIRE"],
        ])
        row = action([
            ["SELL", "MILK", 4], ["SELL", "WOOL", 5],
            ["SELL", "EGG", 3], ["HIRE"],
        ])
        pressure = stable_score_pressure({"EGG": 3, "WOOL": 2, "MILK": 1})
        guard = PressureNoveltyGuard()
        self.assertEqual(guard.choose(base, row, pressure, {}, {}, quote=quote), base)
        self.assertEqual(guard.diagnostics["reason"], "collapsed_by_downstream_pressure")
        self.assertEqual(
            guard.diagnostics["parent_pressure_market"],
            guard.diagnostics["row_shed_pressure_market"],
        )

    def test_equal_pressure_tie_preserves_row_shed_tiebreak(self):
        base = action([
            ["SELL", "WOOL", 5], ["SELL", "MILK", 4],
            ["SELL", "EGG", 3], ["HIRE"],
        ])
        row = action([
            ["SELL", "MILK", 4], ["SELL", "WOOL", 5],
            ["SELL", "EGG", 3], ["HIRE"],
        ])
        pressure = stable_score_pressure({"EGG": 3, "WOOL": 1, "MILK": 1})
        guard = PressureNoveltyGuard()
        self.assertEqual(guard.choose(base, row, pressure, {}, {}, quote=quote), row)
        self.assertEqual(guard.diagnostics["status"], "applied")
        self.assertEqual(guard.diagnostics["reason"], "survives_downstream_pressure")
        self.assertNotEqual(
            guard.diagnostics["parent_pressure_market"],
            guard.diagnostics["row_shed_pressure_market"],
        )

    def test_pressure_identity_preserves_real_row_shed_novelty(self):
        base = action([["SELL", "WOOL", 5], ["SELL", "MILK", 4], ["HIRE"]])
        row = action([["SELL", "MILK", 4], ["SELL", "WOOL", 5], ["HIRE"]])

        def identity(parent, observation, configuration, *, quote):
            del observation, configuration, quote
            return copy.deepcopy(parent)

        self.assertEqual(
            PressureNoveltyGuard().choose(base, row, identity, {}, {}, quote=quote),
            row,
        )

    def test_missing_pressure_transform_fails_closed(self):
        base = action([["SELL", "WOOL", 5], ["SELL", "MILK", 4]])
        row = action([["SELL", "MILK", 4], ["SELL", "WOOL", 5]])
        guard = PressureNoveltyGuard()
        self.assertEqual(guard.choose(base, row, None, {}, {}, quote=quote), base)
        self.assertIn("missing", guard.diagnostics["reason"])

    def test_throwing_pressure_transform_fails_closed(self):
        base = action([["SELL", "WOOL", 5], ["SELL", "MILK", 4]])
        row = action([["SELL", "MILK", 4], ["SELL", "WOOL", 5]])

        def broken(*_args, **_kwargs):
            raise RuntimeError("pressure unavailable")

        guard = PressureNoveltyGuard()
        self.assertEqual(guard.choose(base, row, broken, {}, {}, quote=quote), base)
        self.assertIn("unavailable", guard.diagnostics["reason"])

    def test_pressure_quantity_mutation_fails_closed(self):
        base = action([["SELL", "WOOL", 5], ["SELL", "MILK", 4]])
        row = action([["SELL", "MILK", 4], ["SELL", "WOOL", 5]])

        def bad(parent, observation, configuration, *, quote):
            del observation, configuration, quote
            result = copy.deepcopy(parent)
            result["market"][0][2] += 1
            return result

        self.assertEqual(
            PressureNoveltyGuard().choose(base, row, bad, {}, {}, quote=quote), base
        )

    def test_pressure_non_market_mutation_fails_closed(self):
        base = action([["SELL", "WOOL", 5], ["SELL", "MILK", 4]])
        row = action([["SELL", "MILK", 4], ["SELL", "WOOL", 5]])

        def bad(parent, observation, configuration, *, quote):
            del observation, configuration, quote
            result = copy.deepcopy(parent)
            result["farmer"] = ["LEFT"]
            return result

        self.assertEqual(
            PressureNoveltyGuard().choose(base, row, bad, {}, {}, quote=quote), base
        )

    def test_row_shed_multiset_change_fails_before_pressure(self):
        base = action([["SELL", "WOOL", 5], ["SELL", "MILK", 4]])
        row = action([["SELL", "MILK", 5], ["SELL", "WOOL", 5]])
        calls = []

        def pressure(parent, observation, configuration, *, quote):
            del observation, configuration, quote
            calls.append(parent)
            return copy.deepcopy(parent)

        self.assertEqual(
            PressureNoveltyGuard().choose(base, row, pressure, {}, {}, quote=quote),
            base,
        )
        self.assertEqual(calls, [])

    def test_duplicate_rows_preserve_multiplicity(self):
        base = action([
            ["SELL", "WOOL", 5], ["SELL", "WOOL", 5],
            ["SELL", "MILK", 4], ["HIRE"],
        ])
        row = action([
            ["SELL", "MILK", 4], ["SELL", "WOOL", 5],
            ["SELL", "WOOL", 5], ["HIRE"],
        ])

        def identity(parent, observation, configuration, *, quote):
            del observation, configuration, quote
            return copy.deepcopy(parent)

        self.assertEqual(
            PressureNoveltyGuard().choose(base, row, identity, {}, {}, quote=quote),
            row,
        )

    def test_falsey_barrier_is_immutable(self):
        base = action([["SELL", "WOOL", 5], [], ["SELL", "MILK", 4]])
        guard = PressureNoveltyGuard()
        self.assertEqual(
            guard.choose(base, copy.deepcopy(base), None, {}, {}, quote=quote), base
        )
        self.assertEqual(guard.diagnostics["reason"], "leading_sell_block_lt_2")

    def test_pressure_may_compact_empty_slots_when_rows_are_preserved(self):
        base = action([["SELL", "WOOL", 5], ["SELL", "MILK", 4], [], ["HIRE"]])
        row = action([["SELL", "MILK", 4], ["SELL", "WOOL", 5], [], ["HIRE"]])

        def compact(parent, observation, configuration, *, quote):
            del observation, configuration, quote
            result = copy.deepcopy(parent)
            rows = result["market"]
            rows[2], rows[3] = rows[3], rows[2]
            return result

        self.assertEqual(
            PressureNoveltyGuard().choose(base, row, compact, {}, {}, quote=quote),
            row,
        )

    def test_inputs_and_public_evidence_are_never_mutated(self):
        base = action([["SELL", "WOOL", 5], ["SELL", "MILK", 4], ["HIRE"]])
        row = action([["SELL", "MILK", 4], ["SELL", "WOOL", 5], ["HIRE"]])
        observation = {"market": {"prices": {"WOOL": 100}}}
        configuration = {"maxMarketOrdersPerTurn": 10}
        snapshots = tuple(
            copy.deepcopy(value) for value in (base, row, observation, configuration)
        )

        def mutating(parent, obs, cfg, *, quote):
            del quote
            obs["poison"] = True
            cfg["maxMarketOrdersPerTurn"] = 1
            return copy.deepcopy(parent)

        PressureNoveltyGuard().choose(
            base, row, mutating, observation, configuration, quote=quote
        )
        self.assertEqual((base, row, observation, configuration), snapshots)

    def test_truthy_malformed_parent_fails_closed(self):
        base = action([["SELL", "WOOL", 5], ["SELL", "MILK", 4]])
        base["market"].append(1)
        self.assertEqual(
            PressureNoveltyGuard().choose(
                base, copy.deepcopy(base), None, {}, {}, quote=quote
            ),
            base,
        )


if __name__ == "__main__":
    unittest.main()
