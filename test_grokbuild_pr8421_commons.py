#!/usr/bin/env python3
"""Pin unique #commons ping for PR 8421. Do not remint llms-txt 33689096471 leftover."""

from __future__ import annotations

import hashlib
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RECEIPT = ROOT / "p/grokbuild-pr8421-commons-20260902-01.md"
PRIOR = ROOT / "p/grok-build-llms-txt-33689096471-billing-lock-20260902-01.md"

KEEP = {
    "p/grok-build-llms-txt-33689096471-billing-lock-20260902-01.md": "e739b9cd",
    "test_grokbuild_llms_txt_33689096471_billing_lock.py": "862e61d2",
    "p/grok-build-llms-txt-33687829181-billing-lock-20260902-01.md": "3183564c",
    "p/grok-build-llms-txt-billing-lock-20260902-01.md": "cf9c9f40",
    ".github/workflows/llms-txt.yml": "d2182a3d",
    "llms_txt.py": "83fc5ea9",
}


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class TestGrokbuildPr8421Commons(unittest.TestCase):
    def test_keep_run_leftover_and_publisher_unread(self) -> None:
        for rel, prefix in KEEP.items():
            blob = git_blob(rel)
            self.assertTrue(
                blob.startswith(prefix),
                f"{rel} reminted: want {prefix} got {blob[:8]}",
            )

    def test_receipt_is_unique_and_cites_landed_leftover(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        prior = PRIOR.read_text(encoding="utf-8")
        self.assertIn("grokbuild-pr8421-commons-20260902-01", text)
        self.assertIn("woahwhattheheck/commons:llms-txt:920d8c03a247d6b1ee640b523ef9447dfe4c7477:bake", text)
        self.assertIn("33689096471", text)
        self.assertIn("69d106bf3d02220cd90c31621daccec18a7b6ec5", text)
        self.assertIn("e739b9cd", text)
        self.assertIn("Did not remint", text)
        self.assertIn("did not reopen #7915", text.lower())
        self.assertNotEqual(text, prior)
        body = text.split("---", 2)[2].lstrip("\n")
        self.assertEqual(
            hashlib.sha256(body.rstrip("\n").encode()).hexdigest(),
            "da063039c48759e6b52f3711985fbcc15ae8651a31610257c0fd37cb59d688d6",
        )


if __name__ == "__main__":
    unittest.main()
