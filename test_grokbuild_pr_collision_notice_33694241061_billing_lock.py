#!/usr/bin/env python3
"""Pin unique leftover for pr-collision-notice run 33694241061. Do not remint helper or leftovers."""

from __future__ import annotations

import subprocess
import unittest
from pathlib import Path

import fix_first
import open_door_guard as guard
import pr_collision_notice as notice

ROOT = Path(__file__).resolve().parent
RECEIPT = ROOT / "p/grokbuild-pr-collision-notice-33694241061-billing-lock-20260902-01.md"
PRIOR = ROOT / "p/grokbuild-pr-collision-notice-33689347426-billing-lock-20260902-01.md"
PRIOR2 = ROOT / "p/grokbuild-pr-collision-notice-33689085107-billing-lock-20260902-01.md"
MATCH = ROOT / "p/cursor-goat-pages-super-mcp-land-readback-match-20260902-01.md"
WORKFLOW = ROOT / ".github/workflows/pr-collision-notice.yml"

KEEP = {
    "pr_collision_notice.py": "39dc815a",
    "test_pr_collision_notice.py": "a4890883",
    ".github/workflows/pr-collision-notice.yml": "b0a853dd",
    "p/grokbuild-pr-collision-notice-33689085107-billing-lock-20260902-01.md": "594b5e71",
    "test_grokbuild_pr_collision_notice_33689085107_billing_lock.py": "4888459d",
    "p/grokbuild-pr-collision-notice-33689347426-billing-lock-20260902-01.md": "e92d45af",
    "test_grokbuild_pr_collision_notice_33689347426_billing_lock.py": "ee80b28d",
    "p/goat-pages-super-mcp-land-20260902-01.md": "171e0daaf",
    "p/cursor-goat-pages-super-mcp-land-readback-match-20260902-01.md": "865b3c95",
    "test_cursor_goat_pages_super_mcp_land_readback_match.py": "dae1f645",
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


class TestGrokbuildPrCollisionNotice33694241061BillingLock(unittest.TestCase):
    def test_keep_helper_prior_and_goat_match_unread(self) -> None:
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
        added = [
            guard.AddedLine("test_grokbuild_pr_collision_notice_33694241061_billing_lock.py", 1, line)
            for line in Path(__file__).read_text(encoding="utf-8").splitlines()
        ]
        self.assertEqual(guard.scan_added(added), [])

    def test_receipt_cites_run_and_does_not_steal(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        prior = PRIOR.read_text(encoding="utf-8")
        prior2 = PRIOR2.read_text(encoding="utf-8")
        match = MATCH.read_text(encoding="utf-8")
        self.assertIn("grokbuild-pr-collision-notice-33694241061-billing-lock-20260902-01", text)
        self.assertIn(
            "woahwhattheheck/commons:pr-collision-notice:2065924780515cc5c3d2a20815cdab6584fcb517:notice",
            text,
        )
        self.assertIn("33694241061", text)
        self.assertIn("100459546285", text)
        self.assertIn("100461374957", text)
        self.assertIn("2065924780515cc5c3d2a20815cdab6584fcb517", text)
        self.assertIn("1fb31f62c6af944f339ced5665446891a91c95cd", text)
        self.assertIn(
            "The job was not started because your account is locked due to a billing issue.",
            text,
        )
        self.assertIn("EXTERNAL_BLOCKER", text)
        self.assertIn("594b5e71", text)
        self.assertIn("e92d45af", text)
        self.assertIn("171e0daaf", text)
        self.assertIn("865b3c95", text)
        self.assertIn("39dc815a", text)
        self.assertIn("Did not remint leftover grokbuild-pr-collision-notice-33689085107-billing-lock-20260902-01", text)
        self.assertIn("Did not remint leftover grokbuild-pr-collision-notice-33689347426-billing-lock-20260902-01", text)
        self.assertIn("Did not reopen #7915", text)
        self.assertNotEqual(text, prior)
        self.assertNotEqual(text, prior2)
        self.assertNotEqual(text, match)
        self.assertNotIn(
            "pr-collision-notice:2065924780515cc5c3d2a20815cdab6584fcb517:notice",
            prior,
        )
        self.assertNotIn(
            "pr-collision-notice:2065924780515cc5c3d2a20815cdab6584fcb517:notice",
            match,
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
                "GitHub connector get_job_logs 404; gh run rerun attempt 2 same billing refusal, runner_id=0",
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
