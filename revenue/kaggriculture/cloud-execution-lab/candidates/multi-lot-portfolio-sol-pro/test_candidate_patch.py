# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import hashlib
from pathlib import Path
import unittest

import candidate_patch as patch

HERE = Path(__file__).resolve().parent
LAB = HERE.parents[1]


class ExactPatchContracts(unittest.TestCase):
    def test_canonical_scheduler_blob_and_all_seams(self):
        raw = (LAB / "scheduler.py").read_bytes()
        self.assertEqual(patch.git_blob_sha(raw), patch.EXPECTED_SCHEDULER_GIT_BLOB)
        transformed = patch.patch_scheduler_bytes(raw)
        text = transformed.decode("utf-8")
        self.assertIn("from multi_lot_portfolio import PortfolioError, select_portfolio", text)
        self.assertIn("admitted=[]", text)
        self.assertIn("decision=select_portfolio", text)
        self.assertEqual(text.count("decision=select_portfolio"), 1)
        compile(transformed, "scheduler.py", "exec")

    def test_blob_drift_fails_before_text_transform(self):
        raw = (LAB / "scheduler.py").read_bytes() + b"\n"
        with self.assertRaisesRegex(RuntimeError, "scheduler Git blob drift"):
            patch.patch_scheduler_bytes(raw)

    def test_patched_bytes_are_deterministic(self):
        raw = (LAB / "scheduler.py").read_bytes()
        a = patch.patch_scheduler_bytes(raw)
        b = patch.patch_scheduler_bytes(raw)
        self.assertEqual(a, b)
        self.assertEqual(hashlib.sha256(a).hexdigest(), hashlib.sha256(b).hexdigest())


if __name__ == "__main__":
    unittest.main()
