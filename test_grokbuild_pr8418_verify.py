#!/usr/bin/env python3
"""Pin unique leftover for PR 8418 #commons receipt. Do not remint 8410 leftover."""

from __future__ import annotations

import hashlib
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RECEIPT = ROOT / "p/grokbuild-pr8418-verify-20260902-01.md"
PRIOR = ROOT / "p/grokbuild-pr8410-verify-20260902-01.md"

KEEP = {
    "p/grokbuild-pr8410-verify-20260902-01.md": "4cfe563a",
    "p/grokbuild-pr8401-verify-20260902-01.md": "4d21f9e9",
    "p/grokbuild-pr8399-commons-slack-20260902-01.md": "1905dd74",
    "host/stealable_lanes.py": "c90284fb",
    "p/cursor-stealable-lanes-occupancy-20260902-01.md": "9631e869",
    "p/grokbuild-occupancy-landed-work-keep-lift-20260902-01.md": "67a8a527",
    "p/cursor-stealable-lanes-roles-20260902-01.md": "5f1ef25f",
    "p/cursor-stealable-lanes-roles-readback-20260902-01.md": "ada92980",
    "p/grokbuild-stealable-occupancy-keep-match-20260902-01.md": "dc058b13",
    "ground/OWNER_NOW.md": "59b1fd37",
}


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class TestGrokbuildPr8418Verify(unittest.TestCase):
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
        self.assertIn("grokbuild-pr8418-verify-20260902-01", text)
        self.assertIn("woahwhattheheck/commons#8418@b08ccb7684f93a62f589ae903f15d5a37c54c4be", text)
        self.assertIn("https://github.com/woahwhattheheck/commons/pull/8418", text)
        self.assertIn("f6c9a8675e4b17433266b0d2f4fc002d05a87253", text)
        self.assertIn("4cfe563a", text)
        self.assertIn("VQ4O3Q4foZ7K", text)
        self.assertIn("Did not remint", text)
        self.assertIn("No auth", text)
        self.assertNotEqual(text, prior)
        body = text.split("---", 2)[2].lstrip("\n")
        self.assertEqual(
            hashlib.sha256(body.rstrip("\n").encode()).hexdigest(),
            "b63fba7676f215296e3631f27cb29b4ca38ffb7595e0a4e904d8c28d0b2214fb",
        )


if __name__ == "__main__":
    unittest.main()
