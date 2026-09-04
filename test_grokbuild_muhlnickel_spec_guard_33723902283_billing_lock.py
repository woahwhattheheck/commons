#!/usr/bin/env python3
"""Pin unique leftover for muhlnickel-spec-guard run 33723902283. Do not remint the guard."""

from __future__ import annotations

import subprocess
import unittest
from pathlib import Path

import fix_first
import open_door_guard as guard

ROOT = Path(__file__).resolve().parent
RECEIPT = ROOT / "p/grokbuild-muhlnickel-spec-guard-33723902283-billing-lock-20260903-01.md"
CENSUS = ROOT / "p/grokbuild-leftover-id-census-33723043828-billing-lock-20260903-01.md"
PEER = ROOT / "p/grokbuild-muhlnickel-spec-guard-33718116252-billing-lock-20260903-01.md"
OLDER = ROOT / "p/grokbuild-muhlnickel-spec-guard-33717733967-billing-lock-20260903-01.md"
WORKFLOW = ROOT / ".github/workflows/muhlnickel-spec-guard.yml"

KEEP = {
    "muhlnickel_spec_guard.py": "74423d71",
    "test_muhlnickel_spec_guard.py": "097742ec",
    ".github/workflows/muhlnickel-spec-guard.yml": "7886bdf1",
    "open_door_guard.py": "4b053e43",
    "p/grokbuild-leftover-id-census-33723043828-billing-lock-20260903-01.md": "e135862e",
    "test_grokbuild_leftover_id_census_33723043828_billing_lock.py": "3f77dce1",
    "p/grokbuild-muhlnickel-spec-guard-33718116252-billing-lock-20260903-01.md": "4f43a687",
    "test_grokbuild_muhlnickel_spec_guard_33718116252_billing_lock.py": "50c79882",
    "p/grokbuild-muhlnickel-spec-guard-33717733967-billing-lock-20260903-01.md": "5b7f49cd",
    "test_grokbuild_muhlnickel_spec_guard_33717733967_billing_lock.py": "7c5e9cf7",
    "p/grokbuild-harness-wakeup-33717474657-billing-lock-20260903-01.md": "f54e1846",
    "leftover-census.md": "b02dc321",
    "leftover-census.json": "32d3ee6b",
    ".github/workflows/leftover-id-census.yml": "cd2ac955",
    "host/leftover_id_census.py": "1cfba147",
    "test_work_becomes_automation.py": "2a0c4e51",
    "p/work-becomes-automation-20260830-01.md": "c0ab7d78",
    "p/cursor-wire-catalog-marketplace-latch-readback-rematch-20260903-01.md": "f23e1db8",
    "test_cursor_wire_catalog_marketplace_latch_readback_rematch.py": "b80c0133",
    "wire.html": "5b8edbda",
    "ground/WIRE_SUPER_MCP.md": "f36de0a5",
}


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class TestGrokbuildMuhlnickelSpecGuard33723902283BillingLock(unittest.TestCase):
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
        added = [
            guard.AddedLine(
                "test_grokbuild_muhlnickel_spec_guard_33723902283_billing_lock.py",
                1,
                line,
            )
            for line in Path(__file__).read_text(encoding="utf-8").splitlines()
        ]
        added.extend(
            guard.AddedLine(
                "p/grokbuild-muhlnickel-spec-guard-33723902283-billing-lock-20260903-01.md",
                1,
                line,
            )
            for line in RECEIPT.read_text(encoding="utf-8").splitlines()
        )
        self.assertEqual(guard.scan_added(added), [])

    def test_receipt_cites_run_and_does_not_remint(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        census = CENSUS.read_text(encoding="utf-8")
        peer = PEER.read_text(encoding="utf-8")
        older = OLDER.read_text(encoding="utf-8")
        self.assertIn("grokbuild-muhlnickel-spec-guard-33723902283-billing-lock-20260903-01", text)
        self.assertIn(
            "woahwhattheheck/commons:muhlnickel-spec-guard:ee095dbb6fe94772503c5d1171fc79f5559b26f1:guard",
            text,
        )
        self.assertIn("33723902283", text)
        self.assertIn("100548587423", text)
        self.assertIn("ee095dbb6fe94772503c5d1171fc79f5559b26f1", text)
        self.assertIn(
            "The job was not started because your account is locked due to a billing issue.",
            text,
        )
        self.assertIn("EXTERNAL_BLOCKER", text)
        self.assertIn("74423d71", text)
        self.assertIn("097742ec", text)
        self.assertIn("7886bdf1", text)
        self.assertIn("e135862e", text)
        self.assertIn("3f77dce1", text)
        self.assertIn("4f43a687", text)
        self.assertIn("af125d08", text)
        self.assertIn("5b7f49cd", text)
        self.assertIn("f54e1846", text)
        self.assertIn("b02dc321", text)
        self.assertIn("32d3ee6b", text)
        self.assertIn("cd2ac955", text)
        self.assertIn("1cfba147", text)
        self.assertIn("f23e1db8", text)
        self.assertIn("b9dffb45", text)
        self.assertIn("4ae38ce9", text)
        self.assertIn("f36de0a5", text)
        self.assertIn("Did not remint leftover grokbuild-leftover-id-census-33723043828-billing-lock-20260903-01", text)
        self.assertIn("Did not reopen #7915", text)
        self.assertNotEqual(text, census)
        self.assertNotEqual(text, peer)
        self.assertNotEqual(text, older)
        self.assertNotIn(
            "muhlnickel-spec-guard:ee095dbb6fe94772503c5d1171fc79f5559b26f1:guard",
            peer,
        )
        self.assertNotIn(
            "muhlnickel-spec-guard:ee095dbb6fe94772503c5d1171fc79f5559b26f1:guard",
            census,
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
                "inspected muhlnickel-spec-guard.yml KEEP 7886bdf1; no YAML defect, no billing skip",
                "local test_muhlnickel_spec_guard.py 19/19 PASS",
                "local muhlnickel_spec_guard.py --base HEAD^ --worktree CLEAN",
                "open_door_guard PASS; annotation job 100548587423 billing lock; runner_id=0 steps=[] logs 404",
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
