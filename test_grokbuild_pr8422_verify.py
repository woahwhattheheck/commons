#!/usr/bin/env python3
"""Pin grok-build verify leftover for already-merged PR 8422. Do not remint discord-cloud leftover."""

from __future__ import annotations

import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RECEIPT = ROOT / "p/grokbuild-pr8422-verify-20260902-01.md"
PRIOR = ROOT / "p/grok-build-discord-cloud-33689083145-billing-lock-20260902-01.md"

KEEP = {
    "p/grok-build-discord-cloud-33689083145-billing-lock-20260902-01.md": "6e34f897",
    "test_grokbuild_discord_cloud_33689083145_billing_lock.py": "23e3fe80",
    "p/grok-build-discord-cloud-billing-lock-20260902-01.md": "2e0bfbfb",
    "p/grokbuild-occupancy-landed-work-keep-lift-readback-20260902-01.md": "892bc4c0",
    ".github/workflows/commons-discord-cloud.yml": "6f1c1479",
}


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class TestGrokbuildPr8422Verify(unittest.TestCase):
    def test_keep_8422_leftover_and_helpers_unread(self) -> None:
        for rel, prefix in KEEP.items():
            blob = git_blob(rel)
            self.assertTrue(
                blob.startswith(prefix),
                f"{rel} reminted: want {prefix} got {blob[:8]}",
            )

    def test_receipt_cites_8422_and_does_not_remint(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        prior = PRIOR.read_text(encoding="utf-8")
        self.assertIn("grokbuild-pr8422-verify-20260902-01", text)
        self.assertIn(
            "woahwhattheheck/commons#8422@bf8ad5f3399fa6cef212c8499c41c5f506ac95f1",
            text,
        )
        self.assertIn("https://github.com/woahwhattheheck/commons/pull/8422", text)
        self.assertIn("issuecomment-5517319223", text)
        self.assertIn("2578319c8f0879461cf127b25f13a186aff25816", text)
        self.assertIn("6e34f897", text)
        self.assertIn("23e3fe80", text)
        self.assertIn("2e0bfbfb", text)
        self.assertIn("892bc4c0", text)
        self.assertIn("6f1c1479", text)
        self.assertIn("33689083145", text)
        self.assertIn("ALREADY_MERGED_VERIFIED", text)
        self.assertIn("Did not remint leftover", text)
        self.assertIn("Did not reopen #7915", text)
        self.assertIn("account locked due to a billing issue", text)
        self.assertNotEqual(text, prior)
        self.assertNotIn("grokbuild-pr8422-verify-20260902-01", prior)
        self.assertNotIn("buy.stripe.com", text)

    def test_original_leftover_tests_still_pass(self) -> None:
        proc = subprocess.run(
            [
                "python3",
                "-m",
                "unittest",
                "test_grokbuild_discord_cloud_33689083145_billing_lock.py",
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
        self.assertIn("Ran 5 tests", proc.stderr + proc.stdout)


if __name__ == "__main__":
    unittest.main()
