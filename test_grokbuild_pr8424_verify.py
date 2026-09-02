#!/usr/bin/env python3
"""Pin grok-build verify leftover for PR 8424. Do not remint 33689243568 leftover."""

from __future__ import annotations

import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RECEIPT = ROOT / "p/grokbuild-pr8424-verify-20260902-01.md"
PRIOR = ROOT / "p/grokbuild-open-door-guard-33689243568-billing-lock-20260902-01.md"

KEEP = {
    "p/grokbuild-open-door-guard-33689243568-billing-lock-20260902-01.md": "4ab677c5",
    "test_grokbuild_open_door_guard_33689243568_billing_lock.py": "0ec1378d",
    "open_door_guard.py": "4b053e43",
    "test_open_door_guard.py": "70ee5730",
    ".github/workflows/open-door-guard.yml": "6586644c",
    "p/grokbuild-open-door-guard-33687124472-billing-lock-20260902-01.md": "b91a85d3",
    "test_grokbuild_open_door_guard_33687124472_billing_lock.py": "e6a826cf",
    "p/grokbuild-pr8408-verify-20260902-01.md": "0a594dda",
    "p/grokbuild-pr8411-verify-20260902-01.md": "642dea64",
}


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class TestGrokbuildPr8424Verify(unittest.TestCase):
    def test_keep_8424_leftover_and_guard_unread(self) -> None:
        for rel, prefix in KEEP.items():
            blob = git_blob(rel)
            self.assertTrue(
                blob.startswith(prefix),
                f"{rel} reminted: want {prefix} got {blob[:8]}",
            )

    def test_receipt_cites_8424_and_does_not_remint(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        prior = PRIOR.read_text(encoding="utf-8")
        self.assertIn("grokbuild-pr8424-verify-20260902-01", text)
        self.assertIn(
            "woahwhattheheck/commons#8424@ab4c76be72543309278b008a467bff6b6c5de063",
            text,
        )
        self.assertIn("a16930f88f3ccf26bfdcc47aeb0f25c07da8b025", text)
        self.assertIn("4ab677c5", text)
        self.assertIn("0ec1378d", text)
        self.assertIn("issuecomment-5517318366", text)
        self.assertIn("33689243568", text)
        self.assertIn("ALREADY_MERGED_VERIFIED", text)
        self.assertIn("Did not remint leftover 4ab677c5", text)
        self.assertIn("Did not reopen #7915", text)
        self.assertIn("FOV32BjmrPrm", text)
        self.assertNotEqual(text, prior)
        self.assertNotIn("grokbuild-pr8424-verify-20260902-01", prior)
        self.assertNotIn("buy.stripe.com", text)

    def test_original_leftover_tests_still_pass(self) -> None:
        proc = subprocess.run(
            ["python3", "test_grokbuild_open_door_guard_33689243568_billing_lock.py"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
        self.assertIn("Ran 4 tests", proc.stderr + proc.stdout)


if __name__ == "__main__":
    unittest.main()
