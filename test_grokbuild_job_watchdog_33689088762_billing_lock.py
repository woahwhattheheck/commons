#!/usr/bin/env python3
"""Pin unique leftover for job-watchdog run 33689088762. Do not remint watchdog or PR 8414 leftovers."""

from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

import fix_first

ROOT = Path(__file__).resolve().parent
RECEIPT = ROOT / "p/grok-build-job-watchdog-33689088762-billing-lock-20260902-01.md"
VERIFY = ROOT / "p/grokbuild-pr8414-verify-20260902-01.md"
PRIOR = ROOT / "p/cursor-merge-on-pr-readback-20260902-01.md"
COLLISION = ROOT / "p/grokbuild-pr-collision-notice-33689085107-billing-lock-20260902-01.md"
WORKFLOW = ROOT / ".github/workflows/job-watchdog.yml"

KEEP = {
    ".github/workflows/job-watchdog.yml": "5af545c2",
    "harness_wake/__main__.py": "a4457781",
    "harness_wake/watchdog.py": "149ed075",
    "harness_wake/land.py": "31ae9844",
    "test_job_watchdog_land.py": "2f055030",
    "test_harness_wake.py": "ab71ef24",
    "p/cursor-merge-on-pr-readback-20260902-01.md": "e160b2c3",
    "p/cursor-merge-on-pr-20260902-01.md": "22b63e25",
    "p/grokbuild-pr8414-verify-20260902-01.md": "587cc1cf",
    "test_grokbuild_pr8414_verify.py": "93fd9808",
    "p/grokbuild-pr-collision-notice-33689085107-billing-lock-20260902-01.md": "594b5e71",
    "p/grok-build-llms-txt-33687829181-billing-lock-20260902-01.md": "3183564c",
    "p/grok-build-discord-cloud-billing-lock-20260902-01.md": "2e0bfbfb",
    "p/grokbuild-open-door-guard-33687124472-billing-lock-20260902-01.md": "b91a85d3",
}


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class TestGrokbuildJobWatchdog33689088762BillingLock(unittest.TestCase):
    def test_keep_watchdog_and_8414_leftovers_unread(self) -> None:
        for rel, prefix in KEEP.items():
            blob = git_blob(rel)
            self.assertTrue(
                blob.startswith(prefix),
                f"{rel} reminted: want {prefix} got {blob[:8]}",
            )
        yml = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("python3 -m harness_wake --tick", yml)
        self.assertIn("runs-on: ubuntu-latest", yml)
        self.assertNotIn("if: false", yml)
        self.assertNotIn("billing", yml.lower())

    def test_local_failed_step_still_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            proc = subprocess.run(
                ["python3", "-m", "harness_wake", "--tick", "--jobs-dir", tmp],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
        self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertTrue(payload.get("ok"))
        self.assertEqual(payload.get("state"), "TICKED")
        self.assertFalse(payload.get("invoke_model"))

    def test_receipt_cites_run_and_does_not_remint(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        verify = VERIFY.read_text(encoding="utf-8")
        prior = PRIOR.read_text(encoding="utf-8")
        collision = COLLISION.read_text(encoding="utf-8")
        self.assertIn("grok-build-job-watchdog-33689088762-billing-lock-20260902-01", text)
        self.assertIn(
            "woahwhattheheck/commons:job-watchdog:0675fb559de118427a4c37b3cc406fc9f4cc7b64:tick",
            text,
        )
        self.assertIn("33689088762", text)
        self.assertIn("100443432387", text)
        self.assertIn("100446135280", text)
        self.assertIn("0675fb559de118427a4c37b3cc406fc9f4cc7b64", text)
        self.assertIn(
            "The job was not started because your account is locked due to a billing issue.",
            text,
        )
        self.assertIn("EXTERNAL_BLOCKER", text)
        self.assertIn("5af545c2", text)
        self.assertIn("a4457781", text)
        self.assertIn("e160b2c3", text)
        self.assertIn("22b63e25", text)
        self.assertIn("587cc1cf", text)
        self.assertIn("Did not remint leftover grokbuild-pr8414-verify-20260902-01", text)
        self.assertIn("Did not reopen #7915", text)
        self.assertNotEqual(text, verify)
        self.assertNotEqual(text, prior)
        self.assertNotEqual(text, collision)
        self.assertNotIn(
            "job-watchdog:0675fb559de118427a4c37b3cc406fc9f4cc7b64:tick",
            verify,
        )
        self.assertNotIn(
            "job-watchdog:0675fb559de118427a4c37b3cc406fc9f4cc7b64:tick",
            collision,
        )
        self.assertNotIn("buy.stripe.com", text)

    def test_fix_first_packet_is_external_blocker(self) -> None:
        packet = {
            "outcome": "external_blocker",
            "observed_broken": True,
            "finding_kind": "behavior",
            "expected_contract": (
                "job-watchdog.yml job tick executes "
                "python3 -m harness_wake --tick on pull_request"
            ),
            "repair_attempts": [
                "local test_harness_wake.py 61/61 PASS",
                "local test_job_watchdog_land.py 21/21 PASS",
                "local python3 -m harness_wake --tick TICKED ok",
                "github rerun_failed_jobs attempt 2 same billing refusal",
            ],
            "blocker": (
                "GitHub Actions ubuntu-latest never assigned: "
                "The job was not started because your account is locked due to a billing issue."
            ),
            "report_only_sessions": 0,
            "unconsumed_findings": 0,
        }
        self.assertEqual(fix_first.validate(packet)["state"], "EXTERNAL_BLOCKER")


if __name__ == "__main__":
    unittest.main()
