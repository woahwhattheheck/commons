#!/usr/bin/env python3
"""Pin unique leftover for source-parses run 33717733998. Do not remint parser or prior leftovers."""

from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path

import fix_first
import open_door_guard as guard

ROOT = Path(__file__).resolve().parent
RECEIPT = ROOT / "p/grokbuild-source-parses-33717733998-billing-lock-20260903-01.md"
PRIOR = ROOT / "p/grokbuild-source-parses-33699980140-billing-lock-20260903-01.md"
TRIGGER = ROOT / "p/grokbuild-main-range-verify-33717084528-billing-lock-20260903-01.md"
WORKFLOW = ROOT / ".github/workflows/source-parses.yml"

KEEP = {
    "source_parses.py": "abba903d",
    "test_source_parses.py": "595e543c",
    ".github/workflows/source-parses.yml": "9b4be350",
    "p/grokbuild-source-parses-33699980140-billing-lock-20260903-01.md": "2494f79a",
    "test_grokbuild_source_parses_33699980140_billing_lock.py": "69ea9b3a",
    "p/grokbuild-main-range-verify-33717084528-billing-lock-20260903-01.md": "2b0fd9c9",
    "test_grokbuild_main_range_verify_33717084528_billing_lock.py": "3e89a404",
    "open_door_guard.py": "4b053e43",
}


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class TestGrokbuildSourceParses33717733998BillingLock(unittest.TestCase):
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
        self.assertNotIn("continue-on-error: true", yml)
        self.assertNotIn("billing", yml.lower())
        self.assertIn("runs-on: ubuntu-latest", yml)

    def test_receipt_is_unique_and_does_not_remint(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        prior = PRIOR.read_text(encoding="utf-8")
        trigger = TRIGGER.read_text(encoding="utf-8")
        self.assertIn("grokbuild-source-parses-33717733998-billing-lock-20260903-01", text)
        self.assertIn(
            "woahwhattheheck/commons:source-parses:2890fde44250063aa66ef60735a7cc90407760a6:parse",
            text,
        )
        self.assertIn("33717733998", text)
        self.assertIn("100530342689", text)
        self.assertIn("100532245293", text)
        self.assertIn("2890fde44250063aa66ef60735a7cc90407760a6", text)
        self.assertIn("0ddbdaf51fee6870caf1572ff53db1293852b72b", text)
        self.assertIn("https://github.com/woahwhattheheck/commons/pull/8583", text)
        self.assertIn(
            "The job was not started because your account is locked due to a billing issue.",
            text,
        )
        self.assertIn("state: EXTERNAL_BLOCKER", text)
        self.assertIn("abba903d", text)
        self.assertIn("595e543c", text)
        self.assertIn("9b4be350", text)
        self.assertIn("2494f79a", text)
        self.assertIn("69ea9b3a", text)
        self.assertIn("2b0fd9c9", text)
        self.assertIn("3e89a404", text)
        self.assertIn("4b053e43", text)
        self.assertIn("Did not remint leftover `22b63e25`", text)
        self.assertIn("Did not remint leftover `3b13ac02`", text)
        self.assertIn("Did not reopen #7915", text)
        self.assertIn("Did not reopen #8558", text)
        self.assertIn("Did not reopen #8583", text)
        self.assertIn("source parses: 2905 files, all readable", text)
        self.assertIn("No fake green", text)
        self.assertNotEqual(text, prior)
        self.assertNotEqual(text, trigger)
        self.assertNotIn("33717733998", prior)
        self.assertNotIn(
            "source-parses:2890fde44250063aa66ef60735a7cc90407760a6:parse",
            prior,
        )
        self.assertNotIn(
            "source-parses:2890fde44250063aa66ef60735a7cc90407760a6:parse",
            trigger,
        )
        self.assertNotIn("buy.stripe.com", text)

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

    def test_open_door_guard_and_fix_first_external_blocker(self) -> None:
        added = [
            guard.AddedLine(str(RECEIPT.relative_to(ROOT)), i + 1, line)
            for i, line in enumerate(RECEIPT.read_text(encoding="utf-8").splitlines())
        ]
        added.extend(
            guard.AddedLine(str(Path(__file__).relative_to(ROOT)), i + 1, line)
            for i, line in enumerate(Path(__file__).read_text(encoding="utf-8").splitlines())
        )
        self.assertEqual(guard.scan_added(added), [])
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
                "inspected source-parses.yml blob 9b4be350 valid parse job no YAML defect",
                "local test_source_parses.py 9/9 OK",
                "local source_parses.py rc=0 2905 files all readable",
                "job logs 404 BlobNotFound runner_id=0 steps=[] billing lock annotation",
                "github rerun_failed_jobs 201",
                "attempt 2 job 100532245293 same billing lock",
            ],
            "blocker": (
                "GitHub Actions ubuntu-latest never assigned: "
                "The job was not started because your account is locked due to a billing issue."
            ),
            "report_only_sessions": 0,
            "unconsumed_findings": 0,
        }
        self.assertEqual(fix_first.validate(packet)["state"], "EXTERNAL_BLOCKER")
        proc = subprocess.run(
            ["python3", "fix_first.py", "--json", json.dumps(packet)],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
        self.assertIn("EXTERNAL_BLOCKER", proc.stdout)


if __name__ == "__main__":
    unittest.main()
