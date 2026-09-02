#!/usr/bin/env python3
"""Pin unique leftover for PR 8429 #commons receipt. Do not remint 33689357241 leftover."""

from __future__ import annotations

import hashlib
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RECEIPT = ROOT / "p/grokbuild-pr8429-verify-20260902-01.md"
PRIOR = ROOT / "p/grokbuild-local-compute-guard-33689357241-billing-lock-20260902-01.md"

KEEP = {
    "p/grokbuild-local-compute-guard-33689357241-billing-lock-20260902-01.md": "2517b71d",
    "test_grokbuild_local_compute_guard_33689357241_billing_lock.py": "465d0ca5",
    "local_compute_guard.py": "6be242af",
    "test_local_compute_guard.py": "b8d65280",
    ".github/workflows/local-compute-guard.yml": "9750c6a1",
    "p/grok-build-local-compute-guard-billing-lock-20260902-01.md": "de59bf75",
}


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class TestGrokbuildPr8429Verify(unittest.TestCase):
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
        self.assertIn("grokbuild-pr8429-verify-20260902-01", text)
        self.assertIn(
            "woahwhattheheck/commons#8429@aa86681f790ac86f21137b933218550ec3de1b22",
            text,
        )
        self.assertIn("https://github.com/woahwhattheheck/commons/pull/8429", text)
        self.assertIn("9d0bf6cbb688e807dad746f147983de40134e169", text)
        self.assertIn("2517b71d", text)
        self.assertIn("UDugyQe5tbpT", text)
        self.assertIn("Did not reopen #7915", text)
        self.assertIn("ALREADY_MERGED_VERIFIED", text)
        self.assertNotEqual(text, prior)
        self.assertNotIn("grokbuild-pr8429-verify-20260902-01", prior)
        body = text.split("---", 2)[2].lstrip("\n")
        self.assertEqual(
            hashlib.sha256(body.rstrip("\n").encode()).hexdigest(),
            "0c4a6acd65ec759239c08f6c7df0dd8bc71baa28cf4727d04c6538a17e968b8f",
        )


if __name__ == "__main__":
    unittest.main()
