#!/usr/bin/env python3
"""Pin unique leftover for live-mirror-commons run 33791064118. Do not remint live_mirror contract or prior leftovers."""

from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path

import fix_first
from host import live_mirror

ROOT = Path(__file__).resolve().parent
RECEIPT = ROOT / "p/grok-build-live-mirror-commons-33791064118-billing-lock-20260903-01.md"
PRIOR = ROOT / "p/grok-live-mirror-force-graft-20260828-01.md"

KEEP = {
    "host/live_mirror.py": "ada86332",
    "test_live_mirror.py": "0fee48fd",
    "open_door_guard.py": "861958e9",
    "fix_first.py": "a57aee1c",
    "p/grok-live-mirror-force-graft-20260828-01.md": "e47c185b",
    "p/grok-live-mirror-force-graft-20260828-01.html": "8410fb03",
}


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class TestGrokbuildLiveMirrorCommons33791064118BillingLock(unittest.TestCase):
    def test_keep_live_mirror_contract_and_prior_leftover_unread(self) -> None:
        for rel, prefix in KEEP.items():
            blob = git_blob(rel)
            self.assertTrue(
                blob.startswith(prefix),
                f"{rel} reminted: want {prefix} got {blob[:8]}",
            )
        src = (ROOT / "host/live_mirror.py").read_text(encoding="utf-8")
        self.assertIn("GITHUB_TOKEN-safe live mirror", src)
        self.assertIn("WORKFLOWS_PERMISSION", src)
        self.assertNotIn("if: false", src)

    def test_receipt_is_unique_and_does_not_remint(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        prior = PRIOR.read_text(encoding="utf-8")
        self.assertIn(
            "grok-build-live-mirror-commons-33791064118-billing-lock-20260903-01",
            text,
        )
        self.assertIn(
            "woahwhattheheck/commons-backup:live-mirror-commons:17268727fea21066cda39f5740f02fb6903961d8:mirror",
            text,
        )
        self.assertIn("33791064118", text)
        self.assertIn("100767504479", text)
        self.assertIn("100770367303", text)
        self.assertIn("100771874395", text)
        self.assertIn("17268727fea21066cda39f5740f02fb6903961d8", text)
        self.assertIn("4926eca3cae1d787461c97fe3828f738b8064a93", text)
        self.assertIn(
            "The job was not started because your account is locked due to a billing issue.",
            text,
        )
        self.assertIn("EXTERNAL_BLOCKER", text)
        self.assertIn("state=EXACT", text)
        self.assertIn("Did not remint leftover grok-live-mirror-force-graft-20260828-01", text)
        self.assertIn("e47c185b", text)
        self.assertIn("ada86332", text)
        self.assertIn("0fee48fd", text)
        self.assertIn("4b053e43", text)
        self.assertNotEqual(text, prior)
        self.assertNotIn(
            "live-mirror-commons:17268727fea21066cda39f5740f02fb6903961d8:mirror",
            prior,
        )

    def test_local_live_mirror_plan_still_green(self) -> None:
        src = "a" * 40
        dst = "b" * 40
        self.assertEqual(live_mirror.plan(src, src)["action"], "already_in_sync")
        self.assertEqual(live_mirror.plan(src, dst, src)["reason"], "recorded_source")
        self.assertEqual(live_mirror.plan(src, dst)["action"], "push")
        self.assertEqual(
            live_mirror.classify_push_error(
                "refusing to allow a GitHub App to create or update workflow "
                "without `workflows` permission"
            ),
            "WORKFLOWS_PERMISSION",
        )

    def test_fix_first_packet_is_external_blocker(self) -> None:
        packet = {
            "outcome": "external_blocker",
            "observed_broken": True,
            "finding_kind": "behavior",
            "expected_contract": (
                "live-mirror-commons.yml job mirror on backup ops executes "
                "host/live_mirror.py and force-updates backup main to canonical "
                "commons main"
            ),
            "repair_attempts": [
                "local test_live_mirror.py 7/7; plan action=push; adjacent capsule 24/24 moving-main 15/15",
                "inspected backup ops mirror.yml valid schedule no YAML defect",
                "github rerun_failed_jobs 201; attempt 3 same billing refusal",
                "ephemeral-cloud live_mirror.py push state=EXACT pushed_sha=4926eca3cae1d787461c97fe3828f738b8064a93",
                "GitHub Actions billing APIs unavailable; owner unlock is provider work",
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
