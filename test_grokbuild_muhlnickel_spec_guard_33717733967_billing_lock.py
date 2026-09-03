#!/usr/bin/env python3
"""Pin unique leftover for muhlnickel-spec-guard run 33717733967. Do not remint the guard."""

from __future__ import annotations

import subprocess
import unittest
from pathlib import Path

import fix_first

ROOT = Path(__file__).resolve().parent
RECEIPT = ROOT / "p/grokbuild-muhlnickel-spec-guard-33717733967-billing-lock-20260903-01.md"
PEER = ROOT / "p/grokbuild-muhlnickel-spec-guard-33699980193-billing-lock-20260903-01.md"
OLDER = ROOT / "p/grokbuild-muhlnickel-spec-guard-33699600936-billing-lock-20260903-01.md"
PARENT = ROOT / "p/grokbuild-main-range-verify-33717084528-billing-lock-20260903-01.md"
WORKFLOW = ROOT / ".github/workflows/muhlnickel-spec-guard.yml"

KEEP = {
    "muhlnickel_spec_guard.py": "74423d71",
    "test_muhlnickel_spec_guard.py": "097742ec",
    ".github/workflows/muhlnickel-spec-guard.yml": "7886bdf1",
    "open_door_guard.py": "4b053e43",
    "p/grokbuild-muhlnickel-spec-guard-33699980193-billing-lock-20260903-01.md": "79285c10",
    "test_grokbuild_muhlnickel_spec_guard_33699980193_billing_lock.py": "e4363b6a",
    "p/grokbuild-muhlnickel-spec-guard-33699600936-billing-lock-20260903-01.md": "e063cc7e",
    "test_grokbuild_muhlnickel_spec_guard_33699600936_billing_lock.py": "7098db31",
    "p/grokbuild-muhlnickel-spec-guard-33689347386-billing-lock-20260902-01.md": "2c08e8ab",
    "test_grokbuild_muhlnickel_spec_guard_33689347386_billing_lock.py": "07e46f6f",
    "p/grokbuild-muhlnickel-spec-guard-33689088442-billing-lock-20260902-01.md": "61a98ddd",
    "p/grok-build-muhlnickel-spec-guard-33689243569-billing-lock-20260902-01.md": "7032fbcf",
    "p/grokbuild-main-range-verify-33717084528-billing-lock-20260903-01.md": "2b0fd9c9",
    "test_grokbuild_main_range_verify_33717084528_billing_lock.py": "3e89a404",
    "p/grokbuild-harness-wakeup-33717474657-billing-lock-20260903-01.md": "f54e1846",
    "p/grokbuild-open-door-guard-33699286785-billing-lock-20260902-01.md": "d22e0707",
    "p/grokbuild-muhlnickel-spec-guard-33699939446-billing-lock-20260903-01.md": "00072bfa",
    "test_grokbuild_muhlnickel_spec_guard_33699939446_billing_lock.py": "d4daa8a1",
    "p/grokbuild-slack-service-tags-33717615004-billing-lock-20260903-01.md": "f33a76ef",
}


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class TestGrokbuildMuhlnickelSpecGuard33717733967BillingLock(unittest.TestCase):
    def test_keep_guard_and_prior_leftovers_unread(self) -> None:
        for rel, prefix in KEEP.items():
            blob = git_blob(rel)
            self.assertTrue(
                blob.startswith(prefix),
                f"{rel} reminted: want {prefix} got {blob[:8]}",
            )
        yml = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("python3 muhlnickel_spec_guard.py --base", yml)
        self.assertIn("runs-on: ubuntu-latest", yml)
        self.assertNotIn("if: false", yml)
        self.assertNotIn("billing", yml.lower())

    def test_local_failed_step_still_passes(self) -> None:
        proc = subprocess.run(
            ["python3", "muhlnickel_spec_guard.py", "--base", "HEAD^", "--worktree"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
        self.assertIn("MUHLNICKEL SPEC GUARD: clean", proc.stdout)
        tests = subprocess.run(
            ["python3", "-m", "unittest", "test_muhlnickel_spec_guard"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(tests.returncode, 0, msg=tests.stdout + tests.stderr)
        self.assertIn("Ran 19 tests", tests.stderr + tests.stdout)

    def test_receipt_cites_run_and_does_not_remint(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        peer = PEER.read_text(encoding="utf-8")
        older = OLDER.read_text(encoding="utf-8")
        parent = PARENT.read_text(encoding="utf-8")
        self.assertIn(
            "grokbuild-muhlnickel-spec-guard-33717733967-billing-lock-20260903-01",
            text,
        )
        self.assertIn(
            "woahwhattheheck/commons:muhlnickel-spec-guard:2890fde44250063aa66ef60735a7cc90407760a6:guard",
            text,
        )
        self.assertIn("33717733967", text)
        self.assertIn("100530342636", text)
        self.assertIn("2890fde44250063aa66ef60735a7cc90407760a6", text)
        self.assertIn("/8583", text)
        self.assertIn(
            "The job was not started because your account is locked due to a billing issue.",
            text,
        )
        self.assertIn("EXTERNAL_BLOCKER", text)
        self.assertIn("74423d71", text)
        self.assertIn("097742ec", text)
        self.assertIn("7886bdf1", text)
        self.assertIn("79285c10", text)
        self.assertIn("2b0fd9c9", text)
        self.assertIn("e063cc7e", text)
        self.assertIn("2c08e8ab", text)
        self.assertIn("61a98ddd", text)
        self.assertIn("7032fbcf", text)
        self.assertIn("00072bfa", text)
        self.assertIn("f54e1846", text)
        self.assertIn("f33a76ef", text)
        self.assertIn("d22e0707", text)
        self.assertIn("e4363b6a", text)
        self.assertIn("3e89a404", text)
        self.assertIn("7098db31", text)
        self.assertIn("07e46f6f", text)
        self.assertIn("d4daa8a1", text)
        self.assertIn("4b053e43", text)
        self.assertIn(
            "Did not remint leftover grokbuild-muhlnickel-spec-guard-33699980193-billing-lock-20260903-01",
            text,
        )
        self.assertIn(
            "Did not remint leftover grokbuild-main-range-verify-33717084528-billing-lock-20260903-01",
            text,
        )
        self.assertIn("Did not reopen #7915", text)
        self.assertIn("Did not reopen #8583", text)
        self.assertNotEqual(text, peer)
        self.assertNotEqual(text, older)
        self.assertNotEqual(text, parent)
        self.assertNotIn(
            "muhlnickel-spec-guard:2890fde44250063aa66ef60735a7cc90407760a6:guard",
            peer,
        )
        self.assertNotIn(
            "muhlnickel-spec-guard:2890fde44250063aa66ef60735a7cc90407760a6:guard",
            parent,
        )
        self.assertNotIn("buy.stripe.com", text)

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
                "local test_muhlnickel_spec_guard.py 19/19 PASS",
                "local muhlnickel_spec_guard.py --base HEAD^ --worktree CLEAN",
                "job 100530342636 runner_id=0 steps absent 4s billing lock",
                "GitHub Actions billing APIs 404",
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
