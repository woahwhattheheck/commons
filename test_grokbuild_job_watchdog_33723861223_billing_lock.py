#!/usr/bin/env python3
"""Pin unique leftover for job-watchdog run 33723861223. Do not remint tick/land or prior leftovers."""

from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

import fix_first

ROOT = Path(__file__).resolve().parent
RECEIPT = ROOT / "p/grokbuild-job-watchdog-33723861223-billing-lock-20260903-01.md"
PRIOR = ROOT / "p/grokbuild-job-watchdog-33717733947-billing-lock-20260903-01.md"
SIBLING = ROOT / "p/grok-build-job-watchdog-33718131418-billing-lock-20260903-01.md"
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
    "p/grokbuild-job-watchdog-33717733947-billing-lock-20260903-01.md": "d83537e6",
    "test_grokbuild_job_watchdog_33717733947_billing_lock.py": "645d2b38",
    "p/grok-build-job-watchdog-33718131418-billing-lock-20260903-01.md": "716e86bd",
    "test_grokbuild_job_watchdog_33718131418_billing_lock.py": "5d7d01ad",
    "p/grok-build-commons-board-billing-lock-20260903-01.md": "c07bf913",
    "p/grokbuild-leftover-id-census-33723043828-billing-lock-20260903-01.md": "e135862e",
    "test_grokbuild_leftover_id_census_33723043828_billing_lock.py": "3f77dce1",
    "p/grok-build-owner-net-33723510040-billing-lock-20260903-01.md": "6a2c8239",
    "test_grokbuild_owner_net_33723510040_billing_lock.py": "13e008cf",
}


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class TestGrokbuildJobWatchdog33723861223BillingLock(unittest.TestCase):
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
        self.assertIn("grokbuild-job-watchdog-33723861223-billing-lock-20260903-01", text)
        self.assertIn(
            "woahwhattheheck/commons:job-watchdog:f0a980053dae781f35e8723428d42aae64b7a5d3:tick",
            text,
        )
        self.assertIn("33723861223", text)
        self.assertIn("100548467802", text)
        self.assertIn("100549328451", text)
        self.assertIn("f0a980053dae781f35e8723428d42aae64b7a5d3", text)
        self.assertIn("8635", text)
        self.assertIn(
            "The job was not started because your account is locked due to a billing issue.",
            text,
        )
        self.assertIn("EXTERNAL_BLOCKER", text)
        self.assertIn("Did not remint leftover grokbuild-job-watchdog-33717733947-billing-lock-20260903-01", text)
        self.assertIn("d83537e6", text)
        self.assertIn("b364a427", text)
        self.assertIn("716e86bd", text)
        self.assertIn("ebc1c525", text)
        self.assertIn("c07bf913", text)
        self.assertIn("e135862e", text)
        self.assertIn("3f77dce1", text)
        self.assertIn("6a2c8239", text)
        self.assertIn("13e008cf", text)
        self.assertIn("5af545c2", text)
        self.assertIn("149ed075", text)
        self.assertIn("31ae9844", text)
        self.assertIn("2f055030", text)
        self.assertIn("Did not reopen #7915", text)
        self.assertIn("Did not reopen #8635", text)
        self.assertNotEqual(text, prior)
        self.assertNotEqual(text, sibling)
        self.assertNotIn(
            "job-watchdog:f0a980053dae781f35e8723428d42aae64b7a5d3:tick",
            prior,
        )
        self.assertNotIn(
            "job-watchdog:f0a980053dae781f35e8723428d42aae64b7a5d3:tick",
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
