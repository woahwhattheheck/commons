#!/usr/bin/env python3
"""Pin grok-build verify leftover for already-merged PR 8407. Do not remint llms-txt leftover."""

from __future__ import annotations

import hashlib
import os
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RECEIPT = ROOT / "p/grokbuild-pr8407-verify-20260902-01.md"
PRIOR = ROOT / "p/grok-build-llms-txt-billing-lock-20260902-01.md"
LATER = ROOT / "p/grok-build-llms-txt-33687829181-billing-lock-20260902-01.md"
DISCORD = ROOT / "p/grok-build-discord-cloud-billing-lock-20260902-01.md"
WORKFLOW = ROOT / ".github/workflows/llms-txt.yml"

KEEP = {
    "p/grok-build-llms-txt-billing-lock-20260902-01.md": "cf9c9f40",
    "test_grokbuild_llms_txt_billing_lock.py": "6d73d3f9",
    "p/grok-build-llms-txt-33687829181-billing-lock-20260902-01.md": "3183564c",
    "test_grokbuild_llms_txt_33687829181_billing_lock.py": "e02e5ab5",
    "p/grokbuild-pr8402-verify-20260902-01.md": "3524e382",
    "p/grokbuild-open-door-guard-33687124472-billing-lock-20260902-01.md": "b91a85d3",
    "p/grok-build-discord-cloud-billing-lock-20260902-01.md": "2e0bfbfb",
    "p/grok-build-local-compute-guard-billing-lock-20260902-01.md": "de59bf75",
    "p/grok-resources-tab-freshness-billing-lock-20260902-01.md": "ac39fe78",
    ".github/workflows/llms-txt.yml": "d2182a3d",
    "llms_txt.py": "83fc5ea9",
    "owner_pin.py": "76e19209",
    "test_llms_publish.py": "c07317be",
    "test_llms_pulse.py": "e79f7851",
}

BODY_SHA256 = "bfd6311be41df6fc2baa59213ac75c8abbafca35b98442252078b4b8e88fd38f"


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


def receipt_body(text: str) -> str:
    parts = text.split("---\n", 2)
    return parts[2].rstrip("\n") if len(parts) >= 3 else text


class TestGrokbuildPr8407Verify(unittest.TestCase):
    def test_keep_8407_leftover_and_peers_unread(self) -> None:
        for rel, prefix in KEEP.items():
            blob = git_blob(rel)
            self.assertTrue(
                blob.startswith(prefix),
                f"{rel} reminted: want {prefix} got {blob[:8]}",
            )
        yml = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("python3 llms_txt.py --publish", yml)
        self.assertNotIn("billing", yml.lower())
        self.assertNotIn("if: false", yml)

    def test_publish_still_refuses_outside_actions(self) -> None:
        env = os.environ.copy()
        env.pop("GITHUB_ACTIONS", None)
        rc = subprocess.run(
            ["python3", "llms_txt.py", "--publish"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            env=env,
        )
        self.assertNotEqual(rc.returncode, 0)
        out = (rc.stdout or "") + (rc.stderr or "")
        self.assertIn("refused outside GitHub Actions", out)
        self.assertIn("unsafe-context", out)

    def test_receipt_cites_8407_and_does_not_remint(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        prior = PRIOR.read_text(encoding="utf-8")
        later = LATER.read_text(encoding="utf-8")
        discord = DISCORD.read_text(encoding="utf-8")
        body = receipt_body(text)
        self.assertEqual(hashlib.sha256(body.encode("utf-8")).hexdigest(), BODY_SHA256)
        self.assertIn("grokbuild-pr8407-verify-20260902-01", text)
        self.assertIn("yqMLbRx5aQrA", text)
        self.assertIn(
            "woahwhattheheck/commons:llms-txt:8b42a78e0fa73ba3d343d8e8e78d6ca5d1a7be03:bake",
            text,
        )
        self.assertIn("33686687861", text)
        self.assertIn("1e411a4e", text)
        self.assertIn("issuecomment-5517001800", text)
        self.assertIn("cf9c9f40", text)
        self.assertIn("6d73d3f9", text)
        self.assertIn("3183564c", text)
        self.assertIn("Did not remint leftover", text)
        self.assertIn("Did not reopen #7915", text)
        self.assertIn(
            "The job was not started because your account is locked due to a billing issue.",
            text,
        )
        self.assertIn("ALREADY_MERGED_VERIFIED", text)
        self.assertNotEqual(text, prior)
        self.assertNotEqual(text, later)
        self.assertNotEqual(text, discord)
        self.assertIn("33686687861", prior)
        self.assertNotIn("grokbuild-pr8407-verify-20260902-01", prior)


if __name__ == "__main__":
    unittest.main()
