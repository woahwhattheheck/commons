#!/usr/bin/env python3
"""Pin unique leftover for job-watchdog run 33689096542. Do not remint tick/land or prior leftovers."""

from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path

import fix_first

ROOT = Path(__file__).resolve().parent
RECEIPT = ROOT / "p/grok-build-job-watchdog-33689096542-billing-lock-20260902-01.md"
DISCORD = ROOT / "p/grok-build-discord-cloud-billing-lock-20260902-01.md"
MEETING6 = ROOT / "p/cursor-merge-on-pr-20260902-01.md"
WORKFLOW = ROOT / ".github/workflows/job-watchdog.yml"

KEEP = {
    "p/grok-build-llms-txt-33687829181-billing-lock-20260902-01.md": "3183564c",
    "p/grok-build-llms-txt-billing-lock-20260902-01.md": "cf9c9f40",
    "p/grokbuild-open-door-guard-33687124472-billing-lock-20260902-01.md": "b91a85d3",
    "p/grok-build-discord-cloud-billing-lock-20260902-01.md": "2e0bfbfb",
    "p/grok-build-discord-cloud-33689083145-billing-lock-20260902-01.md": "6e34f897",
    "p/grok-build-local-compute-guard-billing-lock-20260902-01.md": "de59bf75",
    "p/grok-resources-tab-freshness-billing-lock-20260902-01.md": "ac39fe78",
    "p/cursor-merge-on-pr-20260902-01.md": "22b63e25",
    "p/grokbuild-pr8410-verify-20260902-01.md": "4cfe563a",
    ".github/workflows/job-watchdog.yml": "5af545c2",
    "test_job_watchdog_land.py": "2f055030",
    "harness_wake/watchdog.py": "149ed075",
    "enqueue_pending_grok_com.py": "d1e4b9e7",
}


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class TestGrokbuildJobWatchdog33689096542BillingLock(unittest.TestCase):
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
        discord = DISCORD.read_text(encoding="utf-8")
        meeting6 = MEETING6.read_text(encoding="utf-8")
        self.assertIn("grok-build-job-watchdog-33689096542-billing-lock-20260902-01", text)
        self.assertIn(
            "woahwhattheheck/commons:job-watchdog:920d8c03a247d6b1ee640b523ef9447dfe4c7477:tick",
            text,
        )
        self.assertIn("33689096542", text)
        self.assertIn("100443450227", text)
        self.assertIn("100445830167", text)
        self.assertIn("920d8c03a247d6b1ee640b523ef9447dfe4c7477", text)
        self.assertIn(
            "The job was not started because your account is locked due to a billing issue.",
            text,
        )
        self.assertIn("EXTERNAL_BLOCKER", text)
        self.assertIn("Did not remint leftover grok-build-llms-txt-33687829181-billing-lock-20260902-01", text)
        self.assertIn("3183564c", text)
        self.assertIn("2e0bfbfb", text)
        self.assertIn("6e34f897", text)
        self.assertIn("de59bf75", text)
        self.assertIn("22b63e25", text)
        self.assertIn("4cfe563a", text)
        self.assertIn("5af545c2", text)
        self.assertIn("2f055030", text)
        self.assertIn("149ed075", text)
        self.assertIn("did not reopen #7915", text)
        self.assertNotEqual(text, discord)
        self.assertNotEqual(text, meeting6)
        self.assertNotIn(
            "job-watchdog:920d8c03a247d6b1ee640b523ef9447dfe4c7477:tick",
            discord,
        )
        self.assertNotIn(
            "job-watchdog:920d8c03a247d6b1ee640b523ef9447dfe4c7477:tick",
            meeting6,
        )

    def test_local_tick_still_passes(self) -> None:
        proc = subprocess.run(
            ["python3", "-m", "harness_wake", "--tick"],
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
