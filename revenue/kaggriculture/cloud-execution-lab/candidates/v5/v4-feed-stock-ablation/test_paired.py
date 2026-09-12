#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import hashlib
from pathlib import Path
import tempfile
import unittest

import paired


class FeedStockPairedCustodyTest(unittest.TestCase):
    def test_capture_sha256_survives_origin_swap(self):
        raw = b"VALUE = 7\n"
        expected = hashlib.sha256(raw).hexdigest()
        with tempfile.TemporaryDirectory() as td:
            origin = Path(td) / "evaluator.py"
            origin.write_bytes(raw)
            captured = paired.capture_sha256(origin, expected)
            origin.write_bytes(b"VALUE = 99\n")
            module = paired.load_captured(captured, origin, "feed_stock_swap_capture")
            self.assertEqual(7, module.VALUE)
            self.assertNotEqual(captured, origin.read_bytes())

    def test_capture_sha256_survives_origin_delete(self):
        raw = b"VALUE = 11\n"
        expected = hashlib.sha256(raw).hexdigest()
        with tempfile.TemporaryDirectory() as td:
            origin = Path(td) / "pack.py"
            origin.write_bytes(raw)
            captured = paired.capture_sha256(origin, expected)
            origin.unlink()
            module = paired.load_captured(captured, origin, "feed_stock_delete_capture")
            self.assertEqual(11, module.VALUE)
            self.assertFalse(origin.exists())

    def test_capture_sha256_rejects_wrong_digest(self):
        raw = b"VALUE = 13\n"
        with tempfile.TemporaryDirectory() as td:
            origin = Path(td) / "bridge.py"
            origin.write_bytes(raw)
            with self.assertRaisesRegex(ValueError, "snapshot member SHA256 mismatch"):
                paired.capture_sha256(origin, hashlib.sha256(b"other").hexdigest())

    def test_load_captured_never_reopens_public_origin(self):
        captured = b"VALUE = 17\n"
        with tempfile.TemporaryDirectory() as td:
            public = Path(td) / "public-snapshot.py"
            public.write_bytes(b"VALUE = 101\n")
            module = paired.load_captured(captured, public, "feed_stock_public_poison")
            self.assertEqual(17, module.VALUE)
            public.unlink()
            self.assertEqual(17, module.VALUE)

    def test_private_loader_is_published_from_authenticated_capture(self):
        raw = b"VALUE = 23\n"
        expected = hashlib.sha256(raw).hexdigest()
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            origin = root / "snapshot" / "evaluate.py"
            origin.parent.mkdir()
            origin.write_bytes(raw)
            captured = paired.capture_sha256(origin, expected)
            origin.write_bytes(b"VALUE = 101\n")
            private = root / "private-runtime" / "evaluate.py"
            paired.write_private_runtime_bytes(captured, private, expected)
            self.assertEqual(raw, private.read_bytes())
            self.assertNotEqual(private.read_bytes(), origin.read_bytes())

    def test_private_loader_rejects_wrong_capture(self):
        raw = b"VALUE = 23\n"
        expected = hashlib.sha256(raw).hexdigest()
        with tempfile.TemporaryDirectory() as td:
            private = Path(td) / "private-runtime" / "evaluate.py"
            with self.assertRaisesRegex(
                ValueError, "private runtime bytes do not match authenticated SHA256"
            ):
                paired.write_private_runtime_bytes(b"VALUE = 24\n", private, expected)
            self.assertFalse(private.exists())

    def test_public_evidence_copy_is_not_execution_authority(self):
        raw = b"VALUE = 31\n"
        expected = hashlib.sha256(raw).hexdigest()
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            private_root = root / "private"
            private_root.mkdir()
            origin = private_root / "module.py"
            origin.write_bytes(raw)
            captured = paired.capture_sha256(origin, expected)
            module = paired.load_captured(captured, origin, "feed_stock_evidence_copy")
            public = root / "public-evidence"
            paired.copy_evidence_tree(private_root, public)
            (public / "module.py").write_bytes(b"VALUE = -1\n")
            self.assertEqual(31, module.VALUE)
            self.assertEqual(raw, origin.read_bytes())

    def test_copy_evidence_tree_refuses_existing_destination(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / "source"
            destination = root / "destination"
            source.mkdir()
            destination.mkdir()
            with self.assertRaises(FileExistsError):
                paired.copy_evidence_tree(source, destination)

    def test_summary_preserves_opponent_own_score_economics(self):
        cells = [
            {
                "opponent": "apex_v7",
                "status": "complete_pair",
                "engaged": True,
                "score_delta": {"own": 3, "rival": 1, "margin": 2},
            },
            {
                "opponent": "apex_v7",
                "status": "complete_pair",
                "engaged": False,
                "score_delta": {"own": -1, "rival": -1, "margin": 0},
            },
        ]
        result = paired.summarize(cells)["apex_v7"]
        self.assertEqual(1, result["engaged"])
        self.assertEqual(1, result["cold"])
        self.assertEqual(1, result["own_improved"])
        self.assertEqual(1, result["own_regressed"])
        self.assertEqual(1, result["mean_own_score_delta"])


if __name__ == "__main__":
    unittest.main()
