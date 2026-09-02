#!/usr/bin/env python3
"""Pin unique leftover for PR 8475 #commons receipt. Do not remint 8473 verify."""

from __future__ import annotations

import hashlib
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RECEIPT = ROOT / "p/grokbuild-pr8475-verify-20260902-01.md"
PRIOR = ROOT / "p/grokbuild-pr8473-verify-20260902-01.md"

KEEP = {
    "p/grokbuild-pr8473-verify-20260902-01.md": "801cb4e4",
    "test_grokbuild_pr8473_verify.py": "048d22ff",
    ".agents/plugins/marketplace.json": "97875086",
    "host/wire_super_mcp_marketplace.py": "7b408ed9",
    "test_wire_super_mcp_marketplace.py": "42167891",
    "p/cursor-wire-super-mcp-marketplace-20260902-01.md": "fbc20c0d",
}


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class TestGrokbuildPr8475Verify(unittest.TestCase):
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
        self.assertIn("grokbuild-pr8475-verify-20260902-01", text)
        self.assertIn(
            "woahwhattheheck/commons#8475@d87201dfdf40b35566205b8d7e0bd1a4ade662d2",
            text,
        )
        self.assertIn("https://github.com/woahwhattheheck/commons/pull/8475", text)
        self.assertIn("5388dc7d9cef986f6cf1fba3e1bef86e474f85a1", text)
        self.assertIn("801cb4e4", text)
        self.assertIn("VxUM1w4f6vKB", text)
        self.assertIn("ALREADY_MERGED_VERIFIED", text)
        self.assertNotEqual(text, prior)
        self.assertNotIn("grokbuild-pr8475-verify-20260902-01", prior)
        body = text.split("---", 2)[2].lstrip("\n")
        self.assertEqual(
            hashlib.sha256(body.rstrip("\n").encode()).hexdigest(),
            "e2911476f0353105bff2e53a0431b4aa39b9459adae7b84d0b00388ec46ce3ec",
        )


if __name__ == "__main__":
    unittest.main()
