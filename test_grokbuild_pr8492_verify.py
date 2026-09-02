#!/usr/bin/env python3
"""Pin PR 8492 already-merged verify leftover. Do not remint the billing-lock receipt."""

from __future__ import annotations

import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VERIFY = ROOT / "p/grokbuild-pr8492-verify-20260902-01.md"

KEEP = {
    "p/grokbuild-open-door-guard-33694243180-billing-lock-20260902-01.md": "4d7812f8",
    "test_grokbuild_open_door_guard_33694243180_billing_lock.py": "b0579a7d",
    "open_door_guard.py": "4b053e43",
    "test_open_door_guard.py": "70ee5730",
    ".github/workflows/open-door-guard.yml": "6586644c",
}


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class TestGrokbuildPr8492Verify(unittest.TestCase):
    def test_keep_billing_lock_leftover_unread(self) -> None:
        for rel, prefix in KEEP.items():
            blob = git_blob(rel)
            self.assertTrue(
                blob.startswith(prefix),
                f"{rel} reminted: want {prefix} got {blob[:8]}",
            )

    def test_verify_receipt_cites_merged_pr(self) -> None:
        text = VERIFY.read_text(encoding="utf-8")
        self.assertIn("grokbuild-pr8492-verify-20260902-01", text)
        self.assertIn("https://github.com/woahwhattheheck/commons/pull/8492", text)
        self.assertIn("8042b19e119a5ba8927f659c2760b637f3263566", text)
        self.assertIn("aa4725d82ee16520eeaa96b73c456e0bf4a7c6c4", text)
        self.assertIn("ALREADY_MERGED_VERIFIED", text)
        self.assertIn("4d7812f8", text)
        self.assertIn("b0579a7d", text)
        self.assertIn("Did not remint", text)
        self.assertIn("issuecomment-5517952225", text)
        self.assertNotIn("buy.stripe.com", text)


if __name__ == "__main__":
    unittest.main()
