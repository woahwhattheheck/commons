#!/usr/bin/env python3
"""Pin unique leftover for already-merged PR 8583 verify. Do not remint original leftover."""

from __future__ import annotations

import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RECEIPT = ROOT / "p/grokbuild-pr8583-already-merged-verify-20260903-01.md"
ORIGINAL = ROOT / "p/grokbuild-main-range-verify-33717084528-billing-lock-20260903-01.md"
ORIGINAL_TEST = ROOT / "test_grokbuild_main_range_verify_33717084528_billing_lock.py"

KEEP = {
    "p/grokbuild-main-range-verify-33717084528-billing-lock-20260903-01.md": "2b0fd9c9",
    "test_grokbuild_main_range_verify_33717084528_billing_lock.py": "3e89a404",
    "open_door_guard.py": "4b053e43",
}


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class TestGrokbuildPr8583AlreadyMergedVerify(unittest.TestCase):
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
        self.assertIn("grokbuild-pr8583-already-merged-verify-20260903-01", text)
        self.assertIn("ALREADY_MERGED_VERIFIED", text)
        self.assertIn("https://github.com/woahwhattheheck/commons/pull/8583", text)
        self.assertIn("2890fde44250063aa66ef60735a7cc90407760a6", text)
        self.assertIn("0ddbdaf51fee6870caf1572ff53db1293852b72b", text)
        self.assertIn("f13f3552dc3d8ad812cc6f26e48e97eb8cad9791", text)
        self.assertIn("2b0fd9c9", text)
        self.assertIn("3e89a404", text)
        self.assertIn("leftover 4/4", text)
        self.assertIn("Did not remint original leftover", text)
        self.assertIn("Did not reopen #7915", text)
        self.assertIn(
            "woahwhattheheck/commons:main-range-verify:f13f3552dc3d8ad812cc6f26e48e97eb8cad9791:verify-range",
            text,
        )
        self.assertNotEqual(text, original)
        self.assertNotIn("grokbuild-pr8583-already-merged-verify-20260903-01", original)

    def test_original_leftover_battery_still_passes(self) -> None:
        proc = subprocess.run(
            [
                "python3",
                "-m",
                "unittest",
                "test_grokbuild_main_range_verify_33717084528_billing_lock.py",
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
        self.assertIn("Ran 4 tests", proc.stderr)


if __name__ == "__main__":
    unittest.main()
