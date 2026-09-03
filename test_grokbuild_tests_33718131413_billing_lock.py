#!/usr/bin/env python3
"""Pin unique leftover for tests battery run 33718131413. Do not remint peer leftovers."""

from __future__ import annotations

import subprocess
import unittest
from pathlib import Path

import fix_first
import open_door_guard as guard

ROOT = Path(__file__).resolve().parent
RECEIPT = ROOT / "p/grokbuild-tests-33718131413-billing-lock-20260903-01.md"
PRIOR = ROOT / "p/grokbuild-tests-33717733992-billing-lock-20260903-01.md"
SIBLING = ROOT / "p/grokbuild-tests-33717741059-billing-lock-20260903-01.md"
TRIGGER = ROOT / "p/grokbuild-harness-wakeup-33717474657-billing-lock-20260903-01.md"
WORKFLOW = ROOT / ".github/workflows/tests.yml"

KEEP = {
    "p/grokbuild-tests-33717741059-billing-lock-20260903-01.md": "1b6c3021",
    "test_grokbuild_tests_33717741059_billing_lock.py": "c62e238e",
    "p/grokbuild-tests-33717733992-billing-lock-20260903-01.md": "e91d0547",
    "test_grokbuild_tests_33717733992_billing_lock.py": "41a9bcb5",
    "p/grokbuild-harness-wakeup-33717474657-billing-lock-20260903-01.md": "f54e1846",
    "test_grokbuild_harness_wakeup_33717474657_billing_lock.py": "760a8169",
    "p/grokbuild-slack-service-tags-33717615004-billing-lock-20260903-01.md": "f33a76ef",
    "test_grokbuild_slack_service_tags_33717615004_billing_lock.py": "e10a1435",
    "p/grokbuild-open-door-guard-33718116356-billing-lock-20260903-01.md": "25781cf5",
    "test_grokbuild_open_door_guard_33718116356_billing_lock.py": "2166e689",
    "p/admin-owner-marks-20260902-01.md": "cdff4bfb",
    "catalog.html": "154b7b67",
    "boards.html": "3fa79f12",
    "hub_pages.py": "5ac12648",
    ".github/workflows/tests.yml": "8c2f2301",
    "open_door_guard.py": "4b053e43",
    "fix_first.py": "a57aee1c",
}


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class TestGrokbuildTests33718131413BillingLock(unittest.TestCase):
    def test_keep_peer_leftovers_and_tests_yml_unread(self) -> None:
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
            ["python3", "test_subject_keep.py"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
        self.assertIn("ok   subject keep", proc.stdout + proc.stderr)
        added = [
            guard.AddedLine("test_grokbuild_tests_33718131413_billing_lock.py", 1, line)
            for line in Path(__file__).read_text(encoding="utf-8").splitlines()
        ]
        added.extend(
            guard.AddedLine(
                "p/grokbuild-tests-33718131413-billing-lock-20260903-01.md", 1, line
            )
            for line in RECEIPT.read_text(encoding="utf-8").splitlines()
        )
        self.assertEqual(guard.scan_added(added), [])

    def test_receipt_cites_run_and_does_not_steal(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        prior = PRIOR.read_text(encoding="utf-8")
        sibling = SIBLING.read_text(encoding="utf-8")
        trigger = TRIGGER.read_text(encoding="utf-8")
        self.assertIn("grokbuild-tests-33718131413-billing-lock-20260903-01", text)
        self.assertIn(
            "woahwhattheheck/commons:tests:e2699ed63748e7be9d1820c4722d09c8eaf5c04f:battery",
            text,
        )
        self.assertIn("33718131413", text)
        self.assertIn("100531515524", text)
        self.assertIn("e2699ed63748e7be9d1820c4722d09c8eaf5c04f", text)
        self.assertIn("8584", text)
        self.assertIn(
            "The job was not started because your account is locked due to a billing issue.",
            text,
        )
        self.assertIn("EXTERNAL_BLOCKER", text)
        self.assertIn("1b6c3021", text)
        self.assertIn("e91d0547", text)
        self.assertIn("f54e1846", text)
        self.assertIn("f33a76ef", text)
        self.assertIn("25781cf5", text)
        self.assertIn("cdff4bfb", text)
        self.assertIn("154b7b67", text)
        self.assertIn("3fa79f12", text)
        self.assertIn("5ac12648", text)
        self.assertIn("8c2f2301", text)
        self.assertIn("4b053e43", text)
        self.assertIn("a57aee1c", text)
        self.assertIn("Did not remint leftover grokbuild-tests-33717741059-billing-lock-20260903-01", text)
        self.assertIn("Did not reopen #7915", text)
        self.assertNotEqual(text, prior)
        self.assertNotEqual(text, sibling)
        self.assertNotEqual(text, trigger)
        self.assertNotIn(
            "tests:e2699ed63748e7be9d1820c4722d09c8eaf5c04f:battery",
            prior,
        )
        self.assertNotIn(
            "tests:e2699ed63748e7be9d1820c4722d09c8eaf5c04f:battery",
            sibling,
        )
        self.assertNotIn(
            "tests:e2699ed63748e7be9d1820c4722d09c8eaf5c04f:battery",
            trigger,
        )
        self.assertIn("33717733992", prior)
        self.assertIn("33717474657", trigger)

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
                "inspected tests.yml KEEP 8c2f2301; no YAML defect, no billing skip",
                "local publisher inventory 15/15 PASS on current main",
                "test_fix_first.py 6/6; test_path_manifest.py 9/9; test_source_parses.py 9/9",
                "open_door_guard --diff PASS; test_open_door_guard.py PASS",
                "trigger leftover test_grokbuild_harness_wakeup_33717474657_billing_lock.py 4/4",
                "annotation job 100531515524 billing lock; runner_id=0 steps=[] logs 404",
                "github.com/settings/billing/actions 404; githubstatus Actions operational",
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
