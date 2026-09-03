#!/usr/bin/env python3
"""Pin unique PR 8601 already-merged verify. Do not remint tests battery leftover."""

from __future__ import annotations

import hashlib
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VERIFY = ROOT / "p/grokbuild-pr8601-verify-20260903-01.md"
LEFTOVER = ROOT / "p/grokbuild-tests-33718116260-billing-lock-20260903-01.md"
LEFTOVER_TEST = ROOT / "test_grokbuild_tests_33718116260_billing_lock.py"
PRIOR = ROOT / "p/grokbuild-tests-33717741059-billing-lock-20260903-01.md"
WORKFLOW = ROOT / ".github/workflows/tests.yml"
BODY_SHA256 = "71982c472209705ebb98df207c5c051a387127cfe739635e2566e31f9a1d7785"

KEEP = {
    "p/grokbuild-tests-33718116260-billing-lock-20260903-01.md": "70db3e2a",
    "test_grokbuild_tests_33718116260_billing_lock.py": "6e4167e5",
    "p/grokbuild-tests-33717741059-billing-lock-20260903-01.md": "1b6c3021",
    "test_grokbuild_tests_33717741059_billing_lock.py": "c62e238e",
    ".github/workflows/tests.yml": "8c2f2301",
    "open_door_guard.py": "4b053e43",
}


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class TestGrokbuildPr8601Verify(unittest.TestCase):
    def test_keep_8601_leftover_and_tests_yml_unread(self) -> None:
        for rel, prefix in KEEP.items():
            blob = git_blob(rel)
            self.assertTrue(
                blob.startswith(prefix),
                f"{rel} reminted: want {prefix} got {blob[:8]}",
            )
        yml = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("name: tests", yml)
        self.assertIn("battery:", yml)
        self.assertIn("the whole battery, one failure fails the run", yml)
        self.assertIn("find . -maxdepth 1 -type f -name 'test_*.py'", yml)
        self.assertNotIn("billing", yml.lower())
        self.assertNotIn("if: false", yml)
        self.assertNotIn("continue-on-error", yml)

    def test_verify_receipt_is_unique_and_does_not_remint(self) -> None:
        text = VERIFY.read_text(encoding="utf-8")
        leftover = LEFTOVER.read_text(encoding="utf-8")
        leftover_test = LEFTOVER_TEST.read_text(encoding="utf-8")
        prior = PRIOR.read_text(encoding="utf-8")
        self.assertIn("grokbuild-pr8601-verify-20260903-01", text)
        self.assertIn(
            "woahwhattheheck/commons#8601@87f2e0bdd6e659d99172d076622ba2ab34a4bb53",
            text,
        )
        self.assertIn("https://github.com/woahwhattheheck/commons/pull/8601", text)
        self.assertIn("87f2e0bdd6e659d99172d076622ba2ab34a4bb53", text)
        self.assertIn("6b990286fe7ed8c82a59a5c4b2ec37b66567d3ca", text)
        self.assertIn("727feb85fe01df8b08c0bc3435d966babb75581b", text)
        self.assertIn("70db3e2a", text)
        self.assertIn("6e4167e5", text)
        self.assertIn("ALREADY_MERGED_VERIFIED", text)
        self.assertIn("INTEGRATED — VERIFIED ON CURRENT MAIN", text)
        self.assertIn("UjaEGkQhRt4E", text)
        self.assertIn("33718116260", text)
        self.assertIn("EXTERNAL_BLOCKER", text)
        self.assertIn("Did not reopen #7915", text)
        self.assertIn("Did not remint leftover grokbuild-tests-33718116260-billing-lock-20260903-01", text)
        self.assertNotEqual(text, leftover)
        self.assertNotEqual(text, prior)
        self.assertNotEqual(Path(__file__).read_text(encoding="utf-8"), leftover_test)
        self.assertNotIn("woahwhattheheck/commons#8601@", leftover)
        self.assertNotIn("grokbuild-pr8601-verify-20260903-01", leftover)
        parts = text.split("---\n")
        self.assertGreaterEqual(len(parts), 3)
        body = parts[2].lstrip("\n").rstrip("\n")
        self.assertEqual(hashlib.sha256(body.encode("utf-8")).hexdigest(), BODY_SHA256)

    def test_leftover_unittest_still_green(self) -> None:
        proc = subprocess.run(
            ["python3", "-m", "unittest", "test_grokbuild_tests_33718116260_billing_lock.py"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
        self.assertIn("Ran 4 tests", proc.stderr + proc.stdout)


if __name__ == "__main__":
    unittest.main()
