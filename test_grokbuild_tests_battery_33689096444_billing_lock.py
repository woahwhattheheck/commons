#!/usr/bin/env python3
"""Pin unique leftover for tests battery run 33689096444. Do not remint peers."""

from __future__ import annotations

import subprocess
import unittest
from pathlib import Path

import fix_first
import open_door_guard as guard

ROOT = Path(__file__).resolve().parent
RECEIPT = ROOT / "p/grokbuild-tests-battery-33689096444-billing-lock-20260902-01.md"
SIBLING = ROOT / "p/grokbuild-open-door-guard-33687124472-billing-lock-20260902-01.md"
LEFTOVER = ROOT / "p/cursor-merge-on-pr-20260902-01.md"
READBACK = ROOT / "p/cursor-merge-on-pr-readback-20260902-01.md"
WORKFLOW = ROOT / ".github/workflows/tests.yml"

KEEP = {
    ".github/workflows/tests.yml": "8c2f2301",
    "test_cursor_merge_on_pr_readback.py": "a90bb2ff",
    "p/cursor-merge-on-pr-readback-20260902-01.md": "e160b2c3",
    "p/cursor-merge-on-pr-20260902-01.md": "22b63e25",
    "host/merge_on_pr.py": "0270094d",
    "test_merge_on_pr.py": "8224c8cd",
    "host/sprint_integration.py": "b7bec0b9",
    "p/grokbuild-tests-33689281316-billing-lock-20260902-01.md": "3db0ab2e",
    "p/grokbuild-open-door-guard-33687124472-billing-lock-20260902-01.md": "b91a85d3",
    "p/grokbuild-open-door-guard-33689243568-billing-lock-20260902-01.md": "4ab677c5",
    "p/grok-build-llms-txt-33687829181-billing-lock-20260902-01.md": "3183564c",
    "p/grok-build-discord-cloud-billing-lock-20260902-01.md": "2e0bfbfb",
    "p/grok-build-local-compute-guard-billing-lock-20260902-01.md": "de59bf75",
    "p/grok-resources-tab-freshness-billing-lock-20260902-01.md": "ac39fe78",
    "p/grok-build-llms-txt-billing-lock-20260902-01.md": "cf9c9f40",
    "open_door_guard.py": "4b053e43",
    "p/cursor-stealable-lanes-occupancy-20260902-01.md": "9631e869",
}


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class TestGrokbuildTestsBattery33689096444BillingLock(unittest.TestCase):
    def test_keep_workflow_leftover_and_siblings_unread(self) -> None:
        for rel, prefix in KEEP.items():
            blob = git_blob(rel)
            self.assertTrue(
                blob.startswith(prefix),
                f"{rel} reminted: want {prefix} got {blob[:8]}",
            )
        yml = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("the whole battery, one failure fails the run", yml)
        self.assertIn("runs-on: ubuntu-latest", yml)
        self.assertIn("find . -maxdepth 1 -type f -name 'test_*.py'", yml)
        self.assertNotIn("if: false", yml)

    def test_local_failed_step_contract_still_passes(self) -> None:
        # Live GitHub PR #7915 MATCH is FINDER-FAILED on HTTP 403. That is a
        # measurement, not a remint. Pin the local leftover contract instead.
        local = [
            "test_cursor_merge_on_pr_readback.TestCursorMergeOnPrReadback.test_keep_leftover_sprint_qualify_and_unread_packs",
            "test_cursor_merge_on_pr_readback.TestCursorMergeOnPrReadback.test_leftover_json_still_renders_without_reopening_7915",
            "test_cursor_merge_on_pr_readback.TestCursorMergeOnPrReadback.test_leftover_reopen_merge_worktree_refused",
            "test_cursor_merge_on_pr_readback.TestCursorMergeOnPrReadback.test_leftover_tests_still_pass",
            "test_cursor_merge_on_pr_readback.TestCursorMergeOnPrReadback.test_readback_receipt_exists_and_does_not_steal",
        ]
        proc = subprocess.run(
            ["python3", "-m", "unittest", *local],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
        self.assertIn("Ran 5 tests", proc.stderr)
        added = [
            guard.AddedLine(
                "test_grokbuild_tests_battery_33689096444_billing_lock.py", 1, line
            )
            for line in Path(__file__).read_text(encoding="utf-8").splitlines()
        ]
        self.assertEqual(guard.scan_added(added), [])

    def test_receipt_cites_run_and_does_not_steal(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        sibling = SIBLING.read_text(encoding="utf-8")
        leftover = LEFTOVER.read_text(encoding="utf-8")
        readback = READBACK.read_text(encoding="utf-8")
        self.assertIn(
            "grokbuild-tests-battery-33689096444-billing-lock-20260902-01", text
        )
        self.assertIn(
            "woahwhattheheck/commons:tests:920d8c03a247d6b1ee640b523ef9447dfe4c7477:battery",
            text,
        )
        self.assertIn("33689096444", text)
        self.assertIn("100443449694", text)
        self.assertIn("100446361869", text)
        self.assertIn("920d8c03a247d6b1ee640b523ef9447dfe4c7477", text)
        self.assertIn(
            "The job was not started because your account is locked due to a billing issue.",
            text,
        )
        self.assertIn("EXTERNAL_BLOCKER", text)
        self.assertIn("8c2f2301", text)
        self.assertIn("a90bb2ff", text)
        self.assertIn("22b63e25", text)
        self.assertIn("Did not remint those", text)
        self.assertIn("Did not unique-pack merge-on-PR leftover", text)
        self.assertIn("Did not reopen #7915", text)
        self.assertNotEqual(text, sibling)
        self.assertNotEqual(text, leftover)
        self.assertNotEqual(text, readback)
        self.assertNotIn("buy.stripe.com", text)
        self.assertNotIn(
            "woahwhattheheck/commons:tests:920d8c03a247d6b1ee640b523ef9447dfe4c7477:battery",
            sibling,
        )

    def test_fix_first_packet_is_external_blocker(self) -> None:
        packet = {
            "outcome": "external_blocker",
            "observed_broken": True,
            "finding_kind": "behavior",
            "expected_contract": (
                "tests.yml job battery checks out the repo then runs every "
                "discovered root test_*.py / test_*.js plus infra test_*.py "
                "on push to main that touches the path filter"
            ),
            "repair_attempts": [
                "inspected tests.yml battery glob; no YAML defect",
                "local leftover KEEP/json/refuse/tests/receipt 5/5 OK",
                "live PR7915 MATCH FINDER-FAILED http 403 (measurement, not remint)",
                "local test_merge_on_pr.py 6/6 OK",
                "open_door_guard PASS; test_fix_first.py 6/6",
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
