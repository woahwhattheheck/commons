#!/usr/bin/env python3
"""Pin unique #commons ping for PR 8445. Do not remint llms-txt 33689083252 leftover."""

from __future__ import annotations

import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RECEIPT = ROOT / "p/grokbuild-pr8445-commons-20260902-01.md"
PRIOR = ROOT / "p/grok-build-llms-txt-33689083252-billing-lock-20260902-01.md"

KEEP = {
    "p/grok-build-llms-txt-33689083252-billing-lock-20260902-01.md": "31213531",
    "test_grokbuild_llms_txt_33689083252_billing_lock.py": "1fda6a87",
    "p/grok-build-llms-txt-33689096471-billing-lock-20260902-01.md": "e739b9cd",
    "p/grok-build-llms-txt-33687829181-billing-lock-20260902-01.md": "3183564c",
    "p/grok-build-llms-txt-billing-lock-20260902-01.md": "cf9c9f40",
    "p/grokbuild-occupancy-landed-work-keep-lift-20260902-01.md": "67a8a527",
    ".github/workflows/llms-txt.yml": "d2182a3d",
    "llms_txt.py": "83fc5ea9",
}


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class TestGrokbuildPr8445Commons(unittest.TestCase):
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
        self.assertIn("grokbuild-pr8445-commons-20260902-01", text)
        self.assertIn(
            "woahwhattheheck/commons:llms-txt:de52301ba37a900f184bc790c97a336832409091:bake",
            text,
        )
        self.assertIn("33689083252", text)
        self.assertIn("7e5903bb46e5820c10241d71a0d7304bd881c726", text)
        self.assertIn("31213531", text)
        self.assertIn("3386c8ba17fd7543fc09011b97dcbf3569f6d777c3cc6a2875c3cf9cf59be590", text)
        self.assertIn("W5hWrbrg8H7V", text)
        self.assertIn("Did not remint", text)
        self.assertIn("did not reopen #7915", text.lower())
        self.assertNotEqual(text, prior)
        self.assertNotIn(
            "llms-txt:de52301ba37a900f184bc790c97a336832409091:bake",
            prior.split("---", 2)[0] if False else prior[:200],
        )
        self.assertIn(
            "llms-txt:de52301ba37a900f184bc790c97a336832409091:bake",
            prior,
        )


if __name__ == "__main__":
    unittest.main()
