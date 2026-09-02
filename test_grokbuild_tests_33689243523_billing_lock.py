#!/usr/bin/env python3
"""Pin unique leftover for tests battery run 33689243523. Do not remint PR 8411 leftover."""

from __future__ import annotations

import subprocess
import unittest
from pathlib import Path

import fix_first
import open_door_guard as guard

ROOT = Path(__file__).resolve().parent
RECEIPT = ROOT / "p/grokbuild-tests-33689243523-billing-lock-20260902-01.md"
PRIOR = ROOT / "p/grokbuild-pr8411-verify-20260902-01.md"
LLMS = ROOT / "p/grok-build-llms-txt-33687829181-billing-lock-20260902-01.md"
SIBLING = ROOT / "p/grokbuild-open-door-guard-33689243568-billing-lock-20260902-01.md"
WORKFLOW = ROOT / ".github/workflows/tests.yml"

KEEP = {
    "p/grokbuild-pr8411-verify-20260902-01.md": "642dea64",
    "test_grokbuild_pr8411_verify.py": "361f5ca1",
    "p/grok-build-llms-txt-33687829181-billing-lock-20260902-01.md": "3183564c",
    "test_grokbuild_llms_txt_33687829181_billing_lock.py": "e02e5ab5",
    "p/grok-build-llms-txt-billing-lock-20260902-01.md": "cf9c9f40",
    "p/grokbuild-pr8413-terminal-20260902-01.md": "bca13858",
    ".github/workflows/tests.yml": "8c2f2301",
    "open_door_guard.py": "4b053e43",
    "test_open_door_guard.py": "70ee5730",
    "p/grokbuild-open-door-guard-33687124472-billing-lock-20260902-01.md": "b91a85d3",
    "p/grokbuild-open-door-guard-33689243568-billing-lock-20260902-01.md": "4ab677c5",
    "test_grokbuild_open_door_guard_33689243568_billing_lock.py": "0ec1378d",
    "p/grok-build-discord-cloud-billing-lock-20260902-01.md": "2e0bfbfb",
    "p/grok-build-local-compute-guard-billing-lock-20260902-01.md": "de59bf75",
    "p/grok-resources-tab-freshness-billing-lock-20260902-01.md": "ac39fe78",
    "ground/OWNER_NOW.md": "59b1fd37",
}


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class TestGrokbuildTests33689243523BillingLock(unittest.TestCase):
    def test_keep_8411_leftover_and_tests_yml_unread(self) -> None:
        for rel, prefix in KEEP.items():
            blob = git_blob(rel)
            self.assertTrue(
                blob.startswith(prefix),
                f"{rel} reminted: want {prefix} got {blob[:8]}",
            )
        yml = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("name: tests", yml)
        self.assertIn("battery:", yml)
        self.assertIn("the whole battery, one failure fails the run", yml)
        self.assertIn("find . -maxdepth 1 -type f -name 'test_*.py'", yml)
        self.assertNotIn("billing", yml.lower())
        self.assertNotIn("if: false", yml)
        self.assertNotIn("continue-on-error", yml)

    def test_local_failed_step_still_passes(self) -> None:
        for name, expected in (
            ("test_grokbuild_pr8411_verify.py", "Ran 2 tests"),
            ("test_grokbuild_llms_txt_33687829181_billing_lock.py", "Ran 3 tests"),
        ):
            proc = subprocess.run(
                ["python3", "-m", "unittest", name],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(proc.returncode, 0, msg=name + "\n" + proc.stdout + proc.stderr)
            self.assertIn(expected, proc.stderr)
        added = [
            guard.AddedLine("test_grokbuild_tests_33689243523_billing_lock.py", 1, line)
            for line in Path(__file__).read_text(encoding="utf-8").splitlines()
        ]
        self.assertEqual(guard.scan_added(added), [])

    def test_receipt_cites_run_and_does_not_steal(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        prior = PRIOR.read_text(encoding="utf-8")
        llms = LLMS.read_text(encoding="utf-8")
        sibling = SIBLING.read_text(encoding="utf-8")
        self.assertIn("grokbuild-tests-33689243523-billing-lock-20260902-01", text)
        self.assertIn(
            "woahwhattheheck/commons:tests:98eeae83050a6e83effb1c5e52511ec8cf27bf68:battery",
            text,
        )
        self.assertIn("33689243523", text)
        self.assertIn("100443908471", text)
        self.assertIn("100447002468", text)
        self.assertIn("98eeae83050a6e83effb1c5e52511ec8cf27bf68", text)
        self.assertIn("81e8f9ccc7293bf6e5179e615ba460d87f409eb0", text)
        self.assertIn(
            "The job was not started because your account is locked due to a billing issue.",
            text,
        )
        self.assertIn("EXTERNAL_BLOCKER", text)
        self.assertIn("642dea64", text)
        self.assertIn("361f5ca1", text)
        self.assertIn("3183564c", text)
        self.assertIn("8c2f2301", text)
        self.assertIn("4ab677c5", text)
        self.assertIn("Did not remint those", text)
        self.assertIn("Did not remint sibling tests leftovers 33689083188 / 33689281316", text)
        self.assertIn("did not reopen #7915", text.lower())
        self.assertNotEqual(text, prior)
        self.assertNotEqual(text, llms)
        self.assertNotEqual(text, sibling)
        self.assertNotIn("tests:98eeae83050a6e83effb1c5e52511ec8cf27bf68:battery", prior)
        self.assertNotIn("buy.stripe.com", text)
        self.assertFalse((ROOT / "marketplace.html").exists())
        self.assertFalse((ROOT / "qualify.html").exists())

    def test_fix_first_packet_is_external_blocker(self) -> None:
        packet = {
            "outcome": "external_blocker",
            "observed_broken": True,
            "finding_kind": "behavior",
            "expected_contract": (
                "tests.yml job battery checks out the repo and runs every "
                "discovered root test_*.py / test_*.js plus infra test_*.py "
                "on pull_request that touches engine or test paths"
            ),
            "repair_attempts": [
                "local PR 8411 leftover 2/2 on current main",
                "local llms-txt 33687829181 leftover 3/3",
                "test_llms_publish.py ALL PASS; test_llms_pulse.py 4/4; test_baked_head_json.py 10/10",
                "open_door_guard PASS; test_open_door_guard.py PASS; test_fix_first.py 6/6",
                "test_path_manifest.py 9/9; test_source_parses.py 9/9",
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
