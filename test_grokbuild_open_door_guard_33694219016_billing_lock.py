#!/usr/bin/env python3
"""Pin unique leftover for open-door-guard run 33694219016. Do not remint the guard or wire-hub-tick leftover."""

from __future__ import annotations

import subprocess
import unittest
from pathlib import Path

import fix_first
import open_door_guard as guard

ROOT = Path(__file__).resolve().parent
RECEIPT = ROOT / "p/grokbuild-open-door-guard-33694219016-billing-lock-20260902-01.md"
SIBLING = ROOT / "p/grokbuild-open-door-guard-33687124472-billing-lock-20260902-01.md"
SIBLING_TEST = ROOT / "test_grokbuild_open_door_guard_33687124472_billing_lock.py"

KEEP = {
    "open_door_guard.py": "4b053e43",
    "test_open_door_guard.py": "70ee5730",
    ".github/workflows/open-door-guard.yml": "6586644c",
    "p/grokbuild-open-door-guard-33687124472-billing-lock-20260902-01.md": "b91a85d3",
    "test_grokbuild_open_door_guard_33687124472_billing_lock.py": "e6a826cf",
    "p/grok-build-discord-cloud-billing-lock-20260902-01.md": "2e0bfbfb",
    "p/grok-build-local-compute-guard-billing-lock-20260902-01.md": "de59bf75",
    "p/grok-build-llms-txt-billing-lock-20260902-01.md": "cf9c9f40",
    "p/wire-hub-tick-20260902-01.md": "33e99713",
}


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class TestGrokbuildOpenDoorGuard33694219016BillingLock(unittest.TestCase):
    def test_keep_guard_and_sibling_unread(self) -> None:
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
                "test_grokbuild_open_door_guard_33694219016_billing_lock.py", 1, line
            )
            for line in Path(__file__).read_text(encoding="utf-8").splitlines()
        ]
        self.assertEqual(guard.scan_added(added), [])
        receipt_added = [
            guard.AddedLine(
                "p/grokbuild-open-door-guard-33694219016-billing-lock-20260902-01.md",
                1,
                line,
            )
            for line in RECEIPT.read_text(encoding="utf-8").splitlines()
        ]
        self.assertEqual(guard.scan_added(receipt_added), [])

    def test_receipt_cites_this_run_and_does_not_steal(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        sibling = SIBLING.read_text(encoding="utf-8")
        sibling_test = SIBLING_TEST.read_text(encoding="utf-8")
        self.assertIn("grokbuild-open-door-guard-33694219016-billing-lock-20260902-01", text)
        self.assertIn(
            "woahwhattheheck/commons:open-door-guard:6b2a01e8ff3a23b021448f8cb9a80709ff300d26:reject-added-locks",
            text,
        )
        self.assertIn("33694219016", text)
        self.assertIn("6b2a01e8ff3a23b021448f8cb9a80709ff300d26", text)
        self.assertIn(
            "The job was not started because your account is locked due to a billing issue.",
            text,
        )
        self.assertIn("EXTERNAL_BLOCKER", text)
        self.assertIn("4b053e43", text)
        self.assertIn("70ee5730", text)
        self.assertIn("b91a85d3", text)
        self.assertIn("33e99713", text)
        self.assertIn("Did not remint", text)
        self.assertIn("wire-hub-tick", text)
        self.assertNotEqual(text, sibling)
        self.assertNotEqual(Path(__file__).read_text(encoding="utf-8"), sibling_test)
        self.assertNotIn("buy.stripe.com", text)
        self.assertNotIn("33687124472", text.split("KEEP unread", 1)[0])

    def test_fix_first_packet_is_external_blocker(self) -> None:
        packet = {
            "outcome": "external_blocker",
            "observed_broken": True,
            "finding_kind": "behavior",
            "expected_contract": (
                "open-door-guard.yml job reject-added-locks executes "
                "python3 open_door_guard.py --diff BASE HEAD then "
                "python3 test_open_door_guard.py on push to main"
            ),
            "repair_attempts": [
                "local open_door_guard.py --diff 7353841f HEAD PASS on 6b2a01e8",
                "local test_open_door_guard.py PASS",
                "same contracts PASS on current main 0a4c14f8",
                "github billing APIs 404/403; rerun_failed_jobs accepted; attempt 2 runner never assigned",
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
