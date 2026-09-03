#!/usr/bin/env python3
"""Pin unique leftover for job-watchdog run 33717733947. Do not remint tick/land or prior leftovers."""

from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

import fix_first

ROOT = Path(__file__).resolve().parent
RECEIPT = ROOT / "p/grokbuild-job-watchdog-33717733947-billing-lock-20260903-01.md"
PRIOR = ROOT / "p/grok-build-job-watchdog-33699986556-billing-lock-20260903-01.md"
SIBLING = ROOT / "p/grok-build-job-watchdog-33717741080-billing-lock-20260903-01.md"
WORKFLOW = ROOT / ".github/workflows/job-watchdog.yml"

KEEP = {
    ".github/workflows/job-watchdog.yml": "5af545c2",
    "harness_wake/__main__.py": "a4457781",
    "harness_wake/watchdog.py": "149ed075",
    "harness_wake/land.py": "31ae9844",
    "test_job_watchdog_land.py": "2f055030",
    "test_harness_wake.py": "ab71ef24",
    "enqueue_pending_grok_com.py": "d1e4b9e7",
    "open_door_guard.py": "4b053e43",
    "p/grok-build-job-watchdog-33717741080-billing-lock-20260903-01.md": "f3afb926",
    "test_grokbuild_job_watchdog_33717741080_billing_lock.py": "7a1bc6f6",
    "p/grok-build-discord-cloud-33717741051-billing-lock-20260903-01.md": "b7a4ea0e",
    "test_grokbuild_discord_cloud_33717741051_billing_lock.py": "361b7c4b",
    "p/grokbuild-open-door-guard-33717733987-billing-lock-20260903-01.md": "a0af1282",
    "test_grokbuild_open_door_guard_33717733987_billing_lock.py": "0269ac73",
    "p/grok-build-job-watchdog-33699986556-billing-lock-20260903-01.md": "4754031d",
    "test_grokbuild_job_watchdog_33699986556_billing_lock.py": "71915bd1",
    "p/grokbuild-slack-service-tags-33717615004-billing-lock-20260903-01.md": "f33a76ef",
    "test_grokbuild_slack_service_tags_33717615004_billing_lock.py": "e10a1435",
    "p/grokbuild-harness-wakeup-33717474657-billing-lock-20260903-01.md": "f54e1846",
    "test_grokbuild_harness_wakeup_33717474657_billing_lock.py": "760a8169",
    "p/grokbuild-main-range-verify-33717084528-billing-lock-20260903-01.md": "2b0fd9c9",
    "p/admin-owner-marks-20260902-01.md": "cdff4bfb",
}


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class TestGrokbuildJobWatchdog33717733947BillingLock(unittest.TestCase):
    def test_keep_tick_land_and_prior_leftovers_unread(self) -> None:
        for rel, prefix in KEEP.items():
            blob = git_blob(rel)
            self.assertTrue(
                blob.startswith(prefix),
                f"{rel} reminted: want {prefix} got {blob[:8]}",
            )
        yml = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("python3 -m harness_wake --tick --deliver", yml)
        self.assertIn("python3 -m harness_wake --tick", yml)
        self.assertIn("python3 -m harness_wake.land", yml)
        self.assertIn("python3 enqueue_pending_grok_com.py", yml)
        self.assertNotIn("billing", yml.lower())
        self.assertNotIn("if: false", yml)

    def test_receipt_is_unique_and_does_not_remint(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        prior = PRIOR.read_text(encoding="utf-8")
        sibling = SIBLING.read_text(encoding="utf-8")
        self.assertIn("grokbuild-job-watchdog-33717733947-billing-lock-20260903-01", text)
        self.assertIn(
            "woahwhattheheck/commons:job-watchdog:2890fde44250063aa66ef60735a7cc90407760a6:tick",
            text,
        )
        self.assertIn("33717733947", text)
        self.assertIn("100530342701", text)
        self.assertIn("100532377068", text)
        self.assertIn("2890fde44250063aa66ef60735a7cc90407760a6", text)
        self.assertIn("d1c70e6d86eb6eb3180b57e56c6c1620cfbdcb7d", text)
        self.assertIn(
            "The job was not started because your account is locked due to a billing issue.",
            text,
        )
        self.assertIn("EXTERNAL_BLOCKER", text)
        self.assertIn("Did not remint leftover grok-build-job-watchdog-33717741080-billing-lock-20260903-01", text)
        self.assertIn("f3afb926", text)
        self.assertIn("7a1bc6f6", text)
        self.assertIn("b7a4ea0e", text)
        self.assertIn("361b7c4b", text)
        self.assertIn("a0af1282", text)
        self.assertIn("0269ac73", text)
        self.assertIn("4754031d", text)
        self.assertIn("71915bd1", text)
        self.assertIn("f33a76ef", text)
        self.assertIn("e10a1435", text)
        self.assertIn("f54e1846", text)
        self.assertIn("760a8169", text)
        self.assertIn("2b0fd9c9", text)
        self.assertIn("3e89a404", text)
        self.assertIn("4e4d8003", text)
        self.assertIn("81092ec2", text)
        self.assertIn("43c6e5cb", text)
        self.assertIn("cdff4bfb", text)
        self.assertIn("5af545c2", text)
        self.assertIn("149ed075", text)
        self.assertIn("Did not reopen #7915", text)
        self.assertIn("Did not reopen #8400", text)
        self.assertIn("Did not reopen #8583", text)
        self.assertNotEqual(text, prior)
        self.assertNotEqual(text, sibling)
        self.assertNotIn(
            "job-watchdog:2890fde44250063aa66ef60735a7cc90407760a6:tick",
            prior,
        )
        self.assertNotIn(
            "job-watchdog:2890fde44250063aa66ef60735a7cc90407760a6:tick",
            sibling,
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
                "--tick on pull_request (no --deliver) and --tick --deliver "
                "then enqueue_pending_grok_com.py and python3 -m harness_wake.land "
                "on push to main"
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
