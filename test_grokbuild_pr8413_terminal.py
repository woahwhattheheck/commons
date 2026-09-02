#!/usr/bin/env python3
"""Pin grok-build terminal leftover for already-merged PR 8413. Do not remint 8408 leftover."""

from __future__ import annotations

import hashlib
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RECEIPT = ROOT / "p/grokbuild-pr8413-terminal-20260902-01.md"
PRIOR = ROOT / "p/grokbuild-pr8408-verify-20260902-01.md"
ORIGINAL = ROOT / "p/grokbuild-open-door-guard-33687124472-billing-lock-20260902-01.md"

KEEP = {
    "p/grokbuild-pr8408-verify-20260902-01.md": "0a594dda",
    "p/grokbuild-open-door-guard-33687124472-billing-lock-20260902-01.md": "b91a85d3",
    "test_grokbuild_open_door_guard_33687124472_billing_lock.py": "e6a826cf",
    "open_door_guard.py": "4b053e43",
}

BODY_SHA256 = "99904284b6808bb99a957dbd556b42534ec683a48a49490848bb481fde4c8b57"


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


def receipt_body(text: str) -> str:
    parts = text.split("---\n", 2)
    return parts[2].rstrip("\n") if len(parts) >= 3 else text


class TestGrokbuildPr8413Terminal(unittest.TestCase):
    def test_keep_8413_and_8408_leftovers_unread(self) -> None:
        for rel, prefix in KEEP.items():
            blob = git_blob(rel)
            self.assertTrue(
                blob.startswith(prefix),
                f"{rel} reminted: want {prefix} got {blob[:8]}",
            )

    def test_8408_leftover_tests_still_pass(self) -> None:
        proc = subprocess.run(
            ["python3", "-m", "unittest", "test_grokbuild_open_door_guard_33687124472_billing_lock"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
        self.assertIn("Ran 4 tests", proc.stderr + proc.stdout)

    def test_receipt_cites_8413_and_does_not_remint(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        prior = PRIOR.read_text(encoding="utf-8")
        original = ORIGINAL.read_text(encoding="utf-8")
        body = receipt_body(text)
        self.assertEqual(hashlib.sha256(body.encode("utf-8")).hexdigest(), BODY_SHA256)
        self.assertIn("grokbuild-pr8413-terminal-20260902-01", text)
        self.assertIn("woahwhattheheck/commons#8413@246adeed03b8d4a63f51014c7f4d5fc1eae92343", text)
        self.assertIn("https://github.com/woahwhattheheck/commons/pull/8413", text)
        self.assertIn("issuecomment-5517155760", text)
        self.assertIn("f078829d", text)
        self.assertIn("920d8c03", text)
        self.assertIn("0a594dda", text)
        self.assertIn("b91a85d3", text)
        self.assertIn("ALREADY_MERGED_VERIFIED", text)
        self.assertIn("Did not remint leftover", text)
        self.assertIn("Did not reopen #7915", text)
        self.assertIn("account locked due to a billing issue", text)
        self.assertNotEqual(text, prior)
        self.assertNotEqual(text, original)
        self.assertNotIn("grokbuild-pr8413-terminal-20260902-01", prior)


if __name__ == "__main__":
    unittest.main()
