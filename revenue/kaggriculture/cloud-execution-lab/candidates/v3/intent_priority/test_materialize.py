# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import ast
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
FROZEN_SELECTED = LAB / "frozen_selected.py"
TITAN_RUNTIME = LAB / "titan_runtime.py"


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
    def test_exact_current_frozen_selected_materializes_one_file(self):
        original = FROZEN_SELECTED.read_bytes()
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "frozen_selected.py"
            receipt_path = Path(directory) / "receipt.json"
            receipt = m.materialize(FROZEN_SELECTED, output, receipt_path)
            self.assertEqual(FROZEN_SELECTED.read_bytes(), original)
            self.assertNotEqual(output.read_bytes(), original)
            self.assertEqual(
                receipt["source"]["git_blob_sha1"],
                m.EXPECTED_FROZEN_SELECTED_BLOB,
            )
            self.assertEqual(receipt["candidate"]["new_occurrences"], 1)
            self.assertEqual(receipt["candidate"]["old_occurrences"], 0)
            self.assertEqual(receipt["factor"]["changed_files"], ["frozen_selected.py"])
            self.assertEqual(
                receipt["factor"]["runtime_dispatch"],
                "TitanAgent.transform_selected -> FrozenSelected.transform",
            )
            self.assertFalse(receipt["canonical_mutation"])
            self.assertFalse(receipt["enabled"])
            self.assertEqual(json.loads(receipt_path.read_text()), receipt)
            compile(output.read_text(), str(output), "exec")

    def test_patched_expression_is_owned_by_frozen_transform(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "frozen_selected.py"
            m.materialize(FROZEN_SELECTED, output)
            tree = ast.parse(output.read_text())
        frozen = next(
            node for node in tree.body
            if isinstance(node, ast.ClassDef) and node.name == "FrozenSelected"
        )
        transform = next(
            node for node in frozen.body
            if isinstance(node, ast.FunctionDef) and node.name == "transform"
        )
        assignments = [
            node for node in ast.walk(transform)
            if isinstance(node, ast.Assign)
            and any(isinstance(target, ast.Name) and target.id == "target_order"
                    for target in node.targets)
        ]
        self.assertEqual(len(assignments), 1)
        self.assertTrue(any(
            isinstance(node, ast.Name) and node.id == "target_order"
            for node in ast.walk(transform)
        ))

    def test_canonical_dispatch_reaches_frozen_transform(self):
        runtime = TITAN_RUNTIME.read_text()
        self.assertIn("from frozen_selected import FrozenSelected", runtime)
        self.assertIn("self.consumer = FrozenSelected()", runtime)
        self.assertIn("self.consumer.transform(obs, cfg, selected)", runtime)
        self.assertNotIn("self.consumer.act(obs, cfg, selected)", runtime)

    def test_source_blob_is_current_main_bound(self):
        self.assertEqual(
            m.git_blob_sha1(FROZEN_SELECTED.read_bytes()),
            m.EXPECTED_FROZEN_SELECTED_BLOB,
        )

    def test_source_drift_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "frozen_selected.py"
            source.write_text(FROZEN_SELECTED.read_text() + "\n# drift\n")
            with self.assertRaisesRegex(m.PortError, "current frozen_selected drift"):
                m.materialize(source, Path(directory) / "candidate.py")

    def test_output_may_not_alias_source(self):
        with self.assertRaisesRegex(m.PortError, "must not alias"):
            m.materialize(FROZEN_SELECTED, FROZEN_SELECTED)

    def test_admission_receipt_is_exactly_bound(self):
        with tempfile.TemporaryDirectory() as directory:
            receipt = m.materialize(
                FROZEN_SELECTED, Path(directory) / "frozen_selected.py"
            )
        self.assertEqual(receipt["admission"]["head"], m.ADMISSION_HEAD)
        self.assertEqual(
            receipt["admission"]["artifact_sha256"],
            "528f7557a899c1376c8fe04ed328c70a17a760aa3a725e190710ea13ad7e13f8",
        )


if __name__ == "__main__":
    unittest.main()
