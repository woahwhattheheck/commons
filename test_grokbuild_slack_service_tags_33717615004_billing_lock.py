#!/usr/bin/env python3
"""Pin unique leftover for slack-service-tags run 33717615004. Do not remint tag contract or prior leftovers."""

from __future__ import annotations

import subprocess
import unittest
from pathlib import Path

import fix_first

ROOT = Path(__file__).resolve().parent
RECEIPT = ROOT / "p/grokbuild-slack-service-tags-33717615004-billing-lock-20260903-01.md"
PRIOR = ROOT / "p/grokbuild-harness-wakeup-33717474657-billing-lock-20260903-01.md"
KEEP_POST = ROOT / "p/cursor-slack-service-tags-20260902-01.md"
WORKFLOW = ROOT / ".github/workflows/slack-service-tags.yml"

KEEP = {
    ".github/workflows/slack-service-tags.yml": "490ee2c7",
    "host/slack_service_tag_worker.py": "9ef4cae7",
    "host/slack_service_tag.py": "fda35067",
    "test_slack_service_tag_worker.py": "61e405cc",
    "test_slack_service_tags.py": "5fee8c31",
    "open_door_guard.py": "4b053e43",
    "p/cursor-slack-service-tags-20260902-01.md": "4e8382f1",
    "p/cursor-slack-service-tags-peer-pointer-20260902-01.md": "6b13ba9a",
    "p/grokbuild-harness-wakeup-33717474657-billing-lock-20260903-01.md": "f54e1846",
    "test_grokbuild_harness_wakeup_33717474657_billing_lock.py": "760a8169",
    "p/grokbuild-main-range-verify-33717084528-billing-lock-20260903-01.md": "2b0fd9c9",
    "test_grokbuild_main_range_verify_33717084528_billing_lock.py": "3e89a404",
    "p/grokbuild-pr8546-verify-20260903-01.md": "4e4d8003",
    "p/grok-build-job-watchdog-33699286811-billing-lock-20260903-01.md": "81092ec2",
    "p/admin-owner-marks-20260902-01.md": "cdff4bfb",
}


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class TestGrokbuildSlackServiceTags33717615004BillingLock(unittest.TestCase):
    def test_keep_tag_contract_and_prior_leftovers_unread(self) -> None:
        for rel, prefix in KEEP.items():
            blob = git_blob(rel)
            self.assertTrue(
                blob.startswith(prefix),
                f"{rel} reminted: want {prefix} got {blob[:8]}",
            )
        yml = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("python3 -m unittest test_slack_service_tag_worker.py test_slack_service_tags.py", yml)
        self.assertIn("python3 host/slack_service_tag_worker.py --poll", yml)
        self.assertIn("group: slack-service-tags", yml)
        self.assertIn("cancel-in-progress: false", yml)
        self.assertIn('cron: "*/15 * * * *"', yml)
        self.assertNotIn("billing", yml.lower())
        self.assertNotIn("if: false", yml)

    def test_receipt_is_unique_and_does_not_remint(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        prior = PRIOR.read_text(encoding="utf-8")
        keep_post = KEEP_POST.read_text(encoding="utf-8")
        self.assertIn("grokbuild-slack-service-tags-33717615004-billing-lock-20260903-01", text)
        self.assertIn(
            "woahwhattheheck/commons:slack-service-tags:f13f3552dc3d8ad812cc6f26e48e97eb8cad9791:dispatch",
            text,
        )
        self.assertIn("33717615004", text)
        self.assertIn("100530002454", text)
        self.assertIn("100531477367", text)
        self.assertIn("f13f3552dc3d8ad812cc6f26e48e97eb8cad9791", text)
        self.assertIn("e2699ed63748e7be9d1820c4722d09c8eaf5c04f", text)
        self.assertIn(
            "The job was not started because your account is locked due to a billing issue.",
            text,
        )
        self.assertIn("EXTERNAL_BLOCKER", text)
        self.assertIn("Did not remint leftover grokbuild-harness-wakeup-33717474657-billing-lock-20260903-01", text)
        self.assertIn("f54e1846", text)
        self.assertIn("760a8169", text)
        self.assertIn("2b0fd9c9", text)
        self.assertIn("3e89a404", text)
        self.assertIn("4e4d8003", text)
        self.assertIn("81092ec2", text)
        self.assertIn("43c6e5cb", text)
        self.assertIn("4e8382f1", text)
        self.assertIn("6b13ba9a", text)
        self.assertIn("cdff4bfb", text)
        self.assertIn("490ee2c7", text)
        self.assertIn("9ef4cae7", text)
        self.assertIn("fda35067", text)
        self.assertIn("61e405cc", text)
        self.assertIn("5fee8c31", text)
        self.assertIn("4b053e43", text)
        self.assertIn("Did not reopen #7915", text)
        self.assertNotEqual(text, prior)
        self.assertNotEqual(text, keep_post)
        self.assertNotIn(
            "slack-service-tags:f13f3552dc3d8ad812cc6f26e48e97eb8cad9791:dispatch",
            prior,
        )
        self.assertNotIn(
            "slack-service-tags:f13f3552dc3d8ad812cc6f26e48e97eb8cad9791:dispatch",
            keep_post,
        )

    def test_local_tag_contract_still_passes(self) -> None:
        tests = subprocess.run(
            [
                "python3",
                "-m",
                "unittest",
                "test_slack_service_tag_worker.py",
                "test_slack_service_tags.py",
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(tests.returncode, 0, msg=tests.stdout + tests.stderr)
        self.assertIn("Ran 21 tests", tests.stderr)
        poll = subprocess.run(
            ["python3", "host/slack_service_tag_worker.py", "--poll"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            env={"PATH": "/usr/bin:/bin", "HOME": str(ROOT)},
            check=False,
        )
        self.assertEqual(poll.returncode, 0, msg=poll.stdout + poll.stderr)
        self.assertIn("idle: SLACK_BOT_TOKEN is not configured", poll.stdout)

    def test_fix_first_packet_is_external_blocker(self) -> None:
        packet = {
            "outcome": "external_blocker",
            "observed_broken": True,
            "finding_kind": "behavior",
            "expected_contract": (
                "slack-service-tags.yml job dispatch executes "
                "python3 -m unittest test_slack_service_tag_worker.py test_slack_service_tags.py "
                "then python3 host/slack_service_tag_worker.py --poll"
            ),
            "repair_attempts": [
                "local test_slack_service_tag_worker.py 8/8",
                "local test_slack_service_tags.py 13/13",
                "local host/slack_service_tag_worker.py --poll idle rc=0",
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
