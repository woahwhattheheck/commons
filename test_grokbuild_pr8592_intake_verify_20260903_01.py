#!/usr/bin/env python3
"""Pin grok-build verify leftover for already-merged PR 8592. Do not remint the path-manifest leftover."""

from __future__ import annotations

import subprocess
import unittest
from pathlib import Path

import open_door_guard as guard

ROOT = Path(__file__).resolve().parent
RECEIPT = ROOT / "p/grokbuild-pr8592-intake-verify-20260903-01.md"
LEFTOVER = ROOT / "p/grokbuild-path-manifest-33717733938-billing-lock-20260903-01.md"
LEFTOVER_TEST = ROOT / "test_grokbuild_path_manifest_33717733938_billing_lock.py"
SIBLING = ROOT / "p/grokbuild-path-manifest-33699980177-billing-lock-20260903-01.md"
SIBLING_TEST = ROOT / "test_grokbuild_path_manifest_33699980177_billing_lock.py"

KEEP = {
    "p/grokbuild-path-manifest-33717733938-billing-lock-20260903-01.md": "85a5f189",
    "test_grokbuild_path_manifest_33717733938_billing_lock.py": "992e84ca",
    "p/grokbuild-path-manifest-33699980177-billing-lock-20260903-01.md": "d9365b97",
    "test_grokbuild_path_manifest_33699980177_billing_lock.py": "4740e323",
    "test_path_manifest.py": "c6de797a",
    "host/path_manifest.py": "dcc94697",
    ".github/workflows/path-manifest.yml": "b29dec8a",
    "architecture/path-manifest.json": "e5ecb24f",
    "open_door_guard.py": "4b053e43",
}


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class TestGrokbuildPr8592IntakeVerify(unittest.TestCase):
    def test_keep_8592_leftover_and_classifier_unread(self) -> None:
        for rel, prefix in KEEP.items():
            blob = git_blob(rel)
            self.assertTrue(
                blob.startswith(prefix),
                f"{rel} reminted: want {prefix} got {blob[:8]}",
            )

    def test_receipt_cites_8592_and_does_not_remint(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        leftover = LEFTOVER.read_text(encoding="utf-8")
        leftover_test = LEFTOVER_TEST.read_text(encoding="utf-8")
        sibling = SIBLING.read_text(encoding="utf-8")
        sibling_test = SIBLING_TEST.read_text(encoding="utf-8")
        self.assertIn("grokbuild-pr8592-intake-verify-20260903-01", text)
        self.assertIn(
            "woahwhattheheck/commons#8592@9f0318145f5c3045692a67f319f978e05a1de55f",
            text,
        )
        self.assertIn("https://github.com/woahwhattheheck/commons/pull/8592", text)
        self.assertIn("9f0318145f5c3045692a67f319f978e05a1de55f", text)
        self.assertIn("aab69a205ae89ebbbb7500ab4da34da98674a559", text)
        self.assertIn("f6daf48acdd325860f14847d3d9846bac370b949", text)
        self.assertIn("4e2b1410d7e7dc8b89e9b28a522923a86e9ea828", text)
        self.assertIn("85a5f189", text)
        self.assertIn("992e84ca", text)
        self.assertIn("ALREADY_MERGED_VERIFIED", text)
        self.assertIn("INTEGRATED — VERIFIED ON CURRENT MAIN", text)
        self.assertIn("DURABLE_ON_MAIN", text)
        self.assertIn("Did not remint leftover grokbuild-path-manifest-33717733938-billing-lock-20260903-01", text)
        self.assertIn("Did not reopen #7915", text)
        self.assertIn("Did not reopen #8583", text)
        self.assertNotEqual(text, leftover)
        self.assertNotEqual(text, sibling)
        self.assertNotEqual(Path(__file__).read_text(encoding="utf-8"), leftover_test)
        self.assertNotEqual(Path(__file__).read_text(encoding="utf-8"), sibling_test)
        self.assertNotIn("woahwhattheheck/commons#8592@", leftover)
        self.assertNotIn("buy.stripe.com", text)

    def test_original_leftover_unittest_still_green(self) -> None:
        proc = subprocess.run(
            ["python3", "-m", "unittest", "test_grokbuild_path_manifest_33717733938_billing_lock"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
        self.assertIn("Ran 4 tests", proc.stderr + proc.stdout)

    def test_new_files_do_not_add_locks(self) -> None:
        added = [
            guard.AddedLine(
                "test_grokbuild_pr8592_intake_verify_20260903_01.py", 1, line
            )
            for line in Path(__file__).read_text(encoding="utf-8").splitlines()
        ]
        self.assertEqual(guard.scan_added(added), [])
        receipt_added = [
            guard.AddedLine(
                "p/grokbuild-pr8592-intake-verify-20260903-01.md",
                1,
                line,
            )
            for line in RECEIPT.read_text(encoding="utf-8").splitlines()
        ]
        self.assertEqual(guard.scan_added(receipt_added), [])


if __name__ == "__main__":
    unittest.main()
