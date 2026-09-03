#!/usr/bin/env python3
"""Pin unique PR 8605 already-merged verify. Do not remint spec-guard leftover."""

from __future__ import annotations

import hashlib
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VERIFY = ROOT / "p/grokbuild-pr8605-intake-verify-20260903-01.md"
LEFTOVER = ROOT / "p/grokbuild-muhlnickel-spec-guard-33718116252-billing-lock-20260903-01.md"
BODY_SHA256 = "6100142295208625e0bb047b793b19df72be5df848cc2cc85ab9b4333f1f10e7"


def git_blob(rel: str) -> str:
    return subprocess.check_output(["git", "hash-object", str(ROOT / rel)], text=True).strip()


class TestGrokbuildPr8605IntakeVerify(unittest.TestCase):
    def test_original_leftover_unread(self) -> None:
        self.assertTrue(
            git_blob(
                "p/grokbuild-muhlnickel-spec-guard-33718116252-billing-lock-20260903-01.md"
            ).startswith("4f43a687")
        )
        self.assertTrue(
            git_blob(
                "test_grokbuild_muhlnickel_spec_guard_33718116252_billing_lock.py"
            ).startswith("af125d08")
        )
        leftover_tests = subprocess.run(
            [
                "python3",
                "-m",
                "unittest",
                "test_grokbuild_muhlnickel_spec_guard_33718116252_billing_lock",
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(leftover_tests.returncode, 0, leftover_tests.stdout + leftover_tests.stderr)
        self.assertIn("Ran 4 tests", leftover_tests.stderr + leftover_tests.stdout)

    def test_verify_receipt_is_unique(self) -> None:
        text = VERIFY.read_text(encoding="utf-8")
        leftover = LEFTOVER.read_text(encoding="utf-8")
        self.assertIn("grokbuild-pr8605-intake-verify-20260903-01", text)
        self.assertIn("https://github.com/woahwhattheheck/commons/pull/8605", text)
        self.assertIn("99cd17bdb7723fbf9080263d807df7d4de4a7259", text)
        self.assertIn("5c08b567dda00fae0936ba97741aa745d9e24bf1", text)
        self.assertIn("4f43a687", text)
        self.assertIn("af125d08", text)
        self.assertIn("ALREADY_MERGED_VERIFIED", text)
        self.assertIn("INTEGRATED — VERIFIED ON CURRENT MAIN", text)
        self.assertIn("DURABLE_ON_MAIN", text)
        self.assertIn("woahwhattheheck/commons#8605@5c08b567dda00fae0936ba97741aa745d9e24bf1", text)
        self.assertNotEqual(text, leftover)
        self.assertNotIn("grokbuild-pr8605-intake-verify-20260903-01", leftover)
        parts = text.split("---\n")
        self.assertGreaterEqual(len(parts), 3)
        body = parts[2].lstrip("\n").rstrip("\n")
        self.assertEqual(hashlib.sha256(body.encode("utf-8")).hexdigest(), BODY_SHA256)


if __name__ == "__main__":
    unittest.main()
