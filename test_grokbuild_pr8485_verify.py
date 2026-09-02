#!/usr/bin/env python3
"""Pin unique leftover for PR 8485 #commons receipt. Do not remint 8479 leftover."""

from __future__ import annotations

import hashlib
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RECEIPT = ROOT / "p/grokbuild-pr8485-verify-20260902-01.md"
PRIOR = ROOT / "p/grokbuild-pr8479-verify-20260902-01.md"

KEEP = {
    "p/grokbuild-pr8479-verify-20260902-01.md": "658530be",
    "p/cursor-goat-pages-super-mcp-land-readback-match-20260902-01.md": "865b3c95",
    "p/goat-pages-super-mcp-land-20260902-01.md": "171e0daaf",
    "catalog.html": "154b7b67",
    "boards.html": "3fa79f12",
    "hub_pages.py": "5ac12648",
    "p/cursor-goat-pages-super-mcp-land-readback-20260902-01.md": "f98887bf",
}


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class TestGrokbuildPr8485Verify(unittest.TestCase):
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
        self.assertIn("grokbuild-pr8485-verify-20260902-01", text)
        self.assertIn(
            "woahwhattheheck/commons#8485@be8ca26cca348d5ab94ef547bb95575136c40178",
            text,
        )
        self.assertIn("https://github.com/woahwhattheheck/commons/pull/8485", text)
        self.assertIn("58d33c21235c0f596dd2920e8b89ded38904e910", text)
        self.assertIn("658530be", text)
        self.assertIn("171e0daaf", text)
        self.assertIn("ALREADY_MERGED_VERIFIED", text)
        self.assertNotEqual(text, prior)
        self.assertNotIn("grokbuild-pr8485-verify-20260902-01", prior)
        body = text.split("---", 2)[2].lstrip("\n")
        self.assertEqual(
            hashlib.sha256(body.rstrip("\n").encode()).hexdigest(),
            'c399a7b0ba1077f804d57b8d5154f5a383d60f9e14c16684d7894de0371ba768',
        )


if __name__ == "__main__":
    unittest.main()
