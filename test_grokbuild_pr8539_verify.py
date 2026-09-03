#!/usr/bin/env python3
"""Pin grok-build verify leftover for already-merged PR 8539. Do not remint watchdog leftover."""

from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RECEIPT = ROOT / "p/grokbuild-pr8539-verify-20260903-01.md"
LEFTOVER = ROOT / "p/grok-build-job-watchdog-33699607332-billing-lock-20260903-01.md"
LEFTOVER_TEST = ROOT / "test_grokbuild_job_watchdog_33699607332_billing_lock.py"
PRIOR_VERIFY = ROOT / "p/grokbuild-pr8525-verify-20260903-01.md"
WORKFLOW = ROOT / ".github/workflows/job-watchdog.yml"

KEEP = {
    "p/grok-build-job-watchdog-33699607332-billing-lock-20260903-01.md": "dd77b53d",
    "test_grokbuild_job_watchdog_33699607332_billing_lock.py": "7845fbdd",
    "p/grokbuild-pr8525-verify-20260903-01.md": "3e36c93c",
    ".github/workflows/job-watchdog.yml": "5af545c2",
    "harness_wake/watchdog.py": "149ed075",
    "harness_wake/land.py": "31ae9844",
    "test_job_watchdog_land.py": "2f055030",
    "enqueue_pending_grok_com.py": "d1e4b9e7",
}


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class TestGrokbuildPr8539Verify(unittest.TestCase):
    def test_keep_8539_leftover_and_peers_unread(self) -> None:
        for rel, prefix in KEEP.items():
            blob = git_blob(rel)
            self.assertTrue(
                blob.startswith(prefix),
                f"{rel} reminted: want {prefix} got {blob[:8]}",
            )
        yml = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("python3 -m harness_wake --tick --deliver", yml)
        self.assertIn("python3 -m harness_wake.land", yml)
        self.assertNotIn("billing", yml.lower())
        self.assertNotIn("if: false", yml)

    def test_receipt_cites_8539_and_does_not_remint(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        leftover = LEFTOVER.read_text(encoding="utf-8")
        leftover_test = LEFTOVER_TEST.read_text(encoding="utf-8")
        prior = PRIOR_VERIFY.read_text(encoding="utf-8")
        self.assertIn("grokbuild-pr8539-verify-20260903-01", text)
        self.assertIn(
            "woahwhattheheck/commons#8539@358cfea384ee3737e3f39cda871a5e5d24a74040",
            text,
        )
        self.assertIn("https://github.com/woahwhattheheck/commons/pull/8539", text)
        self.assertIn("358cfea384ee3737e3f39cda871a5e5d24a74040", text)
        self.assertIn("ea6b35aedb957d8a5b06ddb47e358c44f8d248fc", text)
        self.assertIn("ALREADY_MERGED_VERIFIED", text)
        self.assertIn("INTEGRATED — VERIFIED ON CURRENT MAIN", text)
        self.assertIn("dd77b53d", text)
        self.assertIn("7845fbdd", text)
        self.assertIn("3e36c93c", text)
        self.assertIn("Did not remint leftover grok-build-job-watchdog-33699607332-billing-lock-20260903-01", text)
        self.assertIn("Did not reopen #8525", text)
        self.assertNotEqual(text, leftover)
        self.assertNotEqual(text, prior)
        self.assertNotEqual(Path(__file__).read_text(encoding="utf-8"), leftover_test)
        self.assertNotIn("woahwhattheheck/commons#8539@", leftover)
        self.assertNotIn("woahwhattheheck/commons#8539@", prior)

    def test_leftover_tick_still_passes(self) -> None:
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

    def test_leftover_unittest_still_green(self) -> None:
        proc = subprocess.run(
            ["python3", "-m", "unittest", "test_grokbuild_job_watchdog_33699607332_billing_lock.py"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
        self.assertIn("Ran 4 tests", proc.stderr + proc.stdout)


if __name__ == "__main__":
    unittest.main()
