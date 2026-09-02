#!/usr/bin/env python3
"""Pin grok-build verify leftover for PR 8411. Do not remint 33687829181 leftover."""

from __future__ import annotations

import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RECEIPT = ROOT / "p/grokbuild-pr8411-verify-20260902-01.md"
PRIOR = ROOT / "p/grok-build-llms-txt-33687829181-billing-lock-20260902-01.md"

KEEP = {
    "p/grok-build-llms-txt-33687829181-billing-lock-20260902-01.md": "3183564c",
    "test_grokbuild_llms_txt_33687829181_billing_lock.py": "e02e5ab5",
    "p/grok-build-llms-txt-billing-lock-20260902-01.md": "cf9c9f40",
    ".github/workflows/llms-txt.yml": "d2182a3d",
    "llms_txt.py": "83fc5ea9",
}


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class TestGrokbuildPr8411Verify(unittest.TestCase):
    def test_keep_8411_leftover_and_publisher_unread(self) -> None:
        for rel, prefix in KEEP.items():
            blob = git_blob(rel)
            self.assertTrue(
                blob.startswith(prefix),
                f"{rel} reminted: want {prefix} got {blob[:8]}",
            )

    def test_receipt_cites_8411_and_does_not_remint(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        prior = PRIOR.read_text(encoding="utf-8")
        self.assertIn("grokbuild-pr8411-verify-20260902-01", text)
        self.assertIn(
            "woahwhattheheck/commons#8411@6ecc81a6004c6bb06184d8a39dc5c82a57605a3b",
            text,
        )
        self.assertIn("4f686e2f6bbabb5862fc405f2318069a5db83c82", text)
        self.assertIn("3183564c", text)
        self.assertIn("e02e5ab5", text)
        self.assertIn("issuecomment-5517139166", text)
        self.assertIn("33687829181", text)
        self.assertIn("EXTERNAL_BLOCKER", text)
        self.assertIn("Did not remint leftover 3183564c", text)
        self.assertIn("did not reopen #7915", text.lower())
        self.assertNotEqual(text, prior)
        self.assertNotIn("grokbuild-pr8411-verify-20260902-01", prior)


if __name__ == "__main__":
    unittest.main()
