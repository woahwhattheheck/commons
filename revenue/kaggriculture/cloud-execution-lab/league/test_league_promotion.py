# SPDX-License-Identifier: Apache-2.0
"""Contracts for fail-closed matched-cell TITAN promotion."""
from __future__ import annotations

import random
import unittest

from promotion import (
    PromotionData,
    PromotionPolicy,
    audit_field,
    audit_promotion,
    expected_keys_from_plan,
    promotion_to_markdown,
)


REFERENCE = "canonical"
CHALLENGER = "challenger"


def row(name, opponent, seed, seat, own_cash, margin=None):
    return {
        "contestant": name,
        "opponent": opponent,
        "seed": seed,
        "candidate_seat": seat,
        "status": "complete",
        "failure": None,
        "own_cash": float(own_cash),
        "margin": float(own_cash if margin is None else margin),
    }


def plan(opponents=("alpha", "beta"), seeds=(11, 12)):
    return {
        "opponents": list(opponents),
        "seeds": list(seeds),
        "cells_per_contestant": len(opponents) * len(seeds) * 2,
    }


def paired_rows(delta_by_key=None):
    delta_by_key = delta_by_key or {}
    rows = []
    for opponent in ("alpha", "beta"):
        for seed in (11, 12):
            for seat in (0, 1):
                key = (opponent, seed, seat)
                base = 1000 + seed + seat
                delta = delta_by_key.get(key, 0)
                rows.append(row(REFERENCE, opponent, seed, seat, base))
                rows.append(row(CHALLENGER, opponent, seed, seat, base + delta))
    return rows


class PlanTest(unittest.TestCase):
    def test_expands_exact_grid_and_checks_declared_size(self):
        keys = expected_keys_from_plan(plan())
        self.assertEqual(len(keys), 8)
        self.assertIn(("alpha", 11, 0), keys)
        bad = plan()
        bad["cells_per_contestant"] = 7
        with self.assertRaises(PromotionData):
            expected_keys_from_plan(bad)

    def test_duplicate_plan_axes_fail_closed(self):
        with self.assertRaises(PromotionData):
            expected_keys_from_plan(plan(opponents=("alpha", "alpha")))
        with self.assertRaises(PromotionData):
            expected_keys_from_plan(plan(seeds=(11, 11)))


class PairedPromotionTest(unittest.TestCase):
    def test_nonnegative_active_uplift_promotes(self):
        rows = paired_rows({("alpha", 11, 0): 25})
        report = audit_promotion(
            rows,
            REFERENCE,
            CHALLENGER,
            expected_keys=expected_keys_from_plan(plan()),
        )
        self.assertTrue(report["eligible"])
        self.assertEqual(report["verdict"], "PROMOTE")
        self.assertEqual(report["metrics"]["positive_cells"], 1)
        self.assertEqual(report["metrics"]["negative_cells"], 0)

    def test_positive_mean_does_not_mask_one_catastrophic_cell(self):
        deltas = {
            ("alpha", 11, 0): 100,
            ("alpha", 11, 1): 100,
            ("beta", 12, 0): -50,
        }
        report = audit_promotion(
            paired_rows(deltas),
            REFERENCE,
            CHALLENGER,
            expected_keys=expected_keys_from_plan(plan()),
        )
        self.assertGreater(report["metrics"]["mean_own_cash_delta"], 0)
        self.assertFalse(report["eligible"])
        self.assertIn("cell_own_cash_regression", {r["kind"] for r in report["reasons"]})

    def test_stratum_gate_can_be_stricter_than_cell_tolerance(self):
        deltas = {
            ("alpha", 11, 0): -4,
            ("alpha", 12, 0): -4,
            ("beta", 11, 1): 20,
        }
        policy = PromotionPolicy(
            max_cell_own_cash_drop=5,
            max_stratum_mean_own_cash_drop=0,
        )
        report = audit_promotion(
            paired_rows(deltas),
            REFERENCE,
            CHALLENGER,
            expected_keys=expected_keys_from_plan(plan()),
            policy=policy,
        )
        kinds = {reason["kind"] for reason in report["reasons"]}
        self.assertNotIn("cell_own_cash_regression", kinds)
        self.assertIn("stratum_mean_own_cash_regression", kinds)

    def test_missing_same_cell_from_both_sides_still_rejects_against_plan(self):
        rows = [
            r for r in paired_rows()
            if not (r["opponent"] == "beta" and r["seed"] == 12 and r["candidate_seat"] == 1)
        ]
        report = audit_promotion(
            rows,
            REFERENCE,
            CHALLENGER,
            expected_keys=expected_keys_from_plan(plan()),
        )
        self.assertFalse(report["coverage"]["complete"])
        self.assertFalse(report["eligible"])
        self.assertIn("incomplete_coverage", {r["kind"] for r in report["reasons"]})

    def test_duplicate_and_nonfinite_evidence_fail_closed(self):
        rows = paired_rows()
        with self.assertRaises(PromotionData):
            audit_promotion(rows + [dict(rows[0])], REFERENCE, CHALLENGER)
        bad = paired_rows()
        bad[0]["own_cash"] = float("nan")
        with self.assertRaises(PromotionData):
            audit_promotion(bad, REFERENCE, CHALLENGER)

    def test_verdict_is_input_order_invariant(self):
        rows = paired_rows({("alpha", 11, 0): 25})
        expected = expected_keys_from_plan(plan())
        baseline = audit_promotion(rows, REFERENCE, CHALLENGER, expected_keys=expected)
        for seed in range(12):
            shuffled = list(rows)
            random.Random(seed).shuffle(shuffled)
            self.assertEqual(
                audit_promotion(shuffled, REFERENCE, CHALLENGER, expected_keys=expected),
                baseline,
            )

    def test_noop_is_not_promotable(self):
        report = audit_promotion(
            paired_rows(),
            REFERENCE,
            CHALLENGER,
            expected_keys=expected_keys_from_plan(plan()),
        )
        self.assertFalse(report["eligible"])
        self.assertIn("insufficient_positive_cells", {r["kind"] for r in report["reasons"]})


class FieldSelectionTest(unittest.TestCase):
    def test_canonical_is_retained_when_only_challenger_regresses(self):
        rows = paired_rows({("beta", 12, 1): -1, ("alpha", 11, 0): 50})
        report = audit_field(
            rows,
            REFERENCE,
            expected_keys=expected_keys_from_plan(plan()),
        )
        self.assertEqual(report["selected"], REFERENCE)
        self.assertFalse(report["promotion"])
        self.assertIn("Promotion: `NO`", promotion_to_markdown(report))

    def test_best_safe_challenger_is_selected_deterministically(self):
        rows = []
        for opponent in ("alpha", "beta"):
            for seed in (11, 12):
                for seat in (0, 1):
                    base = 1000 + seed + seat
                    rows.append(row(REFERENCE, opponent, seed, seat, base))
                    rows.append(row("small", opponent, seed, seat, base + 1))
                    rows.append(row("large", opponent, seed, seat, base + 2))
        report = audit_field(
            rows,
            REFERENCE,
            expected_keys=expected_keys_from_plan(plan()),
        )
        self.assertEqual(report["selected"], "large")
        self.assertTrue(report["promotion"])


if __name__ == "__main__":
    unittest.main()
