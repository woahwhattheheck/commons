#!/usr/bin/env python3
"""Pin unique leftover for local-compute-guard run 33689281338. Do not remint placement."""

from __future__ import annotations

import subprocess
import unittest
from pathlib import Path

import fix_first
import local_compute_guard as guard
import open_door_guard as door

ROOT = Path(__file__).resolve().parent
RECEIPT = ROOT / "p/grok-build-local-compute-guard-33689281338-billing-lock-20260902-01.md"
PRIOR = ROOT / "p/grok-build-local-compute-guard-billing-lock-20260902-01.md"
VERIFY_8411 = ROOT / "p/grokbuild-pr8411-verify-20260902-01.md"
DISCORD = ROOT / "p/grok-build-discord-cloud-billing-lock-20260902-01.md"
WORKFLOW = ROOT / ".github/workflows/local-compute-guard.yml"

KEEP = {
    "p/grok-build-local-compute-guard-billing-lock-20260902-01.md": "de59bf75",
    "local_compute_guard.py": "6be242af",
    ".github/workflows/local-compute-guard.yml": "9750c6a1",
    "test_local_compute_guard.py": "b8d65280",
    "p/grokbuild-pr8411-verify-20260902-01.md": "642dea64",
    "test_grokbuild_pr8411_verify.py": "361f5ca1",
    "p/cursor-stealable-lanes-roles-20260902-01.md": "5f1ef25f",
    "host/stealable_lanes.py": "c90284fb",
    "p/cursor-merge-on-pr-20260902-01.md": "22b63e25",
    "p/grok-build-discord-cloud-billing-lock-20260902-01.md": "2e0bfbfb",
}


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class TestGrokbuildLocalComputeGuard33689281338BillingLock(unittest.TestCase):
    def test_keep_placement_and_prior_leftovers_unread(self) -> None:
        for rel, prefix in KEEP.items():
            blob = git_blob(rel)
            self.assertTrue(
                blob.startswith(prefix),
                f"{rel} reminted: want {prefix} got {blob[:8]}",
            )
        yml = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("python3 local_compute_guard.py", yml)
        self.assertIn("runs-on: ubuntu-latest", yml)
        self.assertNotIn("self-hosted", yml)
        self.assertNotIn("if: false", yml)

    def test_local_failed_step_still_passes(self) -> None:
        self.assertEqual(guard.validate(), [])
        proc = subprocess.run(
            ["python3", "local_compute_guard.py"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
        self.assertIn("CLOUD_PRIMARY / SAFE_STANDBY", proc.stdout)
        tests = subprocess.run(
            ["python3", "-m", "unittest", "test_local_compute_guard"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(tests.returncode, 0, msg=tests.stdout + tests.stderr)
        self.assertIn("Ran 2 tests", tests.stderr + tests.stdout)
        added = [
            door.AddedLine("test_grokbuild_local_compute_guard_33689281338_billing_lock.py", 1, line)
            for line in Path(__file__).read_text(encoding="utf-8").splitlines()
        ]
        self.assertEqual(door.scan_added(added), [])
        receipt_added = [
            door.AddedLine(str(RECEIPT.relative_to(ROOT)), 1, line)
            for line in RECEIPT.read_text(encoding="utf-8").splitlines()
        ]
        self.assertEqual(door.scan_added(receipt_added), [])

    def test_receipt_cites_run_and_does_not_steal(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        prior = PRIOR.read_text(encoding="utf-8")
        verify_8411 = VERIFY_8411.read_text(encoding="utf-8")
        discord = DISCORD.read_text(encoding="utf-8")
        self.assertIn("grok-build-local-compute-guard-33689281338-billing-lock-20260902-01", text)
        self.assertIn(
            "woahwhattheheck/commons:local-compute-guard:81e8f9ccc7293bf6e5179e615ba460d87f409eb0:placement",
            text,
        )
        self.assertIn("33689281338", text)
        self.assertIn("100444021851", text)
        self.assertIn("81e8f9ccc7293bf6e5179e615ba460d87f409eb0", text)
        self.assertIn("issuecomment-5517284230", text)
        self.assertIn(
            "The job was not started because your account is locked due to a billing issue.",
            text,
        )
        self.assertIn("EXTERNAL_BLOCKER", text)
        self.assertIn("de59bf75", text)
        self.assertIn("6be242af", text)
        self.assertIn("9750c6a1", text)
        self.assertIn("b8d65280", text)
        self.assertIn("642dea64", text)
        self.assertIn("Did not remint", text)
        self.assertIn("Did not unique-pack merge-on-PR leftover", text)
        self.assertIn("Did not reopen #7915", text)
        self.assertNotEqual(text, prior)
        self.assertNotEqual(text, verify_8411)
        self.assertNotEqual(text, discord)
        self.assertNotIn(
            "local-compute-guard:81e8f9ccc7293bf6e5179e615ba460d87f409eb0:placement",
            prior,
        )
        self.assertNotIn("buy.stripe.com", text)

    def test_fix_first_packet_is_external_blocker(self) -> None:
        packet = {
            "outcome": "external_blocker",
            "observed_broken": True,
            "finding_kind": "behavior",
            "expected_contract": (
                "local-compute-guard.yml job placement executes "
                "python3 local_compute_guard.py on push to main"
            ),
            "repair_attempts": [
                "local python3 local_compute_guard.py CLOUD_PRIMARY / SAFE_STANDBY exit 0",
                "local test_local_compute_guard.py 2/2",
                "local test_path_manifest.py 9/9",
                "github rerun_failed_jobs 201; hosted runner still billing-locked",
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
