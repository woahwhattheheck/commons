# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

import source_contract
from source_contract import checkpoints, import_bindings, load_json, SOURCE


class SourceContractTests(unittest.TestCase):
    def test_checkpoint_table_is_exact_and_ordered(self):
        self.assertEqual(
            checkpoints(),
            (
                (226, "shop_YARN_STORE", 1, "dc76e4003029ac51"),
                (360, "px_CARROT", 42, "ab9669b9abfbea4e"),
                (433, "inv_MILK", 10067, "a84d06f1d12add7c"),
            ),
        )

    def test_contract_names_current_base_and_no_automatic_promotion(self):
        contract = load_json(SOURCE)
        self.assertEqual(
            contract["authored_base"],
            "2e2e7e52fd2d5c62117ac49c7f1eabb505078ffb",
        )
        self.assertIs(contract["invariants"]["promotion_is_never_automatic"], True)
        self.assertIs(
            contract["invariants"]["source_tree_imports_are_private_and_hash_bound"],
            True,
        )
        self.assertIs(
            contract["invariants"]["frozen_v1_manifest_is_verified"], True
        )

    def test_source_tree_import_binding_is_exact_and_blob_authenticated(self):
        self.assertEqual(
            import_bindings(),
            {"observed_clone": "../cloud-runtime-pulse/observed_clone.py"},
        )
        contract = load_json(SOURCE)
        self.assertIn(
            contract["import_bindings"]["observed_clone"], contract["git_blobs"]
        )

    def test_strict_json_rejects_duplicate_and_nonfinite_values(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "value.json"
            for payload in ('{"x":1,"x":2}', '{"x":NaN}', '{"x":Infinity}'):
                with self.subTest(payload=payload):
                    path.write_text(payload, encoding="utf-8")
                    with self.assertRaises(ValueError):
                        load_json(path)


@unittest.skipUnless(
    source_contract.LAB.is_dir()
    and (source_contract.LAB / "runtime/variants/v1/FREEZE.json").is_file(),
    "requires the complete Kaggriculture source tree",
)
class CurrentTreeSourceClosureTests(unittest.TestCase):
    def test_receipt_covers_exact_import_and_every_frozen_v1_file(self):
        receipt = source_contract.verify_source_contract()
        contract = load_json(SOURCE)
        manifest = load_json(source_contract.source_path(contract["frozen_v1_manifest"]))
        closure = receipt["frozen_v1_closure"]
        self.assertEqual(set(closure["files"]), set(manifest["files"]))
        self.assertTrue(
            source_contract.REQUIRED_V1_EXECUTABLES.issubset(closure["files"])
        )
        self.assertEqual(receipt["import_bindings"], import_bindings(contract))
        observed_key = receipt["import_bindings"]["observed_clone"]
        self.assertIn(observed_key, receipt["git_blobs"])
        self.assertEqual(
            closure["manifest_git_blob"],
            contract["git_blobs"][contract["frozen_v1_manifest"]],
        )


if __name__ == "__main__":
    unittest.main()
