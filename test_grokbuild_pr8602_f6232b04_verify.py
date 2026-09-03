#!/usr/bin/env python3
"""Pin unique PR 8602 already-merged intake verify. Do not remint original leftover."""

from __future__ import annotations

import hashlib
import subprocess
import unittest
from pathlib import Path

import open_door_guard as door

ROOT = Path(__file__).resolve().parent
VERIFY = ROOT / "p/grokbuild-pr8602-f6232b04-verify-20260903-01.md"
ORIGINAL = ROOT / "p/grokbuild-local-compute-guard-33718131429-billing-lock-20260903-01.md"
ORIGINAL_TEST = ROOT / "test_grokbuild_local_compute_guard_33718131429_billing_lock.py"
BODY_SHA256 = "b287847f46da506553cd65ddbdceb1f031d6dac714907471b7a5508736c1b84b"

KEEP = {
    "p/grokbuild-local-compute-guard-33718131429-billing-lock-20260903-01.md": "ceb14fe0",
    "test_grokbuild_local_compute_guard_33718131429_billing_lock.py": "9f712e5f",
    "open_door_guard.py": "4b053e43",
}


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class TestGrokbuildPr8602F6232b04Verify(unittest.TestCase):
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
        self.assertIn("grokbuild-pr8602-f6232b04-verify-20260903-01", text)
        self.assertIn("https://github.com/woahwhattheheck/commons/pull/8602", text)
        self.assertIn("f6232b046251a40aee0292cbfb2914146ab5932e", text)
        self.assertIn("029dce78", text)
        self.assertIn("9edc5b8dd8633ab74472946cc1c1f7080808deee", text)
        self.assertIn("ceb14fe0", text)
        self.assertIn("9f712e5f", text)
        self.assertIn("33718131429", text)
        self.assertIn("ALREADY_MERGED", text)
        self.assertIn("VERIFIED_ON_CURRENT_MAIN", text)
        self.assertIn("wzmNflRRpujg", text)
        self.assertIn("Did not remint", text)
        self.assertIn("Did not reopen #7915", text)
        self.assertNotEqual(text, original)
        self.assertNotIn("grokbuild-pr8602-f6232b04-verify-20260903-01", original)
        parts = text.split("---\n")
        self.assertGreaterEqual(len(parts), 3)
        body = parts[2].lstrip("\n").rstrip("\n")
        self.assertEqual(hashlib.sha256(body.encode("utf-8")).hexdigest(), BODY_SHA256)
        added = [
            door.AddedLine(str(VERIFY.relative_to(ROOT)), 1, line)
            for line in text.splitlines()
        ]
        self.assertEqual(door.scan_added(added), [])
        self.assertTrue(ORIGINAL_TEST.is_file())


if __name__ == "__main__":
    unittest.main()
