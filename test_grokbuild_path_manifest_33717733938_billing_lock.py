#!/usr/bin/env python3
"""Pin unique leftover for path-manifest run 33717733938. Do not remint classifier or prior leftovers."""

from __future__ import annotations

import subprocess
import unittest
from pathlib import Path

import fix_first
import open_door_guard as guard

ROOT = Path(__file__).resolve().parent
RECEIPT = ROOT / "p/grokbuild-path-manifest-33717733938-billing-lock-20260903-01.md"
PRIOR = ROOT / "p/grokbuild-path-manifest-33699980177-billing-lock-20260903-01.md"
KEEP_POST = ROOT / "p/grokbuild-main-range-verify-33717084528-billing-lock-20260903-01.md"
WORKFLOW = ROOT / ".github/workflows/path-manifest.yml"

KEEP = {
    "test_path_manifest.py": "c6de797a",
    "host/path_manifest.py": "dcc94697",
    ".github/workflows/path-manifest.yml": "b29dec8a",
    "architecture/path-manifest.json": "e5ecb24f",
    "open_door_guard.py": "4b053e43",
    "p/grokbuild-path-manifest-33699980177-billing-lock-20260903-01.md": "d9365b97",
    "test_grokbuild_path_manifest_33699980177_billing_lock.py": "4740e323",
    "p/grokbuild-main-range-verify-33717084528-billing-lock-20260903-01.md": "2b0fd9c9",
    "test_grokbuild_main_range_verify_33717084528_billing_lock.py": "3e89a404",
    "p/grokbuild-harness-wakeup-33717474657-billing-lock-20260903-01.md": "f54e1846",
    "test_grokbuild_harness_wakeup_33717474657_billing_lock.py": "760a8169",
    "p/grokbuild-slack-service-tags-33717615004-billing-lock-20260903-01.md": "f33a76ef",
    "test_grokbuild_slack_service_tags_33717615004_billing_lock.py": "e10a1435",
    "p/grokbuild-open-door-guard-33717733987-billing-lock-20260903-01.md": "a0af1282",
    "test_grokbuild_open_door_guard_33717733987_billing_lock.py": "0269ac73",
    "p/grok-build-job-watchdog-33717741080-billing-lock-20260903-01.md": "f3afb926",
    "test_grokbuild_job_watchdog_33717741080_billing_lock.py": "7a1bc6f6",
    "p/grokbuild-pr8546-verify-20260903-01.md": "4e4d8003",
    "p/grok-build-job-watchdog-33699286811-billing-lock-20260903-01.md": "81092ec2",
    "p/admin-owner-marks-20260902-01.md": "cdff4bfb",
}


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class TestGrokbuildPathManifest33717733938BillingLock(unittest.TestCase):
    def test_keep_classifier_and_prior_leftovers_unread(self) -> None:
        for rel, prefix in KEEP.items():
            blob = git_blob(rel)
            self.assertTrue(
                blob.startswith(prefix),
                f"{rel} reminted: want {prefix} got {blob[:8]}",
            )
        yml = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("python3 test_path_manifest.py", yml)
        self.assertIn("python3 host/path_manifest.py", yml)
        self.assertIn("actions/checkout@v4", yml)
        self.assertIn("actions/upload-artifact@v4", yml)
        self.assertNotIn("billing", yml.lower())
        self.assertNotIn("if: false", yml)

    def test_local_failed_step_still_passes(self) -> None:
        proc = subprocess.run(
            ["python3", "-m", "unittest", "test_path_manifest"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
        self.assertIn("Ran 9 tests", proc.stderr + proc.stdout)
        added = [
            guard.AddedLine(
                "test_grokbuild_path_manifest_33717733938_billing_lock.py", 1, line
            )
            for line in Path(__file__).read_text(encoding="utf-8").splitlines()
        ]
        self.assertEqual(guard.scan_added(added), [])
        receipt_added = [
            guard.AddedLine(
                "p/grokbuild-path-manifest-33717733938-billing-lock-20260903-01.md",
                1,
                line,
            )
            for line in RECEIPT.read_text(encoding="utf-8").splitlines()
        ]
        self.assertEqual(guard.scan_added(receipt_added), [])

    def test_receipt_is_unique_and_does_not_remint(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        prior = PRIOR.read_text(encoding="utf-8")
        keep_post = KEEP_POST.read_text(encoding="utf-8")
        self.assertIn("grokbuild-path-manifest-33717733938-billing-lock-20260903-01", text)
        self.assertIn(
            "woahwhattheheck/commons:path-manifest:2890fde44250063aa66ef60735a7cc90407760a6:observe",
            text,
        )
        self.assertIn("33717733938", text)
        self.assertIn("100530342239", text)
        self.assertIn("100531949069", text)
        self.assertIn("2890fde44250063aa66ef60735a7cc90407760a6", text)
        self.assertIn("4a3238bbf65d8082f9c6c0a9776693395ed25fca", text)
        self.assertIn("8583", text)
        self.assertIn(
            "The job was not started because your account is locked due to a billing issue.",
            text,
        )
        self.assertIn("EXTERNAL_BLOCKER", text)
        self.assertIn("Did not remint leftover grokbuild-path-manifest-33699980177-billing-lock-20260903-01", text)
        self.assertIn("d9365b97", text)
        self.assertIn("4740e323", text)
        self.assertIn("2b0fd9c9", text)
        self.assertIn("3e89a404", text)
        self.assertIn("f54e1846", text)
        self.assertIn("760a8169", text)
        self.assertIn("f33a76ef", text)
        self.assertIn("e10a1435", text)
        self.assertIn("a0af1282", text)
        self.assertIn("0269ac73", text)
        self.assertIn("f3afb926", text)
        self.assertIn("7a1bc6f6", text)
        self.assertIn("4e4d8003", text)
        self.assertIn("81092ec2", text)
        self.assertIn("43c6e5cb", text)
        self.assertIn("cdff4bfb", text)
        self.assertIn("c6de797a", text)
        self.assertIn("dcc94697", text)
        self.assertIn("b29dec8a", text)
        self.assertIn("e5ecb24f", text)
        self.assertIn("4b053e43", text)
        self.assertIn("Did not reopen #7915", text)
        self.assertIn("Did not reopen #8583", text)
        self.assertNotEqual(text, prior)
        self.assertNotEqual(text, keep_post)
        sibling_test = ROOT / "test_grokbuild_path_manifest_33699980177_billing_lock.py"
        self.assertNotEqual(
            Path(__file__).read_text(encoding="utf-8"),
            sibling_test.read_text(encoding="utf-8"),
        )
        self.assertNotIn(
            "path-manifest:2890fde44250063aa66ef60735a7cc90407760a6:observe",
            prior,
        )
        self.assertNotIn(
            "path-manifest:2890fde44250063aa66ef60735a7cc90407760a6:observe",
            keep_post,
        )
        self.assertNotIn("buy.stripe.com", text)

    def test_fix_first_packet_is_external_blocker(self) -> None:
        packet = {
            "outcome": "external_blocker",
            "observed_broken": True,
            "finding_kind": "behavior",
            "expected_contract": (
                "path-manifest.yml job observe executes "
                "python3 test_path_manifest.py then "
                "python3 host/path_manifest.py --report on pull_request"
            ),
            "repair_attempts": [
                "local test_path_manifest.py 9/9; host/path_manifest.py report OBSERVED",
                "event SHA 2890fde4 classifier blobs MATCH current main",
                "associated PR 8583 leftover 2b0fd9c9 unread; its tests 4/4",
                "github billing APIs 404/403; rerun_failed_jobs 201; attempt 2 job 100531949069 same billing lock",
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
