#!/usr/bin/env python3
"""Pin unique leftover for llms-txt run 33689281224. Do not remint prior leftover or publisher."""

from __future__ import annotations

import os
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RECEIPT = ROOT / "p/grok-build-llms-txt-33689281224-billing-lock-20260902-01.md"
PRIOR = ROOT / "p/grok-build-llms-txt-33687829181-billing-lock-20260902-01.md"
FIRST = ROOT / "p/grok-build-llms-txt-billing-lock-20260902-01.md"
VERIFY = ROOT / "p/grokbuild-pr8411-verify-20260902-01.md"
WORKFLOW = ROOT / ".github/workflows/llms-txt.yml"

KEEP = {
    "p/grok-build-llms-txt-33687829181-billing-lock-20260902-01.md": "3183564c",
    "p/grok-build-llms-txt-billing-lock-20260902-01.md": "cf9c9f40",
    "p/grokbuild-pr8411-verify-20260902-01.md": "642dea64",
    "p/grokbuild-open-door-guard-33687124472-billing-lock-20260902-01.md": "b91a85d3",
    "p/grok-build-discord-cloud-billing-lock-20260902-01.md": "2e0bfbfb",
    "test_grokbuild_llms_txt_33687829181_billing_lock.py": "e02e5ab5",
    "test_grokbuild_llms_txt_billing_lock.py": "6d73d3f9",
    "test_grokbuild_pr8411_verify.py": "361f5ca1",
    ".github/workflows/llms-txt.yml": "d2182a3d",
    "llms_txt.py": "83fc5ea9",
    "owner_pin.py": "76e19209",
    "test_llms_publish.py": "c07317be",
    "test_llms_pulse.py": "e79f7851",
}


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class TestGrokbuildLlmsTxt33689281224BillingLock(unittest.TestCase):
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
        first = FIRST.read_text(encoding="utf-8")
        verify = VERIFY.read_text(encoding="utf-8")
        self.assertIn("grok-build-llms-txt-33689281224-billing-lock-20260902-01", text)
        self.assertIn(
            "woahwhattheheck/commons:llms-txt:81e8f9ccc7293bf6e5179e615ba460d87f409eb0:bake",
            text,
        )
        self.assertIn("33689281224", text)
        self.assertIn("100444021463", text)
        self.assertIn("100446392928", text)
        self.assertIn("81e8f9ccc7293bf6e5179e615ba460d87f409eb0", text)
        self.assertIn("pull/8415", text)
        self.assertIn(
            "The job was not started because your account is locked due to a billing issue.",
            text,
        )
        self.assertIn("EXTERNAL_BLOCKER", text)
        self.assertIn("Did not remint leftover grok-build-llms-txt-33687829181-billing-lock-20260902-01", text)
        self.assertIn("3183564c", text)
        self.assertIn("cf9c9f40", text)
        self.assertIn("642dea64", text)
        self.assertIn("b91a85d3", text)
        self.assertIn("2e0bfbfb", text)
        self.assertIn("83fc5ea9", text)
        self.assertIn("d2182a3d", text)
        self.assertIn("did not reopen #7915", text)
        self.assertNotEqual(text, prior)
        self.assertNotEqual(text, first)
        self.assertNotEqual(text, verify)
        self.assertNotIn("llms-txt:81e8f9ccc7293bf6e5179e615ba460d87f409eb0:bake", prior)
        self.assertNotIn("llms-txt:81e8f9ccc7293bf6e5179e615ba460d87f409eb0:bake", first)
        self.assertNotIn("33689281224", prior)
        self.assertIn("llms-txt:19d172a397c98974de2b259473bfc670743a46e9:bake", prior)

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
