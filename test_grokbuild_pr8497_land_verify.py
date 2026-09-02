#!/usr/bin/env python3
"""Pin unique leftover for PR 8497 land-verify. Do not remint the billing leftover."""

from __future__ import annotations

import hashlib
import subprocess
import unittest
from pathlib import Path

import open_door_guard as guard

ROOT = Path(__file__).resolve().parent
RECEIPT = ROOT / "p/grokbuild-pr8497-land-verify-20260902-01.md"
PRIOR = ROOT / "p/grokbuild-open-door-guard-33694253452-billing-lock-20260902-01.md"

KEEP = {
    "p/grokbuild-open-door-guard-33694253452-billing-lock-20260902-01.md": "694794f6",
    "test_grokbuild_open_door_guard_33694253452_billing_lock.py": "5c721626",
    "p/grokbuild-pr8480-verify-20260902-01.md": "9200ff14",
    "open_door_guard.py": "4b053e43",
    "test_open_door_guard.py": "70ee5730",
    ".github/workflows/open-door-guard.yml": "6586644c",
}


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class TestGrokbuildPr8497LandVerify(unittest.TestCase):
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
        self.assertIn("grokbuild-pr8497-land-verify-20260902-01", text)
        self.assertIn(
            "woahwhattheheck/commons#8497@3900a4d5bfeb20d8e5286761ddc27f7de98de5e5",
            text,
        )
        self.assertIn("https://github.com/woahwhattheheck/commons/pull/8497", text)
        self.assertIn("3900a4d5bfeb20d8e5286761ddc27f7de98de5e5", text)
        self.assertIn("8d3fe7bd4f7af51b0ce1c481de185c12ac282eb7", text)
        self.assertIn("9942ddd2f689b0c1519dd3a137e788b60028ba45", text)
        self.assertIn("694794f6", text)
        self.assertIn("5c721626", text)
        self.assertIn("hBBC2cJaQTOi", text)
        self.assertIn("MERGED+VERIFIED", text)
        self.assertIn("ALREADY_MERGED_VERIFIED", text)
        self.assertNotEqual(text, prior)
        self.assertNotIn("grokbuild-pr8497-land-verify-20260902-01", prior)
        body = text.split("---", 2)[2].lstrip("\n")
        self.assertEqual(
            hashlib.sha256(body.rstrip("\n").encode()).hexdigest(),
            "b0c7b2aebc09f11d3e92db8aaddd0b0e54946b4d2c330c04432448cb8e4563be",
        )

    def test_added_lines_are_open(self) -> None:
        added = [
            guard.AddedLine(str(RECEIPT.relative_to(ROOT)), 1, line)
            for line in RECEIPT.read_text(encoding="utf-8").splitlines()
        ]
        added.extend(
            guard.AddedLine(str(Path(__file__).name), 1, line)
            for line in Path(__file__).read_text(encoding="utf-8").splitlines()
        )
        self.assertEqual(guard.scan_added(added), [])


if __name__ == "__main__":
    unittest.main()
