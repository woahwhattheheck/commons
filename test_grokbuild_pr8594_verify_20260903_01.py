#!/usr/bin/env python3
"""Pin grok-build verify leftover for already-merged PR 8594. Do not remint the spec-guard leftover."""

from __future__ import annotations

import hashlib
import subprocess
import unittest
from pathlib import Path

import open_door_guard as guard

ROOT = Path(__file__).resolve().parent
RECEIPT = ROOT / "p/grokbuild-pr8594-verify-20260903-01.md"
LEFTOVER = ROOT / "p/grokbuild-muhlnickel-spec-guard-33717733967-billing-lock-20260903-01.md"
LEFTOVER_TEST = ROOT / "test_grokbuild_muhlnickel_spec_guard_33717733967_billing_lock.py"
PEER = ROOT / "p/grokbuild-muhlnickel-spec-guard-33699980193-billing-lock-20260903-01.md"
PEER_TEST = ROOT / "test_grokbuild_muhlnickel_spec_guard_33699980193_billing_lock.py"

KEEP = {
    "p/grokbuild-muhlnickel-spec-guard-33717733967-billing-lock-20260903-01.md": "5b7f49cd",
    "test_grokbuild_muhlnickel_spec_guard_33717733967_billing_lock.py": "87c3be5c",
    "muhlnickel_spec_guard.py": "74423d71",
    "test_muhlnickel_spec_guard.py": "097742ec",
    ".github/workflows/muhlnickel-spec-guard.yml": "7886bdf1",
    "open_door_guard.py": "4b053e43",
    "p/grokbuild-muhlnickel-spec-guard-33699980193-billing-lock-20260903-01.md": "79285c10",
    "test_grokbuild_muhlnickel_spec_guard_33699980193_billing_lock.py": "e4363b6a",
}

BODY_SHA256 = "1dda787eec3da5e31d95ad35482ac74e9efe69b5212bb628efcb5295bc6d63f6"


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


def receipt_body(text: str) -> str:
    marker = "\n---\n"
    idx = text.rfind(marker)
    if idx < 0:
        raise AssertionError("missing body separator")
    return text[idx + len(marker) :]


class TestGrokbuildPr8594Verify(unittest.TestCase):
    def test_keep_8594_leftover_and_guard_unread(self) -> None:
        for rel, prefix in KEEP.items():
            blob = git_blob(rel)
            self.assertTrue(
                blob.startswith(prefix),
                f"{rel} reminted: want {prefix} got {blob[:8]}",
            )

    def test_receipt_cites_8594_and_does_not_remint(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        leftover = LEFTOVER.read_text(encoding="utf-8")
        leftover_test = LEFTOVER_TEST.read_text(encoding="utf-8")
        peer = PEER.read_text(encoding="utf-8")
        peer_test = PEER_TEST.read_text(encoding="utf-8")
        body = receipt_body(text)
        self.assertEqual(hashlib.sha256(body.encode()).hexdigest(), BODY_SHA256)
        self.assertIn("grokbuild-pr8594-verify-20260903-01", text)
        self.assertIn(
            "woahwhattheheck/commons#8594@16f2380582ac86447b35d5991cafd969e3023b70",
            text,
        )
        self.assertIn("https://github.com/woahwhattheheck/commons/pull/8594", text)
        self.assertIn("16f2380582ac86447b35d5991cafd969e3023b70", text)
        self.assertIn("3bd2404fb328970d391ca2a91d59390081ef4a1b", text)
        self.assertIn("e9f6ff71e5b549f3d790e913b0281bb778405d58", text)
        self.assertIn("5b7f49cd", text)
        self.assertIn("87c3be5c", text)
        self.assertIn("ALREADY_MERGED_VERIFIED", text)
        self.assertIn("INTEGRATED — VERIFIED ON CURRENT MAIN", text)
        self.assertIn("DURABLE_ON_MAIN", text)
        self.assertIn(
            "Did not remint leftover grokbuild-muhlnickel-spec-guard-33717733967-billing-lock-20260903-01",
            text,
        )
        self.assertIn("Did not reopen #7915", text)
        self.assertIn("Did not reopen #8583", text)
        self.assertNotEqual(text, leftover)
        self.assertNotEqual(text, peer)
        self.assertNotEqual(Path(__file__).read_text(encoding="utf-8"), leftover_test)
        self.assertNotEqual(Path(__file__).read_text(encoding="utf-8"), peer_test)
        self.assertNotIn("woahwhattheheck/commons#8594@", leftover)
        self.assertNotIn("buy.stripe.com", text)

    def test_original_leftover_unittest_still_green(self) -> None:
        proc = subprocess.run(
            [
                "python3",
                "-m",
                "unittest",
                "test_grokbuild_muhlnickel_spec_guard_33717733967_billing_lock.py",
            ],
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
                "test_grokbuild_pr8594_verify_20260903_01.py", 1, line
            )
            for line in Path(__file__).read_text(encoding="utf-8").splitlines()
        ]
        self.assertEqual(guard.scan_added(added), [])
        receipt_added = [
            guard.AddedLine(
                "p/grokbuild-pr8594-verify-20260903-01.md",
                1,
                line,
            )
            for line in RECEIPT.read_text(encoding="utf-8").splitlines()
        ]
        self.assertEqual(guard.scan_added(receipt_added), [])


if __name__ == "__main__":
    unittest.main()
