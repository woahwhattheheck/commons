#!/usr/bin/env python3
"""Pin unique PR 8604 already-merged verify. Do not remint path-manifest leftover."""

from __future__ import annotations

import hashlib
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
# This receipt records this immutable tree; it does not freeze evolving main.
SOURCE_REV = "d4556b9f8ec1f55b5b4a95d39ff5c68451588412"
VERIFY = ROOT / "p/grokbuild-pr8604-intake-verify-20260903-01.md"
LEFTOVER = ROOT / "p/grokbuild-path-manifest-33718116313-billing-lock-20260903-01.md"
BODY_SHA256 = "f0f3968afff1e6c4e81bc282f43376efa4a28302e878a85db88b0585f2d092e3"


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "rev-parse", f"{SOURCE_REV}:{rel}"], cwd=ROOT, text=True
    ).strip()


class TestGrokbuildPr8604IntakeVerify(unittest.TestCase):
    def test_original_leftover_unread(self) -> None:
        self.assertTrue(
            git_blob("p/grokbuild-path-manifest-33718116313-billing-lock-20260903-01.md").startswith(
                "02c74649"
            )
        )
        self.assertTrue(
            git_blob("test_grokbuild_path_manifest_33718116313_billing_lock.py").startswith("9ed291a5")
        )

    def test_verify_receipt_is_unique(self) -> None:
        text = VERIFY.read_text(encoding="utf-8")
        leftover = LEFTOVER.read_text(encoding="utf-8")
        self.assertIn("grokbuild-pr8604-intake-verify-20260903-01", text)
        self.assertIn("https://github.com/woahwhattheheck/commons/pull/8604", text)
        self.assertIn("241fb8e2e2529348e58ef807899f75bf1cab4bc0", text)
        self.assertIn("02c74649", text)
        self.assertIn("9ed291a5", text)
        self.assertIn("ALREADY_MERGED_VERIFIED", text)
        self.assertIn("DURABLE_ON_MAIN", text)
        self.assertIn("Yvqf4H9LvAnE", text)
        self.assertIn("33718116313", text)
        self.assertNotEqual(text, leftover)
        self.assertNotIn("grokbuild-pr8604-intake-verify-20260903-01", leftover)
        parts = text.split("---\n")
        self.assertGreaterEqual(len(parts), 3)
        body = parts[2].lstrip("\n").rstrip("\n")
        self.assertEqual(hashlib.sha256(body.encode("utf-8")).hexdigest(), BODY_SHA256)


if __name__ == "__main__":
    unittest.main()
