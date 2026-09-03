#!/usr/bin/env python3
"""Pin unique leftover for leftover-id-census run 33723043828. Do not remint peers."""

from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path

import fix_first
import open_door_guard as guard

ROOT = Path(__file__).resolve().parent
RECEIPT = ROOT / "p/grokbuild-leftover-id-census-33723043828-billing-lock-20260903-01.md"
SIBLING = ROOT / "p/grok-build-repo-pulse-billing-lock-20260903-01.md"
WORKFLOW = ROOT / ".github/workflows/leftover-id-census.yml"
CENSUS = ROOT / "host/leftover_id_census.py"

KEEP = {
    ".github/workflows/leftover-id-census.yml": "cd2ac955",
    "host/leftover_id_census.py": "1cfba147",
    "test_work_becomes_automation.py": "2a0c4e51",
    "leftover-census.md": "b02dc321",
    "leftover-census.json": "32d3ee6b",
    "ground/WORK_AUTOMATION.json": "dca944cb",
    "ping/union_git_ntfy.py": "ffd3617b",
    "p/work-becomes-automation-20260830-01.md": "c0ab7d78",
    "open_door_guard.py": "4b053e43",
    "p/grok-build-repo-pulse-billing-lock-20260903-01.md": "b6e5953c",
    "p/grokbuild-tests-33717741059-billing-lock-20260903-01.md": "1b6c3021",
    "p/grokbuild-harness-wakeup-33717474657-billing-lock-20260903-01.md": "f54e1846",
}


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class TestGrokbuildLeftoverIdCensus33723043828BillingLock(unittest.TestCase):
    def test_keep_peer_leftovers_and_census_yml_unread(self) -> None:
        for rel, prefix in KEEP.items():
            blob = git_blob(rel)
            self.assertTrue(
                blob.startswith(prefix),
                f"{rel} reminted: want {prefix} got {blob[:8]}",
            )
        yml = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("name: leftover-id-census", yml)
        self.assertIn("regenerate-or-alarm", yml)
        self.assertIn("host/leftover_id_census.py --regenerate-or-alarm", yml)
        self.assertIn("host/leftover_id_census.py --check", yml)
        self.assertNotIn("continue-on-error", yml)
        self.assertNotIn("if: false", yml)
        self.assertNotIn("billing", yml.lower())

    def test_local_failed_step_still_passes(self) -> None:
        unit = subprocess.run(
            ["python3", "test_work_becomes_automation.py"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(unit.returncode, 0, msg=unit.stdout + unit.stderr)
        check = subprocess.run(
            [
                "python3",
                str(CENSUS),
                "--check",
                "--sha",
                "35ac733fbcf265852bc04e6400ef308a5b82104b",
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(check.returncode, 0, msg=check.stdout + check.stderr)
        payload = json.loads(check.stdout)
        self.assertEqual(payload["state"], "FRESH")
        self.assertEqual(payload["counts"]["present"], 6)
        self.assertEqual(payload["counts"]["missing"], 0)
        self.assertEqual(payload["counts"]["unverified"], 0)
        self.assertEqual(
            payload["digest"],
            "cd0058e73577ca7b364d884e54dc1fbc416f81258c19acb14ba6fd7e92927158",
        )
        added = [
            guard.AddedLine(
                "test_grokbuild_leftover_id_census_33723043828_billing_lock.py",
                1,
                line,
            )
            for line in Path(__file__).read_text(encoding="utf-8").splitlines()
        ]
        added.extend(
            guard.AddedLine(
                "p/grokbuild-leftover-id-census-33723043828-billing-lock-20260903-01.md",
                1,
                line,
            )
            for line in RECEIPT.read_text(encoding="utf-8").splitlines()
        )
        self.assertEqual(guard.scan_added(added), [])

    def test_receipt_cites_run_and_does_not_steal(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        sibling = SIBLING.read_text(encoding="utf-8")
        self.assertIn(
            "grokbuild-leftover-id-census-33723043828-billing-lock-20260903-01",
            text,
        )
        self.assertIn(
            "woahwhattheheck/commons:leftover-id-census:35ac733fbcf265852bc04e6400ef308a5b82104b:regenerate-or-alarm",
            text,
        )
        self.assertIn("33723043828", text)
        self.assertIn("100546023488", text)
        self.assertIn("35ac733fbcf265852bc04e6400ef308a5b82104b", text)
        self.assertIn(
            "The job was not started because your account is locked due to a billing issue.",
            text,
        )
        self.assertIn("EXTERNAL_BLOCKER", text)
        self.assertIn("cd2ac955", text)
        self.assertIn("1cfba147", text)
        self.assertIn("2a0c4e51", text)
        self.assertIn("b02dc321", text)
        self.assertIn("32d3ee6b", text)
        self.assertIn("dca944cb", text)
        self.assertIn("ffd3617b", text)
        self.assertIn("c0ab7d78", text)
        self.assertIn("4b053e43", text)
        self.assertIn("b6e5953c", text)
        self.assertIn("1b6c3021", text)
        self.assertIn("f54e1846", text)
        self.assertIn("Did not remint leftover grok-build-repo-pulse-billing-lock-20260903-01", text)
        self.assertIn("Did not reopen #7915", text)
        self.assertNotEqual(text, sibling)
        self.assertNotIn(
            "leftover-id-census:35ac733fbcf265852bc04e6400ef308a5b82104b:regenerate-or-alarm",
            sibling,
        )
        self.assertIn("33723065167", sibling)

    def test_fix_first_packet_is_external_blocker(self) -> None:
        packet = {
            "outcome": "external_blocker",
            "observed_broken": True,
            "finding_kind": "behavior",
            "expected_contract": (
                "leftover-id-census.yml job regenerate-or-alarm checks out main, "
                "runs test_work_becomes_automation.py, then leftover_id_census.py "
                "--regenerate-or-alarm and --check on schedule"
            ),
            "repair_attempts": [
                "inspected leftover-id-census.yml KEEP cd2ac955; no YAML defect, no billing skip",
                "local test_work_becomes_automation.py 11/11 PASS",
                "leftover_id_census.py --check FRESH digest cd0058e7 present=6",
                "--regenerate-or-alarm rc=0 stamp unchanged",
                "open_door_guard PASS; annotation job 100546023488 billing lock; runner_id=0 steps=[] logs 404",
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
