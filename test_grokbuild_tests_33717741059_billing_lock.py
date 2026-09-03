#!/usr/bin/env python3
"""Pin unique leftover for tests battery run 33717741059. Do not remint peer leftovers."""

from __future__ import annotations

import subprocess
import unittest
from pathlib import Path

import fix_first
import open_door_guard as guard

ROOT = Path(__file__).resolve().parent
RECEIPT = ROOT / "p/grokbuild-tests-33717741059-billing-lock-20260903-01.md"
PRIOR = ROOT / "p/grokbuild-tests-33699945008-billing-lock-20260903-01.md"
SIBLING = ROOT / "p/grokbuild-tests-33699940577-billing-lock-20260903-01.md"
TRIGGER = ROOT / "p/grokbuild-main-range-verify-33717084528-billing-lock-20260903-01.md"
WORKFLOW = ROOT / ".github/workflows/tests.yml"

KEEP = {
    "p/grokbuild-tests-33699945008-billing-lock-20260903-01.md": "a6542e64",
    "test_grokbuild_tests_33699945008_billing_lock.py": "d65621fe",
    "p/grokbuild-tests-33699940577-billing-lock-20260903-01.md": "90b6f8b9",
    "test_grokbuild_tests_33699940577_billing_lock.py": "dfcee481",
    "p/grokbuild-main-range-verify-33717084528-billing-lock-20260903-01.md": "2b0fd9c9",
    "test_grokbuild_main_range_verify_33717084528_billing_lock.py": "3e89a404",
    "p/grokbuild-harness-wakeup-33717474657-billing-lock-20260903-01.md": "f54e1846",
    "test_grokbuild_harness_wakeup_33717474657_billing_lock.py": "760a8169",
    "p/grokbuild-slack-service-tags-33717615004-billing-lock-20260903-01.md": "f33a76ef",
    "test_grokbuild_slack_service_tags_33717615004_billing_lock.py": "e10a1435",
    "p/grok-build-job-watchdog-33717741080-billing-lock-20260903-01.md": "f3afb926",
    "test_grokbuild_job_watchdog_33717741080_billing_lock.py": "7a1bc6f6",
    "p/grokbuild-open-door-guard-33717733987-billing-lock-20260903-01.md": "a0af1282",
    "test_grokbuild_open_door_guard_33717733987_billing_lock.py": "0269ac73",
    "p/admin-owner-marks-20260902-01.md": "cdff4bfb",
    "catalog.html": "154b7b67",
    "boards.html": "3fa79f12",
    "hub_pages.py": "5ac12648",
    ".github/workflows/tests.yml": "8c2f2301",
    "open_door_guard.py": "4b053e43",
}


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class TestGrokbuildTests33717741059BillingLock(unittest.TestCase):
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
            guard.AddedLine("test_grokbuild_tests_33717741059_billing_lock.py", 1, line)
            for line in Path(__file__).read_text(encoding="utf-8").splitlines()
        ]
        added.extend(
            guard.AddedLine(
                "p/grokbuild-tests-33717741059-billing-lock-20260903-01.md", 1, line
            )
            for line in RECEIPT.read_text(encoding="utf-8").splitlines()
        )
        self.assertEqual(guard.scan_added(added), [])

    def test_receipt_cites_run_and_does_not_steal(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        prior = PRIOR.read_text(encoding="utf-8")
        sibling = SIBLING.read_text(encoding="utf-8")
        trigger = TRIGGER.read_text(encoding="utf-8")
        self.assertIn("grokbuild-tests-33717741059-billing-lock-20260903-01", text)
        self.assertIn(
            "woahwhattheheck/commons:tests:0ddbdaf51fee6870caf1572ff53db1293852b72b:battery",
            text,
        )
        self.assertIn("33717741059", text)
        self.assertIn("100530362819", text)
        self.assertIn("0ddbdaf51fee6870caf1572ff53db1293852b72b", text)
        self.assertIn(
            "The job was not started because your account is locked due to a billing issue.",
            text,
        )
        self.assertIn("EXTERNAL_BLOCKER", text)
        self.assertIn("a6542e64", text)
        self.assertIn("90b6f8b9", text)
        self.assertIn("2b0fd9c9", text)
        self.assertIn("f54e1846", text)
        self.assertIn("f33a76ef", text)
        self.assertIn("f3afb926", text)
        self.assertIn("a0af1282", text)
        self.assertIn("cdff4bfb", text)
        self.assertIn("154b7b67", text)
        self.assertIn("3fa79f12", text)
        self.assertIn("5ac12648", text)
        self.assertIn("8c2f2301", text)
        self.assertIn("4b053e43", text)
        self.assertIn("Did not remint leftover grokbuild-tests-33699945008-billing-lock-20260903-01", text)
        self.assertIn("Did not reopen #7915", text)
        self.assertNotEqual(text, prior)
        self.assertNotEqual(text, sibling)
        self.assertNotEqual(text, trigger)
        self.assertNotIn(
            "tests:0ddbdaf51fee6870caf1572ff53db1293852b72b:battery",
            prior,
        )
        self.assertNotIn(
            "tests:0ddbdaf51fee6870caf1572ff53db1293852b72b:battery",
            sibling,
        )
        self.assertNotIn(
            "tests:0ddbdaf51fee6870caf1572ff53db1293852b72b:battery",
            trigger,
        )
        self.assertIn("33699945008", prior)
        self.assertIn("33717084528", trigger)

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
                "annotation job 100530362819 billing lock; runner_id=0 steps=[] logs 404",
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
