#!/usr/bin/env python3
"""Pin unique leftover for job-watchdog run 33694214891. Do not remint prior leftover or watchdog."""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

import fix_first

ROOT = Path(__file__).resolve().parent
RECEIPT = ROOT / "p/grok-build-job-watchdog-33694214891-billing-lock-20260902-01.md"
PRIOR_WATCHDOG = ROOT / "p/grok-build-job-watchdog-33689281276-billing-lock-20260902-01.md"
PR8479 = ROOT / "p/grokbuild-pr8479-verify-20260902-01.md"
GOAT = ROOT / "p/cursor-goat-pages-super-mcp-land-readback-match-20260902-01.md"
WORKFLOW = ROOT / ".github/workflows/job-watchdog.yml"

KEEP = {
    ".github/workflows/job-watchdog.yml": "5af545c2",
    "enqueue_pending_grok_com.py": "d1e4b9e7",
    "test_job_watchdog_land.py": "2f055030",
    "harness_wake/land.py": "31ae9844",
    "harness_wake/__main__.py": "a4457781",
    "harness_wake/cancel_stale.py": "ce59da45",
    "harness_wake/watchdog.py": "149ed075",
    "hub_pages.py": "5ac12648",
    "p/grok-build-job-watchdog-33689281276-billing-lock-20260902-01.md": "29c547f4",
    "p/grok-build-job-watchdog-33689096542-billing-lock-20260902-01.md": "795847b1",
    "p/grok-build-job-watchdog-33689088762-billing-lock-20260902-01.md": "62bb626a",
    "p/grok-build-llms-txt-33687829181-billing-lock-20260902-01.md": "3183564c",
    "p/grok-build-llms-txt-billing-lock-20260902-01.md": "cf9c9f40",
    "p/grokbuild-open-door-guard-33687124472-billing-lock-20260902-01.md": "b91a85d3",
    "p/grokbuild-pr8479-verify-20260902-01.md": "658530be",
    "p/cursor-goat-pages-super-mcp-land-readback-match-20260902-01.md": "865b3c95",
    "test_cursor_goat_pages_super_mcp_land_readback_match.py": "dae1f645",
}


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class TestGrokbuildJobWatchdog33694214891BillingLock(unittest.TestCase):
    def test_keep_watchdog_and_prior_leftovers_unread(self) -> None:
        for rel, prefix in KEEP.items():
            blob = git_blob(rel)
            self.assertTrue(
                blob.startswith(prefix),
                f"{rel} reminted: want {prefix} got {blob[:8]}",
            )
        yml = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("python3 -m harness_wake --tick --deliver", yml)
        self.assertIn("python3 -m harness_wake.land", yml)
        self.assertIn("python3 -m harness_wake.cancel_stale", yml)
        self.assertIn("python3 enqueue_pending_grok_com.py", yml)
        self.assertIn("runs-on: ubuntu-latest", yml)
        self.assertNotIn("billing", yml.lower())
        self.assertNotIn("if: false", yml)

    def test_receipt_is_unique_and_does_not_remint(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        prior = PRIOR_WATCHDOG.read_text(encoding="utf-8")
        pr8479 = PR8479.read_text(encoding="utf-8")
        goat = GOAT.read_text(encoding="utf-8")
        self.assertIn(
            "grok-build-job-watchdog-33694214891-billing-lock-20260902-01", text
        )
        self.assertIn(
            "woahwhattheheck/commons:job-watchdog:41c16748dd1658281ba65d460a6a3694d93c89c3:tick",
            text,
        )
        self.assertIn("33694214891", text)
        self.assertIn("100459466175", text)
        self.assertIn("100461353799", text)
        self.assertIn("41c16748dd1658281ba65d460a6a3694d93c89c3", text)
        self.assertIn(
            "The job was not started because your account is locked due to a billing issue.",
            text,
        )
        self.assertIn("EXTERNAL_BLOCKER", text)
        self.assertIn("did not reopen", text.lower())
        self.assertIn("#8479", text)
        self.assertIn("29c547f4", text)
        self.assertIn("795847b1", text)
        self.assertIn("62bb626a", text)
        self.assertIn("3183564c", text)
        self.assertIn("cf9c9f40", text)
        self.assertIn("b91a85d3", text)
        self.assertIn("658530be", text)
        self.assertIn("865b3c95", text)
        self.assertIn("5ac12648", text)
        self.assertIn("5af545c2", text)
        self.assertIn("31ae9844", text)
        self.assertIn("a4457781", text)
        self.assertIn("ce59da45", text)
        self.assertIn("149ed075", text)
        self.assertIn("d1e4b9e7", text)
        self.assertIn("2f055030", text)
        self.assertNotEqual(text, prior)
        self.assertNotEqual(text, pr8479)
        self.assertNotEqual(text, goat)
        self.assertNotIn(
            "job-watchdog:41c16748dd1658281ba65d460a6a3694d93c89c3:tick", prior
        )
        self.assertNotIn(
            "job-watchdog:41c16748dd1658281ba65d460a6a3694d93c89c3:tick", pr8479
        )
        self.assertNotIn(
            "job-watchdog:41c16748dd1658281ba65d460a6a3694d93c89c3:tick", goat
        )

    def test_local_tick_still_runs_and_fix_first_is_external_blocker(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            proc = subprocess.run(
                ["python3", "-m", "harness_wake", "--tick", "--jobs-dir", tmp],
                cwd=ROOT,
                capture_output=True,
                text=True,
                env={k: v for k, v in os.environ.items() if k != "GITHUB_ACTIONS"},
            )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertTrue(payload.get("ok"))
        self.assertEqual(payload.get("state"), "TICKED")
        self.assertFalse(payload.get("invoke_model"))
        result = fix_first.validate(
            {
                "outcome": "external_blocker",
                "observed_broken": True,
                "expected_contract": "job-watchdog tick job starts on ubuntu-latest and runs harness_wake",
                "repair_attempts": [
                    "inspected job-watchdog.yml",
                    "ran local watchdog tests and --tick",
                    "reran failed jobs; same billing lock",
                    "GitHub Actions billing APIs 404",
                ],
                "blocker": "GitHub account locked due to a billing issue; ubuntu-latest job never started",
                "report_only_sessions": 0,
                "unconsumed_findings": 0,
            }
        )
        self.assertEqual(result["state"], "EXTERNAL_BLOCKER")


if __name__ == "__main__":
    unittest.main()
