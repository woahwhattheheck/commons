#!/usr/bin/env python3
"""Pin unique PR 8597 already-merged verify. Do not remint job-watchdog leftover."""

from __future__ import annotations

import hashlib
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VERIFY = ROOT / "p/grokbuild-pr8597-intake-verify-20260903-01.md"
LEFTOVER = ROOT / "p/grokbuild-job-watchdog-33717733947-billing-lock-20260903-01.md"
BODY_SHA256 = "99df79b355addaabf27257d4e4d5f237c53e059f5ced15e63892ac755f9626ee"


def git_blob(rel: str) -> str:
    return subprocess.check_output(["git", "hash-object", str(ROOT / rel)], text=True).strip()


class TestGrokbuildPr8597IntakeVerify(unittest.TestCase):
    def test_original_leftover_unread(self) -> None:
        self.assertTrue(
            git_blob("p/grokbuild-job-watchdog-33717733947-billing-lock-20260903-01.md").startswith(
                "d83537e6"
            )
        )
        self.assertTrue(
            git_blob("test_grokbuild_job_watchdog_33717733947_billing_lock.py").startswith("b364a427")
        )

    def test_verify_receipt_is_unique(self) -> None:
        text = VERIFY.read_text(encoding="utf-8")
        leftover = LEFTOVER.read_text(encoding="utf-8")
        self.assertIn("grokbuild-pr8597-intake-verify-20260903-01", text)
        self.assertIn("https://github.com/woahwhattheheck/commons/pull/8597", text)
        self.assertIn("7879aefc644176e9557aa3214c7b21ed3d08162b", text)
        self.assertIn("edbc4ddf814954a3fb35c0f58705e642822e7551", text)
        self.assertIn("d83537e6", text)
        self.assertIn("b364a427", text)
        self.assertIn("MERGED_VERIFIED", text)
        self.assertIn("INTEGRATED — VERIFIED ON CURRENT MAIN", text)
        self.assertIn("DURABLE_ON_MAIN", text)
        self.assertIn("msVWW7Ees5XF", text)
        self.assertNotEqual(text, leftover)
        self.assertNotIn("grokbuild-pr8597-intake-verify-20260903-01", leftover)
        parts = text.split("---\n")
        self.assertGreaterEqual(len(parts), 3)
        body = parts[2].lstrip("\n").rstrip("\n")
        self.assertEqual(hashlib.sha256(body.encode("utf-8")).hexdigest(), BODY_SHA256)


if __name__ == "__main__":
    unittest.main()
