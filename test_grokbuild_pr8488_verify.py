#!/usr/bin/env python3
"""Pin unique leftover for PR 8488 #commons receipt. Do not remint 33694219016 leftover."""

from __future__ import annotations

import hashlib
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RECEIPT = ROOT / "p/grokbuild-pr8488-verify-20260902-01.md"
PRIOR = ROOT / "p/grokbuild-open-door-guard-33694219016-billing-lock-20260902-01.md"

KEEP = {
    "p/grokbuild-open-door-guard-33694219016-billing-lock-20260902-01.md": "f1222538",
    "test_grokbuild_open_door_guard_33694219016_billing_lock.py": "1bc439b0",
    "open_door_guard.py": "4b053e43",
    "test_open_door_guard.py": "70ee5730",
    ".github/workflows/open-door-guard.yml": "6586644c",
}


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class TestGrokbuildPr8488Verify(unittest.TestCase):
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
        self.assertIn("grokbuild-pr8488-verify-20260902-01", text)
        self.assertIn("https://github.com/woahwhattheheck/commons/pull/8488", text)
        self.assertIn("ce712a1a2ec4b351a32bc1c1dad5059e57c46ea8", text)
        self.assertIn("f1222538", text)
        self.assertIn("ZmG7GNckuqaf", text)
        self.assertIn("INTEGRATED", text)
        self.assertIn("VERIFIED ON CURRENT MAIN", text)
        self.assertNotEqual(text, prior)
        self.assertNotIn("grokbuild-pr8488-verify-20260902-01", prior)
        body = text.split("---", 2)[2].lstrip("\n")
        digest = hashlib.sha256(body.encode()).hexdigest()
        digest_r = hashlib.sha256(body.rstrip("\n").encode()).hexdigest()
        self.assertTrue(
            digest == "674069318a37c2f6172da2a79a212de559614401b9e062e908300f557d9ab432"
            or digest_r == "674069318a37c2f6172da2a79a212de559614401b9e062e908300f557d9ab432",
            f"body hash mismatch full={digest} rstrip={digest_r}",
        )


if __name__ == "__main__":
    unittest.main()
