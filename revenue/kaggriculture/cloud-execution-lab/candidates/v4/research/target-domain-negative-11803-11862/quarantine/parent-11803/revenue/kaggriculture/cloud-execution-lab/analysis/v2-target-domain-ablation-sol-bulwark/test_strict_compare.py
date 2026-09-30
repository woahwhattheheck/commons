# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import tempfile
import unittest

import bind_execution
from execution_test_support import compare_kwargs, make_fixture, report
import strict_compare


class StrictCompareTests(unittest.TestCase):
    def run_compare(
        self,
        fixture,
        *,
        control=None,
        candidate=None,
        binding=None,
    ):
        control = control or report(fixture, "control")
        candidate = candidate or report(
            fixture,
            "candidate",
            seat_deltas={0: 5.0, 1: 5.0},
        )
        return strict_compare.compare_bound(
            control,
            candidate,
            fixture["receipt"],
            binding or fixture["binding"],
            **compare_kwargs(fixture),
        )

    def test_exact_closure_bound_eight_seed_screen_can_advance(self):
        with tempfile.TemporaryDirectory() as temporary:
            fixture = make_fixture(Path(temporary))
            value = self.run_compare(fixture)
            self.assertEqual(value["verdict"], "UPSIDE_SCREEN")
            self.assertEqual(value["exit_code"], 0)
            self.assertEqual(value["overall"]["cells"], 32)
            self.assertEqual(len(value["by_opponent_seat"]), 4)
            self.assertNotEqual(
                value["invocations"]["control"],
                value["invocations"]["candidate"],
            )

    def test_predecessor_one_seed_positive_fixture_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            fixture = make_fixture(Path(temporary))
            one_seed = [bind_execution.EXPECTED_SEEDS[0]]
            control = report(fixture, "control", seeds=one_seed)
            candidate = report(
                fixture,
                "candidate",
                seeds=one_seed,
                seat_deltas={0: 5.0, 1: 5.0},
            )
            with self.assertRaisesRegex(
                strict_compare.StrictCompareError,
                "seed grid mismatch",
            ):
                self.run_compare(
                    fixture,
                    control=control,
                    candidate=candidate,
                )

    def test_unbound_arbitrary_closure_label_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            fixture = make_fixture(Path(temporary))
            binding = deepcopy(fixture["binding"])
            binding["arms"]["candidate"]["closure_sha256"] = "3" * 64
            with self.assertRaisesRegex(
                strict_compare.StrictCompareError,
                "not bound to materialization",
            ):
                self.run_compare(fixture, binding=binding)

    def test_copied_invocation_id_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            fixture = make_fixture(Path(temporary))
            control = report(fixture, "control", invocation="7" * 32)
            candidate = report(
                fixture,
                "candidate",
                invocation="7" * 32,
                seat_deltas={0: 5.0, 1: 5.0},
            )
            with self.assertRaisesRegex(
                strict_compare.StrictCompareError,
                "invocation IDs are equal",
            ):
                self.run_compare(
                    fixture,
                    control=control,
                    candidate=candidate,
                )

    def test_boolean_candidate_seat_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            fixture = make_fixture(Path(temporary))
            candidate = report(
                fixture,
                "candidate",
                seat_deltas={0: 5.0, 1: 5.0},
            )
            candidate["games"][0]["candidate_seat"] = False
            with self.assertRaisesRegex(
                strict_compare.StrictCompareError,
                "literal integer",
            ):
                self.run_compare(fixture, candidate=candidate)

    def test_overall_gain_cannot_hide_losing_seat_stratum(self):
        with tempfile.TemporaryDirectory() as temporary:
            fixture = make_fixture(Path(temporary))
            candidate = report(
                fixture,
                "candidate",
                seat_deltas={0: 10.0, 1: -1.0},
            )
            value = self.run_compare(fixture, candidate=candidate)
            self.assertEqual(value["overall"]["mean_own_delta"], 4.5)
            self.assertEqual(value["overall"]["positive_cells"], 16)
            self.assertEqual(value["overall"]["negative_cells"], 16)
            self.assertEqual(value["verdict"], "SEAT_STRATUM_REGRESSION")
            self.assertEqual(value["exit_code"], 1)
            self.assertLess(
                value["by_opponent_seat"]["arlene:seat-1"]["mean_own_delta"],
                0,
            )
            self.assertLess(
                value["by_opponent_seat"]["v1:seat-1"]["mean_own_delta"],
                0,
            )

    def test_placeholder_evaluator_identity_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            fixture = make_fixture(Path(temporary))
            candidate = report(
                fixture,
                "candidate",
                seat_deltas={0: 5.0, 1: 5.0},
            )
            candidate["evaluator_sha256"] = "evaluator"
            with self.assertRaisesRegex(
                strict_compare.StrictCompareError,
                "evaluator identity mismatch",
            ):
                self.run_compare(fixture, candidate=candidate)


if __name__ == "__main__":
    unittest.main()
