#!/usr/bin/env python3
"""Pin unique leftover for already-merged PR 8590 verify. Do not remint original leftover."""

from __future__ import annotations

import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RECEIPT = ROOT / "p/grokbuild-pr8590-already-merged-verify-20260903-01.md"
ORIGINAL = ROOT / "p/grokbuild-tests-33717733992-billing-lock-20260903-01.md"
ORIGINAL_TEST = ROOT / "test_grokbuild_tests_33717733992_billing_lock.py"

KEEP = {
    "p/grokbuild-tests-33717733992-billing-lock-20260903-01.md": "e91d0547",
    "test_grokbuild_tests_33717733992_billing_lock.py": "41a9bcb5",
    "open_door_guard.py": "4b053e43",
}


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class TestGrokbuildPr8590AlreadyMergedVerify(unittest.TestCase):
    def test_original_leftover_unread(self) -> None:
        for rel, prefix in KEEP.items():
            blob = git_blob(rel)
            self.assertTrue(
                blob.startswith(prefix),
                f"{rel} reminted: want {prefix} got {blob[:8]}",
            )

    def test_receipt_is_unique_and_points_at_original(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        original = ORIGINAL.read_text(encoding="utf-8")
        self.assertIn("grokbuild-pr8590-already-merged-verify-20260903-01", text)
        self.assertIn("ALREADY_MERGED_VERIFIED", text)
        self.assertIn("https://github.com/woahwhattheheck/commons/pull/8590", text)
        self.assertIn("9ad71fc4c7fb3df878f17e6e83884363798d3013", text)
        self.assertIn("7dd18be7886fb73a622e1fa227c9c8aa262b1cdd", text)
        self.assertIn("f6daf48acdd325860f14847d3d9846bac370b949", text)
        self.assertIn("c9fce69e915e692a19b1f62af829f9354cfb7ba8", text)
        self.assertIn("e91d0547", text)
        self.assertIn("41a9bcb5", text)
        self.assertIn("leftover 4/4", text)
        self.assertIn("Did not remint original leftover", text)
        self.assertIn("Did not reopen #7915", text)
        self.assertIn(
            "woahwhattheheck/commons:tests:2890fde44250063aa66ef60735a7cc90407760a6:battery",
            text,
        )
        self.assertNotEqual(text, original)
        self.assertNotIn("grokbuild-pr8590-already-merged-verify-20260903-01", original)

    def test_original_leftover_battery_still_passes(self) -> None:
        proc = subprocess.run(
            [
                "python3",
                "-m",
                "unittest",
                "test_grokbuild_tests_33717733992_billing_lock.py",
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
        self.assertIn("Ran 4 tests", proc.stderr)

    def test_open_door_on_added_lines(self) -> None:
        import open_door_guard as guard

        added = [
            guard.AddedLine("test_grokbuild_pr8590_already_merged_verify.py", 1, line)
            for line in Path(__file__).read_text(encoding="utf-8").splitlines()
        ]
        added.extend(
            guard.AddedLine(
                "p/grokbuild-pr8590-already-merged-verify-20260903-01.md", 1, line
            )
            for line in RECEIPT.read_text(encoding="utf-8").splitlines()
        )
        self.assertEqual(guard.scan_added(added), [])


if __name__ == "__main__":
    unittest.main()
