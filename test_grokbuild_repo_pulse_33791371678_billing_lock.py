#!/usr/bin/env python3
"""Pin unique leftover for repo-pulse run 33791371678. Do not remint pulse contract or prior leftovers."""

from __future__ import annotations

import subprocess
import unittest
from pathlib import Path

import fix_first
import open_door_guard as guard

ROOT = Path(__file__).resolve().parent
RECEIPT = ROOT / "p/grokbuild-repo-pulse-33791371678-billing-lock-20260903-01.md"
SIBLING = ROOT / "p/grok-build-repo-pulse-billing-lock-20260903-01.md"
WORKFLOW = ROOT / ".github/workflows/repo-pulse.yml"

KEEP = {
    ".github/workflows/repo-pulse.yml": "5c973635",
    "repo_pulse.py": "9ec71eb0",
    "test_repo_pulse.py": "b62b4485",
    "slack_ingest.py": "0040a726",
    "test_slack_ingest.py": "5c46c3eb",
    "exact_body_redact.py": "6b9fff81",
    "host/sprint_integration.py": "b7bec0b9",
    "open_door_guard.py": "861958e9",
    "p/grok-build-repo-pulse-billing-lock-20260903-01.md": "b6e5953c",
}


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class TestGrokbuildRepoPulse33791371678BillingLock(unittest.TestCase):
    def test_keep_pulse_contract_and_prior_leftover_unread(self) -> None:
        for rel, prefix in KEEP.items():
            blob = git_blob(rel)
            self.assertTrue(
                blob.startswith(prefix),
                f"{rel} reminted: want {prefix} got {blob[:8]}",
            )
        yml = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("name: repo-pulse", yml)
        self.assertIn("python3 /tmp/pulse/test_repo_pulse.py", yml)
        self.assertIn("python3 /tmp/pulse/repo_pulse.py", yml)
        self.assertIn("python3 -m unittest -v test_slack_ingest.py", yml)
        self.assertIn('cron: "3,8,13,18,23,28,33,38,43,48,53,58 * * * *"', yml)
        self.assertIn("COMMONS_SLACK_MIRROR", yml)
        self.assertNotIn("if: false", yml)
        self.assertNotIn("continue-on-error", yml)
        self.assertNotIn("billing", yml.lower())

    def test_local_failed_step_still_passes(self) -> None:
        pulse = subprocess.run(
            ["python3", "test_repo_pulse.py"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(pulse.returncode, 0, msg=pulse.stdout + pulse.stderr)
        slack = subprocess.run(
            ["python3", "-m", "unittest", "-q", "test_slack_ingest.py"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(slack.returncode, 0, msg=slack.stdout + slack.stderr)
        added = [
            guard.AddedLine(
                "test_grokbuild_repo_pulse_33791371678_billing_lock.py",
                1,
                line,
            )
            for line in Path(__file__).read_text(encoding="utf-8").splitlines()
        ]
        added.extend(
            guard.AddedLine(
                "p/grokbuild-repo-pulse-33791371678-billing-lock-20260903-01.md",
                1,
                line,
            )
            for line in RECEIPT.read_text(encoding="utf-8").splitlines()
        )
        self.assertEqual(guard.scan_added(added), [])

    def test_receipt_cites_run_and_does_not_steal(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        sibling = SIBLING.read_text(encoding="utf-8")
        self.assertIn(
            "grokbuild-repo-pulse-33791371678-billing-lock-20260903-01",
            text,
        )
        self.assertIn(
            "woahwhattheheck/commons:repo-pulse:f048f0d9df6ce23c13dcc4f086551f8ce35138aa:pulse",
            text,
        )
        self.assertIn("33791371678", text)
        self.assertIn("100768501908", text)
        self.assertIn("100768502079", text)
        self.assertIn("100771490023", text)
        self.assertIn("100771490215", text)
        self.assertIn("f048f0d9df6ce23c13dcc4f086551f8ce35138aa", text)
        self.assertIn("4926eca3cae1d787461c97fe3828f738b8064a93", text)
        self.assertIn(
            "The job was not started because your account is locked due to a billing issue.",
            text,
        )
        self.assertIn("EXTERNAL_BLOCKER", text)
        self.assertIn("1cfc97d0", text)
        self.assertIn("5d716a63", text)
        self.assertIn("b62b4485", text)
        self.assertIn("0040a726", text)
        self.assertIn("5c46c3eb", text)
        self.assertIn("6b9fff81", text)
        self.assertIn("b7bec0b9", text)
        self.assertIn("4b053e43", text)
        self.assertIn("b6e5953c", text)
        self.assertIn("Did not remint leftover grok-build-repo-pulse-billing-lock-20260903-01", text)
        self.assertIn("Did not remint leftover grokbuild-resources-tab-freshness-33791659583-billing-lock-20260903-01", text)
        self.assertIn("Did not reopen #8632", text)
        self.assertIn("Did not reopen #7915", text)
        self.assertNotEqual(text, sibling)
        self.assertNotIn(
            "repo-pulse:f048f0d9df6ce23c13dcc4f086551f8ce35138aa:pulse",
            sibling,
        )
        self.assertIn("33723065167", sibling)

    def test_fix_first_packet_is_external_blocker(self) -> None:
        packet = {
            "outcome": "external_blocker",
            "observed_broken": True,
            "finding_kind": "behavior",
            "expected_contract": (
                "repo-pulse.yml jobs pulse and slack_ingest fetch the engine "
                "over the API, run test_repo_pulse.py then repo_pulse.py, and "
                "run test_slack_ingest.py then slack_ingest.py sync on schedule"
            ),
            "repair_attempts": [
                "inspected repo-pulse.yml KEEP 1cfc97d0; no YAML defect, no billing skip",
                "local test_repo_pulse.py 32/32 PASS; test_slack_ingest.py 28/28 PASS",
                "test_sprint_integration.py ALL PASS; test_fix_first.py 6/6 PASS",
                "github rerun_failed_jobs 201; attempt 2 same billing refusal jobs 100771490023 100771490215",
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
