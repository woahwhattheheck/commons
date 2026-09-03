#!/usr/bin/env python3
"""Pin unique leftover for source-parses run 33699928032. Do not remint parser or prior leftovers."""

from __future__ import annotations

import subprocess
import unittest
from pathlib import Path

import fix_first
import open_door_guard as guard

ROOT = Path(__file__).resolve().parent
RECEIPT = ROOT / "p/grokbuild-source-parses-33699928032-billing-lock-20260903-01.md"
SIBLING = ROOT / "p/grokbuild-source-parses-33689088174-billing-lock-20260902-01.md"
SIBLING_TEST = ROOT / "test_grokbuild_source_parses_33689088174_billing_lock.py"
TRIGGER = ROOT / "p/grokbuild-open-door-guard-33699286785-billing-lock-20260902-01.md"
WORKFLOW = ROOT / ".github/workflows/source-parses.yml"

KEEP = {
    "source_parses.py": "abba903d",
    "test_source_parses.py": "595e543c",
    ".github/workflows/source-parses.yml": "9b4be350",
    "p/grokbuild-source-parses-33689088174-billing-lock-20260902-01.md": "3b13ac02",
    "test_grokbuild_source_parses_33689088174_billing_lock.py": "6f8644b4",
    "p/grokbuild-open-door-guard-33699286785-billing-lock-20260902-01.md": "d22e0707",
    "test_grokbuild_open_door_guard_33699286785_billing_lock.py": "96ce49fa",
    "open_door_guard.py": "4b053e43",
}


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class TestGrokbuildSourceParses33699928032BillingLock(unittest.TestCase):
    def test_keep_parser_and_prior_leftovers_unread(self) -> None:
        for rel, prefix in KEEP.items():
            blob = git_blob(rel)
            self.assertTrue(
                blob.startswith(prefix),
                f"{rel} reminted: want {prefix} got {blob[:8]}",
            )
        yml = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("python3 -m unittest -v test_source_parses.py", yml)
        self.assertIn("python3 source_parses.py", yml)
        self.assertNotIn("if: false", yml)
        self.assertNotIn("billing", yml.lower())

    def test_receipt_is_unique_and_does_not_remint(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        sibling = SIBLING.read_text(encoding="utf-8")
        sibling_test = SIBLING_TEST.read_text(encoding="utf-8")
        trigger = TRIGGER.read_text(encoding="utf-8")
        self.assertIn("grokbuild-source-parses-33699928032-billing-lock-20260903-01", text)
        self.assertIn(
            "woahwhattheheck/commons:source-parses:9f8c2487104f0bfce331eb89b2499aee3b95170f:parse",
            text,
        )
        self.assertIn("33699928032", text)
        self.assertIn("100476821979", text)
        self.assertIn("9f8c2487104f0bfce331eb89b2499aee3b95170f", text)
        self.assertIn("60d5e8fa13824c88d42138a39a9629d41818e4e6", text)
        self.assertIn("https://github.com/woahwhattheheck/commons/pull/8527", text)
        self.assertIn(
            "The job was not started because your account is locked due to a billing issue.",
            text,
        )
        self.assertIn("EXTERNAL_BLOCKER", text)
        self.assertIn("abba903d", text)
        self.assertIn("595e543c", text)
        self.assertIn("9b4be350", text)
        self.assertIn("3b13ac02", text)
        self.assertIn("d22e0707", text)
        self.assertIn("Did not remint leftover `22b63e25`", text)
        self.assertIn("Did not reopen #7915", text)
        self.assertIn("source parses: 2860 files, all readable", text)
        self.assertNotEqual(text, sibling)
        self.assertNotEqual(Path(__file__).read_text(encoding="utf-8"), sibling_test)
        self.assertNotEqual(text, trigger)
        self.assertNotIn(
            "source-parses:9f8c2487104f0bfce331eb89b2499aee3b95170f:parse",
            sibling,
        )
        self.assertNotIn(
            "source-parses:9f8c2487104f0bfce331eb89b2499aee3b95170f:parse",
            trigger,
        )
        self.assertNotIn("33689088174", text.split("KEEP unread", 1)[0])
        self.assertNotIn("buy.stripe.com", text)
        added = [
            guard.AddedLine(
                "test_grokbuild_source_parses_33699928032_billing_lock.py", 1, line
            )
            for line in Path(__file__).read_text(encoding="utf-8").splitlines()
        ]
        self.assertEqual(guard.scan_added(added), [])

    def test_local_source_parses_contract_still_green(self) -> None:
        checker = subprocess.run(
            ["python3", "-m", "unittest", "-v", "test_source_parses.py"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(checker.returncode, 0, msg=checker.stdout + checker.stderr)
        self.assertIn("Ran 9 tests", checker.stderr + checker.stdout)
        parse = subprocess.run(
            ["python3", "source_parses.py"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(parse.returncode, 0, msg=parse.stdout + parse.stderr)
        combined = parse.stdout + parse.stderr
        self.assertRegex(combined, r"source parses: \d+ files, all readable")

    def test_fix_first_packet_is_external_blocker(self) -> None:
        packet = {
            "outcome": "external_blocker",
            "observed_broken": True,
            "finding_kind": "behavior",
            "expected_contract": (
                "source-parses.yml job parse executes "
                "python3 -m unittest -v test_source_parses.py then "
                "python3 source_parses.py on pull_request"
            ),
            "repair_attempts": [
                "local test_source_parses.py 9/9 OK",
                "local source_parses.py rc=0 2860 files all readable",
                "inspected source-parses.yml valid parse job no YAML defect",
                "job logs 404 BlobNotFound runner_id=0 steps=[] billing lock annotation",
                "github billing APIs 404/403; githubstatus Actions operational",
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
