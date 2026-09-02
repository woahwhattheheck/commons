#!/usr/bin/env python3
"""Pin unique leftover for llms-txt run 33687829181. Do not remint prior leftover or publisher."""

from __future__ import annotations

import os
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RECEIPT = ROOT / "p/grok-build-llms-txt-33687829181-billing-lock-20260902-01.md"
PRIOR = ROOT / "p/grok-build-llms-txt-billing-lock-20260902-01.md"
DISCORD = ROOT / "p/grok-build-discord-cloud-billing-lock-20260902-01.md"
WORKFLOW = ROOT / ".github/workflows/llms-txt.yml"

KEEP = {
    "p/grok-build-llms-txt-billing-lock-20260902-01.md": "cf9c9f40",
    "p/grokbuild-open-door-guard-33687124472-billing-lock-20260902-01.md": "b91a85d3",
    "p/grok-build-discord-cloud-billing-lock-20260902-01.md": "2e0bfbfb",
    "p/grok-build-local-compute-guard-billing-lock-20260902-01.md": "de59bf75",
    "p/grok-resources-tab-freshness-billing-lock-20260902-01.md": "ac39fe78",
    "p/grokbuild-pr8402-verify-20260902-01.md": "3524e382",
    ".github/workflows/llms-txt.yml": "d2182a3d",
    "llms_txt.py": "83fc5ea9",
    "owner_pin.py": "76e19209",
    "test_llms_publish.py": "c07317be",
    "test_llms_pulse.py": "e79f7851",
    "test_grokbuild_llms_txt_billing_lock.py": "6d73d3f9",
}


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class TestGrokbuildLlmsTxt33687829181BillingLock(unittest.TestCase):
    def test_keep_publisher_and_prior_leftovers_unread(self) -> None:
        for rel, prefix in KEEP.items():
            blob = git_blob(rel)
            self.assertTrue(
                blob.startswith(prefix),
                f"{rel} reminted: want {prefix} got {blob[:8]}",
            )
        yml = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("python3 llms_txt.py --publish", yml)
        self.assertIn("ref: main", yml)
        self.assertNotIn("billing", yml.lower())
        self.assertNotIn("if: false", yml)
        src = (ROOT / "llms_txt.py").read_text(encoding="utf-8")
        self.assertIn('os.environ.get("GITHUB_ACTIONS") != "true"', src)
        self.assertIn("unsafe-context", src)

    def test_receipt_is_unique_and_does_not_remint(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        prior = PRIOR.read_text(encoding="utf-8")
        discord = DISCORD.read_text(encoding="utf-8")
        self.assertIn("grok-build-llms-txt-33687829181-billing-lock-20260902-01", text)
        self.assertIn(
            "woahwhattheheck/commons:llms-txt:19d172a397c98974de2b259473bfc670743a46e9:bake",
            text,
        )
        self.assertIn("33687829181", text)
        self.assertIn("100439409819", text)
        self.assertIn("100440510020", text)
        self.assertIn(
            "The job was not started because your account is locked due to a billing issue.",
            text,
        )
        self.assertIn("EXTERNAL_BLOCKER", text)
        self.assertIn("Did not remint leftover grok-build-llms-txt-billing-lock-20260902-01", text)
        self.assertIn("cf9c9f40", text)
        self.assertIn("b91a85d3", text)
        self.assertIn("2e0bfbfb", text)
        self.assertIn("de59bf75", text)
        self.assertIn("ac39fe78", text)
        self.assertIn("83fc5ea9", text)
        self.assertIn("d2182a3d", text)
        self.assertIn("did not reopen #7915", text)
        self.assertNotEqual(text, prior)
        self.assertNotEqual(text, discord)
        self.assertNotIn("llms-txt:19d172a397c98974de2b259473bfc670743a46e9:bake", prior)
        self.assertIn("llms-txt:8b42a78e0fa73ba3d343d8e8e78d6ca5d1a7be03:bake", prior)
        self.assertNotIn("llms-txt:19d172a397c98974de2b259473bfc670743a46e9:bake", discord)

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


if __name__ == "__main__":
    unittest.main()
