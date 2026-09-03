#!/usr/bin/env python3
"""Pin unique leftover for job-watchdog run 33723631044. Do not remint tick/land or prior leftovers."""

from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

import fix_first

ROOT = Path(__file__).resolve().parent
RECEIPT = ROOT / "p/grok-build-job-watchdog-33723631044-billing-lock-20260903-01.md"
PRIOR = ROOT / "p/grok-build-job-watchdog-33718131418-billing-lock-20260903-01.md"
KEEP_POST = ROOT / "p/grok-build-repo-pulse-billing-lock-20260903-01.md"
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
    "p/grok-build-job-watchdog-33718131418-billing-lock-20260903-01.md": "716e86bd",
    "test_grokbuild_job_watchdog_33718131418_billing_lock.py": "ebc1c525",
    "p/grok-build-job-watchdog-33718116277-billing-lock-20260903-01.md": "664bd6de",
    "test_grokbuild_job_watchdog_33718116277_billing_lock.py": "1839f626",
    "p/grok-build-job-watchdog-33717741080-billing-lock-20260903-01.md": "f3afb926",
    "test_grokbuild_job_watchdog_33717741080_billing_lock.py": "7a1bc6f6",
    "p/grokbuild-harness-wakeup-33717474657-billing-lock-20260903-01.md": "f54e1846",
    "test_grokbuild_harness_wakeup_33717474657_billing_lock.py": "760a8169",
    "p/grok-build-repo-pulse-billing-lock-20260903-01.md": "b6e5953c",
}


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class TestGrokbuildJobWatchdog33723631044BillingLock(unittest.TestCase):
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
        keep_post = KEEP_POST.read_text(encoding="utf-8")
        self.assertIn("grok-build-job-watchdog-33723631044-billing-lock-20260903-01", text)
        self.assertIn(
            "woahwhattheheck/commons:job-watchdog:e50d0619c6916bfb5c12e360e3c38b4ca3a554fd:tick",
            text,
        )
        self.assertIn("33723631044", text)
        self.assertIn("100547765941", text)
        self.assertIn("100548874495", text)
        self.assertIn("e50d0619c6916bfb5c12e360e3c38b4ca3a554fd", text)
        self.assertIn("8633", text)
        self.assertIn(
            "The job was not started because your account is locked due to a billing issue.",
            text,
        )
        self.assertIn("EXTERNAL_BLOCKER", text)
        self.assertIn("Did not remint leftover grok-build-job-watchdog-33718131418-billing-lock-20260903-01", text)
        self.assertIn("716e86bd", text)
        self.assertIn("ebc1c525", text)
        self.assertIn("664bd6de", text)
        self.assertIn("1839f626", text)
        self.assertIn("f3afb926", text)
        self.assertIn("7a1bc6f6", text)
        self.assertIn("f54e1846", text)
        self.assertIn("760a8169", text)
        self.assertIn("b6e5953c", text)
        self.assertIn("5af545c2", text)
        self.assertIn("149ed075", text)
        self.assertIn("31ae9844", text)
        self.assertIn("2f055030", text)
        self.assertIn("Did not reopen #8632", text)
        self.assertIn("Did not remint #8633 leftover bytes", text)
        self.assertNotEqual(text, prior)
        self.assertNotEqual(text, keep_post)
        self.assertNotIn(
            "job-watchdog:e50d0619c6916bfb5c12e360e3c38b4ca3a554fd:tick",
            prior,
        )
        self.assertNotIn(
            "job-watchdog:e50d0619c6916bfb5c12e360e3c38b4ca3a554fd:tick",
            keep_post,
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
                "job-watchdog.yml job tick on pull_request executes checkout "
                "then python3 -m harness_wake --tick; on push to main it "
                "executes --tick --deliver then enqueue_pending_grok_com.py "
                "and python3 -m harness_wake.land"
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
