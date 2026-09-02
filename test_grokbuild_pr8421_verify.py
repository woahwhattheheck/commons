#!/usr/bin/env python3
"""Pin grok-build verify leftover for already-merged PR 8421. Do not remint llms-txt leftover."""

from __future__ import annotations

import hashlib
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RECEIPT = ROOT / "p/grokbuild-pr8421-verify-20260902-01.md"
PRIOR = ROOT / "p/grok-build-llms-txt-33689096471-billing-lock-20260902-01.md"
ORIGINAL = ROOT / "p/grok-build-llms-txt-billing-lock-20260902-01.md"

KEEP = {
    "p/grok-build-llms-txt-33689096471-billing-lock-20260902-01.md": "e739b9cd",
    "test_grokbuild_llms_txt_33689096471_billing_lock.py": "862e61d2",
    "p/grok-build-llms-txt-billing-lock-20260902-01.md": "cf9c9f40",
    "p/grok-build-llms-txt-33687829181-billing-lock-20260902-01.md": "3183564c",
    ".github/workflows/llms-txt.yml": "d2182a3d",
    "llms_txt.py": "83fc5ea9",
}

BODY_SHA256 = "28435b5fe13a8af234f3ea96e8d74c914235eef42d568b7a349b812c4456aa64"


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


def receipt_body(text: str) -> str:
    parts = text.split("---\n", 2)
    return parts[2].rstrip("\n") if len(parts) >= 3 else text


class TestGrokbuildPr8421Verify(unittest.TestCase):
    def test_keep_8421_leftover_and_publisher_unread(self) -> None:
        for rel, prefix in KEEP.items():
            blob = git_blob(rel)
            self.assertTrue(
                blob.startswith(prefix),
                f"{rel} reminted: want {prefix} got {blob[:8]}",
            )

    def test_leftover_33689096471_tests_still_pass(self) -> None:
        proc = subprocess.run(
            ["python3", "-m", "unittest", "test_grokbuild_llms_txt_33689096471_billing_lock.py"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
        self.assertIn("Ran 3 tests", proc.stderr + proc.stdout)

    def test_receipt_cites_8421_and_does_not_remint(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        prior = PRIOR.read_text(encoding="utf-8")
        original = ORIGINAL.read_text(encoding="utf-8")
        body = receipt_body(text)
        self.assertEqual(hashlib.sha256(body.encode("utf-8")).hexdigest(), BODY_SHA256)
        self.assertIn("grokbuild-pr8421-verify-20260902-01", text)
        self.assertIn(
            "woahwhattheheck/commons#8421@bd06d77d34752316ff4b99e3dfd66340bda45718",
            text,
        )
        self.assertIn("https://github.com/woahwhattheheck/commons/pull/8421", text)
        self.assertIn("issuecomment-5517322927", text)
        self.assertIn("69d106bf", text)
        self.assertIn("e739b9cd", text)
        self.assertIn("862e61d2", text)
        self.assertIn("83fc5ea9", text)
        self.assertIn("d2182a3d", text)
        self.assertIn("ALREADY_MERGED_VERIFIED", text)
        self.assertIn("Did not remint cf9c9f40", text)
        self.assertIn("Did not reopen #7915", text)
        self.assertIn("owner GitHub account billing lock", text)
        self.assertNotEqual(text, prior)
        self.assertNotEqual(text, original)
        self.assertNotIn("grokbuild-pr8421-verify-20260902-01", prior)
        self.assertNotIn("buy.stripe.com", text)


if __name__ == "__main__":
    unittest.main()
