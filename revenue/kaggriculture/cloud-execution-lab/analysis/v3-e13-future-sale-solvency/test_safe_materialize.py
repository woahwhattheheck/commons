#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Adversarial filesystem and exact-generator contracts for safe materialization."""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest

HERE = Path(__file__).resolve().parent


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


safe = load_module("titan_v3_e13_safe_materializer", HERE / "safe_materialize.py")
ROOT = safe.find_repo_root(HERE)
GENERATOR, GENERATOR_PATH, GENERATOR_BYTES = safe.load_generator(ROOT)
SOURCE_PATH = (ROOT / GENERATOR.SOURCE_REL).resolve()
ENGINE_PATH = (ROOT / GENERATOR.ENGINE_REL).resolve()


class SafeMaterializationTests(unittest.TestCase):
    def test_exact_generator_binding(self):
        self.assertEqual(
            safe.git_blob_sha(GENERATOR_BYTES), safe.EXPECTED_GENERATOR_GIT_BLOB
        )
        self.assertEqual(
            GENERATOR.git_blob_sha(SOURCE_PATH.read_bytes()),
            GENERATOR.EXPECTED_SOURCE_GIT_BLOB,
        )
        self.assertEqual(
            GENERATOR.git_blob_sha(ENGINE_PATH.read_bytes()),
            GENERATOR.EXPECTED_ENGINE_GIT_BLOB,
        )

    def test_deterministic_candidate_and_receipt(self):
        with tempfile.TemporaryDirectory() as temporary:
            temporary = Path(temporary)
            payloads = []
            receipts = []
            for index in range(2):
                output = temporary / f"candidate-{index}.py"
                receipt = temporary / f"receipt-{index}.json"
                safe.materialize(ROOT, output, receipt)
                payloads.append(output.read_bytes())
                receipts.append(receipt.read_bytes())
            self.assertEqual(payloads[0], payloads[1])
            self.assertEqual(receipts[0], receipts[1])
            parsed = json.loads(receipts[0])
            self.assertFalse(parsed["custody"]["fixed_tmp_names_used"])
            self.assertFalse(parsed["claims"]["gameplay_strength"])

    def test_fixed_candidate_tmp_hardlink_trap_is_not_followed(self):
        source_before = SOURCE_PATH.read_bytes()
        with tempfile.TemporaryDirectory() as temporary:
            temporary = Path(temporary)
            output = temporary / "candidate.py"
            receipt = temporary / "receipt.json"
            trap = output.with_name(output.name + ".tmp")
            os.link(SOURCE_PATH, trap)
            safe.materialize(ROOT, output, receipt)
            self.assertEqual(SOURCE_PATH.read_bytes(), source_before)
            self.assertTrue(os.path.samefile(trap, SOURCE_PATH))
            self.assertNotEqual(output.read_bytes(), source_before)

    def test_fixed_receipt_tmp_hardlink_trap_is_not_followed(self):
        engine_before = ENGINE_PATH.read_bytes()
        with tempfile.TemporaryDirectory() as temporary:
            temporary = Path(temporary)
            output = temporary / "candidate.py"
            receipt = temporary / "receipt.json"
            trap = receipt.with_name(receipt.name + ".tmp")
            os.link(ENGINE_PATH, trap)
            safe.materialize(ROOT, output, receipt)
            self.assertEqual(ENGINE_PATH.read_bytes(), engine_before)
            self.assertTrue(os.path.samefile(trap, ENGINE_PATH))

    def test_candidate_hardlink_to_source_is_rejected_before_write(self):
        source_before = SOURCE_PATH.read_bytes()
        with tempfile.TemporaryDirectory() as temporary:
            temporary = Path(temporary)
            output = temporary / "candidate.py"
            receipt = temporary / "receipt.json"
            os.link(SOURCE_PATH, output)
            with self.assertRaisesRegex(safe.CustodyError, "same inode"):
                safe.materialize(ROOT, output, receipt)
            self.assertEqual(SOURCE_PATH.read_bytes(), source_before)
            self.assertFalse(receipt.exists())

    def test_receipt_hardlink_to_engine_is_rejected_before_write(self):
        engine_before = ENGINE_PATH.read_bytes()
        with tempfile.TemporaryDirectory() as temporary:
            temporary = Path(temporary)
            output = temporary / "candidate.py"
            receipt = temporary / "receipt.json"
            os.link(ENGINE_PATH, receipt)
            with self.assertRaisesRegex(safe.CustodyError, "same inode"):
                safe.materialize(ROOT, output, receipt)
            self.assertEqual(ENGINE_PATH.read_bytes(), engine_before)
            self.assertFalse(output.exists())

    def test_candidate_and_receipt_same_inode_are_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            temporary = Path(temporary)
            seed = temporary / "seed"
            seed.write_bytes(b"sentinel")
            output = temporary / "candidate.py"
            receipt = temporary / "receipt.json"
            os.link(seed, output)
            os.link(seed, receipt)
            with self.assertRaisesRegex(safe.CustodyError, "same inode"):
                safe.materialize(ROOT, output, receipt)
            self.assertEqual(seed.read_bytes(), b"sentinel")

    def test_direct_symlink_destination_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            temporary = Path(temporary)
            target = temporary / "target.py"
            target.write_bytes(b"sentinel")
            output = temporary / "candidate.py"
            output.symlink_to(target)
            receipt = temporary / "receipt.json"
            with self.assertRaisesRegex(safe.CustodyError, "must not be a symlink"):
                safe.materialize(ROOT, output, receipt)
            self.assertEqual(target.read_bytes(), b"sentinel")
            self.assertFalse(receipt.exists())

    def test_all_three_canonical_inputs_are_invalid_destinations(self):
        protected = (GENERATOR_PATH, SOURCE_PATH, ENGINE_PATH)
        with tempfile.TemporaryDirectory() as temporary:
            temporary = Path(temporary)
            for index, path in enumerate(protected):
                with self.subTest(path=path):
                    receipt = temporary / f"receipt-{index}.json"
                    with self.assertRaisesRegex(safe.CustodyError, "protected source"):
                        safe.materialize(ROOT, path, receipt)

    def test_generator_drift_fails_before_outputs_exist(self):
        with tempfile.TemporaryDirectory() as temporary:
            temporary = Path(temporary)
            for relative in (
                safe.GENERATOR_REL,
                GENERATOR.SOURCE_REL,
                GENERATOR.ENGINE_REL,
            ):
                target = temporary / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(ROOT / relative, target)
            generator = temporary / safe.GENERATOR_REL
            generator.write_bytes(generator.read_bytes() + b"\n")
            output = temporary / "candidate.py"
            receipt = temporary / "receipt.json"
            with self.assertRaisesRegex(safe.CustodyError, "generator Git blob mismatch"):
                safe.materialize(temporary, output, receipt)
            self.assertFalse(output.exists())
            self.assertFalse(receipt.exists())

    def test_no_fixed_tmp_files_are_created(self):
        with tempfile.TemporaryDirectory() as temporary:
            temporary = Path(temporary)
            output = temporary / "candidate.py"
            receipt = temporary / "receipt.json"
            safe.materialize(ROOT, output, receipt)
            self.assertFalse(output.with_name(output.name + ".tmp").exists())
            self.assertFalse(receipt.with_name(receipt.name + ".tmp").exists())
            leftovers = [p.name for p in temporary.iterdir() if p.name.endswith(".tmp")]
            self.assertEqual(leftovers, [])


if __name__ == "__main__":
    unittest.main()
