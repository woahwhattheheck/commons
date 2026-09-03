#!/usr/bin/env python3
"""Pin unique leftover for muhlnickel-spec-guard run 33718116252. Do not remint the guard."""

from __future__ import annotations

import subprocess
import unittest
from pathlib import Path

import fix_first

ROOT = Path(__file__).resolve().parent
RECEIPT = ROOT / "p/grokbuild-muhlnickel-spec-guard-33718116252-billing-lock-20260903-01.md"
WAKE = ROOT / "p/grokbuild-harness-wakeup-33717474657-billing-lock-20260903-01.md"
PEER = ROOT / "p/grokbuild-muhlnickel-spec-guard-33699980193-billing-lock-20260903-01.md"
OLDER = ROOT / "p/grokbuild-muhlnickel-spec-guard-33699600936-billing-lock-20260903-01.md"
WORKFLOW = ROOT / ".github/workflows/muhlnickel-spec-guard.yml"

KEEP = {
    "muhlnickel_spec_guard.py": "74423d71",
    "test_muhlnickel_spec_guard.py": "097742ec",
    ".github/workflows/muhlnickel-spec-guard.yml": "7886bdf1",
    "open_door_guard.py": "4b053e43",
    "p/grokbuild-harness-wakeup-33717474657-billing-lock-20260903-01.md": "f54e1846",
    "test_grokbuild_harness_wakeup_33717474657_billing_lock.py": "760a8169",
    "p/grokbuild-muhlnickel-spec-guard-33699980193-billing-lock-20260903-01.md": "79285c10",
    "test_grokbuild_muhlnickel_spec_guard_33699980193_billing_lock.py": "e4363b6a",
    "p/grokbuild-muhlnickel-spec-guard-33699600936-billing-lock-20260903-01.md": "e063cc7e",
    "test_grokbuild_muhlnickel_spec_guard_33699600936_billing_lock.py": "7098db31",
    "p/grokbuild-muhlnickel-spec-guard-33699939446-billing-lock-20260903-01.md": "00072bfa",
    "test_grokbuild_muhlnickel_spec_guard_33699939446_billing_lock.py": "d4daa8a1",
    "p/cursor-wire-catalog-marketplace-latch-readback-rematch-20260903-01.md": "f23e1db8",
    "test_cursor_wire_catalog_marketplace_latch_readback_rematch.py": "b9dffb45",
    "wire.html": "4ae38ce9",
    "ground/WIRE_SUPER_MCP.md": "f36de0a5",
}


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class TestGrokbuildMuhlnickelSpecGuard33718116252BillingLock(unittest.TestCase):
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
        wake = WAKE.read_text(encoding="utf-8")
        peer = PEER.read_text(encoding="utf-8")
        older = OLDER.read_text(encoding="utf-8")
        self.assertIn("grokbuild-muhlnickel-spec-guard-33718116252-billing-lock-20260903-01", text)
        self.assertIn(
            "woahwhattheheck/commons:muhlnickel-spec-guard:51814ebf019d53c42ec170b4ed626eb0036fc48e:guard",
            text,
        )
        self.assertIn("33718116252", text)
        self.assertIn("100531470321", text)
        self.assertIn("51814ebf019d53c42ec170b4ed626eb0036fc48e", text)
        self.assertIn(
            "The job was not started because your account is locked due to a billing issue.",
            text,
        )
        self.assertIn("EXTERNAL_BLOCKER", text)
        self.assertIn("74423d71", text)
        self.assertIn("097742ec", text)
        self.assertIn("7886bdf1", text)
        self.assertIn("f54e1846", text)
        self.assertIn("760a8169", text)
        self.assertIn("79285c10", text)
        self.assertIn("e063cc7e", text)
        self.assertIn("f23e1db8", text)
        self.assertIn("b9dffb45", text)
        self.assertIn("4ae38ce9", text)
        self.assertIn("f36de0a5", text)
        self.assertIn("Did not remint leftover grokbuild-harness-wakeup-33717474657-billing-lock-20260903-01", text)
        self.assertIn("Did not reopen #7915", text)
        self.assertNotEqual(text, wake)
        self.assertNotEqual(text, peer)
        self.assertNotEqual(text, older)
        self.assertNotIn(
            "muhlnickel-spec-guard:51814ebf019d53c42ec170b4ed626eb0036fc48e:guard",
            peer,
        )
        self.assertNotIn(
            "muhlnickel-spec-guard:51814ebf019d53c42ec170b4ed626eb0036fc48e:guard",
            wake,
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
                "sibling hosted Actions runs fail the same billing lock",
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
