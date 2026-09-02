#!/usr/bin/env python3
"""Pin unique leftover for PR 8471 #commons receipt. Do not remint KEEP-lift."""

from __future__ import annotations

import hashlib
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RECEIPT = ROOT / "p/grokbuild-pr8471-verify-20260902-01.md"
PRIOR = ROOT / "p/cursor-harborline-commerce-compose-keep-lift-20260902-01.md"

KEEP = {
    "p/cursor-harborline-commerce-compose-keep-lift-20260902-01.md": "668dd5c4",
    "test_harborline_commerce_compose.py": "96bea929",
    "test_harborline_commerce_compose_keep_lift.py": "aa5e2571",
    "host/harborline_commerce_compose.py": "75128e5d",
    "p/cursor-harborline-commerce-compose-20260902-01.md": "45b7d435",
    "p/cursor-big-huge-commerce-agents-20260902-01.md": "fddb5a7c",
    "host/commerce_agents_same_loop.py": "c90f6e50",
    "test_commerce_agents_same_loop.py": "623e99e8",
    "p/cursor-harborline-commerce-compose-readback-20260902-01.md": "b33e2e24",
    "test_cursor_harborline_commerce_compose_readback.py": "34da2639",
}


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class TestGrokbuildPr8471Verify(unittest.TestCase):
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
        self.assertIn("grokbuild-pr8471-verify-20260902-01", text)
        self.assertIn(
            "woahwhattheheck/commons#8471@897542c8f8e8c5dc97b2a5ccc0cbaaef0a49a93b",
            text,
        )
        self.assertIn("https://github.com/woahwhattheheck/commons/pull/8471", text)
        self.assertIn("6e6813a4f9fde4adac3b2c0c7113d5a1a1813c10", text)
        self.assertIn("668dd5c4", text)
        self.assertIn("p5B0SDXDzvSH", text)
        self.assertIn("Did not reopen #7915", text)
        self.assertIn("ALREADY_MERGED_VERIFIED", text)
        self.assertNotEqual(text, prior)
        self.assertNotIn("grokbuild-pr8471-verify-20260902-01", prior)
        body = text.split("---", 2)[2].lstrip("\n")
        self.assertEqual(
            hashlib.sha256(body.rstrip("\n").encode()).hexdigest(),
            "9d0fda8135fda10056d27a0af4434177ee051b69000fc8687fc38b31916ee97d",
        )


if __name__ == "__main__":
    unittest.main()
