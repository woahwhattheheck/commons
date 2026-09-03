#!/usr/bin/env python3
"""Pin unique leftover for tests battery run 33699940577. Do not remint the battery."""

from __future__ import annotations

import subprocess
import unittest
from pathlib import Path

import fix_first
import open_door_guard as guard

ROOT = Path(__file__).resolve().parent
RECEIPT = ROOT / "p/grokbuild-tests-33699940577-billing-lock-20260903-01.md"
SIBLING = ROOT / "p/grokbuild-tests-33694253421-billing-lock-20260902-01.md"
SIBLING_TEST = ROOT / "test_grokbuild_tests_33694253421_billing_lock.py"
TRIGGER = ROOT / "p/grokbuild-open-door-guard-33699286785-billing-lock-20260902-01.md"
TRIGGER_TEST = ROOT / "test_grokbuild_open_door_guard_33699286785_billing_lock.py"
WORKFLOW = ROOT / ".github/workflows/tests.yml"

KEEP = {
    ".github/workflows/tests.yml": "8c2f2301",
    "open_door_guard.py": "4b053e43",
    "test_open_door_guard.py": "70ee5730",
    "fix_first.py": "a57aee1c",
    "p/grokbuild-open-door-guard-33699286785-billing-lock-20260902-01.md": "d22e0707",
    "test_grokbuild_open_door_guard_33699286785_billing_lock.py": "96ce49fa",
    "p/grokbuild-tests-33694253421-billing-lock-20260902-01.md": "da396946",
    "test_grokbuild_tests_33694253421_billing_lock.py": "f3ce3fe0",
    "p/grokbuild-tests-33694246830-billing-lock-20260902-01.md": "b07d6192",
    "test_grokbuild_tests_33694246830_billing_lock.py": "fb6fc00d",
}


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class TestGrokbuildTests33699940577BillingLock(unittest.TestCase):
    def test_keep_workflow_and_trigger_unread(self) -> None:
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
        proc = subprocess.run(
            ["python3", "test_grokbuild_open_door_guard_33699286785_billing_lock.py"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
        self.assertIn("Ran 4 tests", proc.stderr)
        added = [
            guard.AddedLine("test_grokbuild_tests_33699940577_billing_lock.py", 1, line)
            for line in Path(__file__).read_text(encoding="utf-8").splitlines()
        ]
        added.extend(
            guard.AddedLine(
                "p/grokbuild-tests-33699940577-billing-lock-20260903-01.md", 1, line
            )
            for line in RECEIPT.read_text(encoding="utf-8").splitlines()
        )
        self.assertEqual(guard.scan_added(added), [])

    def test_receipt_cites_this_run_and_does_not_steal(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        sibling = SIBLING.read_text(encoding="utf-8")
        sibling_test = SIBLING_TEST.read_text(encoding="utf-8")
        trigger = TRIGGER.read_text(encoding="utf-8")
        trigger_test = TRIGGER_TEST.read_text(encoding="utf-8")
        self.assertIn("grokbuild-tests-33699940577-billing-lock-20260903-01", text)
        self.assertIn(
            "woahwhattheheck/commons:tests:60d5e8fa13824c88d42138a39a9629d41818e4e6:battery",
            text,
        )
        self.assertIn("33699940577", text)
        self.assertIn("100476859173", text)
        self.assertIn("60d5e8fa13824c88d42138a39a9629d41818e4e6", text)
        self.assertIn("8527", text)
        self.assertIn(
            "The job was not started because your account is locked due to a billing issue.",
            text,
        )
        self.assertIn("EXTERNAL_BLOCKER", text)
        self.assertIn("8c2f2301", text)
        self.assertIn("4b053e43", text)
        self.assertIn("d22e0707", text)
        self.assertIn("96ce49fa", text)
        self.assertIn("da396946", text)
        self.assertIn("Did not remint", text)
        self.assertNotEqual(text, sibling)
        self.assertNotEqual(text, trigger)
        self.assertNotEqual(Path(__file__).read_text(encoding="utf-8"), sibling_test)
        self.assertNotEqual(Path(__file__).read_text(encoding="utf-8"), trigger_test)
        self.assertNotIn("buy.stripe.com", text)
        self.assertNotIn("33694253421", text.split("KEEP unread", 1)[0])

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
                "local trigger leftover test_grokbuild_open_door_guard_33699286785_billing_lock.py 4/4",
                "local test_open_door_guard.py PASS; test_open_door.py rc=0 OPEN",
                "test_fix_first.py 6/6; test_source_parses.py 9/9; test_path_manifest.py 9/9",
                "publisher inventory 15/15 PASS",
                "later descendant tests runs same billing refusal runner_id=0",
                "github.com/settings/billing 404; githubstatus Actions operational",
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
