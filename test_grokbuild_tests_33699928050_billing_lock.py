#!/usr/bin/env python3
"""Pin unique leftover for tests battery run 33699928050. Do not remint associated leftover."""

from __future__ import annotations

import subprocess
import unittest
from pathlib import Path

import fix_first
import open_door_guard as guard

ROOT = Path(__file__).resolve().parent
RECEIPT = ROOT / "p/grokbuild-tests-33699928050-billing-lock-20260903-01.md"
SIBLING = ROOT / "p/grokbuild-open-door-guard-33699286785-billing-lock-20260902-01.md"
SIBLING_TEST = ROOT / "test_grokbuild_open_door_guard_33699286785_billing_lock.py"
PRIOR = ROOT / "p/grokbuild-tests-33694253421-billing-lock-20260902-01.md"
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
    "p/grokbuild-open-door-guard-33699607387-billing-lock-20260903-01.md": "32f69eaf",
    "p/grokbuild-open-door-guard-33699940644-billing-lock-20260903-01.md": "38fc515e",
    "p/grokbuild-tests-33699945008-billing-lock-20260903-01.md": "a6542e64",
}


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class TestGrokbuildTests33699928050BillingLock(unittest.TestCase):
    def test_keep_workflow_and_associated_leftover_unread(self) -> None:
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
            [
                "python3",
                "-m",
                "unittest",
                "test_grokbuild_open_door_guard_33699286785_billing_lock.py",
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
        self.assertIn("Ran 4 tests", proc.stderr)
        guard_proc = subprocess.run(
            ["python3", "test_open_door_guard.py"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(guard_proc.returncode, 0, msg=guard_proc.stdout + guard_proc.stderr)
        self.assertIn("OPEN DOOR GUARD TEST:", guard_proc.stdout)
        added = [
            guard.AddedLine("test_grokbuild_tests_33699928050_billing_lock.py", 1, line)
            for line in Path(__file__).read_text(encoding="utf-8").splitlines()
        ]
        added.extend(
            guard.AddedLine(
                "p/grokbuild-tests-33699928050-billing-lock-20260903-01.md", 1, line
            )
            for line in RECEIPT.read_text(encoding="utf-8").splitlines()
        )
        self.assertEqual(guard.scan_added(added), [])

    def test_receipt_cites_this_run_and_does_not_steal(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        sibling = SIBLING.read_text(encoding="utf-8")
        sibling_test = SIBLING_TEST.read_text(encoding="utf-8")
        prior = PRIOR.read_text(encoding="utf-8")
        self.assertIn("grokbuild-tests-33699928050-billing-lock-20260903-01", text)
        self.assertIn(
            "woahwhattheheck/commons:tests:9f8c2487104f0bfce331eb89b2499aee3b95170f:battery",
            text,
        )
        self.assertIn("33699928050", text)
        self.assertIn("100476822083", text)
        self.assertIn("9f8c2487104f0bfce331eb89b2499aee3b95170f", text)
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
        self.assertIn("32f69eaf", text)
        self.assertIn("38fc515e", text)
        self.assertIn("a6542e64", text)
        self.assertIn("Did not remint", text)
        self.assertIn("did not reopen #7915", text.lower())
        self.assertNotEqual(text, sibling)
        self.assertNotEqual(text, prior)
        self.assertNotEqual(Path(__file__).read_text(encoding="utf-8"), sibling_test)
        self.assertNotIn("buy.stripe.com", text)
        self.assertNotIn("33694253421", text.split("KEEP unread", 1)[0])
        self.assertNotIn("33699607387", text.split("KEEP unread", 1)[0])
        self.assertNotIn("33699940644", text.split("KEEP unread", 1)[0])
        self.assertNotIn("33699945008", text.split("KEEP unread", 1)[0])

    def test_fix_first_packet_is_external_blocker(self) -> None:
        packet = {
            "outcome": "external_blocker",
            "observed_broken": True,
            "finding_kind": "behavior",
            "expected_contract": (
                "tests.yml job battery checks out the repo and runs every "
                "discovered root test_*.py / test_*.js plus infra test_*.py "
                "on pull_request and on push to main that touches engine or test paths"
            ),
            "repair_attempts": [
                "inspected tests.yml blob 8c2f2301 valid battery job no skip",
                "local unique leftover tests PASS",
                "local associated leftover test_grokbuild_open_door_guard_33699286785_billing_lock.py PASS",
                "open_door_guard PASS; test_open_door_guard.py PASS; test_fix_first.py 6/6",
                "adjacent test_open_door rc=0 OPEN / test_path_manifest 9 / test_source_parses 9",
                "github billing APIs 404/403; later-main tests 33700447578 same billing lock runner_id=0",
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
