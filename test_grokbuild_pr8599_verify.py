#!/usr/bin/env python3
"""Pin unique PR 8599 already-merged verify. Do not remint job-watchdog leftover."""

from __future__ import annotations

import hashlib
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VERIFY = ROOT / "p/grokbuild-pr8599-verify-20260903-01.md"
LEFTOVER = ROOT / "p/grok-build-job-watchdog-33718116277-billing-lock-20260903-01.md"
LEFTOVER_TEST = ROOT / "test_grokbuild_job_watchdog_33718116277_billing_lock.py"
PRIOR = ROOT / "p/grok-build-job-watchdog-33717741080-billing-lock-20260903-01.md"
WORKFLOW = ROOT / ".github/workflows/job-watchdog.yml"
BODY_SHA256 = "bc36ce3e49707207f2f971e012d55f15c16d7a9e1f6433fc0b82c68ba4503dff"

KEEP = {
    "p/grok-build-job-watchdog-33718116277-billing-lock-20260903-01.md": "664bd6de",
    "test_grokbuild_job_watchdog_33718116277_billing_lock.py": "1839f626",
    "p/grok-build-job-watchdog-33717741080-billing-lock-20260903-01.md": "f3afb926",
    "test_grokbuild_job_watchdog_33717741080_billing_lock.py": "7a1bc6f6",
    ".github/workflows/job-watchdog.yml": "5af545c2",
    "harness_wake/__main__.py": "a4457781",
    "harness_wake/watchdog.py": "149ed075",
    "harness_wake/land.py": "31ae9844",
    "test_job_watchdog_land.py": "2f055030",
    "test_harness_wake.py": "ab71ef24",
    "enqueue_pending_grok_com.py": "d1e4b9e7",
    "open_door_guard.py": "4b053e43",
}


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class TestGrokbuildPr8599Verify(unittest.TestCase):
    def test_keep_8599_leftover_and_tick_unread(self) -> None:
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
        self.assertNotIn("billing", yml.lower())
        self.assertNotIn("if: false", yml)

    def test_verify_receipt_is_unique_and_does_not_remint(self) -> None:
        text = VERIFY.read_text(encoding="utf-8")
        leftover = LEFTOVER.read_text(encoding="utf-8")
        leftover_test = LEFTOVER_TEST.read_text(encoding="utf-8")
        prior = PRIOR.read_text(encoding="utf-8")
        self.assertIn("grokbuild-pr8599-verify-20260903-01", text)
        self.assertIn(
            "woahwhattheheck/commons#8599@a62cdf061fe5fd7db8b47caf26029fdc2c048b08",
            text,
        )
        self.assertIn("https://github.com/woahwhattheheck/commons/pull/8599", text)
        self.assertIn("a62cdf061fe5fd7db8b47caf26029fdc2c048b08", text)
        self.assertIn("088e748c68bc7eada5027f5760175bcbd114be1f", text)
        self.assertIn("7de4c5b4f84483c18ef98b86b58f18a2262ab327", text)
        self.assertIn("664bd6de", text)
        self.assertIn("1839f626", text)
        self.assertIn("ALREADY_MERGED_VERIFIED", text)
        self.assertIn("INTEGRATED — VERIFIED ON CURRENT MAIN", text)
        self.assertIn("Unique leftover durable", text)
        self.assertIn("cNTbkL25Zg7H", text)
        self.assertIn("33718116277", text)
        self.assertIn("EXTERNAL_BLOCKER", text)
        self.assertIn("Did not reopen #7915", text)
        self.assertNotEqual(text, leftover)
        self.assertNotEqual(text, prior)
        self.assertNotEqual(Path(__file__).read_text(encoding="utf-8"), leftover_test)
        self.assertNotIn("woahwhattheheck/commons#8599@", leftover)
        self.assertNotIn("grokbuild-pr8599-verify-20260903-01", leftover)
        parts = text.split("---\n")
        self.assertGreaterEqual(len(parts), 3)
        body = parts[2].lstrip("\n").rstrip("\n")
        self.assertEqual(hashlib.sha256(body.encode("utf-8")).hexdigest(), BODY_SHA256)

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

    def test_leftover_unittest_still_green(self) -> None:
        proc = subprocess.run(
            ["python3", "-m", "unittest", "test_grokbuild_job_watchdog_33718116277_billing_lock.py"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
        self.assertIn("Ran 4 tests", proc.stderr + proc.stdout)


if __name__ == "__main__":
    unittest.main()
