from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

import delegate
import materialize as lane


HERE = Path(__file__).resolve().parent
LAB = HERE.parents[1]
FROZEN_V2 = LAB / "runtime" / "variants" / "v2"


class DelegateContracts(unittest.TestCase):
    def test_every_reused_parent_helper_is_git_blob_bound(self):
        self.assertEqual(
            set(delegate.EXPECTED_PARENT_BLOBS),
            {
                "bind_execution.py",
                "compare.py",
                "compare_bound.py",
                "materialize_evaluator.py",
            },
        )
        for filename, expected in delegate.EXPECTED_PARENT_BLOBS.items():
            with self.subTest(filename=filename):
                data = (delegate.PARENT / filename).read_bytes()
                self.assertEqual(delegate.git_blob_sha1(data), expected)

    def test_unregistered_parent_helper_fails_closed(self):
        with self.assertRaises(delegate.DelegateError):
            delegate.load_parent("not-reviewed.py", "_not_reviewed")

    def test_all_adapters_bind_to_this_operation_and_marker_set(self):
        import bind_execution
        import compare
        import compare_bound
        import materialize_evaluator

        self.assertEqual(bind_execution.OPERATION, lane.OPERATION)
        self.assertEqual(compare.OPERATION, lane.OPERATION)
        self.assertEqual(compare_bound.OPERATION, lane.OPERATION)
        self.assertEqual(materialize_evaluator.OPERATION, lane.OPERATION)
        self.assertEqual(
            set(compare.EXPECTED_MARKERS), set(lane.PRESERVED_V2_MARKERS)
        )
        self.assertEqual(bind_execution.lane.OPERATION, lane.OPERATION)
        self.assertEqual(compare_bound.parent.OPERATION, lane.OPERATION)

    def test_materialization_is_accepted_by_both_exact_parent_validators(self):
        import bind_execution
        import compare

        with tempfile.TemporaryDirectory() as directory:
            receipt = lane.materialize(
                FROZEN_V2, Path(directory) / "profit-first"
            )
        bound = bind_execution.validate_materialization(receipt)
        compared = compare.validate_receipt(receipt)
        self.assertEqual(
            bound["source_closure"], compared["source_closure_sha256"]
        )
        self.assertEqual(
            bound["ablation_closure"], compared["ablation_closure_sha256"]
        )

    def test_bound_comparator_preserves_parent_custody_repair_identity(self):
        import bind_execution
        import compare_bound
        import materialize_evaluator

        self.assertEqual(
            compare_bound.binding_module.REPAIR, bind_execution.REPAIR
        )
        self.assertEqual(
            compare_bound.evaluator_module.REPAIR,
            materialize_evaluator.REPAIR,
        )
        self.assertEqual(compare_bound.EXPECTED_EPISODE_STEPS, 720)
        self.assertEqual(compare_bound.EXPECTED_ACTIONS, 719)
        self.assertEqual(len(compare_bound.EXPECTED_SEEDS), 4)
        self.assertTrue(
            all(type(seed) is int for seed in compare_bound.EXPECTED_SEEDS)
        )


if __name__ == "__main__":
    unittest.main()
