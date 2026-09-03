#!/usr/bin/env python3
"""Pin unique PR 8607 already-merged verify. Do not remint janitor leftover."""

from __future__ import annotations

import hashlib
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VERIFY = ROOT / "p/grokbuild-pr8607-intake-verify-20260903-01.md"
LEFTOVER = ROOT / "p/grokbuild-merged-branch-janitor-33718131639-billing-lock-20260903-01.md"
BODY_SHA256 = "f336ecdfe7cc940346946049644d8e7f86e47e06994924b277cc98e7e7d397f5"


def git_blob(rel: str) -> str:
    return subprocess.check_output(["git", "hash-object", str(ROOT / rel)], text=True).strip()


class TestGrokbuildPr8607IntakeVerify(unittest.TestCase):
    def test_original_leftover_unread(self) -> None:
        self.assertTrue(
            git_blob(
                "p/grokbuild-merged-branch-janitor-33718131639-billing-lock-20260903-01.md"
            ).startswith("010f253e")
        )
        self.assertTrue(
            git_blob(
                "test_grokbuild_merged_branch_janitor_33718131639_billing_lock.py"
            ).startswith("06ec66e6")
        )

    def test_verify_receipt_is_unique(self) -> None:
        text = VERIFY.read_text(encoding="utf-8")
        leftover = LEFTOVER.read_text(encoding="utf-8")
        self.assertIn("grokbuild-pr8607-intake-verify-20260903-01", text)
        self.assertIn("https://github.com/woahwhattheheck/commons/pull/8607", text)
        self.assertIn("156770486986b2a22aff08cfd3567cbad66326d9", text)
        self.assertIn("24f5f884c2c3a307ae68559e9ef504fd38e1ce98", text)
        self.assertIn("010f253e", text)
        self.assertIn("ALREADY_MERGED_VERIFIED", text)
        self.assertIn("INTEGRATED — VERIFIED ON CURRENT MAIN", text)
        self.assertIn("DURABLE_ON_MAIN", text)
        self.assertIn("Uawsb03A7GJi", text)
        self.assertNotEqual(text, leftover)
        self.assertNotIn("grokbuild-pr8607-intake-verify-20260903-01", leftover)
        parts = text.split("---\n")
        self.assertGreaterEqual(len(parts), 3)
        body = parts[2].lstrip("\n").rstrip("\n")
        self.assertEqual(hashlib.sha256(body.encode("utf-8")).hexdigest(), BODY_SHA256)


if __name__ == "__main__":
    unittest.main()
