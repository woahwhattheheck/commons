#!/usr/bin/env python3
"""Pin unique leftover for muhlnickel-spec-guard run 33699980193. Do not remint the guard."""

from __future__ import annotations

import subprocess
import unittest
from pathlib import Path

import fix_first

ROOT = Path(__file__).resolve().parent
RECEIPT = ROOT / "p/grokbuild-muhlnickel-spec-guard-33699980193-billing-lock-20260903-01.md"
PEER = ROOT / "p/grokbuild-muhlnickel-spec-guard-33699600936-billing-lock-20260903-01.md"
OLDER = ROOT / "p/grokbuild-muhlnickel-spec-guard-33689347386-billing-lock-20260902-01.md"
DISCORD = ROOT / "p/grok-build-discord-cloud-33699286743-billing-lock-20260902-01.md"
WORKFLOW = ROOT / ".github/workflows/muhlnickel-spec-guard.yml"

KEEP = {
    "muhlnickel_spec_guard.py": "74423d71",
    "test_muhlnickel_spec_guard.py": "097742ec",
    ".github/workflows/muhlnickel-spec-guard.yml": "7886bdf1",
    "open_door_guard.py": "4b053e43",
    "p/grokbuild-muhlnickel-spec-guard-33699600936-billing-lock-20260903-01.md": "e063cc7e",
    "test_grokbuild_muhlnickel_spec_guard_33699600936_billing_lock.py": "7098db31",
    "p/grokbuild-muhlnickel-spec-guard-33689347386-billing-lock-20260902-01.md": "2c08e8ab",
    "test_grokbuild_muhlnickel_spec_guard_33689347386_billing_lock.py": "07e46f6f",
    "p/grokbuild-muhlnickel-spec-guard-33689088442-billing-lock-20260902-01.md": "61a98ddd",
    "p/grok-build-muhlnickel-spec-guard-33689243569-billing-lock-20260902-01.md": "7032fbcf",
    "p/grok-build-discord-cloud-33699286743-billing-lock-20260902-01.md": "e8d308ed",
    "test_grokbuild_discord_cloud_33699286743_billing_lock.py": "fcc155e0",
    "p/grok-build-discord-cloud-billing-lock-20260902-01.md": "2e0bfbfb",
    "p/grokbuild-open-door-guard-33699286785-billing-lock-20260902-01.md": "d22e0707",
}


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class TestGrokbuildMuhlnickelSpecGuard33699980193BillingLock(unittest.TestCase):
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
        discord = DISCORD.read_text(encoding="utf-8")
        self.assertIn(
            "grokbuild-muhlnickel-spec-guard-33699980193-billing-lock-20260903-01",
            text,
        )
        self.assertIn(
            "woahwhattheheck/commons:muhlnickel-spec-guard:e34659bfcc5493969ef7fe00bc9edafe15607a01:guard",
            text,
        )
        self.assertIn("33699980193", text)
        self.assertIn("100476980926", text)
        self.assertIn("e34659bfcc5493969ef7fe00bc9edafe15607a01", text)
        self.assertIn("/8529", text)
        self.assertIn(
            "The job was not started because your account is locked due to a billing issue.",
            text,
        )
        self.assertIn("EXTERNAL_BLOCKER", text)
        self.assertIn("74423d71", text)
        self.assertIn("097742ec", text)
        self.assertIn("7886bdf1", text)
        self.assertIn("e063cc7e", text)
        self.assertIn("e8d308ed", text)
        self.assertIn("2c08e8ab", text)
        self.assertIn("61a98ddd", text)
        self.assertIn("7032fbcf", text)
        self.assertIn("2e0bfbfb", text)
        self.assertIn("d22e0707", text)
        self.assertIn("fcc155e0", text)
        self.assertIn("7098db31", text)
        self.assertIn("4b053e43", text)
        self.assertIn(
            "Did not remint leftover grokbuild-muhlnickel-spec-guard-33699600936-billing-lock-20260903-01",
            text,
        )
        self.assertIn("Did not reopen #7915", text)
        self.assertIn("Did not reopen #8529", text)
        self.assertNotEqual(text, peer)
        self.assertNotEqual(text, older)
        self.assertNotEqual(text, discord)
        self.assertNotIn(
            "muhlnickel-spec-guard:e34659bfcc5493969ef7fe00bc9edafe15607a01:guard",
            peer,
        )
        self.assertNotIn(
            "muhlnickel-spec-guard:e34659bfcc5493969ef7fe00bc9edafe15607a01:guard",
            discord,
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
                "job 100476980926 runner_id=0 steps absent 3s billing lock",
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
