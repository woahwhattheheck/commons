#!/usr/bin/env python3
"""Pin grok-build verify leftover for already-merged PR 8414. Do not remint meeting item 6 leftover."""

from __future__ import annotations

import hashlib
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RECEIPT = ROOT / "p/grokbuild-pr8414-verify-20260902-01.md"
PRIOR = ROOT / "p/cursor-merge-on-pr-readback-20260902-01.md"
ORIGINAL = ROOT / "p/cursor-merge-on-pr-20260902-01.md"

KEEP = {
    "p/cursor-merge-on-pr-readback-20260902-01.md": "e160b2c3",
    "test_cursor_merge_on_pr_readback.py": "a90bb2ff",
    "p/cursor-merge-on-pr-20260902-01.md": "22b63e25",
    "host/merge_on_pr.py": "0270094d",
    "ground/MERGE_ON_PR.json": "4e7967dc",
    "test_merge_on_pr.py": "8224c8cd",
    "merge-on-pr.html": "86fe5e4f",
    "host/sprint_integration.py": "b7bec0b9",
    "host/pr7915_closed_unmerged.py": "9d56ea0e",
}

BODY_SHA256 = "75c21538b188a174292beb320ec33e0cf2b55ec131efec032ac8f15721892028"


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


def receipt_body(text: str) -> str:
    parts = text.split("---\n", 2)
    return parts[2].rstrip("\n") if len(parts) >= 3 else text


class TestGrokbuildPr8414Verify(unittest.TestCase):
    def test_keep_8414_and_item6_leftovers_unread(self) -> None:
        for rel, prefix in KEEP.items():
            blob = git_blob(rel)
            self.assertTrue(
                blob.startswith(prefix),
                f"{rel} reminted: want {prefix} got {blob[:8]}",
            )

    def test_leftover_merge_on_pr_tests_still_pass(self) -> None:
        proc = subprocess.run(
            ["python3", "-m", "unittest", "test_merge_on_pr.py"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
        self.assertIn("Ran 6 tests", proc.stderr + proc.stdout)

    def test_receipt_cites_8414_and_does_not_remint(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        prior = PRIOR.read_text(encoding="utf-8")
        original = ORIGINAL.read_text(encoding="utf-8")
        body = receipt_body(text)
        self.assertEqual(hashlib.sha256(body.encode("utf-8")).hexdigest(), BODY_SHA256)
        self.assertIn("grokbuild-pr8414-verify-20260902-01", text)
        self.assertIn(
            "woahwhattheheck/commons#8414@0675fb559de118427a4c37b3cc406fc9f4cc7b64",
            text,
        )
        self.assertIn("https://github.com/woahwhattheheck/commons/pull/8414", text)
        self.assertIn("issuecomment-5517240398", text)
        self.assertIn("920d8c03", text)
        self.assertIn("e160b2c3", text)
        self.assertIn("22b63e25", text)
        self.assertIn("0270094d", text)
        self.assertIn("ALREADY_MERGED_VERIFIED", text)
        self.assertIn("Did not remint leftover", text)
        self.assertIn("Did not reopen #7915", text)
        self.assertIn("account locked due to a billing issue", text)
        self.assertNotEqual(text, prior)
        self.assertNotEqual(text, original)
        self.assertNotIn("grokbuild-pr8414-verify-20260902-01", prior)
        self.assertNotIn("buy.stripe.com", text)


if __name__ == "__main__":
    unittest.main()
