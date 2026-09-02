#!/usr/bin/env python3
"""Pin unique leftover for open-door-guard run 33689281182. Do not remint the guard."""

from __future__ import annotations

import subprocess
import unittest
from pathlib import Path

import fix_first
import open_door_guard as guard

ROOT = Path(__file__).resolve().parent
RECEIPT = ROOT / "p/grokbuild-open-door-guard-33689281182-billing-lock-20260902-01.md"
PRIOR = ROOT / "p/grokbuild-open-door-guard-33687124472-billing-lock-20260902-01.md"
VERIFY_8408 = ROOT / "p/grokbuild-pr8408-verify-20260902-01.md"
VERIFY_8411 = ROOT / "p/grokbuild-pr8411-verify-20260902-01.md"
OCCUPANCY = ROOT / "p/cursor-stealable-lanes-occupancy-20260902-01.md"
READBACK = ROOT / "p/cursor-stealable-lanes-occupancy-readback-20260902-01.md"

KEEP = {
    "open_door_guard.py": "4b053e43",
    "test_open_door_guard.py": "70ee5730",
    ".github/workflows/open-door-guard.yml": "6586644c",
    "p/grokbuild-open-door-guard-33687124472-billing-lock-20260902-01.md": "b91a85d3",
    "test_grokbuild_open_door_guard_33687124472_billing_lock.py": "e6a826cf",
    "p/grokbuild-pr8408-verify-20260902-01.md": "0a594dda",
    "p/grokbuild-pr8411-verify-20260902-01.md": "642dea64",
    "test_grokbuild_pr8411_verify.py": "361f5ca1",
    "p/grok-build-discord-cloud-billing-lock-20260902-01.md": "2e0bfbfb",
    "p/grok-build-local-compute-guard-billing-lock-20260902-01.md": "de59bf75",
    "p/cursor-stealable-lanes-occupancy-readback-20260902-01.md": "b2df1cf1",
    "p/cursor-stealable-lanes-occupancy-20260902-01.md": "9631e869",
    "test_cursor_stealable_lanes_occupancy_readback.py": "589e56e7",
    "test_stealable_lanes_occupancy.py": "92c23495",
    "host/stealable_lanes.py": "c90284fb",
    "p/cursor-merge-on-pr-20260902-01.md": "22b63e25",
}


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class TestGrokbuildOpenDoorGuard33689281182BillingLock(unittest.TestCase):
    def test_keep_guard_occupancy_and_sibling_unread(self) -> None:
        for rel, prefix in KEEP.items():
            blob = git_blob(rel)
            self.assertTrue(
                blob.startswith(prefix),
                f"{rel} reminted: want {prefix} got {blob[:8]}",
            )

    def test_prior_33687124472_leftover_tests_still_pass(self) -> None:
        proc = subprocess.run(
            ["python3", "-m", "unittest", "test_grokbuild_open_door_guard_33687124472_billing_lock"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
        self.assertIn("Ran 4 tests", proc.stderr + proc.stdout)

    def test_local_failed_step_still_passes(self) -> None:
        proc = subprocess.run(
            ["python3", "test_open_door_guard.py"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
        self.assertIn("OPEN DOOR GUARD TEST:", proc.stdout)
        added = [
            guard.AddedLine("test_grokbuild_open_door_guard_33689281182_billing_lock.py", 1, line)
            for line in Path(__file__).read_text(encoding="utf-8").splitlines()
        ]
        self.assertEqual(guard.scan_added(added), [])
        receipt_added = [
            guard.AddedLine("p/grokbuild-open-door-guard-33689281182-billing-lock-20260902-01.md", 1, line)
            for line in RECEIPT.read_text(encoding="utf-8").splitlines()
        ]
        self.assertEqual(guard.scan_added(receipt_added), [])

    def test_receipt_cites_run_and_does_not_steal(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        prior = PRIOR.read_text(encoding="utf-8")
        verify_8408 = VERIFY_8408.read_text(encoding="utf-8")
        verify_8411 = VERIFY_8411.read_text(encoding="utf-8")
        leftover = OCCUPANCY.read_text(encoding="utf-8")
        readback = READBACK.read_text(encoding="utf-8")
        self.assertIn("grokbuild-open-door-guard-33689281182-billing-lock-20260902-01", text)
        self.assertIn(
            "woahwhattheheck/commons:open-door-guard:81e8f9ccc7293bf6e5179e615ba460d87f409eb0:reject-added-locks",
            text,
        )
        self.assertIn("33689281182", text)
        self.assertIn("81e8f9ccc7293bf6e5179e615ba460d87f409eb0", text)
        self.assertIn("100444020895", text)
        self.assertIn("100446335188", text)
        self.assertIn("The job was not started because your account is locked due to a billing issue.", text)
        self.assertIn("EXTERNAL_BLOCKER", text)
        self.assertIn("4b053e43", text)
        self.assertIn("70ee5730", text)
        self.assertIn("b91a85d3", text)
        self.assertIn("e6a826cf", text)
        self.assertIn("Did not remint", text)
        self.assertIn("Did not unique-pack merge-on-PR leftover", text)
        self.assertIn("Did not reopen #7915", text)
        self.assertNotEqual(text, prior)
        self.assertNotEqual(text, verify_8408)
        self.assertNotEqual(text, verify_8411)
        self.assertNotEqual(text, leftover)
        self.assertNotEqual(text, readback)
        self.assertNotIn("grokbuild-open-door-guard-33689281182-billing-lock-20260902-01", prior)
        self.assertNotIn("buy.stripe.com", text)

    def test_fix_first_packet_is_external_blocker(self) -> None:
        packet = {
            "outcome": "external_blocker",
            "observed_broken": True,
            "finding_kind": "behavior",
            "expected_contract": (
                "open-door-guard.yml job reject-added-locks executes "
                "python3 open_door_guard.py --diff BASE HEAD then "
                "python3 test_open_door_guard.py on push to main"
            ),
            "repair_attempts": [
                "local open_door_guard.py --diff 920d8c03 81e8f9cc PASS",
                "local test_open_door_guard.py PASS",
                "occupancy readback 6/6 OK",
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
