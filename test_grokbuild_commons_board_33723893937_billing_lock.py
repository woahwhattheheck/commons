#!/usr/bin/env python3
"""Pin unique leftover for commons-board run 33723893937. Do not remint ingest tree or prior leftovers."""

from __future__ import annotations

import subprocess
import unittest
from pathlib import Path

import fix_first
import open_door_guard as guard

ROOT = Path(__file__).resolve().parent
# This receipt records this immutable tree; it does not freeze evolving main.
SOURCE_REV = "b80c62d7aa9bca8d71d023c2d078bbfd830d7311"
RECEIPT = ROOT / "p/grok-build-commons-board-33723893937-billing-lock-20260903-01.md"
PRIOR_BOARD = ROOT / "p/grok-build-commons-board-billing-lock-20260903-01.md"
PRIOR_MIRROR = ROOT / "p/grok-build-moving-main-mirror-billing-lock-20260903-01.md"
WORKFLOW = ROOT / ".github/workflows/commons-board.yml"

KEEP = {
    ".github/workflows/commons-board.yml": "ce1c2867",
    "board_ingest.py": "7c6c5b8c",
    "open_door_guard.py": "4b053e43",
    "fix_first.py": "a57aee1c",
    "p/grok-build-commons-board-billing-lock-20260903-01.md": "c07bf913",
    "p/grok-build-moving-main-mirror-billing-lock-20260903-01.md": "4550e922",
    "p/grok-build-repo-pulse-billing-lock-20260903-01.md": "b6e5953c",
    "p/grok-build-discord-cloud-billing-lock-20260902-01.md": "2e0bfbfb",
    "p/grok-resources-tab-freshness-billing-lock-20260902-01.md": "ac39fe78",
}


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "rev-parse", f"{SOURCE_REV}:{rel}"], cwd=ROOT, text=True
    ).strip()


class TestGrokbuildCommonsBoard33723893937BillingLock(unittest.TestCase):
    def test_keep_ingest_tree_and_prior_leftovers_unread(self) -> None:
        for rel, prefix in KEEP.items():
            blob = git_blob(rel)
            self.assertTrue(
                blob.startswith(prefix),
                f"{rel} reminted: want {prefix} got {blob[:8]}",
            )
        yml = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("name: commons-board", yml)
        self.assertIn("python3 board_ingest.py --publish", yml)
        self.assertIn("ubuntu-24.04-arm", yml)
        self.assertIn("runs-on: ubuntu-24.04-arm", yml)
        self.assertIn("issues:", yml)
        self.assertIn("types: [opened]", yml)
        self.assertNotIn("billing", yml.lower())
        self.assertNotIn("if: false", yml)
        self.assertNotIn("continue-on-error", yml)

    def test_receipt_is_unique_and_does_not_remint(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        prior_board = PRIOR_BOARD.read_text(encoding="utf-8")
        prior_mirror = PRIOR_MIRROR.read_text(encoding="utf-8")
        self.assertIn(
            "grok-build-commons-board-33723893937-billing-lock-20260903-01",
            text,
        )
        self.assertIn(
            "woahwhattheheck/commons:commons-board:f0a980053dae781f35e8723428d42aae64b7a5d3:ingest",
            text,
        )
        self.assertIn("33723893937", text)
        self.assertIn("100548561785", text)
        self.assertIn("100550307438", text)
        self.assertIn("f0a980053dae781f35e8723428d42aae64b7a5d3", text)
        self.assertIn("https://github.com/woahwhattheheck/commons/issues/8637", text)
        self.assertIn(
            "The job was not started because your account is locked due to a billing issue.",
            text,
        )
        self.assertIn("EXTERNAL_BLOCKER", text)
        self.assertIn(
            "Did not remint leftover grok-build-commons-board-billing-lock-20260903-01",
            text,
        )
        self.assertIn("c07bf913", text)
        self.assertIn("4550e922", text)
        self.assertIn("b6e5953c", text)
        self.assertIn("2e0bfbfb", text)
        self.assertIn("ac39fe78", text)
        self.assertIn("ce1c2867", text)
        self.assertIn("7c6c5b8c", text)
        self.assertIn("4b053e43", text)
        self.assertIn("a57aee1c", text)
        self.assertNotEqual(text, prior_board)
        self.assertNotEqual(text, prior_mirror)
        self.assertNotIn(
            "commons-board:f0a980053dae781f35e8723428d42aae64b7a5d3:ingest",
            prior_board,
        )
        self.assertNotIn(
            "commons-board:f0a980053dae781f35e8723428d42aae64b7a5d3:ingest",
            prior_mirror,
        )
        self.assertIn("33722889836", prior_board)

    def test_local_failed_step_still_passes(self) -> None:
        for mod in (
            "test_board_batch_drain.py",
            "test_board_issue_fanout.py",
            "test_ntfy_append_post_silent_drop.py",
            "test_enqueue_pending_grok_com.py",
            "test_fix_first.py",
        ):
            unit = subprocess.run(
                ["python3", "-m", "unittest", mod, "-q"],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(unit.returncode, 0, msg=mod + "\n" + unit.stdout + unit.stderr)
        added = [
            guard.AddedLine(
                "test_grokbuild_commons_board_33723893937_billing_lock.py",
                1,
                line,
            )
            for line in Path(__file__).read_text(encoding="utf-8").splitlines()
        ]
        added.extend(
            guard.AddedLine(
                "p/grok-build-commons-board-33723893937-billing-lock-20260903-01.md",
                1,
                line,
            )
            for line in RECEIPT.read_text(encoding="utf-8").splitlines()
        )
        self.assertEqual(guard.scan_added(added), [])

    def test_fix_first_packet_is_external_blocker(self) -> None:
        packet = {
            "outcome": "external_blocker",
            "observed_broken": True,
            "finding_kind": "behavior",
            "expected_contract": (
                "commons-board.yml job ingest on issues:opened checks out main, "
                "polls ntfy on ordinary issues, then python3 board_ingest.py --publish"
            ),
            "repair_attempts": [
                "inspected commons-board.yml KEEP ce1c2867; no YAML defect, no billing skip",
                "local test_board_batch_drain.py 6/6",
                "local test_board_issue_fanout.py 7/7",
                "local test_ntfy_append_post_silent_drop.py 6/6",
                "local test_enqueue_pending_grok_com.py 7/7",
                "local test_fix_first.py 6/6",
                "github rerun_failed_jobs; attempt 2 same billing refusal job 100550307438",
                "gmail_search GitHub billing lock empty",
                "GitHub Actions billing write road absent",
            ],
            "blocker": (
                "GitHub Actions ubuntu-24.04-arm never assigned: "
                "The job was not started because your account is locked due to a billing issue."
            ),
            "report_only_sessions": 0,
            "unconsumed_findings": 0,
        }
        self.assertEqual(fix_first.validate(packet)["state"], "EXTERNAL_BLOCKER")


if __name__ == "__main__":
    unittest.main()
