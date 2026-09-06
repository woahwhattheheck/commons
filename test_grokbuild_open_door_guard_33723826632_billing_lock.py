#!/usr/bin/env python3
"""Pin unique leftover for open-door-guard run 33723826632. Do not remint the guard."""

from __future__ import annotations

import subprocess
import unittest
from pathlib import Path

import fix_first
import open_door_guard as guard

ROOT = Path(__file__).resolve().parent
RECEIPT = ROOT / "p/grokbuild-open-door-guard-33723826632-billing-lock-20260903-01.md"
SIBLING = ROOT / "p/grokbuild-open-door-guard-33723638501-billing-lock-20260903-01.md"
SIBLING_TEST = ROOT / "test_grokbuild_open_door_guard_33723638501_billing_lock.py"
TRIGGER = ROOT / "p/grok-build-moving-main-mirror-billing-lock-20260903-01.md"

KEEP = {
    "open_door_guard.py": "861958e9",
    "test_open_door_guard.py": "2fb0d87b",
    ".github/workflows/open-door-guard.yml": "c2121049",
    "p/grokbuild-open-door-guard-33723638501-billing-lock-20260903-01.md": "37f54fd8",
    "test_grokbuild_open_door_guard_33723638501_billing_lock.py": "0d1ed934",
    "p/grok-build-moving-main-mirror-billing-lock-20260903-01.md": "4550e922",
    "p/grok-build-owner-net-33723510040-billing-lock-20260903-01.md": "6a2c8239",
    "p/grokbuild-leftover-id-census-33723043828-billing-lock-20260903-01.md": "e135862e",
}


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class TestGrokbuildOpenDoorGuard33723826632BillingLock(unittest.TestCase):
    def test_keep_guard_and_sibling_unread(self) -> None:
        for rel, prefix in KEEP.items():
            blob = git_blob(rel)
            self.assertTrue(
                blob.startswith(prefix),
                f"{rel} reminted: want {prefix} got {blob[:8]}",
            )

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
            guard.AddedLine(
                "test_grokbuild_open_door_guard_33723826632_billing_lock.py", 1, line
            )
            for line in Path(__file__).read_text(encoding="utf-8").splitlines()
        ]
        self.assertEqual(guard.scan_added(added), [])
        receipt_added = [
            guard.AddedLine(
                "p/grokbuild-open-door-guard-33723826632-billing-lock-20260903-01.md",
                1,
                line,
            )
            for line in RECEIPT.read_text(encoding="utf-8").splitlines()
        ]
        self.assertEqual(guard.scan_added(receipt_added), [])
        trigger_added = [
            guard.AddedLine(
                "p/grok-build-moving-main-mirror-billing-lock-20260903-01.md",
                1,
                line,
            )
            for line in TRIGGER.read_text(encoding="utf-8").splitlines()
        ]
        self.assertEqual(guard.scan_added(trigger_added), [])

    def test_receipt_cites_this_run_and_does_not_steal(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        sibling = SIBLING.read_text(encoding="utf-8")
        sibling_test = SIBLING_TEST.read_text(encoding="utf-8")
        self.assertIn("grokbuild-open-door-guard-33723826632-billing-lock-20260903-01", text)
        self.assertIn(
            "woahwhattheheck/commons:open-door-guard:178602e324ec73532d6f6acd99850dc0081370f6:reject-added-locks",
            text,
        )
        self.assertIn("33723826632", text)
        self.assertIn("178602e324ec73532d6f6acd99850dc0081370f6", text)
        self.assertIn("100548362565", text)
        self.assertIn("100549755121", text)
        self.assertIn(
            "The job was not started because your account is locked due to a billing issue.",
            text,
        )
        self.assertIn("EXTERNAL_BLOCKER", text)
        self.assertIn("4b053e43", text)
        self.assertIn("70ee5730", text)
        self.assertIn("37f54fd8", text)
        self.assertIn("4550e922", text)
        self.assertIn("Did not remint", text)
        self.assertIn("Did not reopen #7915", text)
        self.assertNotEqual(text, sibling)
        self.assertNotEqual(Path(__file__).read_text(encoding="utf-8"), sibling_test)
        self.assertNotIn("buy.stripe.com", text)
        self.assertNotIn("33723638501", text.split("KEEP unread", 1)[0])

    def test_fix_first_packet_is_external_blocker(self) -> None:
        packet = {
            "outcome": "external_blocker",
            "observed_broken": True,
            "finding_kind": "behavior",
            "expected_contract": (
                "open-door-guard.yml job reject-added-locks executes "
                "python3 open_door_guard.py --diff BASE HEAD then "
                "python3 test_open_door_guard.py on pull_request and push to main"
            ),
            "repair_attempts": [
                "local open_door_guard.py --diff 0c87db15 178602e3 PASS",
                "local test_open_door_guard.py PASS",
                "adjacent test_open_door rc=0 OPEN / test_path_manifest 9 / test_fix_first 6 / test_source_parses 9 / test_merge_on_pr 6",
                "github.com/settings/billing 404; users/woahwhattheheck/settings/billing/actions 403; rerun_failed_jobs 201; attempt 2 runner_id=0 job 100549755121",
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
