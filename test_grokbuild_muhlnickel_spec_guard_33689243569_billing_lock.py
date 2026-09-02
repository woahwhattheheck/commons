#!/usr/bin/env python3
"""Pin unique leftover for muhlnickel-spec-guard run 33689243569. Do not remint 8411 leftover."""

from __future__ import annotations

import subprocess
import unittest
from pathlib import Path

import fix_first
import muhlnickel_spec_guard as guard

ROOT = Path(__file__).resolve().parent
RECEIPT = ROOT / "p/grok-build-muhlnickel-spec-guard-33689243569-billing-lock-20260902-01.md"
PRIOR = ROOT / "p/grokbuild-pr8411-verify-20260902-01.md"
LLMS = ROOT / "p/grok-build-llms-txt-33687829181-billing-lock-20260902-01.md"
WORKFLOW = ROOT / ".github/workflows/muhlnickel-spec-guard.yml"

KEEP = {
    "p/grokbuild-pr8411-verify-20260902-01.md": "642dea64",
    "test_grokbuild_pr8411_verify.py": "361f5ca1",
    "p/grok-build-llms-txt-33687829181-billing-lock-20260902-01.md": "3183564c",
    "test_grokbuild_llms_txt_33687829181_billing_lock.py": "e02e5ab5",
    "p/grok-build-llms-txt-billing-lock-20260902-01.md": "cf9c9f40",
    ".github/workflows/muhlnickel-spec-guard.yml": "7886bdf1",
    "llms_txt.py": "83fc5ea9",
}


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class TestGrokbuildMuhlnickelSpecGuard33689243569BillingLock(unittest.TestCase):
    def test_keep_8411_leftover_publisher_and_workflow_unread(self) -> None:
        for rel, prefix in KEEP.items():
            blob = git_blob(rel)
            self.assertTrue(
                blob.startswith(prefix),
                f"{rel} reminted: want {prefix} got {blob[:8]}",
            )
        yml = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("python3 muhlnickel_spec_guard.py --base", yml)
        self.assertIn("--worktree", yml)
        self.assertNotIn("billing", yml.lower())
        self.assertNotIn("if: false", yml)

    def test_receipt_is_unique_and_does_not_remint(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        prior = PRIOR.read_text(encoding="utf-8")
        llms = LLMS.read_text(encoding="utf-8")
        self.assertIn("grok-build-muhlnickel-spec-guard-33689243569-billing-lock-20260902-01", text)
        self.assertIn(
            "woahwhattheheck/commons:muhlnickel-spec-guard:98eeae83050a6e83effb1c5e52511ec8cf27bf68:guard",
            text,
        )
        self.assertIn("33689243569", text)
        self.assertIn("100443908248", text)
        self.assertIn("98eeae83050a6e83effb1c5e52511ec8cf27bf68", text)
        self.assertIn(
            "The job was not started because your account is locked due to a billing issue.",
            text,
        )
        self.assertIn("EXTERNAL_BLOCKER", text)
        self.assertIn("Did not remint leftover grokbuild-pr8411-verify-20260902-01", text)
        self.assertIn("642dea64", text)
        self.assertIn("3183564c", text)
        self.assertIn("e02e5ab5", text)
        self.assertIn("did not reopen #7915", text.lower())
        self.assertNotEqual(text, prior)
        self.assertNotEqual(text, llms)
        self.assertNotIn("33689243569", prior)
        self.assertNotIn("muhlnickel-spec-guard:98eeae83050a6e83effb1c5e52511ec8cf27bf68:guard", llms)

    def test_nul_byte_corpus_is_outside_python_scope(self) -> None:
        payload = b"MUHLRD01\x08\x00\x00\x00H\x00import numpy\n"
        self.assertFalse(guard.is_python(Path("payload.mno"), payload))
        facts = guard.analyze_python("payload.mno", payload)
        self.assertTrue(facts.parse_error)

    def test_fix_first_packet_is_external_blocker(self) -> None:
        packet = {
            "outcome": "external_blocker",
            "observed_broken": True,
            "expected_contract": "muhlnickel-spec-guard job guard starts and runs python3 muhlnickel_spec_guard.py --worktree",
            "finding_kind": "behavior",
            "prior_door_state": "not_applicable",
            "repair_attempts": [
                "inspected muhlnickel-spec-guard.yml",
                "ran test_muhlnickel_spec_guard.py",
                "ran muhlnickel_spec_guard.py --worktree; treated NUL corpus as non-Python",
                "no Actions-billing write road",
            ],
            "blocker": "The job was not started because your account is locked due to a billing issue.",
            "report_only_sessions": 0,
            "unconsumed_findings": 0,
        }
        result = fix_first.validate(packet)
        self.assertEqual(result["state"], "EXTERNAL_BLOCKER")


if __name__ == "__main__":
    unittest.main()
