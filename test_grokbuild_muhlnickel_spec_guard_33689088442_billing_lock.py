#!/usr/bin/env python3
"""Pin unique leftover for muhlnickel-spec-guard run 33689088442.

Do not remint peer leftover 33689243569, meeting-item-6 leftover, or the workflow.
"""

from __future__ import annotations

import subprocess
import unittest
from pathlib import Path

import fix_first
import muhlnickel_spec_guard as guard

ROOT = Path(__file__).resolve().parent
RECEIPT = ROOT / "p/grokbuild-muhlnickel-spec-guard-33689088442-billing-lock-20260902-01.md"
PEER = ROOT / "p/grok-build-muhlnickel-spec-guard-33689243569-billing-lock-20260902-01.md"
READBACK = ROOT / "p/cursor-merge-on-pr-readback-20260902-01.md"
ORIGINAL = ROOT / "p/cursor-merge-on-pr-20260902-01.md"
VERIFY = ROOT / "p/grokbuild-pr8414-verify-20260902-01.md"
WORKFLOW = ROOT / ".github/workflows/muhlnickel-spec-guard.yml"

KEEP = {
    ".github/workflows/muhlnickel-spec-guard.yml": "7886bdf1",
    "muhlnickel_spec_guard.py": "74423d71",
    "test_muhlnickel_spec_guard.py": "097742ec",
    "p/grok-build-muhlnickel-spec-guard-33689243569-billing-lock-20260902-01.md": "7032fbcf",
    "test_grokbuild_muhlnickel_spec_guard_33689243569_billing_lock.py": "897ba184",
    "p/cursor-merge-on-pr-20260902-01.md": "22b63e25",
    "p/cursor-merge-on-pr-readback-20260902-01.md": "e160b2c3",
    "test_cursor_merge_on_pr_readback.py": "a90bb2ff",
    "host/merge_on_pr.py": "0270094d",
    "p/grokbuild-pr8414-verify-20260902-01.md": "587cc1cf",
}


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class TestGrokbuildMuhlnickelSpecGuard33689088442BillingLock(unittest.TestCase):
    def test_keep_peer_guard_item6_and_workflow_unread(self) -> None:
        for rel, prefix in KEEP.items():
            blob = git_blob(rel)
            self.assertTrue(
                blob.startswith(prefix),
                f"{rel} reminted: want {prefix} got {blob[:8]}",
            )
        yml = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("python3 muhlnickel_spec_guard.py --base", yml)
        self.assertIn("--worktree", yml)
        self.assertNotIn("if: false", yml)
        self.assertNotIn("billing", yml.lower())

    def test_local_failed_step_still_passes_on_landed_guard(self) -> None:
        page = b"RING\x00DELTA\x00PAGE"
        self.assertFalse(guard.is_python(Path("page-0000.mno.page"), page))
        proc = subprocess.run(
            ["python3", "muhlnickel_spec_guard.py", "--base", "HEAD^", "--worktree"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
        self.assertIn("MUHLNICKEL SPEC GUARD: clean", proc.stdout)
        self.assertNotIn("source code string cannot contain null bytes", proc.stderr)

    def test_peer_leftover_tests_still_pass(self) -> None:
        proc = subprocess.run(
            ["python3", "test_grokbuild_muhlnickel_spec_guard_33689243569_billing_lock.py"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)

    def test_receipt_cites_this_run_and_does_not_steal(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        peer = PEER.read_text(encoding="utf-8")
        readback = READBACK.read_text(encoding="utf-8")
        original = ORIGINAL.read_text(encoding="utf-8")
        verify = VERIFY.read_text(encoding="utf-8")
        self.assertIn("grokbuild-muhlnickel-spec-guard-33689088442-billing-lock-20260902-01", text)
        self.assertIn(
            "woahwhattheheck/commons:muhlnickel-spec-guard:0675fb559de118427a4c37b3cc406fc9f4cc7b64:guard",
            text,
        )
        self.assertIn("33689088442", text)
        self.assertIn("100443430407", text)
        self.assertIn("100446735703", text)
        self.assertIn("0675fb559de118427a4c37b3cc406fc9f4cc7b64", text)
        self.assertIn(
            "The job was not started because your account is locked due to a billing issue.",
            text,
        )
        self.assertIn("EXTERNAL_BLOCKER", text)
        self.assertIn("74423d71", text)
        self.assertIn("7032fbcf", text)
        self.assertIn("097742ec", text)
        self.assertIn("7886bdf1", text)
        self.assertIn("22b63e25", text)
        self.assertIn("e160b2c3", text)
        self.assertIn("587cc1cf", text)
        self.assertIn("Did not remint", text)
        self.assertIn("Did not reopen #7915", text)
        self.assertNotEqual(text, peer)
        self.assertNotEqual(text, readback)
        self.assertNotEqual(text, original)
        self.assertNotEqual(text, verify)
        self.assertNotIn("buy.stripe.com", text)
        self.assertNotIn(
            "muhlnickel-spec-guard:0675fb559de118427a4c37b3cc406fc9f4cc7b64:guard",
            peer,
        )
        self.assertNotIn("33689088442", peer)

    def test_fix_first_packet_is_external_blocker(self) -> None:
        packet = {
            "outcome": "external_blocker",
            "observed_broken": True,
            "finding_kind": "behavior",
            "expected_contract": (
                "muhlnickel-spec-guard.yml job guard executes "
                "python3 muhlnickel_spec_guard.py --base BASE --worktree "
                "on pull_request"
            ),
            "repair_attempts": [
                "local --worktree PASS on current main (peer NUL repair KEEP 74423d71)",
                "test_muhlnickel_spec_guard.py PASS",
                "github rerun_failed_jobs 201; attempt 2 same billing refusal runner_id=0",
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
