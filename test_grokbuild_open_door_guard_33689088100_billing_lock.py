#!/usr/bin/env python3
"""Pin unique leftover for open-door-guard run 33689088100. Do not remint the guard or prior leftover."""

from __future__ import annotations

import subprocess
import unittest
from pathlib import Path

import fix_first
import open_door_guard as guard

ROOT = Path(__file__).resolve().parent
RECEIPT = ROOT / "p/grokbuild-open-door-guard-33689088100-billing-lock-20260902-01.md"
PRIOR = ROOT / "p/grokbuild-open-door-guard-33687124472-billing-lock-20260902-01.md"
SIBLING = ROOT / "p/grok-build-discord-cloud-billing-lock-20260902-01.md"
READBACK = ROOT / "p/cursor-merge-on-pr-readback-20260902-01.md"
MERGE_ON_PR = ROOT / "p/cursor-merge-on-pr-20260902-01.md"

KEEP = {
    "open_door_guard.py": "4b053e43",
    "test_open_door_guard.py": "70ee5730",
    ".github/workflows/open-door-guard.yml": "6586644c",
    "p/grokbuild-open-door-guard-33687124472-billing-lock-20260902-01.md": "b91a85d3",
    "test_grokbuild_open_door_guard_33687124472_billing_lock.py": "e6a826cf",
    "p/grok-build-discord-cloud-billing-lock-20260902-01.md": "2e0bfbfb",
    "p/grok-build-local-compute-guard-billing-lock-20260902-01.md": "de59bf75",
    "p/grok-build-llms-txt-33687829181-billing-lock-20260902-01.md": "3183564c",
    "p/grok-build-llms-txt-billing-lock-20260902-01.md": "cf9c9f40",
    "p/grok-resources-tab-freshness-billing-lock-20260902-01.md": "ac39fe78",
    "p/cursor-merge-on-pr-readback-20260902-01.md": "e160b2c3",
    "test_cursor_merge_on_pr_readback.py": "a90bb2ff",
    "p/cursor-merge-on-pr-20260902-01.md": "22b63e25",
    "host/merge_on_pr.py": "0270094d",
    "host/sprint_integration.py": "b7bec0b9",
    "p/grokbuild-pr8402-verify-20260902-01.md": "3524e382",
}


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class TestGrokbuildOpenDoorGuard33689088100BillingLock(unittest.TestCase):
    def test_keep_guard_prior_leftover_and_siblings_unread(self) -> None:
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
            guard.AddedLine("test_grokbuild_open_door_guard_33689088100_billing_lock.py", 1, line)
            for line in Path(__file__).read_text(encoding="utf-8").splitlines()
        ]
        self.assertEqual(guard.scan_added(added), [])
        receipt_added = [
            guard.AddedLine(str(RECEIPT.relative_to(ROOT)), 1, line)
            for line in RECEIPT.read_text(encoding="utf-8").splitlines()
        ]
        self.assertEqual(guard.scan_added(receipt_added), [])

    def test_receipt_cites_run_and_does_not_steal(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        prior = PRIOR.read_text(encoding="utf-8")
        sibling = SIBLING.read_text(encoding="utf-8")
        readback = READBACK.read_text(encoding="utf-8")
        merge_on_pr = MERGE_ON_PR.read_text(encoding="utf-8")
        self.assertIn("grokbuild-open-door-guard-33689088100-billing-lock-20260902-01", text)
        self.assertIn(
            "woahwhattheheck/commons:open-door-guard:0675fb559de118427a4c37b3cc406fc9f4cc7b64:reject-added-locks",
            text,
        )
        self.assertIn("33689088100", text)
        self.assertIn("100443429590", text)
        self.assertIn("100445876538", text)
        self.assertIn("0675fb559de118427a4c37b3cc406fc9f4cc7b64", text)
        self.assertIn(
            "The job was not started because your account is locked due to a billing issue.",
            text,
        )
        self.assertIn("EXTERNAL_BLOCKER", text)
        self.assertIn("4b053e43", text)
        self.assertIn("70ee5730", text)
        self.assertIn("b91a85d3", text)
        self.assertIn("e160b2c3", text)
        self.assertIn("22b63e25", text)
        self.assertIn("0270094d", text)
        self.assertIn("b7bec0b9", text)
        self.assertIn("Did not remint those", text)
        self.assertIn("Did not reopen #7915", text)
        self.assertIn("Did not dump marketplace.html", text)
        self.assertNotEqual(text, prior)
        self.assertNotEqual(text, sibling)
        self.assertNotEqual(text, readback)
        self.assertNotEqual(text, merge_on_pr)
        self.assertNotIn(
            "open-door-guard:0675fb559de118427a4c37b3cc406fc9f4cc7b64:reject-added-locks",
            prior,
        )
        self.assertIn(
            "open-door-guard:dc2dc72aaae94decbe2bbbe7144504f30919916f:reject-added-locks",
            prior,
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
                "python3 test_open_door_guard.py on pull_request and push to main"
            ),
            "repair_attempts": [
                "local open_door_guard.py --diff f078829d 0675fb55 PASS",
                "local test_open_door_guard.py PASS",
                "merge 920d8c03 and current main parent diffs PASS",
                "github rerun_failed_jobs 201; attempt 2 same billing refusal",
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
