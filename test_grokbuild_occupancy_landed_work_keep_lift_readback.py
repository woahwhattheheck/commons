#!/usr/bin/env python3
"""Pin unique-pack readback of occupancy KEEP-lift leftover. Do not remint occupancy."""

from __future__ import annotations

import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RECEIPT = ROOT / "p/grokbuild-occupancy-landed-work-keep-lift-readback-20260902-01.md"
LEFTOVER = ROOT / "p/grokbuild-occupancy-landed-work-keep-lift-20260902-01.md"

KEEP = {
    "p/grokbuild-occupancy-landed-work-keep-lift-20260902-01.md": "67a8a527",
    "test_grokbuild_occupancy_landed_work_keep_lift.py": "b65527ed",
    "p/cursor-stealable-lanes-occupancy-20260902-01.md": "9631e869",
    "host/stealable_lanes.py": "c90284fb",
    "p/cursor-stealable-lanes-roles-20260902-01.md": "5f1ef25f",
    "p/cursor-stealable-lanes-roles-readback-20260902-01.md": "ada92980",
    "p/cursor-stealable-lanes-occupancy-readback-20260902-01.md": "b2df1cf1",
    "p/cursor-landed-work-feed-20260902-01.md": "d566f495",
    "p/cursor-landed-work-feed-readback-20260902-01.md": "d37eb307",
    "p/grokbuild-pr8365-terminal-20260902-01.md": "212208a2",
    "p/grokbuild-repair-337-living-clear-20260902-01.md": "1884a299",
    "p/grokbuild-owner-now-337-closer-strip-20260902-01.md": "71135011",
    "p/grokbuild-pr8399-commons-slack-readback-20260902-01.md": "aaf290ad",
    "p/grok-build-discord-cloud-billing-lock-readback-20260902-01.md": "e14e443b",
    "p/cursor-mcp-get-grounding-readback-20260902-01.md": "4d7bc317",
    "p/cursor-merge-on-pr-20260902-01.md": "22b63e25",
    "p/cursor-harborline-qualify-live-probe-20260902-01.md": "92c4e31f",
    "ground/OWNER_NOW.md": "59b1fd37",
    "test_stealable_lanes.py": "a4d48d19",
    "test_stealable_lanes_occupancy.py": "92c23495",
    "test_landed_work_feed.py": "3f7919e0",
    "test_landed_work_feed_readback.py": "932ba427",
    "hub_pages.py": "5ac12648",
    "door.js": "dc59355d",
    "api/mcp.py": "bc558a5f",
    "autogtm.html": "9d8b3e85",
}


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class TestGrokbuildOccupancyLandedWorkKeepLiftReadback(unittest.TestCase):
    def test_keep_leftover_occupancy_and_unread_packs(self) -> None:
        for rel, prefix in KEEP.items():
            blob = git_blob(rel)
            self.assertTrue(
                blob.startswith(prefix),
                f"{rel} reminted: want {prefix} got {blob[:8]}",
            )

    def test_leftover_unique_tests_still_pass(self) -> None:
        proc = subprocess.run(
            [
                "python3",
                "-m",
                "unittest",
                "test_grokbuild_occupancy_landed_work_keep_lift.py",
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
        self.assertIn("Ran 4 tests", proc.stderr)

    def test_occupancy_leftover_tests_still_pass(self) -> None:
        proc = subprocess.run(
            ["python3", "-m", "unittest", "test_stealable_lanes_occupancy.py"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
        self.assertIn("Ran 4 tests", proc.stderr)

    def test_leftover_send_unrecognized_or_refused(self) -> None:
        proc = subprocess.run(
            ["python3", "host/stealable_lanes.py", "--send"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 2, msg=proc.stdout + proc.stderr)
        combined = (proc.stdout + proc.stderr).lower()
        self.assertIn("unrecognized arguments", combined)
        feed = subprocess.run(
            ["python3", "host/landed_work_feed.py", "--send"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(feed.returncode, 2, msg=feed.stdout + feed.stderr)
        self.assertIn('"sent": 0', feed.stdout)

    def test_readback_receipt_exists_and_does_not_steal(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        leftover = LEFTOVER.read_text(encoding="utf-8")
        self.assertIn("grokbuild-occupancy-landed-work-keep-lift-readback-20260902-01", text)
        self.assertIn("7badb00f7", text)
        self.assertIn("67a8a527", text)
        self.assertIn("Did **not** remint", text)
        self.assertIn("Did **not** unique-pack this seat leftover", text)
        self.assertIn("Did **not** unique-pack later billing-lock leftovers", text)
        self.assertIn("Did **not** ACK LEAD ACK", text)
        self.assertIn("721adc44", leftover)
        self.assertNotEqual(text, leftover)
        self.assertNotIn("buy.stripe.com", text)
        self.assertNotIn("cursor-merge-on-pr-readback-20260902-01", text)
        self.assertFalse((ROOT / "marketplace.html").exists())
        self.assertFalse((ROOT / "qualify.html").exists())
        self.assertFalse((ROOT / "CLAUDE_CORNER.md").exists())


if __name__ == "__main__":
    unittest.main()
