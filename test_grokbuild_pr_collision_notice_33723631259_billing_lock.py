#!/usr/bin/env python3
"""Pin unique leftover for pr-collision-notice run 33723631259. Do not remint helper or leftovers."""

from __future__ import annotations

import subprocess
import unittest
from pathlib import Path

import fix_first
import open_door_guard as guard
import pr_collision_notice as notice

ROOT = Path(__file__).resolve().parent
RECEIPT = ROOT / "p/grokbuild-pr-collision-notice-33723631259-billing-lock-20260903-01.md"
PRIOR = ROOT / "p/grokbuild-pr-collision-notice-33718116234-billing-lock-20260903-01.md"
PRIOR2 = ROOT / "p/grokbuild-pr-collision-notice-33717734032-billing-lock-20260903-01.md"
PRIOR3 = ROOT / "p/grokbuild-pr-collision-notice-33699939369-billing-lock-20260903-01.md"
ASSOCIATED = ROOT / "p/grok-build-repo-pulse-billing-lock-20260903-01.md"
PEER = ROOT / "p/grok-build-commons-board-billing-lock-20260903-01.md"
REMATCH = ROOT / "p/cursor-wire-catalog-marketplace-latch-readback-rematch-20260903-01.md"
WORKFLOW = ROOT / ".github/workflows/pr-collision-notice.yml"

