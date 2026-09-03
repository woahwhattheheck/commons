#!/usr/bin/env python3
"""Pin unique PR 8585 already-merged verify. Do not remint slack-service-tags leftover."""

from __future__ import annotations

import hashlib
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VERIFY = ROOT / "p/grokbuild-pr8585-intake-verify-20260903-01.md"
LEFTOVER = ROOT / "p/grokbuild-slack-service-tags-33717615004-billing-lock-20260903-01.md"
BODY_SHA256 = "95d847f97d693f8c14e7f859ee5c0bf507a806bff8b150131c8ffe040d00d87c"


def git_blob(rel: str) -> str:
    return subprocess.check_output(["git", "hash-object", str(ROOT / rel)], text=True).strip()


class TestGrokbuildPr8585IntakeVerify(unittest.TestCase):
    def test_original_leftover_unread(self) -> None:
        self.assertTrue(
            git_blob("p/grokbuild-slack-service-tags-33717615004-billing-lock-20260903-01.md").startswith(
                "f33a76ef"
            )
        )
        self.assertTrue(
            git_blob("test_grokbuild_slack_service_tags_33717615004_billing_lock.py").startswith("e10a1435")
        )

    def test_verify_receipt_is_unique(self) -> None:
        text = VERIFY.read_text(encoding="utf-8")
        leftover = LEFTOVER.read_text(encoding="utf-8")
        self.assertIn("grokbuild-pr8585-intake-verify-20260903-01", text)
        self.assertIn("https://github.com/woahwhattheheck/commons/pull/8585", text)
        self.assertIn("fd44bb2d1aaef4175286c455f9574508109d0e8b", text)
        self.assertIn("992c67d48c3ff20f293d5f190787ece735c5ffb7", text)
        self.assertIn("f33a76ef", text)
        self.assertIn("ALREADY_MERGED_VERIFIED", text)
        self.assertIn("INTEGRATED — VERIFIED ON CURRENT MAIN", text)
        self.assertIn("DURABLE_ON_MAIN", text)
        self.assertIn("E7dBG3XTLANF", text)
        self.assertNotEqual(text, leftover)
        self.assertNotIn("grokbuild-pr8585-intake-verify-20260903-01", leftover)
        parts = text.split("---\n")
        self.assertGreaterEqual(len(parts), 3)
        body = parts[2].lstrip("\n").rstrip("\n")
        self.assertEqual(hashlib.sha256(body.encode("utf-8")).hexdigest(), BODY_SHA256)


if __name__ == "__main__":
    unittest.main()
