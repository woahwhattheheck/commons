# SPDX-License-Identifier: Apache-2.0
"""Exact-repository discriminator for SOL-FORGE evaluator receipt accounting."""
from __future__ import annotations

import copy
from pathlib import Path
import tempfile
import unittest

import compare_bound
import materialize_evaluator


HERE = Path(__file__).resolve().parent
EVALUATOR = HERE.parents[2] / "cloud-eval" / "evaluate.py"


class RealEvaluatorReceiptTests(unittest.TestCase):
    def test_normalized_receipt_separates_embedded_bytes_from_unconsumed_sites(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "evaluate.py"
            receipt = materialize_evaluator.materialize_evaluator(EVALUATOR, output)

            patches = receipt["patched"]["patches"]
            self.assertEqual(
                [row["old_occurrences_before"] for row in patches], [1, 1, 1]
            )
            self.assertEqual(
                [row["old_occurrences_after"] for row in patches], [0, 0, 0]
            )
            self.assertEqual(
                [row["old_occurrences_after_raw"] for row in patches], [0, 1, 0]
            )
            self.assertEqual(
                [
                    row["old_occurrences_embedded_in_replacement"]
                    for row in patches
                ],
                [0, 1, 0],
            )
            self.assertEqual(
                [row["new_occurrences_after"] for row in patches], [1, 1, 1]
            )

            old, new, _label = materialize_evaluator.NEEDLES[1]
            patched = output.read_bytes()
            self.assertEqual(patched.count(old), 1)
            self.assertEqual(patched.count(new), 1)
            self.assertEqual(
                compare_bound.validate_evaluator(receipt, output),
                receipt["patched"]["sha256"],
            )

    def test_predecessor_receipt_is_rejected_by_current_validator(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "evaluate.py"
            legacy = materialize_evaluator._ORIGINAL_MATERIALIZE_EVALUATOR(
                EVALUATOR, output
            )
            self.assertEqual(
                [row["old_occurrences_after"] for row in legacy["patched"]["patches"]],
                [0, 1, 0],
            )
            with self.assertRaisesRegex(
                compare_bound.BoundCompareError,
                "evaluator patch 1 cardinality is invalid",
            ):
                compare_bound.validate_evaluator(legacy, output)

    def test_raw_embedded_accounting_tamper_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "evaluate.py"
            receipt = materialize_evaluator.materialize_evaluator(EVALUATOR, output)
            for field, value in (
                ("old_occurrences_after_raw", 0),
                ("old_occurrences_embedded_in_replacement", 0),
                ("old_sha256", "0" * 64),
            ):
                with self.subTest(field=field):
                    forged = copy.deepcopy(receipt)
                    forged["patched"]["patches"][1][field] = value
                    with self.assertRaisesRegex(
                        compare_bound.BoundCompareError,
                        "evaluator patch 1 raw/embedded accounting is invalid",
                    ):
                        compare_bound.validate_evaluator(forged, output)


if __name__ == "__main__":
    unittest.main(verbosity=2)
