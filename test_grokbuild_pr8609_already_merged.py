#!/usr/bin/env python3
"""Pin unique PR 8609 already-merged intake verify. Do not remint original leftovers."""

from __future__ import annotations

import hashlib
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VERIFY = ROOT / "p/grokbuild-pr8609-already-merged-20260903-01.md"
ORIGINAL = ROOT / "p/grokbuild-pr8584-verify-20260903-01.md"
BODY_SHA256 = "b9d6ba80cfc4dde7b44042c450857a25ac2e991d98444a892b69eb3e7a34904d"

KEEP = {
    "p/grokbuild-pr8584-verify-20260903-01.md": "80fa5f50",
    "test_grokbuild_pr8584_verify.py": "505a6d3d",
    "p/grokbuild-harness-wakeup-33717474657-billing-lock-20260903-01.md": "f54e1846",
    "test_grokbuild_harness_wakeup_33717474657_billing_lock.py": "760a8169",
    "open_door_guard.py": "4b053e43",
    "wakeup.py": "7988ceb2",
    "test_wakeup_reliability.py": "aca39ab4",
    ".github/workflows/harness-wakeup.yml": "813043ab",
}


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class TestGrokbuildPr8609AlreadyMerged(unittest.TestCase):
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
        self.assertIn("grokbuild-pr8609-already-merged-20260903-01", text)
        self.assertIn("https://github.com/woahwhattheheck/commons/pull/8609", text)
        self.assertIn("938ac45e20ea1e89be81a9ceb563d8c8a5c280c1", text)
        self.assertIn("4a9c2db19101a013da026a1c038309024a32646a", text)
        self.assertIn("029dce78fc4f6bdc08d342b05cc5e02c861deb3e", text)
        self.assertIn("50c30b0dc6a22c561f68d2eca35b75972823a2ae", text)
        self.assertIn("80fa5f50", text)
        self.assertIn("505a6d3d", text)
        self.assertIn("f54e1846", text)
        self.assertIn("760a8169", text)
        self.assertIn("ALREADY_MERGED_VERIFIED", text)
        self.assertIn("INTEGRATED — VERIFIED ON CURRENT MAIN", text)
        self.assertIn("DURABLE_ON_MAIN", text)
        self.assertIn("3qsDjZvb9d3R", text)
        self.assertIn("issuecomment-5521021150", text)
        self.assertIn("Did not remint leftover grokbuild-pr8584-verify-20260903-01", text)
        self.assertIn("Did not reopen #7915", text)
        self.assertNotEqual(text, original)
        self.assertNotIn("grokbuild-pr8609-already-merged-20260903-01", original)
        parts = text.split("---\n")
        self.assertGreaterEqual(len(parts), 3)
        body = parts[2].lstrip("\n").rstrip("\n")
        self.assertEqual(hashlib.sha256(body.encode("utf-8")).hexdigest(), BODY_SHA256)

    def test_prior_verify_unittest_still_green(self) -> None:
        proc = subprocess.run(
            ["python3", "-m", "unittest", "test_grokbuild_pr8584_verify.py"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
        self.assertIn("Ran 4 tests", proc.stderr + proc.stdout)


if __name__ == "__main__":
    unittest.main()
