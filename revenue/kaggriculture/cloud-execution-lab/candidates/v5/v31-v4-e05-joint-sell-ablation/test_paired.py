# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import hashlib
from pathlib import Path
import tempfile
import unittest

import paired


class PairedHelpersTest(unittest.TestCase):
    def test_git_blob_bytes_matches_git_formula(self):
        raw = b"abc\n"
        expected = hashlib.sha1(b"blob 4\0abc\n").hexdigest()
        self.assertEqual(paired.git_blob_bytes(raw), expected)

    def test_capture_git_blob_single_read(self):
        raw = b"x = 1\n"
        expected = paired.git_blob_bytes(raw)
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "helper.py"
            path.write_bytes(raw)
            captured = paired.capture_git_blob(path, expected)
            path.write_bytes(b"poison = True\n")
            self.assertEqual(captured, raw)

    def test_load_captured_does_not_reopen_origin(self):
        raw = b"VALUE = 7\n"
        with tempfile.TemporaryDirectory() as td:
            origin = Path(td) / "module.py"
            origin.write_bytes(b"VALUE = 99\n")
            module = paired.load_captured(raw, origin, "e05_test_captured")
            self.assertEqual(module.VALUE, 7)

    def test_margin_requires_complete_719(self):
        self.assertEqual(paired.margin({"status": "complete", "steps": 719, "scores": [10, 4]}, 0), 6)
        self.assertIsNone(paired.margin({"status": "complete", "steps": 718, "scores": [10, 4]}, 0))
        self.assertIsNone(paired.margin({"status": "error", "steps": 719, "scores": [10, 4]}, 0))

    def test_summary_keeps_opponents_separate(self):
        cells = [
            {"opponent": "apex_v7", "margin_delta": 5},
            {"opponent": "apex_v7", "margin_delta": -1},
            {"opponent": "arlene_v14", "margin_delta": 0},
        ]
        value = paired.summarize(cells)
        self.assertEqual(value["complete_pairs"], 3)
        self.assertEqual(value["opponents"]["apex_v7"]["mean_margin_delta"], 2)
        self.assertEqual(value["opponents"]["arlene_v14"]["unchanged"], 1)


if __name__ == "__main__":
    unittest.main()