KEEP = {
    "pr_collision_notice.py": "39dc815a",
    "test_pr_collision_notice.py": "a4890883",
    ".github/workflows/pr-collision-notice.yml": "b0a853dd",
    "p/grokbuild-pr-collision-notice-33689085107-billing-lock-20260902-01.md": "594b5e71",
    "test_grokbuild_pr_collision_notice_33689085107_billing_lock.py": "c6fb83fc",
    "p/grokbuild-pr-collision-notice-33689347426-billing-lock-20260902-01.md": "e92d45af",
    "test_grokbuild_pr_collision_notice_33689347426_billing_lock.py": "c9688953",
    "p/grokbuild-pr-collision-notice-33694241061-billing-lock-20260902-01.md": "71afa5e6",
    "test_grokbuild_pr_collision_notice_33694241061_billing_lock.py": "cec0f9dc",
    "p/grokbuild-pr-collision-notice-33699600937-billing-lock-20260903-01.md": "0fc75f49",
    "test_grokbuild_pr_collision_notice_33699600937_billing_lock.py": "590ee285",
    "p/grokbuild-pr-collision-notice-33699928196-billing-lock-20260903-01.md": "9b9b45f6",
    "test_grokbuild_pr_collision_notice_33699928196_billing_lock.py": "9ab12a5c",
    "p/grokbuild-pr-collision-notice-33699939369-billing-lock-20260903-01.md": "3110f1c7",
    "test_grokbuild_pr_collision_notice_33699939369_billing_lock.py": "b5434092",
    "p/grokbuild-pr-collision-notice-33717734032-billing-lock-20260903-01.md": "a558758f",
    "test_grokbuild_pr_collision_notice_33717734032_billing_lock.py": "29a93b08",
    "p/grokbuild-pr-collision-notice-33718116234-billing-lock-20260903-01.md": "0e641800",
    "test_grokbuild_pr_collision_notice_33718116234_billing_lock.py": "7419ed78",
    "p/grok-build-repo-pulse-billing-lock-20260903-01.md": "b6e5953c",
    "p/grok-build-commons-board-billing-lock-20260903-01.md": "c07bf913",
    "p/grok-build-moving-main-mirror-billing-lock-20260903-01.md": "4550e922",
    "p/cursor-wire-catalog-marketplace-latch-readback-rematch-20260903-01.md": "f23e1db8",
    "test_cursor_wire_catalog_marketplace_latch_readback_rematch.py": "6619e83b",
    "open_door_guard.py": "4b053e43",
    "test_open_door_guard.py": "70ee5730",
    "wire.html": "5b8edbda",
    "ground/WIRE_SUPER_MCP.md": "f36de0a5",
}


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class TestGrokbuildPrCollisionNotice33723631259BillingLock(unittest.TestCase):
    def test_keep_helper_prior_associated_and_peer_unread(self) -> None:
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
            guard.AddedLine("test_grokbuild_pr_collision_notice_33723631259_billing_lock.py", 1, line)
            for line in Path(__file__).read_text(encoding="utf-8").splitlines()
        ]
        self.assertEqual(guard.scan_added(added), [])

    def test_receipt_cites_run_and_does_not_steal(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        prior = PRIOR.read_text(encoding="utf-8")
        prior2 = PRIOR2.read_text(encoding="utf-8")
        prior3 = PRIOR3.read_text(encoding="utf-8")
        associated = ASSOCIATED.read_text(encoding="utf-8")
        peer = PEER.read_text(encoding="utf-8")
        rematch = REMATCH.read_text(encoding="utf-8")
        self.assertIn("grokbuild-pr-collision-notice-33723631259-billing-lock-20260903-01", text)
        self.assertIn(
            "woahwhattheheck/commons:pr-collision-notice:e50d0619c6916bfb5c12e360e3c38b4ca3a554fd:notice",
            text,
        )
        self.assertIn("33723631259", text)
        self.assertIn("100547766557", text)
        self.assertIn("100549245008", text)
        self.assertIn("e50d0619c6916bfb5c12e360e3c38b4ca3a554fd", text)
        self.assertIn("0c87db157b8e02aa90a3769df71b9b178e864112", text)
        self.assertIn(
            "The job was not started because your account is locked due to a billing issue.",
            text,
        )
        self.assertIn("EXTERNAL_BLOCKER", text)
        self.assertIn("594b5e71", text)
        self.assertIn("e92d45af", text)
        self.assertIn("71afa5e6", text)
        self.assertIn("0fc75f49", text)
        self.assertIn("9b9b45f6", text)
        self.assertIn("3110f1c7", text)
        self.assertIn("a558758f", text)
        self.assertIn("0e641800", text)
        self.assertIn("b6e5953c", text)
        self.assertIn("c07bf913", text)
        self.assertIn("4550e922", text)
        self.assertIn("f23e1db8", text)
        self.assertIn("b9dffb45", text)
        self.assertIn("39dc815a", text)
        self.assertIn("4ae38ce9", text)
        self.assertIn("f36de0a5", text)
        self.assertIn("Did not remint leftover grokbuild-pr-collision-notice-33689085107-billing-lock-20260902-01", text)
        self.assertIn("Did not remint leftover grokbuild-pr-collision-notice-33689347426-billing-lock-20260902-01", text)
        self.assertIn("Did not remint leftover grokbuild-pr-collision-notice-33694241061-billing-lock-20260902-01", text)
        self.assertIn("Did not remint leftover grokbuild-pr-collision-notice-33699600937-billing-lock-20260903-01", text)
        self.assertIn("Did not remint leftover grokbuild-pr-collision-notice-33699928196-billing-lock-20260903-01", text)
        self.assertIn("Did not remint leftover grokbuild-pr-collision-notice-33699939369-billing-lock-20260903-01", text)
        self.assertIn("Did not remint leftover grokbuild-pr-collision-notice-33717734032-billing-lock-20260903-01", text)
        self.assertIn("Did not remint leftover grokbuild-pr-collision-notice-33718116234-billing-lock-20260903-01", text)
        self.assertIn("Did not remint leftover grok-build-repo-pulse-billing-lock-20260903-01", text)
        self.assertIn("Did not remint rematch f23e1db8", text)
        self.assertIn("Did not reopen #7915", text)
        self.assertNotEqual(text, prior)
        self.assertNotEqual(text, prior2)
        self.assertNotEqual(text, prior3)
        self.assertNotEqual(text, associated)
        self.assertNotEqual(text, peer)
        self.assertNotEqual(text, rematch)
        self.assertNotIn(
            "pr-collision-notice:e50d0619c6916bfb5c12e360e3c38b4ca3a554fd:notice",
            prior,
        )
        self.assertNotIn(
            "pr-collision-notice:e50d0619c6916bfb5c12e360e3c38b4ca3a554fd:notice",
            associated,
        )
        self.assertNotIn(
            "pr-collision-notice:e50d0619c6916bfb5c12e360e3c38b4ca3a554fd:notice",
            rematch,
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
                "GitHub connector get_job_logs 404; annotations billing lock; runner_id=0; steps=[]; billable 0ms",
                "github rerun_failed_jobs 201; attempt 2 job 100549245008 same billing lock",
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
