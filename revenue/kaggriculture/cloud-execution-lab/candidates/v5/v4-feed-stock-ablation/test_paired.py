# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import hashlib
from pathlib import Path
import tempfile
import unittest

import paired


class PairedCustodyTest(unittest.TestCase):
    def test_load_captured_does_not_reopen_origin(self):
        raw = b"VALUE = 7\n"
        with tempfile.TemporaryDirectory() as td:
            origin = Path(td) / "module.py"
            origin.write_bytes(b"VALUE = 99\n")
            module = paired.load_captured(raw, origin, "feed_stock_test_captured")
            self.assertEqual(module.VALUE, 7)

    def test_captured_harness_survives_source_swap_after_auth(self):
        raw = b"VALUE = 7\n"
        expected = hashlib.sha256(raw).hexdigest()
        with tempfile.TemporaryDirectory() as td:
            origin = Path(td) / "evaluator.py"
            origin.write_bytes(raw)
            captured = paired.capture_sha256(origin, expected)
            origin.write_bytes(b"VALUE = 99\n")
            module = paired.load_captured(captured, origin, "feed_stock_swap_captured")
            self.assertEqual(module.VALUE, 7)
            self.assertNotEqual(origin.read_bytes(), captured)

    def test_captured_harness_survives_source_delete_after_auth(self):
        raw = b"VALUE = 11\n"
        expected = hashlib.sha256(raw).hexdigest()
        with tempfile.TemporaryDirectory() as td:
            origin = Path(td) / "pack.py"
            origin.write_bytes(raw)
            captured = paired.capture_sha256(origin, expected)
            origin.unlink()
            module = paired.load_captured(captured, origin, "feed_stock_delete_captured")
            self.assertEqual(module.VALUE, 11)
            self.assertFalse(origin.exists())

    def test_private_loader_uses_capture_not_public_origin(self):
        raw = b"VALUE = 23\n"
        expected = hashlib.sha256(raw).hexdigest()
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            visible = root / "visible-loader.py"
            visible.write_bytes(raw)
            captured = paired.capture_sha256(visible, expected)
            visible.write_bytes(b"VALUE = 101\n")
            private = root / "private-runtime" / "evaluate.py"
            self.assertEqual(
                paired.write_private_runtime_bytes(captured, private, expected), private
            )
            self.assertEqual(private.read_bytes(), raw)
            self.assertNotEqual(private.read_bytes(), visible.read_bytes())

    def test_private_loader_rejects_wrong_captured_digest(self):
        raw = b"VALUE = 23\n"
        expected = hashlib.sha256(raw).hexdigest()
        with tempfile.TemporaryDirectory() as td:
            private = Path(td) / "private-runtime" / "evaluate.py"
            with self.assertRaisesRegex(
                ValueError, "private runtime bytes do not match authenticated SHA256"
            ):
                paired.write_private_runtime_bytes(b"VALUE = 24\n", private, expected)
            self.assertFalse(private.exists())

    def test_capture_sha256_rejects_wrong_digest(self):
        raw = b"VALUE = 31\n"
        with tempfile.TemporaryDirectory() as td:
            origin = Path(td) / "bridge.py"
            origin.write_bytes(raw)
            with self.assertRaisesRegex(ValueError, "snapshot member SHA256 mismatch"):
                paired.capture_sha256(origin, "0" * 64)

    def test_schema_rotated_for_harness_execution_receipt(self):
        self.assertEqual("astra.v5.v4-feed-stock-ablation.v2", paired.SCHEMA)


if __name__ == "__main__":
    unittest.main()
