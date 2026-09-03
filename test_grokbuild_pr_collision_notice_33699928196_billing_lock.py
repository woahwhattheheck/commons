#!/usr/bin/env python3
"""Pin unique leftover for pr-collision-notice run 33699928196. Do not remint helper or leftovers."""

from __future__ import annotations

import subprocess
import unittest
from pathlib import Path

import fix_first
import open_door_guard as guard
import pr_collision_notice as notice

ROOT = Path(__file__).resolve().parent
RECEIPT = ROOT / "p/grokbuild-pr-collision-notice-33699928196-billing-lock-20260903-01.md"
PRIOR = ROOT / "p/grokbuild-pr-collision-notice-33699600937-billing-lock-20260903-01.md"
PRIOR2 = ROOT / "p/grokbuild-pr-collision-notice-33694241061-billing-lock-20260902-01.md"
PRIOR3 = ROOT / "p/grokbuild-pr-collision-notice-33689347426-billing-lock-20260902-01.md"
PRIOR4 = ROOT / "p/grokbuild-pr-collision-notice-33689085107-billing-lock-20260902-01.md"
ASSOC = ROOT / "p/grokbuild-open-door-guard-33699286785-billing-lock-20260902-01.md"
WORKFLOW = ROOT / ".github/workflows/pr-collision-notice.yml"

KEEP = {
    "pr_collision_notice.py": "39dc815a",
    "test_pr_collision_notice.py": "a4890883",
    ".github/workflows/pr-collision-notice.yml": "b0a853dd",
    "p/grokbuild-pr-collision-notice-33689085107-billing-lock-20260902-01.md": "594b5e71",
    "test_grokbuild_pr_collision_notice_33689085107_billing_lock.py": "4888459d",
    "p/grokbuild-pr-collision-notice-33689347426-billing-lock-20260902-01.md": "e92d45af",
    "test_grokbuild_pr_collision_notice_33689347426_billing_lock.py": "ee80b28d",
    "p/grokbuild-pr-collision-notice-33694241061-billing-lock-20260902-01.md": "71afa5e6",
    "test_grokbuild_pr_collision_notice_33694241061_billing_lock.py": "bf6cbf7d",
    "p/grokbuild-pr-collision-notice-33699600937-billing-lock-20260903-01.md": "0fc75f49",
    "test_grokbuild_pr_collision_notice_33699600937_billing_lock.py": "92ba101c",
    "p/grokbuild-open-door-guard-33699286785-billing-lock-20260902-01.md": "d22e0707",
    "test_grokbuild_open_door_guard_33699286785_billing_lock.py": "96ce49fa",
    "open_door_guard.py": "4b053e43",
    "test_open_door_guard.py": "70ee5730",
}


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class TestGrokbuildPrCollisionNotice33699928196BillingLock(unittest.TestCase):
    def test_keep_helper_prior_and_assoc_unread(self) -> None:
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
            guard.AddedLine(
                "test_grokbuild_pr_collision_notice_33699928196_billing_lock.py", 1, line
            )
            for line in Path(__file__).read_text(encoding="utf-8").splitlines()
        ]
        self.assertEqual(guard.scan_added(added), [])
        receipt_added = [
            guard.AddedLine(
                "p/grokbuild-pr-collision-notice-33699928196-billing-lock-20260903-01.md",
                1,
                line,
            )
            for line in RECEIPT.read_text(encoding="utf-8").splitlines()
        ]
        self.assertEqual(guard.scan_added(receipt_added), [])

    def test_receipt_cites_run_and_does_not_steal(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        prior = PRIOR.read_text(encoding="utf-8")
        prior2 = PRIOR2.read_text(encoding="utf-8")
        prior3 = PRIOR3.read_text(encoding="utf-8")
        prior4 = PRIOR4.read_text(encoding="utf-8")
        assoc = ASSOC.read_text(encoding="utf-8")
        self.assertIn("grokbuild-pr-collision-notice-33699928196-billing-lock-20260903-01", text)
        self.assertIn(
            "woahwhattheheck/commons:pr-collision-notice:9f8c2487104f0bfce331eb89b2499aee3b95170f:notice",
            text,
        )
        self.assertIn("33699928196", text)
        self.assertIn("100476822235", text)
        self.assertIn("100477814553", text)
        self.assertIn("9f8c2487104f0bfce331eb89b2499aee3b95170f", text)
        self.assertIn("60d5e8fa13824c88d42138a39a9629d41818e4e6", text)
        self.assertIn(
            "The job was not started because your account is locked due to a billing issue.",
            text,
        )
        self.assertIn("EXTERNAL_BLOCKER", text)
        self.assertIn("594b5e71", text)
        self.assertIn("e92d45af", text)
        self.assertIn("71afa5e6", text)
        self.assertIn("0fc75f49", text)
        self.assertIn("d22e0707", text)
        self.assertIn("39dc815a", text)
        self.assertIn("Did not remint leftover grokbuild-pr-collision-notice-33689085107-billing-lock-20260902-01", text)
        self.assertIn("Did not remint leftover grokbuild-pr-collision-notice-33689347426-billing-lock-20260902-01", text)
        self.assertIn("Did not remint leftover grokbuild-pr-collision-notice-33694241061-billing-lock-20260902-01", text)
        self.assertIn("Did not remint leftover grokbuild-pr-collision-notice-33699600937-billing-lock-20260903-01", text)
        self.assertIn("Did not remint leftover grokbuild-open-door-guard-33699286785-billing-lock-20260902-01", text)
        self.assertIn("Did not reopen #7915", text)
        self.assertNotEqual(text, prior)
        self.assertNotEqual(text, prior2)
        self.assertNotEqual(text, prior3)
        self.assertNotEqual(text, prior4)
        self.assertNotEqual(text, assoc)
        self.assertNotEqual(Path(__file__).read_text(encoding="utf-8"), (ROOT / "test_grokbuild_pr_collision_notice_33699600937_billing_lock.py").read_text(encoding="utf-8"))
        self.assertNotIn(
            "pr-collision-notice:9f8c2487104f0bfce331eb89b2499aee3b95170f:notice",
            prior,
        )
        self.assertNotIn(
            "pr-collision-notice:9f8c2487104f0bfce331eb89b2499aee3b95170f:notice",
            assoc,
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
                "GitHub connector/gh get_job_logs 404 BlobNotFound; annotations billing lock; runner_id=0; steps=[]; billable 0ms",
                "gh run rerun --failed accepted; attempt 2 job 100477814553 same billing lock",
                "gh api user/settings/billing/actions 404; users/.../billing/actions 403; orgs/... 404",
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
