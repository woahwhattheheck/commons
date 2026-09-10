# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("intent_priority_materialize", HERE / "materialize.py")
assert SPEC and SPEC.loader
m = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)
LAB = HERE.parents[2]
SCHEDULER = LAB / "scheduler.py"


class TargetOrderContracts(unittest.TestCase):
    PRODUCTS = ("WHEAT", "CARROT", "MILK", "EGG", "FERTILIZER")
    SHED = {"WHEAT": 3, "CARROT": 7, "MILK": 2, "EGG": 0, "FERTILIZER": 1}

    def test_membership_and_quantities_are_identical(self):
        control = m.control_targets(products=self.PRODUCTS, shed=self.SHED)
        candidate = m.priority_targets(
            pending={"MILK": [(9, 1)]},
            baseline_q={"CARROT": 2},
            products=self.PRODUCTS,
            shed=self.SHED,
        )
        self.assertEqual(candidate, control)
        self.assertEqual(set(candidate), set(control))

    def test_pending_then_baseline_then_products_order(self):
        candidate = m.priority_targets(
            pending={"MILK": object(), "CARROT": object()},
            baseline_q={"FERTILIZER": 1, "WHEAT": 1},
            products=self.PRODUCTS,
            shed=self.SHED,
        )
        self.assertEqual(
            tuple(candidate),
            ("MILK", "CARROT", "FERTILIZER", "WHEAT"),
        )

    def test_unknown_and_zero_stock_keys_cannot_expand_domain(self):
        candidate = m.priority_targets(
            pending={"UNKNOWN": 1, "EGG": 1},
            baseline_q={"OTHER": 1},
            products=self.PRODUCTS,
            shed=self.SHED,
        )
        self.assertNotIn("UNKNOWN", candidate)
        self.assertNotIn("OTHER", candidate)
        self.assertNotIn("EGG", candidate)

    def test_no_intent_preserves_products_order(self):
        control = m.control_targets(products=self.PRODUCTS, shed=self.SHED)
        candidate = m.priority_targets(
            pending={}, baseline_q={}, products=self.PRODUCTS, shed=self.SHED
        )
        self.assertEqual(tuple(candidate), tuple(control))


class MaterializationContracts(unittest.TestCase):
    def test_exact_current_scheduler_materializes_one_file(self):
        original = SCHEDULER.read_bytes()
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "scheduler.py"
            receipt_path = Path(directory) / "receipt.json"
            receipt = m.materialize(SCHEDULER, output, receipt_path)
            self.assertEqual(SCHEDULER.read_bytes(), original)
            self.assertNotEqual(output.read_bytes(), original)
            self.assertEqual(receipt["source"]["git_blob_sha1"], m.EXPECTED_SCHEDULER_BLOB)
            self.assertEqual(receipt["candidate"]["new_occurrences"], 1)
            self.assertEqual(receipt["candidate"]["old_occurrences"], 0)
            self.assertEqual(receipt["factor"]["changed_files"], ["scheduler.py"])
            self.assertFalse(receipt["canonical_mutation"])
            self.assertFalse(receipt["enabled"])
            self.assertEqual(json.loads(receipt_path.read_text()), receipt)
            compile(output.read_text(), str(output), "exec")

    def test_source_blob_is_current_main_bound(self):
        self.assertEqual(m.git_blob_sha1(SCHEDULER.read_bytes()), m.EXPECTED_SCHEDULER_BLOB)

    def test_source_drift_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "scheduler.py"
            source.write_text(SCHEDULER.read_text() + "\n# drift\n")
            with self.assertRaisesRegex(m.PortError, "current scheduler drift"):
                m.materialize(source, Path(directory) / "candidate.py")

    def test_output_may_not_alias_source(self):
        with self.assertRaisesRegex(m.PortError, "must not alias"):
            m.materialize(SCHEDULER, SCHEDULER)

    def test_admission_receipt_is_exactly_bound(self):
        with tempfile.TemporaryDirectory() as directory:
            receipt = m.materialize(SCHEDULER, Path(directory) / "scheduler.py")
        self.assertEqual(receipt["admission"]["head"], m.ADMISSION_HEAD)
        self.assertEqual(
            receipt["admission"]["artifact_sha256"],
            "528f7557a899c1376c8fe04ed328c70a17a760aa3a725e190710ea13ad7e13f8",
        )


if __name__ == "__main__":
    unittest.main()
