#!/usr/bin/env python3
"""Pin grok-build verify leftover for already-merged PR 8638. Do not remint the owner-net leftover."""

from __future__ import annotations

import subprocess
import unittest
from pathlib import Path

import open_door_guard as guard

ROOT = Path(__file__).resolve().parent
RECEIPT = ROOT / "p/grokbuild-pr8638-intake-verify-20260903-01.md"
LEFTOVER = ROOT / "p/grok-build-owner-net-33723510040-billing-lock-20260903-01.md"
LEFTOVER_TEST = ROOT / "test_grokbuild_owner_net_33723510040_billing_lock.py"

KEEP = {
    "p/grok-build-owner-net-33723510040-billing-lock-20260903-01.md": "6a2c8239",
    "test_grokbuild_owner_net_33723510040_billing_lock.py": "2ef5c846",
    ".github/workflows/owner-net.yml": "5df56a0a",
    "owner_net.py": "941b0d8a",
    "owner.json": "dc6c0592",
    "test_owner_hash.py": "0f0e6870",
    "open_door_guard.py": "861958e9",
    "fix_first.py": "a57aee1c",
}


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class TestGrokbuildPr8638IntakeVerify(unittest.TestCase):
    def test_keep_8638_leftover_and_persist_tree_unread(self) -> None:
        for rel, prefix in KEEP.items():
            blob = git_blob(rel)
            self.assertTrue(
                blob.startswith(prefix),
                f"{rel} reminted: want {prefix} got {blob[:8]}",
            )

    def test_receipt_cites_8638_and_does_not_remint(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        leftover = LEFTOVER.read_text(encoding="utf-8")
        leftover_test = LEFTOVER_TEST.read_text(encoding="utf-8")
        self.assertIn("grokbuild-pr8638-intake-verify-20260903-01", text)
        self.assertIn(
            "woahwhattheheck/commons#8638@4e7d788418bc4dbe82a85ae30efc0b1b3d7a4682",
            text,
        )
        self.assertIn("https://github.com/woahwhattheheck/commons/pull/8638", text)
        self.assertIn("4e7d788418bc4dbe82a85ae30efc0b1b3d7a4682", text)
        self.assertIn("010ad9a30d67c13fcbc517f2c80c26ccba2cfc31", text)
        self.assertIn("0975e08c23eac8786f05d5cf8d06123cec94575c", text)
        self.assertIn("bf237e02c8e9b594e983c2eededbc7aec6340842", text)
        self.assertIn("6a2c8239", text)
        self.assertIn("13e008cf", text)
        self.assertIn("ALREADY_MERGED_VERIFIED", text)
        self.assertIn("INTEGRATED — VERIFIED ON CURRENT MAIN", text)
        self.assertIn("DURABLE_ON_MAIN", text)
        self.assertIn(
            "Did not remint leftover grok-build-owner-net-33723510040-billing-lock-20260903-01",
            text,
        )
        self.assertIn("x7cbLgmccqfG", text)
        self.assertNotEqual(text, leftover)
        self.assertNotEqual(Path(__file__).read_text(encoding="utf-8"), leftover_test)
        self.assertNotIn("woahwhattheheck/commons#8638@", leftover)
        self.assertNotIn("buy.stripe.com", text)

    def test_original_leftover_unittest_still_green(self) -> None:
        proc = subprocess.run(
            ["python3", "-m", "unittest", "test_grokbuild_owner_net_33723510040_billing_lock"],
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
                "test_grokbuild_pr8638_intake_verify_20260903_01.py", 1, line
            )
            for line in Path(__file__).read_text(encoding="utf-8").splitlines()
        ]
        self.assertEqual(guard.scan_added(added), [])
        receipt_added = [
            guard.AddedLine(
                "p/grokbuild-pr8638-intake-verify-20260903-01.md",
                1,
                line,
            )
            for line in RECEIPT.read_text(encoding="utf-8").splitlines()
        ]
        self.assertEqual(guard.scan_added(receipt_added), [])


if __name__ == "__main__":
    unittest.main()
