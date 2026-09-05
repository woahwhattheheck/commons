#!/usr/bin/env python3
"""Pin unique leftover for open-door-guard run 33723902241. Do not remint the guard."""

from __future__ import annotations

import subprocess
import unittest
from pathlib import Path

import fix_first
import open_door_guard as guard

ROOT = Path(__file__).resolve().parent
RECEIPT = ROOT / "p/grokbuild-open-door-guard-33723902241-billing-lock-20260903-01.md"
SIBLING = ROOT / "p/grokbuild-open-door-guard-33718116356-billing-lock-20260903-01.md"
SIBLING_TEST = ROOT / "test_grokbuild_open_door_guard_33718116356_billing_lock.py"
TRIGGER = ROOT / "p/grokbuild-leftover-id-census-33723043828-billing-lock-20260903-01.md"
TRIGGER_TEST = ROOT / "test_grokbuild_leftover_id_census_33723043828_billing_lock.py"

KEEP = {
    "open_door_guard.py": "4b053e43",
    "test_open_door_guard.py": "70ee5730",
    ".github/workflows/open-door-guard.yml": "6586644c",
    "p/grokbuild-open-door-guard-33718116356-billing-lock-20260903-01.md": "25781cf5",
    "test_grokbuild_open_door_guard_33718116356_billing_lock.py": "1c3a8da3",
    "p/grokbuild-open-door-guard-33717741083-billing-lock-20260903-01.md": "d4c58153",
    "test_grokbuild_open_door_guard_33717741083_billing_lock.py": "fb68099e",
    "p/grokbuild-leftover-id-census-33723043828-billing-lock-20260903-01.md": "e135862e",
    "test_grokbuild_leftover_id_census_33723043828_billing_lock.py": "3f77dce1",
}


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class TestGrokbuildOpenDoorGuard33723902241BillingLock(unittest.TestCase):
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
                "test_grokbuild_open_door_guard_33723902241_billing_lock.py", 1, line
            )
            for line in Path(__file__).read_text(encoding="utf-8").splitlines()
        ]
        self.assertEqual(guard.scan_added(added), [])
        receipt_added = [
            guard.AddedLine(
                "p/grokbuild-open-door-guard-33723902241-billing-lock-20260903-01.md",
                1,
                line,
            )
            for line in RECEIPT.read_text(encoding="utf-8").splitlines()
        ]
        self.assertEqual(guard.scan_added(receipt_added), [])
        trigger_added = [
            guard.AddedLine(
                "p/grokbuild-leftover-id-census-33723043828-billing-lock-20260903-01.md",
                1,
                line,
            )
            for line in TRIGGER.read_text(encoding="utf-8").splitlines()
        ]
        self.assertEqual(guard.scan_added(trigger_added), [])
        trigger_test_added = [
            guard.AddedLine(
                "test_grokbuild_leftover_id_census_33723043828_billing_lock.py", 1, line
            )
            for line in TRIGGER_TEST.read_text(encoding="utf-8").splitlines()
        ]
        self.assertEqual(guard.scan_added(trigger_test_added), [])

    def test_receipt_cites_this_run_and_does_not_steal(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        sibling = SIBLING.read_text(encoding="utf-8")
        sibling_test = SIBLING_TEST.read_text(encoding="utf-8")
        self.assertIn("grokbuild-open-door-guard-33723902241-billing-lock-20260903-01", text)
        self.assertIn(
            "woahwhattheheck/commons:open-door-guard:ee095dbb6fe94772503c5d1171fc79f5559b26f1:reject-added-locks",
            text,
        )
        self.assertIn("33723902241", text)
        self.assertIn("ee095dbb6fe94772503c5d1171fc79f5559b26f1", text)
        self.assertIn("100548587195", text)
        self.assertIn("100550023602", text)
        self.assertIn(
            "The job was not started because your account is locked due to a billing issue.",
            text,
        )
        self.assertIn("EXTERNAL_BLOCKER", text)
        self.assertIn("4b053e43", text)
        self.assertIn("70ee5730", text)
        self.assertIn("25781cf5", text)
        self.assertIn("e135862e", text)
        self.assertIn("Did not remint", text)
        self.assertIn("Did not reopen #7915", text)
        self.assertNotEqual(text, sibling)
        self.assertNotEqual(Path(__file__).read_text(encoding="utf-8"), sibling_test)
        self.assertNotIn("buy.stripe.com", text)
        self.assertNotIn("33718116356", text.split("KEEP unread", 1)[0])

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
                "local open_door_guard.py --diff f0a98005 ee095dbb PASS",
                "local test_open_door_guard.py PASS",
                "adjacent test_open_door rc=0 OPEN / test_path_manifest 9 / test_fix_first 6 / test_source_parses 9 / test_merge_on_pr 6",
                "github.com/settings/billing 404; users/woahwhattheheck/settings/billing/actions 403; rerun_failed_jobs 201; attempt 2 runner_id=0 job 100550023602",
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
