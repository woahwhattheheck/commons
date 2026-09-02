#!/usr/bin/env python3
"""Pin unique leftover for tests battery run 33694246830. Do not remint peers."""

from __future__ import annotations

import subprocess
import unittest
from pathlib import Path

import fix_first
import open_door_guard as guard

ROOT = Path(__file__).resolve().parent
RECEIPT = ROOT / "p/grokbuild-tests-33694246830-billing-lock-20260902-01.md"
SIBLING = ROOT / "p/grokbuild-tests-33689083188-billing-lock-20260902-01.md"
HUB_TICK = ROOT / "ground/HUB_TICK.md"
WORKFLOW = ROOT / ".github/workflows/tests.yml"

KEEP = {
    ".github/workflows/tests.yml": "8c2f2301",
    "ground/HUB_TICK.md": "f4cc7938",
    "p/grokbuild-tests-33689083188-billing-lock-20260902-01.md": "ea4625e6",
    "p/grokbuild-tests-33689243523-billing-lock-20260902-01.md": "119ccb17",
    "p/grokbuild-tests-33689281316-billing-lock-20260902-01.md": "3db0ab2e",
    "p/grokbuild-tests-battery-33689096444-billing-lock-20260902-01.md": "a7ff1feb",
    "open_door_guard.py": "4b053e43",
}


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class TestGrokbuildTests33694246830BillingLock(unittest.TestCase):
    def test_keep_workflow_hub_tick_and_siblings_unread(self) -> None:
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
        self.assertIn("ground/**", yml)
        self.assertNotIn("if: false", yml)
        self.assertNotIn("continue-on-error", yml)
        hub = HUB_TICK.read_text(encoding="utf-8")
        self.assertIn("Tick ≠ content.", hub)
        self.assertIn("wire-hub-tick-20260902-01", hub)

    def test_local_failed_step_contract_still_passes(self) -> None:
        proc = subprocess.run(
            ["python3", "-m", "unittest", "test_fix_first"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
        self.assertIn("Ran 6 tests", proc.stderr)
        added = [
            guard.AddedLine(
                "test_grokbuild_tests_33694246830_billing_lock.py", 1, line
            )
            for line in Path(__file__).read_text(encoding="utf-8").splitlines()
        ]
        self.assertEqual(guard.scan_added(added), [])

    def test_receipt_cites_run_and_does_not_steal(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        sibling = SIBLING.read_text(encoding="utf-8")
        self.assertIn(
            "grokbuild-tests-33694246830-billing-lock-20260902-01", text
        )
        self.assertIn(
            "woahwhattheheck/commons:tests:5467954de17e748a52f18c70955105cb020e325b:battery",
            text,
        )
        self.assertIn("33694246830", text)
        self.assertIn("100459564591", text)
        self.assertIn("100461271975", text)
        self.assertIn("5467954de17e748a52f18c70955105cb020e325b", text)
        self.assertIn(
            "The job was not started because your account is locked due to a billing issue.",
            text,
        )
        self.assertIn("EXTERNAL_BLOCKER", text)
        self.assertIn("8c2f2301", text)
        self.assertIn("f4cc7938", text)
        self.assertIn("ea4625e6", text)
        self.assertIn("Did not remint those", text)
        self.assertIn("ground/HUB_TICK.md", text)
        self.assertNotEqual(text, sibling)
        self.assertNotIn(
            "woahwhattheheck/commons:tests:5467954de17e748a52f18c70955105cb020e325b:battery",
            sibling,
        )
        self.assertNotIn("buy.stripe.com", text)

    def test_fix_first_packet_is_external_blocker(self) -> None:
        packet = {
            "outcome": "external_blocker",
            "observed_broken": True,
            "finding_kind": "behavior",
            "expected_contract": (
                "tests.yml job battery checks out the repo then runs every "
                "discovered root test_*.py / test_*.js plus infra test_*.py "
                "on push to main that touches ground/** including HUB_TICK.md"
            ),
            "repair_attempts": [
                "inspected tests.yml battery glob; no YAML defect",
                "local publisher inventory 15/15 PASS",
                "open_door_guard PASS; test_open_door_guard.py PASS; test_fix_first.py 6/6",
                "node test_board_overlay.js overlay PASS",
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
