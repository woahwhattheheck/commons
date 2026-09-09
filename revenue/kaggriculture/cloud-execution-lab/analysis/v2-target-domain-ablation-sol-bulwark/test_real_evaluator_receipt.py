# SPDX-License-Identifier: Apache-2.0
"""Exact-repository discriminator for evaluator materialization receipts."""
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
    def test_real_receipt_distinguishes_raw_containment_from_unconsumed_sites(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "evaluate-bound.py"
            receipt = materialize_evaluator.materialize_evaluator(
                EVALUATOR,
                output,
            )

            patches = receipt["patched"]["patches"]
            self.assertEqual(
                [row["old_occurrences_before"] for row in patches],
                [1, 1, 1],
            )
            self.assertEqual(
                [row["old_occurrences_after"] for row in patches],
                [0, 0, 0],
            )
            self.assertEqual(
                [row["old_occurrences_after_raw"] for row in patches],
                [0, 1, 0],
            )
            self.assertEqual(
                [
                    row["old_occurrences_embedded_in_replacement"]
                    for row in patches
                ],
                [0, 1, 0],
            )
            self.assertEqual(
                [row["new_occurrences_after"] for row in patches],
                [1, 1, 1],
            )

            old, new, _label = materialize_evaluator.NEEDLES[1]
            patched = output.read_bytes()
            self.assertEqual(patched.count(old), 1)
            self.assertEqual(patched.count(new), 1)
            self.assertEqual(
                compare_bound.validate_evaluator(receipt),
                receipt["patched"]["sha256"],
            )

            invalid = copy.deepcopy(receipt)
            invalid["patched"]["patches"][1]["old_occurrences_after"] = 1
            with self.assertRaisesRegex(
                compare_bound.BoundCompareError,
                "evaluator patch 1 cardinality is invalid",
            ):
                compare_bound.validate_evaluator(invalid)


if __name__ == "__main__":
    unittest.main(verbosity=2)
