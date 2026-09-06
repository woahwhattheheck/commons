#!/usr/bin/env python3
"""Pin grok-build verify leftover for already-merged PR 8642. Do not remint the open-door-guard leftover."""

from __future__ import annotations

import subprocess
import unittest
from pathlib import Path

import open_door_guard as guard

ROOT = Path(__file__).resolve().parent
RECEIPT = ROOT / "p/grok-build-pr8642-intake-20260903-01.md"
LEFTOVER = ROOT / "p/grokbuild-open-door-guard-33723631068-billing-lock-20260903-01.md"
LEFTOVER_TEST = ROOT / "test_grokbuild_open_door_guard_33723631068_billing_lock.py"
SIBLING = ROOT / "p/grok-build-repo-pulse-billing-lock-20260903-01.md"
PRIOR = ROOT / "p/grokbuild-open-door-guard-33718116356-billing-lock-20260903-01.md"

KEEP = {
    "p/grokbuild-open-door-guard-33723631068-billing-lock-20260903-01.md": "ba9914fd",
    "test_grokbuild_open_door_guard_33723631068_billing_lock.py": "ae8481c9",
    "p/grok-build-repo-pulse-billing-lock-20260903-01.md": "b6e5953c",
    "p/grokbuild-open-door-guard-33718116356-billing-lock-20260903-01.md": "25781cf5",
    "open_door_guard.py": "861958e9",
    "test_open_door_guard.py": "2fb0d87b",
    ".github/workflows/open-door-guard.yml": "c2121049",
}


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class TestGrokbuildPr8642Intake(unittest.TestCase):
    def test_keep_8642_leftover_and_guard_unread(self) -> None:
        for rel, prefix in KEEP.items():
            blob = git_blob(rel)
            self.assertTrue(
                blob.startswith(prefix),
                f"{rel} reminted: want {prefix} got {blob[:8]}",
            )

    def test_receipt_cites_8642_and_does_not_remint(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        leftover = LEFTOVER.read_text(encoding="utf-8")
        leftover_test = LEFTOVER_TEST.read_text(encoding="utf-8")
        sibling = SIBLING.read_text(encoding="utf-8")
        prior = PRIOR.read_text(encoding="utf-8")
        self.assertIn("grok-build-pr8642-intake-20260903-01", text)
        self.assertIn(
            "woahwhattheheck/commons#8642@5afba38205d7ef3d7203b3968950b1f541d4bd20",
            text,
        )
        self.assertIn("https://github.com/woahwhattheheck/commons/pull/8642", text)
        self.assertIn("5afba38205d7ef3d7203b3968950b1f541d4bd20", text)
        self.assertIn("16bd686f39bc4f861599abcbeed94b9aa543097b", text)
        self.assertIn("fb3efe439f91eb9bfc85d4b96f42494602e885fe", text)
        self.assertIn("ba9914fd", text)
        self.assertIn("509c2b22", text)
        self.assertIn("ALREADY_MERGED_VERIFIED", text)
        self.assertIn("INTEGRATED — VERIFIED ON CURRENT MAIN", text)
        self.assertIn("DURABLE_ON_MAIN", text)
        self.assertIn(
            "Did not remint leftover grokbuild-open-door-guard-33723631068-billing-lock-20260903-01",
            text,
        )
        self.assertIn("Did not reopen #7915", text)
        self.assertIn("Did not reopen #8633", text)
        self.assertIn("GppdwbXSKqu2", text)
        self.assertNotEqual(text, leftover)
        self.assertNotEqual(text, sibling)
        self.assertNotEqual(text, prior)
        self.assertNotEqual(Path(__file__).read_text(encoding="utf-8"), leftover_test)
        self.assertNotIn("woahwhattheheck/commons#8642@", leftover)
        self.assertNotIn("buy.stripe.com", text)

    def test_original_leftover_unittest_still_green(self) -> None:
        proc = subprocess.run(
            [
                "python3",
                "-m",
                "unittest",
                "test_grokbuild_open_door_guard_33723631068_billing_lock",
            ],
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
                "test_grokbuild_pr8642_intake_20260903_01.py", 1, line
            )
            for line in Path(__file__).read_text(encoding="utf-8").splitlines()
        ]
        self.assertEqual(guard.scan_added(added), [])
        receipt_added = [
            guard.AddedLine(
                "p/grok-build-pr8642-intake-20260903-01.md",
                1,
                line,
            )
            for line in RECEIPT.read_text(encoding="utf-8").splitlines()
        ]
        self.assertEqual(guard.scan_added(receipt_added), [])


if __name__ == "__main__":
    unittest.main()
