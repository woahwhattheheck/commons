#!/usr/bin/env python3
"""Pin unique leftover for job-watchdog run 33699986556. Do not remint tick/land or prior leftovers."""

from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

import fix_first

ROOT = Path(__file__).resolve().parent
RECEIPT = ROOT / "p/grok-build-job-watchdog-33699986556-billing-lock-20260903-01.md"
PRIOR = ROOT / "p/grok-build-job-watchdog-33699600934-billing-lock-20260903-01.md"
DISCORD = ROOT / "p/grok-build-discord-cloud-33699286743-billing-lock-20260902-01.md"
WORKFLOW = ROOT / ".github/workflows/job-watchdog.yml"

KEEP = {
    ".github/workflows/job-watchdog.yml": "5af545c2",
    "harness_wake/__main__.py": "a4457781",
    "harness_wake/watchdog.py": "149ed075",
    "harness_wake/land.py": "31ae9844",
    "test_job_watchdog_land.py": "2f055030",
    "test_harness_wake.py": "ab71ef24",
    "enqueue_pending_grok_com.py": "d1e4b9e7",
    "p/grok-build-job-watchdog-33699600934-billing-lock-20260903-01.md": "b654c48d",
    "test_grokbuild_job_watchdog_33699600934_billing_lock.py": "7c7c76ee",
    "p/grok-build-job-watchdog-33699607332-billing-lock-20260903-01.md": "dd77b53d",
    "test_grokbuild_job_watchdog_33699607332_billing_lock.py": "7845fbdd",
    "p/grok-build-job-watchdog-33699286811-billing-lock-20260903-01.md": "81092ec2",
    "test_grokbuild_job_watchdog_33699286811_billing_lock.py": "bec31b0f",
    "p/grok-build-job-watchdog-33694253472-billing-lock-20260902-01.md": "ad44ca9c",
    "p/grok-build-discord-cloud-33699286743-billing-lock-20260902-01.md": "e8d308ed",
    "p/grokbuild-pr8525-verify-20260903-01.md": "3e36c93c",
    "p/admin-owner-marks-20260902-01.md": "cdff4bfb",
}


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class TestGrokbuildJobWatchdog33699986556BillingLock(unittest.TestCase):
    def test_keep_tick_land_and_prior_leftovers_unread(self) -> None:
        for rel, prefix in KEEP.items():
            blob = git_blob(rel)
            self.assertTrue(
                blob.startswith(prefix),
                f"{rel} reminted: want {prefix} got {blob[:8]}",
            )
        yml = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("python3 -m harness_wake --tick --deliver", yml)
        self.assertIn("python3 -m harness_wake.land", yml)
        self.assertIn("python3 enqueue_pending_grok_com.py", yml)
        self.assertNotIn("billing", yml.lower())
        self.assertNotIn("if: false", yml)

    def test_receipt_is_unique_and_does_not_remint(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        prior = PRIOR.read_text(encoding="utf-8")
        discord = DISCORD.read_text(encoding="utf-8")
        self.assertIn("grok-build-job-watchdog-33699986556-billing-lock-20260903-01", text)
        self.assertIn(
            "woahwhattheheck/commons:job-watchdog:dd428e4e3d774588fe5f5d2801b2acf7c9db67b7:tick",
            text,
        )
        self.assertIn("33699986556", text)
        self.assertIn("100477000846", text)
        self.assertIn("100478266695", text)
        self.assertIn("dd428e4e3d774588fe5f5d2801b2acf7c9db67b7", text)
        self.assertIn(
            "The job was not started because your account is locked due to a billing issue.",
            text,
        )
        self.assertIn("EXTERNAL_BLOCKER", text)
        self.assertIn("Did not remint leftover grok-build-job-watchdog-33699600934-billing-lock-20260903-01", text)
        self.assertIn("b654c48d", text)
        self.assertIn("7c7c76ee", text)
        self.assertIn("dd77b53d", text)
        self.assertIn("7845fbdd", text)
        self.assertIn("81092ec2", text)
        self.assertIn("bec31b0f", text)
        self.assertIn("ad44ca9c", text)
        self.assertIn("e8d308ed", text)
        self.assertIn("3e36c93c", text)
        self.assertIn("cdff4bfb", text)
        self.assertIn("5af545c2", text)
        self.assertIn("149ed075", text)
        self.assertIn("Did not reopen #7915", text)
        self.assertIn("Did not reopen #8400", text)
        self.assertNotEqual(text, prior)
        self.assertNotEqual(text, discord)
        self.assertNotIn(
            "job-watchdog:dd428e4e3d774588fe5f5d2801b2acf7c9db67b7:tick",
            prior,
        )
        self.assertNotIn(
            "job-watchdog:dd428e4e3d774588fe5f5d2801b2acf7c9db67b7:tick",
            discord,
        )

    def test_local_tick_still_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            proc = subprocess.run(
                ["python3", "-m", "harness_wake", "--tick", "--jobs-dir", tmp],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
        self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
        summary = json.loads(proc.stdout)
        self.assertEqual(summary.get("state"), "TICKED")
        self.assertFalse(summary.get("invoke_model"))
        self.assertEqual(summary.get("process_model_invocations"), 0)

    def test_fix_first_packet_is_external_blocker(self) -> None:
        packet = {
            "outcome": "external_blocker",
            "observed_broken": True,
            "finding_kind": "behavior",
            "expected_contract": (
                "job-watchdog.yml job tick executes python3 -m harness_wake "
                "--tick --deliver then enqueue_pending_grok_com.py and "
                "python3 -m harness_wake.land on push to main"
            ),
            "repair_attempts": [
                "local test_job_watchdog_land.py 21/21",
                "local test_harness_wake.py 61/61",
                "local python3 -m harness_wake --tick rc=0 TICKED",
                "github rerun_failed_jobs 201; attempt 2 same billing refusal",
                "GitHub Actions billing APIs 404",
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
