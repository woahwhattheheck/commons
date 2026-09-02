#!/usr/bin/env python3
"""Pin unique leftover for open-door-guard run 33689243568. Do not remint the guard."""

from __future__ import annotations

import subprocess
import unittest
from pathlib import Path

import fix_first
import open_door_guard as guard

ROOT = Path(__file__).resolve().parent
RECEIPT = ROOT / "p/grokbuild-open-door-guard-33689243568-billing-lock-20260902-01.md"
PRIOR = ROOT / "p/grokbuild-open-door-guard-33687124472-billing-lock-20260902-01.md"
VERIFY_8411 = ROOT / "p/grokbuild-pr8411-verify-20260902-01.md"

KEEP = {
    "open_door_guard.py": "4b053e43",
    "test_open_door_guard.py": "70ee5730",
    ".github/workflows/open-door-guard.yml": "6586644c",
    "p/grokbuild-open-door-guard-33687124472-billing-lock-20260902-01.md": "b91a85d3",
    "test_grokbuild_open_door_guard_33687124472_billing_lock.py": "e6a826cf",
    "p/grokbuild-pr8408-verify-20260902-01.md": "0a594dda",
    "p/grokbuild-pr8411-verify-20260902-01.md": "642dea64",
    "test_grokbuild_pr8411_verify.py": "361f5ca1",
    "p/grokbuild-pr8413-terminal-20260902-01.md": "bca13858",
    "p/cursor-stealable-lanes-occupancy-20260902-01.md": "9631e869",
    "p/cursor-stealable-lanes-occupancy-readback-20260902-01.md": "b2df1cf1",
    "p/grokbuild-pr-collision-notice-33689085107-billing-lock-20260902-01.md": "594b5e71",
    "test_grokbuild_pr_collision_notice_33689085107_billing_lock.py": "4888459d",
}


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class TestGrokbuildOpenDoorGuard33689243568BillingLock(unittest.TestCase):
    def test_keep_guard_and_prior_leftovers_unread(self) -> None:
        for rel, prefix in KEEP.items():
            blob = git_blob(rel)
            self.assertTrue(
                blob.startswith(prefix),
                f"{rel} reminted: want {prefix} got {blob[:8]}",
            )

    def test_local_failed_step_still_passes(self) -> None:
        proc = subprocess.run(
            ["python3", "test_open_door_guard.py"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
        self.assertIn("OPEN DOOR GUARD TEST:", proc.stdout)
        added = [
            guard.AddedLine(
                "test_grokbuild_open_door_guard_33689243568_billing_lock.py", 1, line
            )
            for line in Path(__file__).read_text(encoding="utf-8").splitlines()
        ]
        self.assertEqual(guard.scan_added(added), [])

    def test_receipt_cites_run_and_does_not_steal(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        prior = PRIOR.read_text(encoding="utf-8")
        verify = VERIFY_8411.read_text(encoding="utf-8")
        self.assertIn(
            "grokbuild-open-door-guard-33689243568-billing-lock-20260902-01", text
        )
        self.assertIn(
            "woahwhattheheck/commons:open-door-guard:98eeae83050a6e83effb1c5e52511ec8cf27bf68:reject-added-locks",
            text,
        )
        self.assertIn("33689243568", text)
        self.assertIn("98eeae83050a6e83effb1c5e52511ec8cf27bf68", text)
        self.assertIn(
            "The job was not started because your account is locked due to a billing issue.",
            text,
        )
        self.assertIn("EXTERNAL_BLOCKER", text)
        self.assertIn("4b053e43", text)
        self.assertIn("70ee5730", text)
        self.assertIn("b91a85d3", text)
        self.assertIn("642dea64", text)
        self.assertIn("594b5e71", text)
        self.assertIn("Did not remint", text)
        self.assertIn("Did not reopen #7915", text)
        self.assertNotEqual(text, prior)
        self.assertNotEqual(text, verify)
        self.assertNotIn(
            "grokbuild-open-door-guard-33689243568-billing-lock-20260902-01", prior
        )
        self.assertNotIn("buy.stripe.com", text)

    def test_fix_first_packet_is_external_blocker(self) -> None:
        packet = {
            "outcome": "external_blocker",
            "observed_broken": True,
            "finding_kind": "behavior",
            "expected_contract": (
                "open-door-guard.yml job reject-added-locks executes "
                "python3 open_door_guard.py --diff BASE HEAD then "
                "python3 test_open_door_guard.py on pull_request"
            ),
            "repair_attempts": [
                "local open_door_guard.py --diff HEAD^ HEAD PASS on f6c9a867",
                "local test_open_door_guard.py PASS",
                "test_fix_first.py 6/6; test_path_manifest.py 9/9; test_source_parses.py 9/9",
                "occupancy 10/10 OK; did not remint prior leftover b91a85d3",
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
