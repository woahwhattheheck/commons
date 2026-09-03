#!/usr/bin/env python3
"""Pin unique leftover for path-manifest run 33699928065. Do not remint classifier or prior leftovers."""

from __future__ import annotations

import subprocess
import unittest
from pathlib import Path

import fix_first
import open_door_guard as guard

ROOT = Path(__file__).resolve().parent
RECEIPT = ROOT / "p/grokbuild-path-manifest-33699928065-billing-lock-20260903-01.md"
SIBLING = ROOT / "p/grokbuild-path-manifest-33694214802-billing-lock-20260902-01.md"
SIBLING_TEST = ROOT / "test_grokbuild_path_manifest_33694214802_billing_lock.py"
OLDER = ROOT / "p/grokbuild-pr8415-path-manifest-33689243555-20260902-01.md"
OLDER_TEST = ROOT / "test_grokbuild_pr8415_path_manifest_33689243555.py"
OPEN_DOOR = ROOT / "p/grokbuild-open-door-guard-33699286785-billing-lock-20260902-01.md"
WORKFLOW = ROOT / ".github/workflows/path-manifest.yml"

KEEP = {
    "test_path_manifest.py": "c6de797a",
    "host/path_manifest.py": "dcc94697",
    ".github/workflows/path-manifest.yml": "b29dec8a",
    "architecture/path-manifest.json": "e5ecb24f",
    "p/grokbuild-path-manifest-33694214802-billing-lock-20260902-01.md": "d9331b17",
    "test_grokbuild_path_manifest_33694214802_billing_lock.py": "456e9d0d",
    "p/grokbuild-pr8415-path-manifest-33689243555-20260902-01.md": "3c72cd09",
    "test_grokbuild_pr8415_path_manifest_33689243555.py": "5494bffe",
    "p/grokbuild-open-door-guard-33699286785-billing-lock-20260902-01.md": "d22e0707",
    "test_grokbuild_open_door_guard_33699286785_billing_lock.py": "96ce49fa",
    "p/admin-owner-marks-20260902-01.md": "cdff4bfb",
}


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class TestGrokbuildPathManifest33699928065BillingLock(unittest.TestCase):
    def test_keep_classifier_and_sibling_unread(self) -> None:
        for rel, prefix in KEEP.items():
            blob = git_blob(rel)
            self.assertTrue(
                blob.startswith(prefix),
                f"{rel} reminted: want {prefix} got {blob[:8]}",
            )
        yml = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("python3 test_path_manifest.py", yml)
        self.assertIn("host/path_manifest.py", yml)
        self.assertIn("runs-on: ubuntu-latest", yml)
        self.assertNotIn("self-hosted", yml)
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
                "test_grokbuild_path_manifest_33699928065_billing_lock.py", 1, line
            )
            for line in Path(__file__).read_text(encoding="utf-8").splitlines()
        ]
        self.assertEqual(guard.scan_added(added), [])
        receipt_added = [
            guard.AddedLine(
                "p/grokbuild-path-manifest-33699928065-billing-lock-20260903-01.md",
                1,
                line,
            )
            for line in RECEIPT.read_text(encoding="utf-8").splitlines()
        ]
        self.assertEqual(guard.scan_added(receipt_added), [])

    def test_receipt_cites_this_run_and_does_not_steal(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        sibling = SIBLING.read_text(encoding="utf-8")
        sibling_test = SIBLING_TEST.read_text(encoding="utf-8")
        older = OLDER.read_text(encoding="utf-8")
        older_test = OLDER_TEST.read_text(encoding="utf-8")
        open_door = OPEN_DOOR.read_text(encoding="utf-8")
        self.assertIn("grokbuild-path-manifest-33699928065-billing-lock-20260903-01", text)
        self.assertIn(
            "woahwhattheheck/commons:path-manifest:9f8c2487104f0bfce331eb89b2499aee3b95170f:observe",
            text,
        )
        self.assertIn("33699928065", text)
        self.assertIn("9f8c2487104f0bfce331eb89b2499aee3b95170f", text)
        self.assertIn("100476821874", text)
        self.assertIn("100478071917", text)
        self.assertIn("33700229321", text)
        self.assertIn("100477723872", text)
        self.assertIn(
            "The job was not started because your account is locked due to a billing issue.",
            text,
        )
        self.assertIn("EXTERNAL_BLOCKER", text)
        self.assertIn("c6de797a", text)
        self.assertIn("dcc94697", text)
        self.assertIn("b29dec8a", text)
        self.assertIn("e5ecb24f", text)
        self.assertIn("d9331b17", text)
        self.assertIn("456e9d0d", text)
        self.assertIn("3c72cd09", text)
        self.assertIn("5494bffe", text)
        self.assertIn("d22e0707", text)
        self.assertIn("96ce49fa", text)
        self.assertIn("cdff4bfb", text)
        self.assertIn("Did not remint", text)
        self.assertIn("Did not reopen #7915", text)
        self.assertIn("/8527", text)
        self.assertNotEqual(text, sibling)
        self.assertNotEqual(text, older)
        self.assertNotEqual(text, open_door)
        self.assertNotEqual(Path(__file__).read_text(encoding="utf-8"), sibling_test)
        self.assertNotEqual(Path(__file__).read_text(encoding="utf-8"), older_test)
        self.assertNotIn("buy.stripe.com", text)
        self.assertNotIn("33694214802", text.split("KEEP unread", 1)[0])
        self.assertNotIn("33689243555", text.split("KEEP unread", 1)[0])

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
                "local test_path_manifest.py 9/9 OK; host/path_manifest.py report OBSERVED",
                "event SHA 9f8c2487 classifier blobs MATCH current main",
                "github billing APIs 404/403; rerun_failed_jobs 201; attempt 2 job 100478071917 same billing lock",
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
