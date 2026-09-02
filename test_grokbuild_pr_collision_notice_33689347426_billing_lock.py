#!/usr/bin/env python3
"""Pin unique leftover for pr-collision-notice run 33689347426. Do not remint helper or leftovers."""

from __future__ import annotations

import subprocess
import unittest
from pathlib import Path

import fix_first
import pr_collision_notice as notice

ROOT = Path(__file__).resolve().parent
RECEIPT = ROOT / "p/grokbuild-pr-collision-notice-33689347426-billing-lock-20260902-01.md"
PRIOR = ROOT / "p/grokbuild-pr-collision-notice-33689085107-billing-lock-20260902-01.md"
VERIFY = ROOT / "p/grokbuild-pr8409-verify-20260902-01.md"
WORKFLOW = ROOT / ".github/workflows/pr-collision-notice.yml"
DISCORD = ROOT / "p/grok-build-discord-cloud-billing-lock-20260902-01.md"

KEEP = {
    "pr_collision_notice.py": "39dc815a",
    "test_pr_collision_notice.py": "a4890883",
    ".github/workflows/pr-collision-notice.yml": "b0a853dd",
    "p/grokbuild-pr-collision-notice-33689085107-billing-lock-20260902-01.md": "594b5e71",
    "test_grokbuild_pr_collision_notice_33689085107_billing_lock.py": "4888459d",
    "p/grokbuild-pr8409-verify-20260902-01.md": "199cc075",
    "p/grok-build-discord-cloud-billing-lock-20260902-01.md": "2e0bfbfb",
    "p/grok-build-local-compute-guard-billing-lock-20260902-01.md": "de59bf75",
    "p/grokbuild-open-door-guard-33687124472-billing-lock-20260902-01.md": "b91a85d3",
    "p/grok-build-llms-txt-33687829181-billing-lock-20260902-01.md": "3183564c",
    "p/grok-build-llms-txt-billing-lock-20260902-01.md": "cf9c9f40",
    "p/grok-resources-tab-freshness-billing-lock-20260902-01.md": "ac39fe78",
    "open_door_guard.py": "4b053e43",
    "test_open_door_guard.py": "70ee5730",
}


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class TestGrokbuildPrCollisionNotice33689347426BillingLock(unittest.TestCase):
    def test_keep_helper_prior_and_pr8409_unread(self) -> None:
        for rel, prefix in KEEP.items():
            blob = git_blob(rel)
            self.assertTrue(
                blob.startswith(prefix),
                f"{rel} reminted: want {prefix} got {blob[:8]}",
            )
        yml = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("pull_request_target:", yml)
        self.assertNotIn("schedule:", yml)
        self.assertIn("ref: ${{ github.event.pull_request.base.sha }}", yml)
        self.assertNotIn("github.event.pull_request.head.sha", yml)
        self.assertIn("python3 pr_collision_notice.py", yml)
        self.assertNotIn("if: false", yml)
        self.assertNotIn("billing", yml.lower())

    def test_local_failed_step_still_passes(self) -> None:
        proc = subprocess.run(
            ["python3", "test_pr_collision_notice.py"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        out = (proc.stdout or "") + (proc.stderr or "")
        self.assertEqual(proc.returncode, 0, msg=out)
        self.assertIn("Ran 4 tests", out)
        self.assertIn("OK", out)
        rows = notice.find_pr_overlaps(
            10,
            {"alpha.py", "shared.json"},
            [
                {"number": 10, "html_url": "self", "title": "self"},
                {"number": 12, "html_url": "https://example.test/12", "title": "peer"},
            ],
            {12: [{"filename": "shared.json"}]},
        )
        self.assertEqual(len(rows), 1)
        body = notice.render_notice(10, "abc123", rows, [])
        self.assertIn("Advisory only", body)
        self.assertNotIn("block", body.lower().replace("never blocks", ""))

    def test_receipt_cites_run_and_does_not_steal(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        prior = PRIOR.read_text(encoding="utf-8")
        verify = VERIFY.read_text(encoding="utf-8")
        discord = DISCORD.read_text(encoding="utf-8")
        self.assertIn("grokbuild-pr-collision-notice-33689347426-billing-lock-20260902-01", text)
        self.assertIn(
            "woahwhattheheck/commons:pr-collision-notice:718682437ac745edaadd304b8199f28af3c4ad6d:notice",
            text,
        )
        self.assertIn("33689347426", text)
        self.assertIn("100444237231", text)
        self.assertIn("100445983482", text)
        self.assertIn("718682437ac745edaadd304b8199f28af3c4ad6d", text)
        self.assertIn("ffacc45de870c3e7f7890f0e8cd025d40dc619f4", text)
        self.assertIn(
            "The job was not started because your account is locked due to a billing issue.",
            text,
        )
        self.assertIn("EXTERNAL_BLOCKER", text)
        self.assertIn("594b5e71", text)
        self.assertIn("199cc075", text)
        self.assertIn("39dc815a", text)
        self.assertIn("Did not remint leftover grokbuild-pr-collision-notice-33689085107-billing-lock-20260902-01", text)
        self.assertIn("Did not reopen #7915", text)
        self.assertNotEqual(text, prior)
        self.assertNotEqual(text, verify)
        self.assertNotEqual(text, discord)
        self.assertNotIn(
            "pr-collision-notice:718682437ac745edaadd304b8199f28af3c4ad6d:notice",
            prior,
        )
        self.assertNotIn(
            "pr-collision-notice:718682437ac745edaadd304b8199f28af3c4ad6d:notice",
            verify,
        )
        self.assertNotIn("buy.stripe.com", text)

    def test_fix_first_packet_is_external_blocker(self) -> None:
        packet = {
            "outcome": "external_blocker",
            "observed_broken": True,
            "finding_kind": "behavior",
            "expected_contract": (
                "pr-collision-notice.yml job notice checks out base.sha and "
                "runs python3 pr_collision_notice.py on pull_request_target"
            ),
            "repair_attempts": [
                "local test_pr_collision_notice.py 4/4 OK",
                "workflow YAML valid; never executes PR head",
                "gh run rerun 33689347426 attempt 2 same billing refusal, runner empty",
                "gh api user/settings/billing/actions 404",
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
