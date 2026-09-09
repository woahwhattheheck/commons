# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import copy
import json
from pathlib import Path
import tempfile
import unittest

import compare_bound
import compare_exact
import materialize
import materialize_evaluator

HERE = Path(__file__).resolve().parent
LAB = HERE.parents[1]
KAG = LAB.parent
EVALUATOR = KAG / "cloud-eval" / "evaluate.py"
WORKFLOW = (
    HERE.parents[4]
    / ".github"
    / "workflows"
    / "titan-v2-forced-feasibility-ablation-sol-keel.yml"
)


def build_evaluator(root: Path) -> tuple[Path, dict]:
    patched = root / "evaluate-bound.py"
    receipt = materialize_evaluator.materialize_evaluator(EVALUATOR, patched)
    return patched, receipt


class ExactEvaluatorDerivationContracts(unittest.TestCase):
    def test_exact_materialized_evaluator_passes(self):
        with tempfile.TemporaryDirectory() as directory:
            patched, receipt = build_evaluator(Path(directory))
            expected = compare_exact.validate_evaluator(receipt, patched)
            self.assertEqual(expected, receipt["patched"]["sha256"])
            self.assertTrue(
                all(
                    row["old_occurrences_after"] == 0
                    for row in receipt["patched"]["patches"]
                )
            )

    def test_receipt_and_evaluator_co_tamper_kills_predecessor(self):
        with tempfile.TemporaryDirectory() as directory:
            patched, receipt = build_evaluator(Path(directory))
            tampered = patched.read_bytes() + b"\n# coordinated post-materialization drift\n"
            patched.write_bytes(tampered)
            forged = copy.deepcopy(receipt)
            helper = materialize._load_base()
            forged["patched"]["bytes"] = len(tampered)
            forged["patched"]["sha256"] = helper.sha256(tampered)
            forged["patched"]["git_blob_sha1"] = helper.git_blob_sha1(tampered)

            # The predecessor trusted mutually consistent receipt/live-file hashes.
            self.assertEqual(
                compare_bound.validate_evaluator(forged, patched),
                forged["patched"]["sha256"],
            )
            with self.assertRaisesRegex(
                compare_bound.BoundCompareError,
                "exact pinned-source derivation",
            ):
                compare_exact.validate_evaluator(forged, patched)

    def test_patch_metadata_tamper_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            patched, receipt = build_evaluator(Path(directory))
            forged = copy.deepcopy(receipt)
            forged["patched"]["patches"][1]["label"] = "plausible lie"
            with self.assertRaisesRegex(
                compare_bound.BoundCompareError,
                "exact derivation receipt",
            ):
                compare_exact.validate_evaluator(forged, patched)

    def test_workflow_executes_and_pins_exact_comparator(self):
        workflow = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn('git hash-object "$CASE/compare_exact.py"', workflow)
        self.assertIn('git hash-object "$CASE/test_contract_repair.py"', workflow)
        self.assertIn("test_contract_repair.py", workflow)
        self.assertIn('python -B "$CASE/compare_exact.py"', workflow)
        self.assertNotIn(
            'python -B "$CASE/compare_bound.py" \\\n            --control',
            workflow,
        )


if __name__ == "__main__":
    unittest.main()
