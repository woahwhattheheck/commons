#!/usr/bin/env python3
"""Focused regression coverage for frontier_paired_screen."""

from __future__ import annotations

import math
import unittest

import frontier_paired_screen as fps


def row(variant, opponent, seed, seat, margin=None, status="complete"):
    value = {
        "variant": variant,
        "opponent": opponent,
        "seed": seed,
        "seat": seat,
        "status": status,
    }
    if margin is not None:
        value["margin"] = margin
    return value


class PairedScreenTest(unittest.TestCase):
    def setUp(self):
        self.expected = [
            {"opponent": "submission:11", "seed": 101, "seat": 0},
            {"opponent": "submission:11", "seed": 101, "seat": 1},
        ]

    def test_paired_complete_is_promotion_ready(self):
        rows = [
            row("base", "submission:11", 101, 0, 10),
            row("cand", "submission:11", 101, 0, 13),
            row("base", "submission:11", 101, 1, -2),
            row("cand", "submission:11", 101, 1, 4),
        ]
        report = fps.paired_summary(
            rows, baseline="base", candidate="cand", expected_cells=self.expected
        )
        self.assertTrue(report["promotion_ready"])
        self.assertEqual(report["paired_n"], 2)
        self.assertEqual(report["paired_mean_delta"], 4.5)
        self.assertEqual([x["delta"] for x in report["paired_deltas"]], [3.0, 6.0])

    def test_unequal_n_stays_partial_and_reports_missing(self):
        rows = [
            row("base", "submission:11", 101, 0, 10),
            row("cand", "submission:11", 101, 0, 15),
            row("base", "submission:11", 101, 1, 30),
        ]
        report = fps.paired_summary(
            rows, baseline="base", candidate="cand", expected_cells=self.expected
        )
        self.assertFalse(report["promotion_ready"])
        self.assertEqual(report["paired_n"], 1)
        self.assertEqual(report["paired_mean_delta"], 5.0)
        self.assertEqual(
            report["missing"]["cand"],
            [{"opponent": "submission:11", "seed": 101, "seat": 1}],
        )

    def test_failed_cell_is_diagnostic_not_score(self):
        rows = [
            row("base", "submission:11", 101, 0, 10),
            row("cand", "submission:11", 101, 0, status="timeout"),
        ]
        report = fps.paired_summary(
            rows,
            baseline="base",
            candidate="cand",
            expected_cells=[self.expected[0]],
        )
        self.assertFalse(report["promotion_ready"])
        self.assertEqual(report["paired_n"], 0)
        self.assertEqual(
            report["incomplete"]["cand"],
            [
                {
                    "opponent": "submission:11",
                    "seed": 101,
                    "seat": 0,
                    "status": "timeout",
                }
            ],
        )

    def test_without_declared_design_never_promotes(self):
        rows = [
            row("base", "submission:11", 101, 0, 0),
            row("cand", "submission:11", 101, 0, 100),
        ]
        report = fps.paired_summary(rows, baseline="base", candidate="cand")
        self.assertEqual(report["paired_n"], 1)
        self.assertFalse(report["expected_declared"])
        self.assertFalse(report["promotion_ready"])

    def test_interaction_math_uses_exact_quadruples(self):
        rows = []
        values = {
            0: {"base": 100, "a": 110, "b": 120, "ab": 145},
            1: {"base": 80, "a": 90, "b": 85, "ab": 102},
        }
        for seat, seat_values in values.items():
            for variant, margin in seat_values.items():
                rows.append(row(variant, "submission:11", 101, seat, margin))
        report = fps.interaction_summary(
            rows,
            baseline="base",
            a="a",
            b="b",
            ab="ab",
            expected_cells=self.expected,
        )
        self.assertTrue(report["promotion_ready"])
        self.assertEqual(report["quadruple_n"], 2)
        self.assertEqual(report["mean_interaction"], 11.0)
        self.assertEqual(
            report["paired_mean_deltas"],
            {"a": 10.0, "b": 12.5, "ab": 33.5},
        )
        self.assertEqual(
            [cell["interaction"] for cell in report["cells"]], [15.0, 7.0]
        )

    def test_duplicate_variant_cell_rejected(self):
        rows = [
            row("base", "submission:11", 101, 0, 1),
            row("base", "submission:11", 101, 0, 1),
            row("cand", "submission:11", 101, 0, 2),
        ]
        with self.assertRaisesRegex(fps.EvidenceError, "duplicate result"):
            fps.paired_summary(rows, baseline="base", candidate="cand")

    def test_malformed_and_nonfinite_evidence_rejected(self):
        bad_rows = [
            row("base", "submission:11", 101, True, 1),
            row("base", "submission:11", 101, 0, math.inf),
            row("base", "", 101, 0, 1),
        ]
        for bad in bad_rows:
            with self.subTest(bad=bad):
                with self.assertRaises(fps.EvidenceError):
                    fps.paired_summary(
                        [bad, row("cand", "submission:11", 101, 0, 2)],
                        baseline="base",
                        candidate="cand",
                    )

    def test_score_derived_margin_must_match_explicit_margin(self):
        good = {
            "variant": "base",
            "opponent": "submission:11",
            "seed": 101,
            "seat": 0,
            "candidate_score": 9,
            "opponent_score": 4,
            "margin": 5,
        }
        other = row("cand", "submission:11", 101, 0, 9)
        report = fps.paired_summary([good, other], baseline="base", candidate="cand")
        self.assertEqual(report["paired_mean_delta"], 4.0)
        bad = dict(good, margin=6)
        with self.assertRaisesRegex(fps.EvidenceError, "disagrees"):
            fps.paired_summary([bad, other], baseline="base", candidate="cand")

    def test_interaction_partial_reports_missing_variant(self):
        rows = [
            row("base", "submission:11", 101, 0, 0),
            row("a", "submission:11", 101, 0, 1),
            row("b", "submission:11", 101, 0, 2),
            row("ab", "submission:11", 101, 0, 4),
            row("base", "submission:11", 101, 1, 0),
            row("a", "submission:11", 101, 1, 1),
            row("b", "submission:11", 101, 1, 2),
        ]
        report = fps.interaction_summary(
            rows,
            baseline="base",
            a="a",
            b="b",
            ab="ab",
            expected_cells=self.expected,
        )
        self.assertEqual(report["quadruple_n"], 1)
        self.assertFalse(report["promotion_ready"])
        self.assertEqual(
            report["missing"]["ab"],
            [{"opponent": "submission:11", "seed": 101, "seat": 1}],
        )


if __name__ == "__main__":
    unittest.main()
