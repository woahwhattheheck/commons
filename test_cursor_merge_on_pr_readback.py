#!/usr/bin/env python3
"""Pin independent readback of meeting item 6 leftover. Do not remint leftover or reopen #7915."""

from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RECEIPT = ROOT / "p/cursor-merge-on-pr-readback-20260902-01.md"
LEFTOVER = ROOT / "p/cursor-merge-on-pr-20260902-01.md"
HELPER = ROOT / "host/merge_on_pr.py"
DOOR = ROOT / "merge-on-pr.html"

KEEP = {
    "p/cursor-merge-on-pr-20260902-01.md": "22b63e25",
    "host/merge_on_pr.py": "0270094d",
    "ground/MERGE_ON_PR.json": "4e7967dc",
    "merge-on-pr.html": "86fe5e4f",
    "test_merge_on_pr.py": "8224c8cd",
    "host/sprint_integration.py": "b7bec0b9",
    "ground/SPRINT_INTEGRATION.json": "eba10870",
    "host/pr7915_closed_unmerged.py": "9d56ea0e",
    "test_pr7915_closed_unmerged.py": "195a38c0",
    "p/cursor-pr7915-closed-unmerged-readback-20260902-01.md": "2a7f31a4",
    "p/cursor-harborline-qualify-live-probe-20260902-01.md": "92c4e31f",
    "host/harborline_qualify_live_probe.py": "2c1797b2",
    "p/cursor-stealable-lanes-occupancy-20260902-01.md": "9631e869",
    "host/stealable_lanes.py": "c90284fb",
    "ground/STEALABLE_LANES.json": "b34e36c2",
    "p/cursor-stealable-lanes-occupancy-readback-20260902-01.md": "b2df1cf1",
    "p/cursor-pack-quality-dictates-tier-20260902-01.md": "f2054b18",
    "p/cursor-pack-quality-dictates-tier-readback-20260902-01.md": "aa5f6bbd",
    "p/grokbuild-pr8399-commons-slack-readback-20260902-01.md": "aaf290ad",
    "p/grok-build-discord-cloud-billing-lock-readback-20260902-01.md": "e14e443b",
    "p/cursor-mcp-get-grounding-readback-20260902-01.md": "4d7bc317",
    "hub_pages.py": "5ac12648",
    "door.js": "dc59355d",
    "api/mcp.py": "bc558a5f",
    "ground/OWNER_NOW.md": "59b1fd37",
    "autogtm.html": "9d8b3e85",
}


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


def run_helper(*flags: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["python3", str(HELPER), *flags],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


class TestCursorMergeOnPrReadback(unittest.TestCase):
    def test_keep_leftover_sprint_qualify_and_unread_packs(self) -> None:
        for rel, prefix in KEEP.items():
            blob = git_blob(rel)
            self.assertTrue(
                blob.startswith(prefix),
                f"{rel} reminted: want {prefix} got {blob[:8]}",
            )

    def test_leftover_json_still_renders_without_reopening_7915(self) -> None:
        proc = run_helper("--json")
        self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
        packet = json.loads(proc.stdout)
        self.assertEqual(packet["verdict"], "RENDER")
        self.assertTrue(packet["merge_default"])
        self.assertFalse(packet["stacked_worktrees"])
        self.assertFalse(packet["busy_main_is_stop"])
        self.assertFalse(packet["stale_base_is_stop"])
        self.assertFalse(packet["unrelated_checks_is_stop"])
        self.assertTrue(packet["sprint_self_test_ok"])
        self.assertEqual(packet["pr7915_leftover_state"], "MATCH")
        self.assertFalse(packet["pr7915_merged"])
        self.assertTrue(packet["pr7915_reopen_refused"])
        self.assertFalse(packet["pr7915_this_seat_reopen"])
        self.assertEqual(packet["sends"], 0)
        self.assertFalse(packet["invented_stripe_urls"])

    def test_leftover_reopen_merge_worktree_refused(self) -> None:
        for flag in ("--send", "--go", "--reopen", "--merge", "--worktree"):
            proc = run_helper(flag)
            self.assertEqual(proc.returncode, 2, msg=proc.stdout + proc.stderr)
            payload = json.loads(proc.stdout)
            self.assertEqual(payload["sent"], 0)
            self.assertEqual(payload["refused"], flag)
            self.assertFalse(payload["reopened"])
            self.assertFalse(payload["merged_7915"])
            self.assertFalse(payload["worktree_added"])

    def test_leftover_tests_still_pass(self) -> None:
        proc = subprocess.run(
            ["python3", "-m", "unittest", "test_merge_on_pr.py"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
        self.assertIn("Ran 6 tests", proc.stderr)

    def test_leftover_sprint_and_pr7915_still_match(self) -> None:
        sprint = subprocess.run(
            ["python3", "host/sprint_integration.py", "--self-test"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(sprint.returncode, 0, msg=sprint.stdout + sprint.stderr)
        self.assertIn("ok disjoint CLEAR_TO_MERGE", sprint.stdout)
        closed = subprocess.run(
            ["python3", "host/pr7915_closed_unmerged.py", "--json"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(closed.returncode, 0, msg=closed.stdout + closed.stderr)
        packet = json.loads(closed.stdout)
        self.assertEqual(packet["state"], "MATCH")
        self.assertFalse(packet["merged"])
        self.assertEqual(
            packet["head_sha"],
            "fa046ce059009f0ddece9d91eaa5d60a1f281f39",
        )
        self.assertFalse(packet["reopened"])

    def test_readback_receipt_exists_and_does_not_steal(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        leftover = LEFTOVER.read_text(encoding="utf-8")
        door = DOOR.read_text(encoding="utf-8")
        self.assertIn("cursor-merge-on-pr-readback-20260902-01", text)
        self.assertIn("8b42a78e0", text)
        self.assertIn("22b63e25", text)
        self.assertIn("0270094d", text)
        self.assertIn("Did **not** remint leftover id", text)
        self.assertIn("Did **not** reopen", text)
        self.assertIn("1788386939.481919", text)
        self.assertNotEqual(text, leftover)
        self.assertNotIn("buy.stripe.com", text)
        self.assertIn("No login", door)
        self.assertIn("fa046ce05900", door)
        self.assertFalse((ROOT / "marketplace.html").exists())
        self.assertFalse((ROOT / "qualify.html").exists())
        self.assertFalse((ROOT / "CLAUDE_CORNER.md").exists())


if __name__ == "__main__":
    unittest.main()
