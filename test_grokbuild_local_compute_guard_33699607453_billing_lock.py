#!/usr/bin/env python3
"""Pin unique leftover for local-compute-guard run 33699607453. Do not remint prior leftover or guard."""

from __future__ import annotations

import subprocess
import unittest
from pathlib import Path

import fix_first
import local_compute_guard as guard
import open_door_guard as door

ROOT = Path(__file__).resolve().parent
RECEIPT = ROOT / "p/grokbuild-local-compute-guard-33699607453-billing-lock-20260903-01.md"
PRIOR = ROOT / "p/grok-build-local-compute-guard-billing-lock-20260902-01.md"
PRIOR_RUN = ROOT / "p/grokbuild-local-compute-guard-33694402730-billing-lock-20260902-01.md"
VERIFY = ROOT / "p/grokbuild-pr8525-verify-20260903-01.md"
WORKFLOW = ROOT / ".github/workflows/local-compute-guard.yml"

KEEP = {
    "p/grok-build-local-compute-guard-billing-lock-20260902-01.md": "de59bf75",
    "p/grokbuild-local-compute-guard-33689357241-billing-lock-20260902-01.md": "2517b71d",
    "p/grok-build-local-compute-guard-33689281338-billing-lock-20260902-01.md": "a33a1c81",
    "p/grokbuild-local-compute-guard-33694243175-billing-lock-20260902-01.md": "c4ee237f",
    "p/grokbuild-local-compute-guard-33694253447-billing-lock-20260902-01.md": "417b7f6a",
    "p/grokbuild-local-compute-guard-33694402730-billing-lock-20260902-01.md": "eb6f1406",
    "p/grokbuild-local-compute-guard-33694219035-billing-lock-20260902-01.md": "2bd967cb",
    "p/grok-build-discord-cloud-billing-lock-20260902-01.md": "2e0bfbfb",
    "p/grok-build-discord-cloud-33699286743-billing-lock-20260902-01.md": "e8d308ed",
    "p/grok-build-llms-txt-33699286770-billing-lock-20260903-01.md": "43c6e5cb",
    "p/grokbuild-open-door-guard-33699286785-billing-lock-20260902-01.md": "d22e0707",
    "p/grokbuild-pr8525-verify-20260903-01.md": "3e36c93c",
    "test_grokbuild_local_compute_guard_33694402730_billing_lock.py": "05b40e7e",
    "local_compute_guard.py": "6be242af",
    "test_local_compute_guard.py": "b8d65280",
    ".github/workflows/local-compute-guard.yml": "9750c6a1",
}


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class TestGrokbuildLocalComputeGuard33699607453BillingLock(unittest.TestCase):
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
        added = [
            door.AddedLine(
                "test_grokbuild_local_compute_guard_33699607453_billing_lock.py",
                1,
                line,
            )
            for line in Path(__file__).read_text(encoding="utf-8").splitlines()
        ]
        self.assertEqual(door.scan_added(added), [])
        receipt_added = [
            door.AddedLine(str(RECEIPT.relative_to(ROOT)), 1, line)
            for line in RECEIPT.read_text(encoding="utf-8").splitlines()
        ]
        self.assertEqual(door.scan_added(receipt_added), [])

    def test_receipt_is_unique_and_does_not_remint(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        prior = PRIOR.read_text(encoding="utf-8")
        prior_run = PRIOR_RUN.read_text(encoding="utf-8")
        verify = VERIFY.read_text(encoding="utf-8")
        self.assertIn(
            "grokbuild-local-compute-guard-33699607453-billing-lock-20260903-01",
            text,
        )
        self.assertIn(
            "woahwhattheheck/commons:local-compute-guard:e25521733acdd3387c285e37483a74d7af8de3c3:placement",
            text,
        )
        self.assertIn("33699607453", text)
        self.assertIn("100475840427", text)
        self.assertIn("100476513632", text)
        self.assertIn("e25521733acdd3387c285e37483a74d7af8de3c3", text)
        self.assertIn("grokbuild-pr8525-verify-20260903-01", text)
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
        self.assertIn("2517b71d", text)
        self.assertIn("a33a1c81", text)
        self.assertIn("c4ee237f", text)
        self.assertIn("417b7f6a", text)
        self.assertIn("eb6f1406", text)
        self.assertIn("2bd967cb", text)
        self.assertIn("2e0bfbfb", text)
        self.assertIn("e8d308ed", text)
        self.assertIn("43c6e5cb", text)
        self.assertIn("d22e0707", text)
        self.assertIn("3e36c93c", text)
        self.assertIn("05b40e7e", text)
        self.assertIn("6be242af", text)
        self.assertIn("b8d65280", text)
        self.assertIn("9750c6a1", text)
        self.assertIn("did not reopen #7915", text)
        self.assertIn("/8525", text)
        self.assertNotEqual(text, prior)
        self.assertNotEqual(text, prior_run)
        self.assertNotEqual(text, verify)
        self.assertNotIn(
            "local-compute-guard:e25521733acdd3387c285e37483a74d7af8de3c3:placement",
            prior,
        )
        self.assertNotIn(
            "local-compute-guard:e25521733acdd3387c285e37483a74d7af8de3c3:placement",
            prior_run,
        )
        self.assertNotIn(
            "local-compute-guard:e25521733acdd3387c285e37483a74d7af8de3c3:placement",
            verify,
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
