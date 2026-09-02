#!/usr/bin/env python3
"""Pin merge-on-PR leftover. Do not remint sprint-integration or reopen #7915."""

from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
HELPER = ROOT / "host/merge_on_pr.py"
RECEIPT = ROOT / "p/cursor-merge-on-pr-20260902-01.md"
CATALOG = ROOT / "ground/MERGE_ON_PR.json"
DOOR = ROOT / "merge-on-pr.html"

KEEP = {
    "host/sprint_integration.py": "b7bec0b9",
    "ground/SPRINT_INTEGRATION.json": "eba10870",
    "ground/SPRINT_INTEGRATION.md": "8d569755",
    "host/pr7915_closed_unmerged.py": "9d56ea0e",
    "test_pr7915_closed_unmerged.py": "195a38c0",
    "p/cursor-pr7915-closed-unmerged-readback-20260902-01.md": "2a7f31a4",
    "p/cursor-harborline-qualify-live-probe-20260902-01.md": "92c4e31f",
    "host/harborline_qualify_live_probe.py": "2c1797b2",
    "p/cursor-pack-quality-dictates-tier-20260902-01.md": "f2054b18",
    "host/pack_quality_dictates_tier.py": "74d36b0a",
    "p/cursor-pack-quality-dictates-tier-readback-20260902-01.md": "aa5f6bbd",
    "p/cursor-commons-slack-full-body-20260902-01.md": "86f4eddc",
    "p/cursor-since-you-last-looked-20260902-01.md": "003828c9",
    "p/cursor-landed-work-feed-20260902-01.md": "d566f495",
    "p/cursor-stealable-lanes-roles-20260902-01.md": "5f1ef25f",
    "p/cursor-stealable-lanes-occupancy-20260902-01.md": "9631e869",
    "hub_pages.py": "5ac12648",
    "door.js": "dc59355d",
    "api/mcp.py": "bc558a5f",
    "repo_pulse.py": "5d716a63",
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


class TestMergeOnPr(unittest.TestCase):
    def test_keep_sprint_pr7915_qualify_and_item12(self) -> None:
        for rel, prefix in KEEP.items():
            blob = git_blob(rel)
            self.assertTrue(
                blob.startswith(prefix),
                f"{rel} reminted: want {prefix} got {blob[:8]}",
            )

    def test_catalog_merge_default_no_worktree(self) -> None:
        data = json.loads(CATALOG.read_text(encoding="utf-8"))
        self.assertEqual(data["id"], "cursor-merge-on-pr-20260902-01")
        self.assertEqual(data["item"], 6)
        self.assertTrue(data["merge_default"])
        self.assertFalse(data["stacked_worktrees"])
        self.assertFalse(data["busy_main_is_stop"])
        self.assertFalse(data["stale_base_is_stop"])
        self.assertFalse(data["unrelated_checks_is_stop"])
        self.assertFalse(data["login"])
        self.assertFalse(data["gate"])
        self.assertTrue(data["pr7915"]["owner_said_merges"])
        self.assertFalse(data["pr7915"]["this_seat_reopen"])
        self.assertFalse(data["pr7915"]["this_seat_merge"])

    def test_json_renders_without_reopening_7915(self) -> None:
        proc = run_helper("--json")
        self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
        packet = json.loads(proc.stdout)
        self.assertEqual(packet["verdict"], "RENDER")
        self.assertTrue(packet["merge_default"])
        self.assertFalse(packet["stacked_worktrees"])
        self.assertFalse(packet["busy_main_is_stop"])
        self.assertFalse(packet["stale_base_is_stop"])
        self.assertFalse(packet["unrelated_checks_is_stop"])
        self.assertTrue(packet["ride_sprint_integration"])
        self.assertFalse(packet["remint_sprint_integration"])
        self.assertTrue(packet["sprint_self_test_ok"])
        self.assertEqual(packet["sprint_default"], "MERGE")
        self.assertTrue(packet["pr7915_owner_said_merges"])
        self.assertFalse(packet["pr7915_this_seat_reopen"])
        self.assertFalse(packet["pr7915_this_seat_merge"])
        self.assertEqual(packet["pr7915_leftover_state"], "MATCH")
        self.assertFalse(packet["pr7915_merged"])
        self.assertTrue(packet["pr7915_reopen_refused"])
        self.assertEqual(packet["sends"], 0)
        self.assertFalse(packet["invented_stripe_urls"])
        self.assertFalse(packet["login"])
        self.assertFalse(packet["gate"])

    def test_send_reopen_merge_worktree_refused(self) -> None:
        for flag in (
            "--send",
            "--apply",
            "--go",
            "--autopilot",
            "--reopen",
            "--merge",
            "--worktree",
        ):
            proc = run_helper(flag)
            self.assertEqual(proc.returncode, 2, msg=proc.stdout + proc.stderr)
            payload = json.loads(proc.stdout)
            self.assertEqual(payload["sent"], 0)
            self.assertEqual(payload["cash"], 0)
            self.assertEqual(payload["refused"], flag)
            self.assertFalse(payload["reopened"])
            self.assertFalse(payload["merged_7915"])
            self.assertFalse(payload["worktree_added"])
        proc = run_helper("--not-a-real-flag")
        self.assertEqual(proc.returncode, 1)
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["verdict"], "FINDER-FAILED")
        self.assertEqual(payload["sent"], 0)

    def test_leftover_sprint_self_test_still_ok(self) -> None:
        proc = subprocess.run(
            ["python3", "host/sprint_integration.py", "--self-test"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
        self.assertIn("ok disjoint CLEAR_TO_MERGE", proc.stdout)
        self.assertIn("ok semantic_conflict CONFLICT", proc.stdout)

    def test_receipt_and_door_do_not_steal(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        door = DOOR.read_text(encoding="utf-8")
        self.assertIn("cursor-merge-on-pr-20260902-01", text)
        self.assertIn("1788385254.638229", text)
        self.assertIn("Did not remint", text)
        self.assertIn("b7bec0b9", text)
        self.assertIn("9d56ea0e", text)
        self.assertIn("92c4e31f", text)
        self.assertIn("aa5f6bbd", text)
        self.assertNotIn("buy.stripe.com", text)
        self.assertIn("No login", door)
        self.assertIn("Merge", door)
        self.assertIn("fa046ce05900", door)
        self.assertIn("worktree", door.lower())
        self.assertNotIn("https://buy.stripe.com/", door)
        self.assertNotIn("oauth", door.lower())
        self.assertNotIn("api key", door.lower())
        self.assertFalse((ROOT / "qualify.html").exists())
        self.assertFalse((ROOT / "marketplace.html").exists())
        self.assertFalse((ROOT / "CLAUDE_CORNER.md").exists())


if __name__ == "__main__":
    unittest.main()
