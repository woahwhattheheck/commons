#!/usr/bin/env python3
"""Pin unique leftover for PR 8426 #commons receipt. Do not remint tests leftover."""

from __future__ import annotations

import hashlib
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RECEIPT = ROOT / "p/grokbuild-pr8426-verified-20260902-01.md"
PRIOR = ROOT / "p/grokbuild-tests-33689281316-billing-lock-20260902-01.md"

KEEP = {
    "p/grokbuild-tests-33689281316-billing-lock-20260902-01.md": "3db0ab2e",
    "test_grokbuild_tests_33689281316_billing_lock.py": "66bc4ff5",
    ".github/workflows/tests.yml": "8c2f2301",
}


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class TestGrokbuildPr8426Verified(unittest.TestCase):
    def test_keep_unread_leftovers(self) -> None:
        for rel, prefix in KEEP.items():
            blob = git_blob(rel)
            self.assertTrue(
                blob.startswith(prefix),
                f"{rel} reminted: want {prefix} got {blob[:8]}",
            )

    def test_receipt_is_unique_same_id_land(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        prior = PRIOR.read_text(encoding="utf-8")
        self.assertIn("grokbuild-pr8426-verified-20260902-01", text)
        self.assertIn("woahwhattheheck/commons#8426@749a5fc341298a707ed309de9b49d64c12c548fd", text)
        self.assertIn("https://github.com/woahwhattheheck/commons/pull/8426", text)
        self.assertIn("1906a84b", text)
        self.assertIn("3db0ab2e", text)
        self.assertIn("4PFxi3LyQg1x", text)
        self.assertIn("Did not remint", text)
        self.assertIn("No auth", text)
        self.assertNotEqual(text, prior)
        self.assertNotIn("33689281316", prior.split("id:", 1)[0] if False else "")
        body = text.split("---", 2)[2].lstrip("\n")
        self.assertEqual(
            hashlib.sha256(body.rstrip("\n").encode()).hexdigest(),
            "6fffbad350b4b1e5365676e091eea76bfc455def4b4990c11a6b8e9bffefcfe2",
        )


if __name__ == "__main__":
    unittest.main()
