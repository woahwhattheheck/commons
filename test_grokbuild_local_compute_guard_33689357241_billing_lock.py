#!/usr/bin/env python3
"""Pin unique leftover for local-compute-guard run 33689357241. Do not remint prior leftover or guard."""

from __future__ import annotations

import subprocess
import unittest
from pathlib import Path

import fix_first
import local_compute_guard as guard

ROOT = Path(__file__).resolve().parent
RECEIPT = ROOT / "p/grokbuild-local-compute-guard-33689357241-billing-lock-20260902-01.md"
PRIOR = ROOT / "p/grok-build-local-compute-guard-billing-lock-20260902-01.md"
VERIFY = ROOT / "p/grokbuild-pr8409-verify-20260902-01.md"
DISCORD = ROOT / "p/grok-build-discord-cloud-billing-lock-20260902-01.md"
WORKFLOW = ROOT / ".github/workflows/local-compute-guard.yml"

KEEP = {
    "p/grok-build-local-compute-guard-billing-lock-20260902-01.md": "de59bf75",
    "p/grokbuild-pr8409-verify-20260902-01.md": "199cc075",
    "p/grok-build-discord-cloud-billing-lock-20260902-01.md": "2e0bfbfb",
    "p/grokbuild-open-door-guard-33687124472-billing-lock-20260902-01.md": "b91a85d3",
    "p/grokbuild-pr8402-verify-20260902-01.md": "3524e382",
    "p/grok-resources-tab-freshness-billing-lock-20260902-01.md": "ac39fe78",
    "local_compute_guard.py": "6be242af",
    "test_local_compute_guard.py": "b8d65280",
    ".github/workflows/local-compute-guard.yml": "9750c6a1",
}


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class TestGrokbuildLocalComputeGuard33689357241BillingLock(unittest.TestCase):
    def test_keep_guard_and_prior_leftovers_unread(self) -> None:
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
        self.assertNotIn("billing", yml.lower())
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

    def test_receipt_is_unique_and_does_not_remint(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        prior = PRIOR.read_text(encoding="utf-8")
        verify = VERIFY.read_text(encoding="utf-8")
        discord = DISCORD.read_text(encoding="utf-8")
        self.assertIn(
            "grokbuild-local-compute-guard-33689357241-billing-lock-20260902-01",
            text,
        )
        self.assertIn(
            "woahwhattheheck/commons:local-compute-guard:ffacc45de870c3e7f7890f0e8cd025d40dc619f4:placement",
            text,
        )
        self.assertIn("33689357241", text)
        self.assertIn("100444265153", text)
        self.assertIn("100446371510", text)
        self.assertIn("ffacc45de870c3e7f7890f0e8cd025d40dc619f4", text)
        self.assertIn(
            "The job was not started because your account is locked due to a billing issue.",
            text,
        )
        self.assertIn("EXTERNAL_BLOCKER", text)
        self.assertIn(
            "Did not remint leftover grok-build-local-compute-guard-billing-lock-20260902-01",
            text,
        )
        self.assertIn("de59bf75", text)
        self.assertIn("199cc075", text)
        self.assertIn("2e0bfbfb", text)
        self.assertIn("b91a85d3", text)
        self.assertIn("3524e382", text)
        self.assertIn("6be242af", text)
        self.assertIn("b8d65280", text)
        self.assertIn("9750c6a1", text)
        self.assertIn("did not reopen #7915", text)
        self.assertNotEqual(text, prior)
        self.assertNotEqual(text, verify)
        self.assertNotEqual(text, discord)
        self.assertNotIn(
            "local-compute-guard:ffacc45de870c3e7f7890f0e8cd025d40dc619f4:placement",
            prior,
        )
        self.assertIn(
            "local-compute-guard:dc2dc72aaae94decbe2bbbe7144504f30919916f:placement",
            prior,
        )
        self.assertNotIn(
            "local-compute-guard:ffacc45de870c3e7f7890f0e8cd025d40dc619f4:placement",
            discord,
        )

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
                "local test_local_compute_guard.py 2/2 PASS",
                "github rerun_failed_jobs 201; attempt 2 same billing refusal",
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
