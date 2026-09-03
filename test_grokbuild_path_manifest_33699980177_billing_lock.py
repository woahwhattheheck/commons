#!/usr/bin/env python3
"""Pin unique leftover for path-manifest run 33699980177. Do not remint classifier or prior leftovers."""

from __future__ import annotations

import subprocess
import unittest
from pathlib import Path

import fix_first
import open_door_guard as guard

ROOT = Path(__file__).resolve().parent
RECEIPT = ROOT / "p/grokbuild-path-manifest-33699980177-billing-lock-20260903-01.md"
SIBLING = ROOT / "p/grokbuild-path-manifest-33694214802-billing-lock-20260902-01.md"
SIBLING_TEST = ROOT / "test_grokbuild_path_manifest_33694214802_billing_lock.py"
DISCORD = ROOT / "p/grok-build-discord-cloud-33699286743-billing-lock-20260902-01.md"
DISCORD_TEST = ROOT / "test_grokbuild_discord_cloud_33699286743_billing_lock.py"

KEEP = {
    "test_path_manifest.py": "c6de797a",
    "host/path_manifest.py": "dcc94697",
    ".github/workflows/path-manifest.yml": "b29dec8a",
    "architecture/path-manifest.json": "e5ecb24f",
    "p/grokbuild-path-manifest-33694214802-billing-lock-20260902-01.md": "d9331b17",
    "test_grokbuild_path_manifest_33694214802_billing_lock.py": "456e9d0d",
    "p/grokbuild-pr8415-path-manifest-33689243555-20260902-01.md": "3c72cd09",
    "test_grokbuild_pr8415_path_manifest_33689243555.py": "5494bffe",
    "p/grok-build-discord-cloud-33699286743-billing-lock-20260902-01.md": "e8d308ed",
    "test_grokbuild_discord_cloud_33699286743_billing_lock.py": "fcc155e0",
    "p/admin-owner-marks-20260902-01.md": "cdff4bfb",
}


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class TestGrokbuildPathManifest33699980177BillingLock(unittest.TestCase):
    def test_keep_classifier_and_sibling_unread(self) -> None:
        for rel, prefix in KEEP.items():
            blob = git_blob(rel)
            self.assertTrue(
                blob.startswith(prefix),
                f"{rel} reminted: want {prefix} got {blob[:8]}",
            )

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
                "test_grokbuild_path_manifest_33699980177_billing_lock.py", 1, line
            )
            for line in Path(__file__).read_text(encoding="utf-8").splitlines()
        ]
        self.assertEqual(guard.scan_added(added), [])
        receipt_added = [
            guard.AddedLine(
                "p/grokbuild-path-manifest-33699980177-billing-lock-20260903-01.md",
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
        discord = DISCORD.read_text(encoding="utf-8")
        discord_test = DISCORD_TEST.read_text(encoding="utf-8")
        self.assertIn("grokbuild-path-manifest-33699980177-billing-lock-20260903-01", text)
        self.assertIn(
            "woahwhattheheck/commons:path-manifest:e34659bfcc5493969ef7fe00bc9edafe15607a01:observe",
            text,
        )
        self.assertIn("33699980177", text)
        self.assertIn("e34659bfcc5493969ef7fe00bc9edafe15607a01", text)
        self.assertIn("100476980537", text)
        self.assertIn("100478624188", text)
        self.assertIn("8529", text)
        self.assertIn(
            "The job was not started because your account is locked due to a billing issue.",
            text,
        )
        self.assertIn("EXTERNAL_BLOCKER", text)
        self.assertIn("c6de797a", text)
        self.assertIn("dcc94697", text)
        self.assertIn("b29dec8a", text)
        self.assertIn("e8d308ed", text)
        self.assertIn("d9331b17", text)
        self.assertIn("Did not remint", text)
        self.assertIn("Did not reopen #7915", text)
        self.assertIn("Did not reopen #8529", text)
        self.assertNotEqual(text, sibling)
        self.assertNotEqual(text, discord)
        self.assertNotEqual(Path(__file__).read_text(encoding="utf-8"), sibling_test)
        self.assertNotEqual(Path(__file__).read_text(encoding="utf-8"), discord_test)
        self.assertNotIn("buy.stripe.com", text)
        self.assertNotIn("33694214802", text.split("KEEP unread", 1)[0])

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
                "event SHA e34659bf classifier blobs MATCH current main",
                "associated PR 8529 leftover e8d308ed unread; its tests 5/5",
                "github billing APIs 404/401; rerun_failed_jobs 201; attempt 2 job 100478624188 same billing lock",
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
