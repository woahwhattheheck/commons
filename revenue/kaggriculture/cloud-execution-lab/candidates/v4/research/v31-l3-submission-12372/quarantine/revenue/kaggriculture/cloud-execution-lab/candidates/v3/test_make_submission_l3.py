# SPDX-License-Identifier: Apache-2.0
"""Fail-closed contracts for the V3.1 L3 submission-only promotion transform."""
from __future__ import annotations

import copy
import unittest
from pathlib import Path

import make_submission as ms

HERE = Path(__file__).resolve().parent


class L3SubmissionTransformTests(unittest.TestCase):
    def test_real_router_is_one_seam_and_roundtrips_exactly(self):
        original = (HERE / "overlay" / "r04_full_router.py").read_bytes()
        files = {"r04_full_router.py": original, "sentinel": b"unchanged"}
        before = copy.deepcopy(files)
        out = ms.apply_l3_no_late_sale_advance(files)

        self.assertEqual(files, before, "input mapping must not mutate")
        self.assertEqual(out["sentinel"], b"unchanged")
        src = out["r04_full_router.py"].decode("utf-8")
        self.assertEqual(src.count("    if step < 648:\n"), 1)
        self.assertEqual(src.count(ms.L3_REPLACEMENT), 1)
        self.assertNotIn(ms.L3_SEAM, src.splitlines(keepends=True))
        compile(src, "r04_full_router.py", "exec")

        restored = src.replace(ms.L3_REPLACEMENT, ms.L3_SEAM, 1).encode("utf-8")
        self.assertEqual(restored, original, "L3 must be the only router-source delta")

    def test_missing_seam_fails_closed(self):
        with self.assertRaisesRegex(RuntimeError, r"count 0 != 1"):
            ms.apply_l3_no_late_sale_advance({"r04_full_router.py": b"pass\n"})

    def test_duplicate_seam_fails_closed(self):
        duplicate = (ms.L3_SEAM + ms.L3_SEAM).encode("utf-8")
        with self.assertRaisesRegex(RuntimeError, r"count 2 != 1"):
            ms.apply_l3_no_late_sale_advance({"r04_full_router.py": duplicate})

    def test_transform_changes_only_router_bytes(self):
        original = (HERE / "overlay" / "r04_full_router.py").read_bytes()
        files = {
            "r04_full_router.py": original,
            "TITAN-CONFIG.json": b'{"r04_sale_window": false}\n',
            "other.py": b"x = 1\n",
        }
        out = ms.apply_l3_no_late_sale_advance(files)
        self.assertEqual(set(out), set(files))
        self.assertNotEqual(out["r04_full_router.py"], original)
        self.assertEqual(out["TITAN-CONFIG.json"], files["TITAN-CONFIG.json"])
        self.assertEqual(out["other.py"], files["other.py"])

    def test_threshold_is_exact_promoted_648(self):
        self.assertEqual(ms.L3_STEP, 648)
        self.assertIn("if step < 648", ms.L3_REPLACEMENT)


if __name__ == "__main__":
    unittest.main(verbosity=2)
