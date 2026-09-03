#!/usr/bin/env python3
"""Pin grok-build verify leftover for already-merged PR 8595. Do not remint the guard leftover."""

from __future__ import annotations

import subprocess
import unittest
from pathlib import Path

import open_door_guard as guard

ROOT = Path(__file__).resolve().parent
RECEIPT = ROOT / "p/grokbuild-pr8595-verify-1b4f521a-20260903.md"
LEFTOVER = ROOT / "p/grokbuild-open-door-guard-33717741083-billing-lock-20260903-01.md"
LEFTOVER_TEST = ROOT / "test_grokbuild_open_door_guard_33717741083_billing_lock.py"
SIBLING = ROOT / "p/grokbuild-open-door-guard-33699980139-billing-lock-20260903-01.md"
SIBLING_TEST = ROOT / "test_grokbuild_open_door_guard_33699980139_billing_lock.py"

KEEP = {
    "p/grokbuild-open-door-guard-33717741083-billing-lock-20260903-01.md": "d4c58153",
    "test_grokbuild_open_door_guard_33717741083_billing_lock.py": "3c6c37cd",
    "open_door_guard.py": "4b053e43",
    "test_open_door_guard.py": "70ee5730",
    ".github/workflows/open-door-guard.yml": "6586644c",
    "p/grokbuild-open-door-guard-33699980139-billing-lock-20260903-01.md": "81d9e0a0",
    "test_grokbuild_open_door_guard_33699980139_billing_lock.py": "d101998a",
}


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class TestGrokbuildPr8595Verify(unittest.TestCase):
    def test_keep_8595_leftover_and_guard_unread(self) -> None:
        for rel, prefix in KEEP.items():
            blob = git_blob(rel)
            self.assertTrue(
                blob.startswith(prefix),
                f"{rel} reminted: want {prefix} got {blob[:8]}",
            )

    def test_receipt_cites_8595_and_does_not_remint(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        leftover = LEFTOVER.read_text(encoding="utf-8")
        leftover_test = LEFTOVER_TEST.read_text(encoding="utf-8")
        sibling = SIBLING.read_text(encoding="utf-8")
        sibling_test = SIBLING_TEST.read_text(encoding="utf-8")
        self.assertIn("grokbuild-pr8595-verify-1b4f521a-20260903", text)
        self.assertIn(
            "woahwhattheheck/commons#8595@1b4f521a374b11a11af00a838cdeb044bcc8739b",
            text,
        )
        self.assertIn("https://github.com/woahwhattheheck/commons/pull/8595", text)
        self.assertIn("1b4f521a374b11a11af00a838cdeb044bcc8739b", text)
        self.assertIn("7de4c5b4f84483c18ef98b86b58f18a2262ab327", text)
        self.assertIn("e9f6ff71e5b549f3d790e913b0281bb778405d58", text)
        self.assertIn("d4c58153", text)
        self.assertIn("3c6c37cd", text)
        self.assertIn("ALREADY_MERGED_VERIFIED", text)
        self.assertIn("INTEGRATED — VERIFIED ON CURRENT MAIN", text)
        self.assertIn("DURABLE_ON_MAIN", text)
        self.assertIn("Did not remint leftover grokbuild-open-door-guard-33717741083-billing-lock-20260903-01", text)
        self.assertIn("Did not reopen #7915", text)
        self.assertNotEqual(text, leftover)
        self.assertNotEqual(text, sibling)
        self.assertNotEqual(Path(__file__).read_text(encoding="utf-8"), leftover_test)
        self.assertNotEqual(Path(__file__).read_text(encoding="utf-8"), sibling_test)
        self.assertNotIn("woahwhattheheck/commons#8595@", leftover)
        self.assertNotIn("buy.stripe.com", text)

    def test_original_leftover_unittest_still_green(self) -> None:
        proc = subprocess.run(
            ["python3", "-m", "unittest", "test_grokbuild_open_door_guard_33717741083_billing_lock.py"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
        self.assertIn("Ran 4 tests", proc.stderr + proc.stdout)

    def test_new_files_do_not_add_locks(self) -> None:
        added = [
            guard.AddedLine(
                "test_grokbuild_pr8595_verify_1b4f521a_20260903.py", 1, line
            )
            for line in Path(__file__).read_text(encoding="utf-8").splitlines()
        ]
        self.assertEqual(guard.scan_added(added), [])
        receipt_added = [
            guard.AddedLine(
                "p/grokbuild-pr8595-verify-1b4f521a-20260903.md",
                1,
                line,
            )
            for line in RECEIPT.read_text(encoding="utf-8").splitlines()
        ]
        self.assertEqual(guard.scan_added(receipt_added), [])


if __name__ == "__main__":
    unittest.main()
