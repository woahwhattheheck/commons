#!/usr/bin/env python3
"""Pin unique leftover for open-door-guard run 33689347393. Do not remint the guard."""

from __future__ import annotations

import subprocess
import unittest
from pathlib import Path

import fix_first
import open_door_guard as guard

ROOT = Path(__file__).resolve().parent
RECEIPT = ROOT / "p/grokbuild-open-door-guard-33689347393-billing-lock-20260902-01.md"
SIBLING = ROOT / "p/grokbuild-open-door-guard-33687124472-billing-lock-20260902-01.md"
SIBLING_TEST = ROOT / "test_grokbuild_open_door_guard_33687124472_billing_lock.py"
NEARBY = ROOT / "p/grokbuild-open-door-guard-33689357297-billing-lock-20260902-01.md"
VERIFY_8409 = ROOT / "p/grokbuild-pr8409-verify-20260902-01.md"

KEEP = {
    "open_door_guard.py": "4b053e43",
    "test_open_door_guard.py": "70ee5730",
    ".github/workflows/open-door-guard.yml": "6586644c",
    "p/grokbuild-open-door-guard-33687124472-billing-lock-20260902-01.md": "b91a85d3",
    "test_grokbuild_open_door_guard_33687124472_billing_lock.py": "e6a826cf",
    "p/grokbuild-open-door-guard-33689357297-billing-lock-20260902-01.md": "261c9cf6",
    "test_grokbuild_open_door_guard_33689357297_billing_lock.py": "f2a2a68d",
    "p/grokbuild-pr8409-verify-20260902-01.md": "199cc075",
    "p/grok-build-discord-cloud-billing-lock-20260902-01.md": "2e0bfbfb",
}


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class TestGrokbuildOpenDoorGuard33689347393BillingLock(unittest.TestCase):
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
                "test_grokbuild_open_door_guard_33689347393_billing_lock.py", 1, line
            )
            for line in Path(__file__).read_text(encoding="utf-8").splitlines()
        ]
        self.assertEqual(guard.scan_added(added), [])
        receipt_added = [
            guard.AddedLine(
                "p/grokbuild-open-door-guard-33689347393-billing-lock-20260902-01.md",
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
        nearby = NEARBY.read_text(encoding="utf-8")
        verify = VERIFY_8409.read_text(encoding="utf-8")
        self.assertIn(
            "grokbuild-open-door-guard-33689347393-billing-lock-20260902-01", text
        )
        self.assertIn(
            "woahwhattheheck/commons:open-door-guard:718682437ac745edaadd304b8199f28af3c4ad6d:reject-added-locks",
            text,
        )
        self.assertIn("33689347393", text)
        self.assertIn("718682437ac745edaadd304b8199f28af3c4ad6d", text)
        self.assertIn("100444236551", text)
        self.assertIn(
            "The job was not started because your account is locked due to a billing issue.",
            text,
        )
        self.assertIn("EXTERNAL_BLOCKER", text)
        self.assertIn("4b053e43", text)
        self.assertIn("70ee5730", text)
        self.assertIn("b91a85d3", text)
        self.assertIn("261c9cf6", text)
        self.assertIn("199cc075", text)
        self.assertIn("Did not remint", text)
        self.assertIn("Did not reopen #7915", text)
        self.assertNotEqual(text, sibling)
        self.assertNotEqual(text, nearby)
        self.assertNotEqual(text, verify)
        self.assertNotEqual(Path(__file__).read_text(encoding="utf-8"), sibling_test)
        self.assertNotIn(
            "grokbuild-open-door-guard-33689347393-billing-lock-20260902-01", sibling
        )
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
                "python3 test_open_door_guard.py on pull_request"
            ),
            "repair_attempts": [
                "local open_door_guard.py --diff 81e8f9cc 71868243 PASS on 7186824",
                "local test_open_door_guard.py PASS",
                "test_fix_first.py 6/6; test_path_manifest.py 9/9; test_source_parses.py 9/9",
                "test_open_door.py OPEN; did not remint nearby leftover 261c9cf6 or 8409 leftover 199cc075",
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
