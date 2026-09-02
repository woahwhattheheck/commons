#!/usr/bin/env python3
"""Pin unique leftover for tests run 33689281316. Do not remint prior leftovers or tests.yml."""

from __future__ import annotations

import subprocess
import unittest
from pathlib import Path

import fix_first
import open_door_guard as guard

ROOT = Path(__file__).resolve().parent
RECEIPT = ROOT / "p/grokbuild-tests-33689281316-billing-lock-20260902-01.md"
PRIOR_VERIFY = ROOT / "p/grokbuild-pr8411-verify-20260902-01.md"
PRIOR_LLMS = ROOT / "p/grok-build-llms-txt-33687829181-billing-lock-20260902-01.md"
WORKFLOW = ROOT / ".github/workflows/tests.yml"

KEEP = {
    ".github/workflows/tests.yml": "8c2f2301",
    "p/grokbuild-pr8411-verify-20260902-01.md": "642dea64",
    "test_grokbuild_pr8411_verify.py": "361f5ca1",
    "p/grok-build-llms-txt-33687829181-billing-lock-20260902-01.md": "3183564c",
    "test_grokbuild_llms_txt_33687829181_billing_lock.py": "e02e5ab5",
    "p/grokbuild-open-door-guard-33687124472-billing-lock-20260902-01.md": "b91a85d3",
    "p/grok-build-discord-cloud-billing-lock-20260902-01.md": "2e0bfbfb",
    "p/grok-build-local-compute-guard-billing-lock-20260902-01.md": "de59bf75",
    "p/grok-resources-tab-freshness-billing-lock-20260902-01.md": "ac39fe78",
    "open_door_guard.py": "4b053e43",
    "fix_first.py": "a57aee1c",
}


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class TestGrokbuildTests33689281316BillingLock(unittest.TestCase):
    def test_keep_workflow_and_prior_leftovers_unread(self) -> None:
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
        self.assertNotIn("billing", yml.lower())
        self.assertNotIn("if: false", yml)

    def test_receipt_is_unique_and_does_not_remint(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        prior = PRIOR_VERIFY.read_text(encoding="utf-8")
        llms = PRIOR_LLMS.read_text(encoding="utf-8")
        self.assertIn("grokbuild-tests-33689281316-billing-lock-20260902-01", text)
        self.assertIn(
            "woahwhattheheck/commons:tests:81e8f9ccc7293bf6e5179e615ba460d87f409eb0:battery",
            text,
        )
        self.assertIn("33689281316", text)
        self.assertIn("100444021767", text)
        self.assertIn("100446187730", text)
        self.assertIn(
            "The job was not started because your account is locked due to a billing issue.",
            text,
        )
        self.assertIn("EXTERNAL_BLOCKER", text)
        self.assertIn("Did not remint leftover grokbuild-pr8411-verify-20260902-01", text)
        self.assertIn("642dea64", text)
        self.assertIn("3183564c", text)
        self.assertIn("8c2f2301", text)
        self.assertIn("did not reopen #7915", text.lower())
        self.assertNotEqual(text, prior)
        self.assertNotEqual(text, llms)
        self.assertNotIn(
            "woahwhattheheck/commons:tests:81e8f9ccc7293bf6e5179e615ba460d87f409eb0:battery",
            prior,
        )
        self.assertNotIn("33689281316", prior)
        self.assertNotIn("33689281316", llms)

    def test_fix_first_packet_is_external_blocker(self) -> None:
        packet = {
            "outcome": "external_blocker",
            "observed_broken": True,
            "finding_kind": "behavior",
            "expected_contract": (
                "tests.yml job battery executes the discovered root test_*.py / "
                "test_*.js plus infra test_*.py on push to main"
            ),
            "repair_attempts": [
                "inspected tests.yml: valid battery, no skip",
                "local test_grokbuild_pr8411_verify.py 2/2",
                "local test_open_door_guard.py PASS",
                "local test_path_manifest.py 9/9",
                "local test_fix_first.py 6/6",
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

    def test_open_door_guard_accepts_this_leftover(self) -> None:
        added = [
            guard.AddedLine("test_grokbuild_tests_33689281316_billing_lock.py", 1, line)
            for line in Path(__file__).read_text(encoding="utf-8").splitlines()
        ]
        added.extend(
            guard.AddedLine("p/grokbuild-tests-33689281316-billing-lock-20260902-01.md", 1, line)
            for line in RECEIPT.read_text(encoding="utf-8").splitlines()
        )
        self.assertEqual(guard.scan_added(added), [])


if __name__ == "__main__":
    unittest.main()
