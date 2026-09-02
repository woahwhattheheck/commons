#!/usr/bin/env python3
"""Pin unique leftover for PR 8428 #commons receipt. Do not remint 33689281182 leftover."""

from __future__ import annotations

import hashlib
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RECEIPT = ROOT / "p/grokbuild-pr8428-verify-20260902-01.md"
PRIOR = ROOT / "p/grokbuild-open-door-guard-33689281182-billing-lock-20260902-01.md"

KEEP = {
    "p/grokbuild-open-door-guard-33689281182-billing-lock-20260902-01.md": "41bcb27d",
    "test_grokbuild_open_door_guard_33689281182_billing_lock.py": "91543e5d",
    "open_door_guard.py": "4b053e43",
    "test_open_door_guard.py": "70ee5730",
    ".github/workflows/open-door-guard.yml": "6586644c",
    "p/grokbuild-open-door-guard-33687124472-billing-lock-20260902-01.md": "b91a85d3",
    "test_grokbuild_open_door_guard_33687124472_billing_lock.py": "e6a826cf",
    "p/grokbuild-pr8408-verify-20260902-01.md": "0a594dda",
}


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class TestGrokbuildPr8428Verify(unittest.TestCase):
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
        self.assertIn("grokbuild-pr8428-verify-20260902-01", text)
        self.assertIn(
            "woahwhattheheck/commons#8428@6ff5e58eddb5a7a52b44a72f1f6987d0612d9707",
            text,
        )
        self.assertIn("https://github.com/woahwhattheheck/commons/pull/8428", text)
        self.assertIn("dd73b2168e1f1bfef95be59b64bbe1349312fb26", text)
        self.assertIn("41bcb27d", text)
        self.assertIn("fC0UXFoOoD1M", text)
        self.assertIn("Did not reopen #7915", text)
        self.assertIn("No fake green", text)
        self.assertNotEqual(text, prior)
        self.assertNotIn("grokbuild-pr8428-verify-20260902-01", prior)
        body = text.split("---", 2)[2].lstrip("\n")
        self.assertEqual(
            hashlib.sha256(body.rstrip("\n").encode()).hexdigest(),
            "a11c1d1778e46fb5c318dbaf6d5ea915741536b3bec7cf36a7c1218a9fe8357e",
        )


if __name__ == "__main__":
    unittest.main()
