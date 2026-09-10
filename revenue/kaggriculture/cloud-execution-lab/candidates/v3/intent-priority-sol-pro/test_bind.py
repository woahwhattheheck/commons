# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

import bind
import materialize


def write_tree(root: Path, scheduler: bytes) -> dict[str, object]:
    root.mkdir(parents=True)
    (root / "main.py").write_text(
        "def agent(observation, configuration=None):\n"
        "    return {'farmer':['PASS'],'hands':[],'market':[]}\n"
    )
    (root / "scheduler.py").write_bytes(scheduler)
    (root / "SOURCE.json").write_text("{}\n")
    inventory = bind.inventory(root)
    return {
        "inventory": inventory,
        "closure": bind.closure_sha256(inventory),
        "scheduler_blob": materialize.git_blob_sha1(scheduler),
        "scheduler_sha": materialize.sha256(scheduler),
    }


def receipt(
    *,
    head: str,
    source: dict[str, object],
    result: dict[str, object],
    enabled: bool,
) -> dict[str, object]:
    return {
        "schema_version": 1,
        "operation": bind.EXPERIMENT,
        "experiment": bind.EXPERIMENT,
        "integration_head": head,
        "canonical_base_head": materialize.CANONICAL_BASE_HEAD,
        "feature": {
            "name": materialize.FEATURE,
            "enabled": enabled,
            "default": False,
        },
        "source": {
            "archive_path": "exports/titan-current.tar.gz",
            "archive_sha256": materialize.EXPECTED_ARCHIVE_SHA256,
            "archive_bytes": materialize.EXPECTED_ARCHIVE_BYTES,
            "source_manifest_sha256": (
                materialize.EXPECTED_SOURCE_MANIFEST_SHA256
            ),
            "runtime_files": materialize.EXPECTED_RUNTIME_FILES,
            "materialized_files": 3,
            "closure_sha256": source["closure"],
            "scheduler_git_blob_sha1": source["scheduler_blob"],
            "scheduler_sha256": source["scheduler_sha"],
        },
        "candidate": {
            "changed_files": ["scheduler.py"] if enabled else [],
            "closure_sha256": result["closure"],
            "scheduler_git_blob_sha1": result["scheduler_blob"],
            "scheduler_sha256": result["scheduler_sha"],
            "old_occurrences_before": 1,
            "old_occurrences_after": 0 if enabled else 1,
            "new_occurrences_before": 0,
            "new_occurrences_after": 1 if enabled else 0,
        },
    }


class BindTests(unittest.TestCase):
    def test_binds_exact_closures_and_wrapper_loads(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            control_root = root / "control"
            candidate_root = root / "candidate"
            control_data = write_tree(control_root, materialize.OLD)
            candidate_data = write_tree(candidate_root, materialize.NEW)
            head = "f" * 40
            control_receipt = receipt(
                head=head,
                source=control_data,
                result=control_data,
                enabled=False,
            )
            candidate_receipt = receipt(
                head=head,
                source=control_data,
                result=candidate_data,
                enabled=True,
            )
            control_path = root / "control.json"
            candidate_path = root / "candidate.json"
            control_path.write_text(json.dumps(control_receipt))
            candidate_path.write_text(json.dumps(candidate_receipt))
            result = bind.bind(
                control_root=control_root,
                candidate_root=candidate_root,
                control_receipt_path=control_path,
                candidate_receipt_path=candidate_path,
                output_dir=root / "bound",
                head=head,
            )
            self.assertNotEqual(
                result["control"]["closure_sha256"],
                result["candidate"]["closure_sha256"],
            )
            wrapper = Path(result["candidate"]["entry"])
            spec = importlib.util.spec_from_file_location(
                "_test_bound", wrapper
            )
            self.assertIsNotNone(spec)
            self.assertIsNotNone(spec.loader)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            self.assertEqual(
                module.agent({"step": 0}),
                {"farmer": ["PASS"], "hands": [], "market": []},
            )

    def test_binding_fails_after_tree_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            control_root = root / "control"
            candidate_root = root / "candidate"
            control_data = write_tree(control_root, materialize.OLD)
            candidate_data = write_tree(candidate_root, materialize.NEW)
            head = "e" * 40
            control_path = root / "control.json"
            candidate_path = root / "candidate.json"
            control_path.write_text(
                json.dumps(
                    receipt(
                        head=head,
                        source=control_data,
                        result=control_data,
                        enabled=False,
                    )
                )
            )
            candidate_path.write_text(
                json.dumps(
                    receipt(
                        head=head,
                        source=control_data,
                        result=candidate_data,
                        enabled=True,
                    )
                )
            )
            (candidate_root / "scheduler.py").write_bytes(
                materialize.NEW + b"# drift\n"
            )
            with self.assertRaisesRegex(
                bind.BindError, "detached from receipt"
            ):
                bind.bind(
                    control_root=control_root,
                    candidate_root=candidate_root,
                    control_receipt_path=control_path,
                    candidate_receipt_path=candidate_path,
                    output_dir=root / "bound",
                    head=head,
                )

    def test_control_cannot_be_enabled(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            control_root = root / "control"
            candidate_root = root / "candidate"
            control_data = write_tree(control_root, materialize.OLD)
            candidate_data = write_tree(candidate_root, materialize.NEW)
            head = "d" * 40
            bad_control = receipt(
                head=head,
                source=control_data,
                result=control_data,
                enabled=False,
            )
            bad_control["feature"]["enabled"] = True
            control_path = root / "control.json"
            candidate_path = root / "candidate.json"
            control_path.write_text(json.dumps(bad_control))
            candidate_path.write_text(
                json.dumps(
                    receipt(
                        head=head,
                        source=control_data,
                        result=candidate_data,
                        enabled=True,
                    )
                )
            )
            with self.assertRaisesRegex(bind.BindError, "control is not"):
                bind.bind(
                    control_root=control_root,
                    candidate_root=candidate_root,
                    control_receipt_path=control_path,
                    candidate_receipt_path=candidate_path,
                    output_dir=root / "bound",
                    head=head,
                )


if __name__ == "__main__":
    unittest.main()
