#!/usr/bin/env python3
"""Pin unique leftover for staleness-alarm run 33767754124. Do not remint alarm contract or prior leftovers."""

from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path

import fix_first

ROOT = Path(__file__).resolve().parent
RECEIPT = ROOT / "p/grokbuild-staleness-alarm-33767754124-billing-lock-20260903-01.md"
PRIOR = ROOT / "p/solder-staleness-alarm-landed-20260823-01.md"
KEEP_POST = ROOT / "p/grokbuild-harness-wakeup-33741135628-billing-lock-20260903-01.md"
WORKFLOW = ROOT / ".github/workflows/staleness-alarm.yml"

KEEP = {
    ".github/workflows/staleness-alarm.yml": "7c8aee71",
    "host_offload/staleness_alarm.py": "7c66eb31",
    "test_staleness_alarm.py": "168af224",
    "open_door_guard.py": "4b053e43",
    "p/solder-staleness-alarm-landed-20260823-01.md": "58e2ffec",
    "p/grokbuild-harness-wakeup-33741135628-billing-lock-20260903-01.md": "07fd32a5",
    "test_grokbuild_harness_wakeup_33741135628_billing_lock.py": "6ae4d101",
    "p/grokbuild-slack-service-tags-33741230551-billing-lock-20260903-01.md": "1e1d7999",
    "test_grokbuild_slack_service_tags_33741230551_billing_lock.py": "c89a60a1",
    "p/grokbuild-resources-tab-freshness-33767588782-billing-lock-20260903-01.md": "eca6f65c",
    "test_grokbuild_resources_tab_freshness_33767588782_billing_lock.py": "38cd74d1",
}


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class TestGrokbuildStalenessAlarm33767754124BillingLock(unittest.TestCase):
    def test_keep_alarm_contract_and_prior_leftovers_unread(self) -> None:
        for rel, prefix in KEEP.items():
            blob = git_blob(rel)
            self.assertTrue(
                blob.startswith(prefix),
                f"{rel} reminted: want {prefix} got {blob[:8]}",
            )
        yml = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("python3 test_staleness_alarm.py", yml)
        self.assertIn(
            "python3 host_offload/staleness_alarm.py --sync sync.json --send",
            yml,
        )
        self.assertIn('cron: "3,18,33,48 * * * *"', yml)
        self.assertNotIn("billing", yml.lower())
        self.assertNotIn("if: false", yml)

    def test_receipt_is_unique_and_does_not_remint(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        prior = PRIOR.read_text(encoding="utf-8")
        keep_post = KEEP_POST.read_text(encoding="utf-8")
        self.assertIn("grokbuild-staleness-alarm-33767754124-billing-lock-20260903-01", text)
        self.assertIn(
            "woahwhattheheck/commons:staleness-alarm:65696513919e99943eb71155c8ca813ecb6e2e54:alarm",
            text,
        )
        self.assertIn("33767754124", text)
        self.assertIn("100689853088", text)
        self.assertIn("100711105129", text)
        self.assertIn("65696513919e99943eb71155c8ca813ecb6e2e54", text)
        self.assertIn("687a3b2770afee473992887d021bdc3512596825", text)
        self.assertIn(
            "The job was not started because your account is locked due to a billing issue.",
            text,
        )
        self.assertIn("EXTERNAL_BLOCKER", text)
        self.assertIn("Did not remint leftover grokbuild-harness-wakeup-33741135628-billing-lock-20260903-01", text)
        self.assertIn("07fd32a5", text)
        self.assertIn("6ae4d101", text)
        self.assertIn("1e1d7999", text)
        self.assertIn("c89a60a1", text)
        self.assertIn("eca6f65c", text)
        self.assertIn("c048e4b8", text)
        self.assertIn("58e2ffec", text)
        self.assertIn("7c8aee71", text)
        self.assertIn("7c66eb31", text)
        self.assertIn("168af224", text)
        self.assertIn("4b053e43", text)
        self.assertIn("Did not reopen #7915", text)
        self.assertNotEqual(text, prior)
        self.assertNotEqual(text, keep_post)
        self.assertNotIn(
            "staleness-alarm:65696513919e99943eb71155c8ca813ecb6e2e54:alarm",
            prior,
        )
        self.assertNotIn(
            "staleness-alarm:65696513919e99943eb71155c8ca813ecb6e2e54:alarm",
            keep_post,
        )

    def test_local_alarm_contract_still_passes(self) -> None:
        tests = subprocess.run(
            ["python3", "test_staleness_alarm.py"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(tests.returncode, 0, msg=tests.stdout + tests.stderr)
        self.assertIn("Ran 8 tests", tests.stderr)
        send = subprocess.run(
            [
                "python3",
                "host_offload/staleness_alarm.py",
                "--sync",
                "sync.json",
                "--send",
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(send.returncode, 0, msg=send.stdout + send.stderr)
        payload = json.loads(send.stdout)
        self.assertEqual(payload.get("state"), "QUIET")
        self.assertEqual(payload.get("reason"), "sync.json absent")

    def test_fix_first_packet_is_external_blocker(self) -> None:
        packet = {
            "outcome": "external_blocker",
            "observed_broken": True,
            "finding_kind": "behavior",
            "expected_contract": (
                "staleness-alarm.yml job alarm executes python3 test_staleness_alarm.py "
                "then python3 host_offload/staleness_alarm.py --sync sync.json --send"
            ),
            "repair_attempts": [
                "local test_staleness_alarm.py 8/8",
                "local host_offload/staleness_alarm.py --sync sync.json --send QUIET rc=0",
                "github rerun_failed_jobs 201; attempt 2 same billing refusal",
                "GitHub Actions billing unlock is owner/provider work",
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
