#!/usr/bin/env python3
"""Pin unique leftover for PR 8491 #commons receipt. Do not remint 8491 leftover."""

from __future__ import annotations

import hashlib
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RECEIPT = ROOT / "p/grokbuild-pr8491-verify-20260902-01.md"
PRIOR = ROOT / "p/grokbuild-open-door-guard-33694402752-billing-lock-20260902-01.md"
PRIOR_TEST = ROOT / "test_grokbuild_open_door_guard_33694402752_billing_lock.py"

KEEP = {
    "p/grokbuild-open-door-guard-33694402752-billing-lock-20260902-01.md": "e3d789b6",
    "test_grokbuild_open_door_guard_33694402752_billing_lock.py": "9eb278db",
    "open_door_guard.py": "4b053e43",
    "test_open_door_guard.py": "70ee5730",
    ".github/workflows/open-door-guard.yml": "6586644c",
    "p/grokbuild-pr8481-verify-20260902-01.md": "ccbaff70",
    "p/latch-hub-eyes-wake-habit-20260902-01.md": "dc83d42c",
}


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class TestGrokbuildPr8491Verify(unittest.TestCase):
    def test_keep_unread_leftovers(self) -> None:
        for rel, prefix in KEEP.items():
            blob = git_blob(rel)
            self.assertTrue(
                blob.startswith(prefix),
                f"{rel} reminted: want {prefix} got {blob[:8]}",
            )

    def test_receipt_is_unique_same_id_land(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        prior = PRIOR.read_text(encoding="utf-8")
        self.assertIn("grokbuild-pr8491-verify-20260902-01", text)
        self.assertIn(
            "woahwhattheheck/commons#8491@4e75b540623fef8a3aa37e0a7afab4f2c0d27e68",
            text,
        )
        self.assertIn("https://github.com/woahwhattheheck/commons/pull/8491", text)
        self.assertIn("c950e77b89eaa859426967de2fd058a1b76ecbeb", text)
        self.assertIn("4e75b540623fef8a3aa37e0a7afab4f2c0d27e68", text)
        self.assertIn("e3d789b61e1242144740c1f54b5ab08954f94c33", text)
        self.assertIn("9eb278db7bb5e3e676d92a3d0dfda65f639da94e", text)
        self.assertIn("4b053e43", text)
        self.assertIn("IKvS3NW0MVsf", text)
        self.assertIn("ALREADY_MERGED", text)
        self.assertIn("EXTERNAL_BLOCKER", text)
        self.assertNotEqual(text, prior)
        self.assertNotIn("grokbuild-pr8491-verify-20260902-01", prior)
        self.assertNotEqual(
            Path(__file__).read_text(encoding="utf-8"),
            PRIOR_TEST.read_text(encoding="utf-8"),
        )
        body = text.split("---", 2)[2].lstrip("\n")
        self.assertEqual(
            hashlib.sha256(body.rstrip("\n").encode()).hexdigest(),
            "ba91e3669bf1db33c6a0eb52483978b15c9d0c315ba2fddbba6adbe803890d08",
        )

    def test_local_guard_still_passes(self) -> None:
        proc = subprocess.run(
            ["python3", "test_open_door_guard.py"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)


if __name__ == "__main__":
    unittest.main()
