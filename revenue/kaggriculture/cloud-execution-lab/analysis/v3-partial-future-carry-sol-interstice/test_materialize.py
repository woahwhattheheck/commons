# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import copy
import os
from pathlib import Path
import shutil
import tempfile
import unittest

import materialize as lane

HERE = Path(__file__).resolve().parent
DEFAULT_SOURCE = HERE.parents[1] / "runtime" / "variants" / "v2"


def source_path() -> Path:
    return Path(os.environ.get("TITAN_V2_SOURCE", DEFAULT_SOURCE)).resolve()


class MaterializeTests(unittest.TestCase):
    def test_exact_materialization_is_scheduler_only_and_source_immutable(self):
        source = source_path()
        before = lane.inventory(source)
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "candidate"
            receipt = lane.materialize(source, output)
            self.assertEqual(receipt["operation"], lane.OPERATION)
            self.assertEqual(receipt["candidate"]["changed_files"], ["scheduler.py"])
            self.assertEqual(
                receipt["candidate"]["scheduler_git_blob_sha1"],
                lane.EXPECTED_PATCHED_SCHEDULER_BLOB,
            )
            self.assertEqual(
                receipt["candidate"]["scheduler_sha256"],
                lane.EXPECTED_PATCHED_SCHEDULER_SHA256,
            )
            self.assertEqual(lane.inventory(source), before)
            after = lane.inventory(output)
            changed = [
                name
                for name in before
                if before[name]["sha256"] != after[name]["sha256"]
            ]
            self.assertEqual(changed, ["scheduler.py"])
            compile(
                (output / "scheduler.py").read_text(encoding="utf-8"),
                str(output / "scheduler.py"),
                "exec",
            )

    def test_each_patch_contract_is_exact(self):
        original = (source_path() / "scheduler.py").read_bytes()
        patched, records = lane._apply_exact_patches(original)
        self.assertEqual(lane.git_blob_sha1(patched), lane.EXPECTED_PATCHED_SCHEDULER_BLOB)
        self.assertEqual(lane.sha256(patched), lane.EXPECTED_PATCHED_SCHEDULER_SHA256)
        self.assertEqual([row["label"] for row in records], [row[0] for row in lane.PATCHES])
        for record in records:
            self.assertEqual(record["old_occurrences_before"], 1)
            self.assertEqual(record["old_occurrences_after"], 0)
            self.assertEqual(record["new_occurrences_before"], 0)
            self.assertEqual(record["new_occurrences_after"], 1)

    def test_wrong_frozen_scheduler_fails_closed_before_copy(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source"
            output = root / "output"
            shutil.copytree(source_path(), source)
            scheduler = source / "scheduler.py"
            scheduler.write_bytes(scheduler.read_bytes() + b"\n")
            with self.assertRaisesRegex(lane.MaterializeError, "blob mismatch"):
                lane.materialize(source, output)
            self.assertFalse(output.exists())

    def test_duplicate_patch_anchor_fails_closed(self):
        original = (source_path() / "scheduler.py").read_bytes()
        label, old, _new = lane.PATCHES[1]
        corrupt = original + old.encode("utf-8")
        with self.assertRaisesRegex(lane.MaterializeError, label):
            lane._apply_exact_patches(corrupt)

    def test_output_inside_source_is_rejected(self):
        source = source_path()
        with self.assertRaisesRegex(lane.MaterializeError, "nested inside source"):
            lane.materialize(source, source / "forbidden-output")

    def test_existing_output_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "existing"
            output.mkdir()
            with self.assertRaisesRegex(lane.MaterializeError, "already exists"):
                lane.materialize(source_path(), output)

    def test_patch_metadata_does_not_mutate_global_contract(self):
        snapshot = copy.deepcopy(lane.PATCHES)
        lane._apply_exact_patches((source_path() / "scheduler.py").read_bytes())
        self.assertEqual(lane.PATCHES, snapshot)


if __name__ == "__main__":
    unittest.main()
