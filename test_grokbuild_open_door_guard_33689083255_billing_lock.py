#!/usr/bin/env python3
"""Pin unique leftover for open-door-guard run 33689083255. Do not remint the guard."""

from __future__ import annotations

import subprocess
import unittest
from pathlib import Path

import fix_first
import open_door_guard as guard

ROOT = Path(__file__).resolve().parent
RECEIPT = ROOT / "p/grokbuild-open-door-guard-33689083255-billing-lock-20260902-01.md"
PRIOR = ROOT / "p/grokbuild-open-door-guard-33689281182-billing-lock-20260902-01.md"
KEEP_LIFT = ROOT / "p/grokbuild-occupancy-landed-work-keep-lift-20260902-01.md"
KEEP_LIFT_READBACK = ROOT / "p/grokbuild-occupancy-landed-work-keep-lift-readback-20260902-01.md"
OCCUPANCY = ROOT / "p/cursor-stealable-lanes-occupancy-20260902-01.md"
READBACK = ROOT / "p/cursor-stealable-lanes-occupancy-readback-20260902-01.md"

KEEP = {
    "open_door_guard.py": "4b053e43",
    "test_open_door_guard.py": "70ee5730",
    ".github/workflows/open-door-guard.yml": "6586644c",
    "p/grokbuild-open-door-guard-33687124472-billing-lock-20260902-01.md": "b91a85d3",
    "test_grokbuild_open_door_guard_33687124472_billing_lock.py": "e6a826cf",
    "p/grokbuild-open-door-guard-33689243568-billing-lock-20260902-01.md": "4ab677c5",
    "test_grokbuild_open_door_guard_33689243568_billing_lock.py": "0ec1378d",
    "p/grokbuild-open-door-guard-33689088100-billing-lock-20260902-01.md": "2d8ebb0c",
    "test_grokbuild_open_door_guard_33689088100_billing_lock.py": "d584cf4f",
    "p/grokbuild-open-door-guard-33689357297-billing-lock-20260902-01.md": "261c9cf6",
    "test_grokbuild_open_door_guard_33689357297_billing_lock.py": "f2a2a68d",
    "p/grokbuild-open-door-guard-33689281182-billing-lock-20260902-01.md": "41bcb27d",
    "test_grokbuild_open_door_guard_33689281182_billing_lock.py": "91543e5d",
    "p/grokbuild-occupancy-landed-work-keep-lift-20260902-01.md": "67a8a527",
    "test_grokbuild_occupancy_landed_work_keep_lift.py": "b65527ed",
    "p/grokbuild-occupancy-landed-work-keep-lift-readback-20260902-01.md": "892bc4c0",
    "test_grokbuild_occupancy_landed_work_keep_lift_readback.py": "67ce7021",
    "p/cursor-stealable-lanes-occupancy-20260902-01.md": "9631e869",
    "p/cursor-stealable-lanes-occupancy-readback-20260902-01.md": "b2df1cf1",
    "host/stealable_lanes.py": "c90284fb",
    "p/cursor-merge-on-pr-20260902-01.md": "22b63e25",
}


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class TestGrokbuildOpenDoorGuard33689083255BillingLock(unittest.TestCase):
    def test_keep_guard_occupancy_and_sibling_unread(self) -> None:
        for rel, prefix in KEEP.items():
            blob = git_blob(rel)
            self.assertTrue(
                blob.startswith(prefix),
                f"{rel} reminted: want {prefix} got {blob[:8]}",
            )

    def test_prior_33689281182_leftover_tests_still_pass(self) -> None:
        proc = subprocess.run(
            ["python3", "-m", "unittest", "test_grokbuild_open_door_guard_33689281182_billing_lock"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
        self.assertIn("Ran 5 tests", proc.stderr + proc.stdout)

    def test_occupancy_keep_lift_leftover_and_readback_still_pass(self) -> None:
        leftover = subprocess.run(
            ["python3", "-m", "unittest", "test_grokbuild_occupancy_landed_work_keep_lift"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(leftover.returncode, 0, msg=leftover.stdout + leftover.stderr)
        self.assertIn("Ran 4 tests", leftover.stderr + leftover.stdout)
        readback = subprocess.run(
            ["python3", "-m", "unittest", "test_grokbuild_occupancy_landed_work_keep_lift_readback"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(readback.returncode, 0, msg=readback.stdout + readback.stderr)
        self.assertIn("Ran 5 tests", readback.stderr + readback.stdout)

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
            guard.AddedLine("test_grokbuild_open_door_guard_33689083255_billing_lock.py", 1, line)
            for line in Path(__file__).read_text(encoding="utf-8").splitlines()
        ]
        self.assertEqual(guard.scan_added(added), [])
        receipt_added = [
            guard.AddedLine("p/grokbuild-open-door-guard-33689083255-billing-lock-20260902-01.md", 1, line)
            for line in RECEIPT.read_text(encoding="utf-8").splitlines()
        ]
        self.assertEqual(guard.scan_added(receipt_added), [])
        parent = "f078829d8a45fefe9d501fed55bfe330056f1335"
        fail_sha = "de52301ba37a900f184bc790c97a336832409091"
        diff = subprocess.run(
            ["python3", "open_door_guard.py", "--diff", parent, fail_sha],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(diff.returncode, 0, msg=diff.stdout + diff.stderr)
        self.assertIn("OPEN DOOR GUARD: PASS", diff.stdout)

    def test_receipt_cites_run_and_does_not_steal(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        prior = PRIOR.read_text(encoding="utf-8")
        leftover = KEEP_LIFT.read_text(encoding="utf-8")
        keep_lift_readback = KEEP_LIFT_READBACK.read_text(encoding="utf-8")
        occupancy = OCCUPANCY.read_text(encoding="utf-8")
        readback = READBACK.read_text(encoding="utf-8")
        self.assertIn("grokbuild-open-door-guard-33689083255-billing-lock-20260902-01", text)
        self.assertIn(
            "woahwhattheheck/commons:open-door-guard:de52301ba37a900f184bc790c97a336832409091:reject-added-locks",
            text,
        )
        self.assertIn("33689083255", text)
        self.assertIn("de52301ba37a900f184bc790c97a336832409091", text)
        self.assertIn("100443406983", text)
        self.assertIn("100447671017", text)
        self.assertIn("The job was not started because your account is locked due to a billing issue.", text)
        self.assertIn("EXTERNAL_BLOCKER", text)
        self.assertIn("4b053e43", text)
        self.assertIn("70ee5730", text)
        self.assertIn("67a8a527", text)
        self.assertIn("892bc4c0", text)
        self.assertIn("Did not remint", text)
        self.assertIn("Did not unique-pack merge-on-PR leftover", text)
        self.assertIn("Did not reopen #7915", text)
        self.assertIn("33689083188", text)
        self.assertNotEqual(text, prior)
        self.assertNotEqual(text, leftover)
        self.assertNotEqual(text, keep_lift_readback)
        self.assertNotEqual(text, occupancy)
        self.assertNotEqual(text, readback)
        self.assertNotIn("grokbuild-open-door-guard-33689083255-billing-lock-20260902-01", prior)
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
                "local open_door_guard.py --diff f078829d8a45fefe9d501fed55bfe330056f1335 de52301ba37a900f184bc790c97a336832409091 PASS",
                "local test_open_door_guard.py PASS",
                "occupancy KEEP-lift leftover 4/4 and readback 5/5 OK",
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
