#!/usr/bin/env python3
"""Pin unique PR 8598 already-merged intake verify. Do not remint original leftovers."""

from __future__ import annotations

import hashlib
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VERIFY = ROOT / "p/grokbuild-pr8598-intake-verify-20260903-01.md"
ORIGINAL = ROOT / "p/grokbuild-pr8583-already-merged-verify-20260903-01.md"
BODY_SHA256 = "fe871f503b202973ff5cc53db72d06caa87496eeb138c051b9eff3470005c746"

KEEP = {
    "p/grokbuild-main-range-verify-33717084528-billing-lock-20260903-01.md": "2b0fd9c9",
    "test_grokbuild_main_range_verify_33717084528_billing_lock.py": "3e89a404",
    "p/grokbuild-pr8583-already-merged-verify-20260903-01.md": "b3e4e1af",
    "test_grokbuild_pr8583_already_merged_verify.py": "3868499a",
    "open_door_guard.py": "4b053e43",
}


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class TestGrokbuildPr8598IntakeVerify(unittest.TestCase):
    def test_original_leftovers_unread(self) -> None:
        for rel, prefix in KEEP.items():
            blob = git_blob(rel)
            self.assertTrue(
                blob.startswith(prefix),
                f"{rel} reminted: want {prefix} got {blob[:8]}",
            )

    def test_verify_receipt_is_unique(self) -> None:
        text = VERIFY.read_text(encoding="utf-8")
        original = ORIGINAL.read_text(encoding="utf-8")
        self.assertIn("grokbuild-pr8598-intake-verify-20260903-01", text)
        self.assertIn("https://github.com/woahwhattheheck/commons/pull/8598", text)
        self.assertIn("0cbe53666cdf85f981f816923524744b5f6032b1", text)
        self.assertIn("09fbb39287e303cbb5c4530d28430a5e52599047", text)
        self.assertIn("727feb85fe01df8b08c0bc3435d966babb75581b", text)
        self.assertIn("c9fce69e915e692a19b1f62af829f9354cfb7ba8", text)
        self.assertIn("b3e4e1af", text)
        self.assertIn("3868499a", text)
        self.assertIn("2b0fd9c9", text)
        self.assertIn("3e89a404", text)
        self.assertIn("ALREADY_MERGED_VERIFIED", text)
        self.assertIn("INTEGRATED — VERIFIED ON CURRENT MAIN", text)
        self.assertIn("DURABLE_ON_MAIN", text)
        self.assertIn("EvaUaxdIaovE", text)
        self.assertIn("Did not remint", text)
        self.assertIn("Did not reopen #7915", text)
        self.assertNotEqual(text, original)
        self.assertNotIn("grokbuild-pr8598-intake-verify-20260903-01", original)
        parts = text.split("---\n")
        self.assertGreaterEqual(len(parts), 3)
        body = parts[2].lstrip("\n").rstrip("\n")
        self.assertEqual(hashlib.sha256(body.encode("utf-8")).hexdigest(), BODY_SHA256)


if __name__ == "__main__":
    unittest.main()
