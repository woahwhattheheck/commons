# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import unittest

from runtime_budget_profile import BudgetProfileError, profile_rows


def row(candidate, seed, seat, step, elapsed, cpu=None, *, status="completed", stage=None, nested=False):
    diagnostics = {
        "status": status,
        "elapsed_seconds": elapsed,
        "act_cpu_seconds": elapsed if cpu is None else cpu,
    }
    if stage is not None:
        diagnostics["fallback_stage"] = stage
    base = {"candidate": candidate, "seed": seed, "seat": seat, "step": step}
    if nested:
        base["diagnostics"] = diagnostics
    else:
        base.update(diagnostics)
    return base


class RuntimeBudgetProfileTests(unittest.TestCase):
    def test_complete_design_profiles_phases_and_nearest_rank(self):
        rows = [
            row("v5c:a", 1, 0, 0, 0.010, nested=True),
            row("v5c:a", 1, 0, 239, 0.020),
            row("v5c:a", 1, 0, 240, 0.030),
            row("v5c:a", 1, 0, 479, 0.040),
            row("v5c:a", 1, 0, 480, 0.050),
            row("v5c:a", 1, 0, 719, 0.060),
        ]
        expected = [
            {key: value for key, value in item.items()
             if key in ("candidate", "seed", "seat", "step")}
            for item in rows
        ]
        report = profile_rows(
            rows,
            budget_seconds=0.100,
            reserve_seconds=0.020,
            expected_rows=expected,
        )
        self.assertTrue(report["promotion_ready"])
        self.assertEqual(report["classification"], "PASS")
        self.assertEqual(report["overall"]["wall_seconds"]["p50"], 0.030)
        self.assertEqual(report["overall"]["wall_seconds"]["p95"], 0.060)
        self.assertEqual(report["overall"]["wall_seconds"]["p99"], 0.060)
        self.assertEqual(report["by_phase"]["early"]["count"], 2)
        self.assertEqual(report["by_phase"]["mid"]["count"], 2)
        self.assertEqual(report["by_phase"]["late"]["count"], 2)
        self.assertAlmostEqual(report["p99_headroom_seconds"], 0.020)

    def test_missing_design_or_deadline_fallback_blocks_promotion(self):
        rows = [
            row("v5c:a", 2, 1, 10, 0.030),
            row(
                "v5c:a", 2, 1, 11, 0.091,
                status="deadline_fallback", stage="selected_transform",
            ),
        ]
        no_design = profile_rows(rows, budget_seconds=0.1, reserve_seconds=0.01)
        self.assertFalse(no_design["promotion_ready"])
        self.assertFalse(no_design["expected_design_declared"])

        expected = [
            {"candidate": "v5c:a", "seed": 2, "seat": 1, "step": 10},
            {"candidate": "v5c:a", "seed": 2, "seat": 1, "step": 11},
            {"candidate": "v5c:a", "seed": 2, "seat": 1, "step": 12},
        ]
        incomplete = profile_rows(
            rows,
            budget_seconds=0.1,
            reserve_seconds=0.01,
            max_fallback_rate=0.5,
            expected_rows=expected,
        )
        self.assertFalse(incomplete["promotion_ready"])
        self.assertEqual(incomplete["deadline_fallback_count"], 1)
        self.assertEqual(incomplete["fallback_stage_counts"], {"selected_transform": 1})
        self.assertEqual(incomplete["missing_expected"][0]["step"], 12)

    def test_fallback_ceiling_and_usable_budget_are_both_hard_gates(self):
        rows = [
            row("v5c:a", 3, 0, 0, 0.04),
            row("v5c:a", 3, 0, 1, 0.09,
                status="deadline_fallback", stage="cold_start"),
        ]
        expected = [
            {"candidate": "v5c:a", "seed": 3, "seat": 0, "step": 0},
            {"candidate": "v5c:a", "seed": 3, "seat": 0, "step": 1},
        ]
        fallback_block = profile_rows(
            rows,
            budget_seconds=0.2,
            reserve_seconds=0.01,
            max_fallback_rate=0.49,
            expected_rows=expected,
        )
        self.assertFalse(fallback_block["promotion_ready"])
        headroom_block = profile_rows(
            rows,
            budget_seconds=0.1,
            reserve_seconds=0.02,
            max_fallback_rate=0.5,
            expected_rows=expected,
        )
        self.assertFalse(headroom_block["promotion_ready"])
        self.assertLess(headroom_block["p99_headroom_seconds"], 0)

    def test_duplicate_and_malformed_timing_fail_closed(self):
        good = row("v5c:a", 4, 0, 1, 0.01)
        with self.assertRaises(BudgetProfileError):
            profile_rows([good, dict(good)], budget_seconds=0.1)
        for bad in (True, -1, float("nan"), float("inf"), "0.1", None):
            broken = row("v5c:a", 4, 0, 1, 0.01)
            broken["elapsed_seconds"] = bad
            with self.subTest(bad=bad):
                with self.assertRaises(BudgetProfileError):
                    profile_rows([broken], budget_seconds=0.1)

    def test_identity_and_fallback_stage_are_exact(self):
        for field, bad in (
            ("candidate", ""),
            ("seed", True),
            ("seat", 0.0),
            ("step", -1),
        ):
            broken = row("v5c:a", 5, 0, 1, 0.01)
            broken[field] = bad
            with self.subTest(field=field, bad=bad):
                with self.assertRaises(BudgetProfileError):
                    profile_rows([broken], budget_seconds=0.1)
        broken = row("v5c:a", 5, 0, 1, 0.01, status="deadline_fallback")
        with self.assertRaises(BudgetProfileError):
            profile_rows([broken], budget_seconds=0.1)

    def test_expected_duplicates_and_bad_budget_contract_fail_closed(self):
        rows = [row("v5c:a", 6, 0, 1, 0.01)]
        expected = [{"candidate": "v5c:a", "seed": 6, "seat": 0, "step": 1}]
        with self.assertRaises(BudgetProfileError):
            profile_rows(rows, budget_seconds=0.1, expected_rows=expected + expected)
        for budget, reserve, fallback in (
            (0.0, 0.0, 0.0),
            (0.1, 0.1, 0.0),
            (0.1, 0.0, 1.1),
        ):
            with self.subTest(budget=budget, reserve=reserve, fallback=fallback):
                with self.assertRaises(BudgetProfileError):
                    profile_rows(
                        rows,
                        budget_seconds=budget,
                        reserve_seconds=reserve,
                        max_fallback_rate=fallback,
                    )


if __name__ == "__main__":
    unittest.main(verbosity=2)
