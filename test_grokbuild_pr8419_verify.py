#!/usr/bin/env python3
"""Pin grok-build verify leftover for already-merged PR 8419. Do not remint collision-notice leftover."""

from __future__ import annotations

import hashlib
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RECEIPT = ROOT / "p/grokbuild-pr8419-verify-20260902-01.md"
PRIOR = ROOT / "p/grokbuild-pr-collision-notice-33689085107-billing-lock-20260902-01.md"
ORIGINAL = ROOT / "p/cursor-merge-on-pr-20260902-01.md"

KEEP = {
    "p/grokbuild-pr-collision-notice-33689085107-billing-lock-20260902-01.md": "594b5e71",
    "test_grokbuild_pr_collision_notice_33689085107_billing_lock.py": "4888459d",
    "pr_collision_notice.py": "39dc815a",
    "test_pr_collision_notice.py": "a4890883",
    ".github/workflows/pr-collision-notice.yml": "b0a853dd",
    "p/cursor-merge-on-pr-20260902-01.md": "22b63e25",
    "p/cursor-merge-on-pr-readback-20260902-01.md": "e160b2c3",
}

BODY_SHA256 = "0382eb41780f39fb6cfb83d3230ff6e8db4c027b9fa61d7cef582e39fc4d068a"


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


def receipt_body(text: str) -> str:
    parts = text.split("---\n", 2)
    return parts[2].rstrip("\n") if len(parts) >= 3 else text


class TestGrokbuildPr8419Verify(unittest.TestCase):
    def test_keep_8419_leftover_and_helper_unread(self) -> None:
        for rel, prefix in KEEP.items():
            blob = git_blob(rel)
            self.assertTrue(
                blob.startswith(prefix),
                f"{rel} reminted: want {prefix} got {blob[:8]}",
            )

    def test_leftover_collision_notice_tests_still_pass(self) -> None:
        proc = subprocess.run(
            ["python3", "test_grokbuild_pr_collision_notice_33689085107_billing_lock.py"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        out = (proc.stdout or "") + (proc.stderr or "")
        self.assertEqual(proc.returncode, 0, msg=out)
        self.assertIn("Ran 4 tests", out)
        self.assertIn("OK", out)

    def test_receipt_cites_8419_and_does_not_remint(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        prior = PRIOR.read_text(encoding="utf-8")
        original = ORIGINAL.read_text(encoding="utf-8")
        body = receipt_body(text)
        self.assertEqual(hashlib.sha256(body.encode("utf-8")).hexdigest(), BODY_SHA256)
        self.assertIn("grokbuild-pr8419-verify-20260902-01", text)
        self.assertIn(
            "woahwhattheheck/commons#8419@e1716b3506927b4b8ad50ebe591c73cbabb37a58",
            text,
        )
        self.assertIn("https://github.com/woahwhattheheck/commons/pull/8419", text)
        self.assertIn("issuecomment-5517257860", text)
        self.assertIn("034587c4", text)
        self.assertIn("594b5e71", text)
        self.assertIn("4888459d", text)
        self.assertIn("39dc815a", text)
        self.assertIn("ALREADY_MERGED_VERIFIED", text)
        self.assertIn("Did not remint leftover", text)
        self.assertIn("Did not reopen #7915", text)
        self.assertIn("account locked due to a billing issue", text)
        self.assertIn("33689085107", text)
        self.assertNotEqual(text, prior)
        self.assertNotEqual(text, original)
        self.assertNotIn("grokbuild-pr8419-verify-20260902-01", prior)
        self.assertNotIn("buy.stripe.com", text)


if __name__ == "__main__":
    unittest.main()
