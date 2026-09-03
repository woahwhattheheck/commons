#!/usr/bin/env python3
"""Pin grok-build verify leftover for already-merged PR 8596. Do not remint the guard leftover."""

from __future__ import annotations

import subprocess
import unittest
from pathlib import Path

import open_door_guard as guard

ROOT = Path(__file__).resolve().parent
RECEIPT = ROOT / "p/grokbuild-pr8596-verify-20260903-01.md"
LEFTOVER = ROOT / "p/grokbuild-open-door-guard-33718116356-billing-lock-20260903-01.md"
LEFTOVER_TEST = ROOT / "test_grokbuild_open_door_guard_33718116356_billing_lock.py"
SIBLING = ROOT / "p/grokbuild-open-door-guard-33717733987-billing-lock-20260903-01.md"
SIBLING_TEST = ROOT / "test_grokbuild_open_door_guard_33717733987_billing_lock.py"

KEEP = {
    "p/grokbuild-open-door-guard-33718116356-billing-lock-20260903-01.md": "25781cf5",
    "test_grokbuild_open_door_guard_33718116356_billing_lock.py": "2166e689",
    "open_door_guard.py": "4b053e43",
    "test_open_door_guard.py": "70ee5730",
    ".github/workflows/open-door-guard.yml": "6586644c",
    "p/grokbuild-open-door-guard-33717733987-billing-lock-20260903-01.md": "a0af1282",
    "test_grokbuild_open_door_guard_33717733987_billing_lock.py": "0269ac73",
}


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class TestGrokbuildPr8596Verify(unittest.TestCase):
    def test_keep_8596_leftover_and_guard_unread(self) -> None:
        for rel, prefix in KEEP.items():
            blob = git_blob(rel)
            self.assertTrue(
                blob.startswith(prefix),
                f"{rel} reminted: want {prefix} got {blob[:8]}",
            )

    def test_receipt_cites_8596_and_does_not_remint(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        leftover = LEFTOVER.read_text(encoding="utf-8")
        leftover_test = LEFTOVER_TEST.read_text(encoding="utf-8")
        sibling = SIBLING.read_text(encoding="utf-8")
        sibling_test = SIBLING_TEST.read_text(encoding="utf-8")
        self.assertIn("grokbuild-pr8596-verify-20260903-01", text)
        self.assertIn(
            "woahwhattheheck/commons#8596@57627c6efeeee33aec87672c7761ad87f7f92f8e",
            text,
        )
        self.assertIn("https://github.com/woahwhattheheck/commons/pull/8596", text)
        self.assertIn("57627c6efeeee33aec87672c7761ad87f7f92f8e", text)
        self.assertIn("470d46da58517c9400c1120b5612a4f4e939c4f0", text)
        self.assertIn("25781cf5", text)
        self.assertIn("2166e689", text)
        self.assertIn("ALREADY_MERGED_VERIFIED", text)
        self.assertIn("INTEGRATED — VERIFIED ON CURRENT MAIN", text)
        self.assertIn("DURABLE_ON_MAIN", text)
        self.assertIn("Did not remint leftover grokbuild-open-door-guard-33718116356-billing-lock-20260903-01", text)
        self.assertIn("Did not reopen #7915", text)
        self.assertNotEqual(text, leftover)
        self.assertNotEqual(text, sibling)
        self.assertNotEqual(Path(__file__).read_text(encoding="utf-8"), leftover_test)
        self.assertNotEqual(Path(__file__).read_text(encoding="utf-8"), sibling_test)
        self.assertNotIn("woahwhattheheck/commons#8596@", leftover)
        self.assertNotIn("buy.stripe.com", text)

    def test_original_leftover_unittest_still_green(self) -> None:
        proc = subprocess.run(
            ["python3", "-m", "unittest", "test_grokbuild_open_door_guard_33718116356_billing_lock.py"],
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
                "test_grokbuild_pr8596_verify_20260903_01.py", 1, line
            )
            for line in Path(__file__).read_text(encoding="utf-8").splitlines()
        ]
        self.assertEqual(guard.scan_added(added), [])
        receipt_added = [
            guard.AddedLine(
                "p/grokbuild-pr8596-verify-20260903-01.md",
                1,
                line,
            )
            for line in RECEIPT.read_text(encoding="utf-8").splitlines()
        ]
        self.assertEqual(guard.scan_added(receipt_added), [])


if __name__ == "__main__":
    unittest.main()
