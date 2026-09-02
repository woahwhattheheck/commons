#!/usr/bin/env python3
"""Pin unique leftover for tests battery run 33689083188. Do not remint occupancy KEEP."""

from __future__ import annotations

import subprocess
import unittest
from pathlib import Path

import fix_first
import open_door_guard as guard

ROOT = Path(__file__).resolve().parent
RECEIPT = ROOT / "p/grokbuild-tests-33689083188-billing-lock-20260902-01.md"
KEEP_LIFT = ROOT / "p/grokbuild-occupancy-landed-work-keep-lift-20260902-01.md"
KEEP_LIFT_RB = ROOT / "p/grokbuild-occupancy-landed-work-keep-lift-readback-20260902-01.md"
OCCUPANCY = ROOT / "p/cursor-stealable-lanes-occupancy-20260902-01.md"
WORKFLOW = ROOT / ".github/workflows/tests.yml"

KEEP = {
    "p/grokbuild-occupancy-landed-work-keep-lift-20260902-01.md": "67a8a527",
    "test_grokbuild_occupancy_landed_work_keep_lift.py": "b65527ed",
    "p/grokbuild-occupancy-landed-work-keep-lift-readback-20260902-01.md": "892bc4c0",
    "test_grokbuild_occupancy_landed_work_keep_lift_readback.py": "67ce7021",
    "p/cursor-stealable-lanes-occupancy-20260902-01.md": "9631e869",
    "host/stealable_lanes.py": "c90284fb",
    "p/cursor-stealable-lanes-occupancy-readback-20260902-01.md": "b2df1cf1",
    "test_stealable_lanes_occupancy.py": "92c23495",
    "p/cursor-merge-on-pr-20260902-01.md": "22b63e25",
    ".github/workflows/tests.yml": "8c2f2301",
    "p/grokbuild-open-door-guard-33687124472-billing-lock-20260902-01.md": "b91a85d3",
    "p/grok-build-discord-cloud-billing-lock-20260902-01.md": "2e0bfbfb",
    "p/grok-build-llms-txt-33687829181-billing-lock-20260902-01.md": "3183564c",
    "p/grok-build-llms-txt-billing-lock-20260902-01.md": "cf9c9f40",
    "p/grok-build-local-compute-guard-billing-lock-20260902-01.md": "de59bf75",
    "p/grok-resources-tab-freshness-billing-lock-20260902-01.md": "ac39fe78",
    "ground/OWNER_NOW.md": "59b1fd37",
    "open_door_guard.py": "4b053e43",
    "test_open_door_guard.py": "70ee5730",
}


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class TestGrokbuildTests33689083188BillingLock(unittest.TestCase):
    def test_keep_occupancy_and_tests_yml_unread(self) -> None:
        for rel, prefix in KEEP.items():
            blob = git_blob(rel)
            self.assertTrue(
                blob.startswith(prefix),
                f"{rel} reminted: want {prefix} got {blob[:8]}",
            )
        yml = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("name: tests", yml)
        self.assertIn("battery:", yml)
        self.assertIn("the whole battery, one failure fails the run", yml)
        self.assertIn("find . -maxdepth 1 -type f -name 'test_*.py'", yml)
        self.assertNotIn("billing", yml.lower())
        self.assertNotIn("if: false", yml)
        self.assertNotIn("continue-on-error", yml)

    def test_local_failed_step_still_passes(self) -> None:
        for name, expected in (
            ("test_grokbuild_occupancy_landed_work_keep_lift.py", "Ran 4 tests"),
            ("test_grokbuild_occupancy_landed_work_keep_lift_readback.py", "Ran 5 tests"),
            ("test_stealable_lanes_occupancy.py", "Ran 4 tests"),
        ):
            proc = subprocess.run(
                ["python3", "-m", "unittest", name],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(proc.returncode, 0, msg=name + "\n" + proc.stdout + proc.stderr)
            self.assertIn(expected, proc.stderr)
        added = [
            guard.AddedLine("test_grokbuild_tests_33689083188_billing_lock.py", 1, line)
            for line in Path(__file__).read_text(encoding="utf-8").splitlines()
        ]
        self.assertEqual(guard.scan_added(added), [])

    def test_receipt_cites_run_and_does_not_steal(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        leftover = KEEP_LIFT.read_text(encoding="utf-8")
        readback = KEEP_LIFT_RB.read_text(encoding="utf-8")
        occupancy = OCCUPANCY.read_text(encoding="utf-8")
        self.assertIn("grokbuild-tests-33689083188-billing-lock-20260902-01", text)
        self.assertIn(
            "woahwhattheheck/commons:tests:de52301ba37a900f184bc790c97a336832409091:battery",
            text,
        )
        self.assertIn("33689083188", text)
        self.assertIn("100443407559", text)
        self.assertIn("100445636702", text)
        self.assertIn("de52301ba37a900f184bc790c97a336832409091", text)
        self.assertIn(
            "The job was not started because your account is locked due to a billing issue.",
            text,
        )
        self.assertIn("EXTERNAL_BLOCKER", text)
        self.assertIn("67a8a527", text)
        self.assertIn("b65527ed", text)
        self.assertIn("892bc4c0", text)
        self.assertIn("8c2f2301", text)
        self.assertIn("Did not remint", text)
        self.assertIn("Did not unique-pack merge-on-PR leftover", text)
        self.assertIn("did not reopen #7915", text)
        self.assertNotEqual(text, leftover)
        self.assertNotEqual(text, readback)
        self.assertNotEqual(text, occupancy)
        self.assertNotIn("buy.stripe.com", text)
        self.assertFalse((ROOT / "marketplace.html").exists())
        self.assertFalse((ROOT / "qualify.html").exists())

    def test_fix_first_packet_is_external_blocker(self) -> None:
        packet = {
            "outcome": "external_blocker",
            "observed_broken": True,
            "finding_kind": "behavior",
            "expected_contract": (
                "tests.yml job battery checks out the repo and runs every "
                "discovered root test_*.py / test_*.js plus infra test_*.py "
                "on push to main that touches engine or test paths"
            ),
            "repair_attempts": [
                "local occupancy KEEP-lift leftover 4/4 on current main",
                "local occupancy KEEP-lift readback 5/5",
                "local occupancy leftover 4/4",
                "open_door_guard PASS; test_open_door_guard.py PASS; test_fix_first.py 6/6",
                "publisher inventory 15/15 PASS",
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
