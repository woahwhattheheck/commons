#!/usr/bin/env python3
"""Pin unique PR 8606 already-merged verify. Do not remint tests leftover."""

from __future__ import annotations

import hashlib
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VERIFY = ROOT / "p/grokbuild-pr8606-intake-verify-20260903-01.md"
LEFTOVER = ROOT / "p/grokbuild-tests-33718131413-billing-lock-20260903-01.md"
BODY_SHA256 = "0204f59d909c33f1eef34790c72c1d68468c1f660e92a57c2db1c24e7e4b8f24"


def git_blob(rel: str) -> str:
    return subprocess.check_output(["git", "hash-object", str(ROOT / rel)], text=True).strip()


class TestGrokbuildPr8606IntakeVerify(unittest.TestCase):
    def test_original_leftover_unread(self) -> None:
        self.assertTrue(
            git_blob(
                "p/grokbuild-tests-33718131413-billing-lock-20260903-01.md"
            ).startswith("9fa188cb")
        )
        self.assertTrue(
            git_blob(
                "test_grokbuild_tests_33718131413_billing_lock.py"
            ).startswith("af716e04")
        )

    def test_verify_receipt_is_unique(self) -> None:
        text = VERIFY.read_text(encoding="utf-8")
        leftover = LEFTOVER.read_text(encoding="utf-8")
        self.assertIn("grokbuild-pr8606-intake-verify-20260903-01", text)
        self.assertIn("https://github.com/woahwhattheheck/commons/pull/8606", text)
        self.assertIn("75e8a9af012a0b5d8f7fcb59b378e88f6efbd6f9", text)
        self.assertIn("9c6377ea7aa5e21ba34bba136ff5919a6021c8ac", text)
        self.assertIn("9fa188cb", text)
        self.assertIn("ALREADY_MERGED_VERIFIED", text)
        self.assertIn("INTEGRATED — VERIFIED ON CURRENT MAIN", text)
        self.assertIn("DURABLE_ON_MAIN", text)
        self.assertIn("AtkuSnFPIyA2", text)
        self.assertNotEqual(text, leftover)
        self.assertNotIn("grokbuild-pr8606-intake-verify-20260903-01", leftover)
        parts = text.split("---\n")
        self.assertGreaterEqual(len(parts), 3)
        body = parts[2].lstrip("\n").rstrip("\n")
        self.assertEqual(hashlib.sha256(body.encode("utf-8")).hexdigest(), BODY_SHA256)


if __name__ == "__main__":
    unittest.main()
