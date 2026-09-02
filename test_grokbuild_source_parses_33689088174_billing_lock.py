#!/usr/bin/env python3
"""Pin unique leftover for source-parses run 33689088174. Do not remint parser or prior leftovers."""

from __future__ import annotations

import subprocess
import unittest
from pathlib import Path

import fix_first

ROOT = Path(__file__).resolve().parent
RECEIPT = ROOT / "p/grokbuild-source-parses-33689088174-billing-lock-20260902-01.md"
LLMS = ROOT / "p/grok-build-llms-txt-33687829181-billing-lock-20260902-01.md"
GUARD = ROOT / "p/grokbuild-open-door-guard-33687124472-billing-lock-20260902-01.md"
WORKFLOW = ROOT / ".github/workflows/source-parses.yml"

KEEP = {
    "source_parses.py": "abba903d",
    "test_source_parses.py": "595e543c",
    ".github/workflows/source-parses.yml": "9b4be350",
    "p/grok-build-llms-txt-33687829181-billing-lock-20260902-01.md": "3183564c",
    "p/grokbuild-open-door-guard-33687124472-billing-lock-20260902-01.md": "b91a85d3",
    "p/grok-build-llms-txt-billing-lock-20260902-01.md": "cf9c9f40",
    "p/grok-build-discord-cloud-billing-lock-20260902-01.md": "2e0bfbfb",
    "p/grok-build-local-compute-guard-billing-lock-20260902-01.md": "de59bf75",
    "p/grok-resources-tab-freshness-billing-lock-20260902-01.md": "ac39fe78",
    "p/cursor-merge-on-pr-readback-20260902-01.md": "e160b2c3",
    "test_cursor_merge_on_pr_readback.py": "a90bb2ff",
    "test_grokbuild_open_door_guard_33687124472_billing_lock.py": "e6a826cf",
    "test_grokbuild_llms_txt_33687829181_billing_lock.py": "e02e5ab5",
    "open_door_guard.py": "4b053e43",
    "p/grok-build-llms-txt-33689096471-billing-lock-20260902-01.md": "e739b9cd",
    "test_grokbuild_llms_txt_33689096471_billing_lock.py": "862e61d2",
    "p/grokbuild-pr-collision-notice-33689085107-billing-lock-20260902-01.md": "594b5e71",
    "p/grokbuild-pr8414-verify-20260902-01.md": "587cc1cf",
    "test_grokbuild_pr8414_verify.py": "93fd9808",
}


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class TestGrokbuildSourceParses33689088174BillingLock(unittest.TestCase):
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
        llms = LLMS.read_text(encoding="utf-8")
        guard = GUARD.read_text(encoding="utf-8")
        self.assertIn("grokbuild-source-parses-33689088174-billing-lock-20260902-01", text)
        self.assertIn(
            "woahwhattheheck/commons:source-parses:0675fb559de118427a4c37b3cc406fc9f4cc7b64:parse",
            text,
        )
        self.assertIn("33689088174", text)
        self.assertIn("100443430387", text)
        self.assertIn("0675fb559de118427a4c37b3cc406fc9f4cc7b64", text)
        self.assertIn("920d8c03a247d6b1ee640b523ef9447dfe4c7477", text)
        self.assertIn("https://github.com/woahwhattheheck/commons/pull/8414", text)
        self.assertIn(
            "The job was not started because your account is locked due to a billing issue.",
            text,
        )
        self.assertIn("EXTERNAL_BLOCKER", text)
        self.assertIn("abba903d", text)
        self.assertIn("595e543c", text)
        self.assertIn("9b4be350", text)
        self.assertIn("3183564c", text)
        self.assertIn("b91a85d3", text)
        self.assertIn("e160b2c3", text)
        self.assertIn("e739b9cd", text)
        self.assertIn("587cc1cf", text)
        self.assertIn("Did not remint leftover `22b63e25`", text)
        self.assertIn("Did not reopen #7915", text)
        self.assertIn("source parses: 2744 files, all readable", text)
        self.assertNotEqual(text, llms)
        self.assertNotEqual(text, guard)
        self.assertNotIn(
            "source-parses:0675fb559de118427a4c37b3cc406fc9f4cc7b64:parse",
            llms,
        )
        self.assertNotIn(
            "source-parses:0675fb559de118427a4c37b3cc406fc9f4cc7b64:parse",
            guard,
        )

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
                "local source_parses.py rc=0 2744 files all readable",
                "inspected source-parses.yml valid parse job no YAML defect",
                "job logs 404 BlobNotFound runner_id=0 steps=[] billing lock annotation",
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
