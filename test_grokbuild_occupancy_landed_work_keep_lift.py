#!/usr/bin/env python3
"""Lift leftover KEEP freeze of leftover tests reminted by OWNER_NOW 337 strip."""
from __future__ import annotations

import importlib
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
UNPIN_RECEIPT = ROOT / "p/grokbuild-occupancy-landed-work-keep-lift-20260902-01.md"
CARD = ROOT / "ground/OWNER_NOW.md"
SIGNATURE = "337 NO"

KEEP_UNREAD = {
    "p/cursor-stealable-lanes-occupancy-20260902-01.md": "9631e869",
    "p/cursor-stealable-lanes-roles-20260902-01.md": "5f1ef25f",
    "host/stealable_lanes.py": "c90284fb",
    "p/cursor-landed-work-feed-20260902-01.md": "d566f495",
    "p/cursor-landed-work-feed-readback-20260902-01.md": "d37eb307",
    "p/grokbuild-pr8365-terminal-20260902-01.md": "212208a2",
    "p/grokbuild-repair-337-living-clear-20260902-01.md": "1884a299",
    "p/grokbuild-owner-now-337-closer-strip-20260902-01.md": "71135011",
    "ground/OWNER_NOW.md": "59b1fd37",
    "autogtm.html": "9d8b3e85",
    "p/cursor-harborline-qualify-live-probe-20260902-01.md": "92c4e31f",
    "p/cursor-owner-now-readback-20260902-01.md": "1b3cd631",
    "p/cursor-owner-now-revenue-20260902-01.md": "fe5ba035",
    "p/cursor-big-things-incoming-alert-20260902-01.md": "fde94226",
    "p/cursor-big-things-incoming-shots-20260902-01.md": "60b24eff",
    "p/cursor-incoming-models-hub-payload-20260902-01.md": "63aa4736",
}


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class GrokbuildOccupancyLandedWorkKeepLiftTest(unittest.TestCase):
    def test_leftover_keep_does_not_freeze_stale_leftover_tests(self) -> None:
        occupancy = importlib.import_module("test_stealable_lanes_occupancy")
        terminal = importlib.import_module("test_grokbuild_pr8365_terminal")
        self.assertNotEqual(
            occupancy.KEEP.get("test_stealable_lanes.py"), "721adc44"
        )
        self.assertNotEqual(terminal.KEEP.get("test_landed_work_feed.py"), "1c35b970")
        self.assertNotEqual(
            terminal.KEEP.get("test_landed_work_feed_readback.py"), "cb58ab08"
        )
        self.assertTrue(git_blob("test_stealable_lanes.py").startswith("a4d48d19"))
        self.assertTrue(git_blob("test_landed_work_feed.py").startswith("3f7919e0"))
        self.assertTrue(
            git_blob("test_landed_work_feed_readback.py").startswith("932ba427")
        )

    def test_living_owner_now_stays_clear_of_invented_signature(self) -> None:
        text = CARD.read_text(encoding="utf-8")
        self.assertNotIn(SIGNATURE, text)
        self.assertIn("invented closer was never Bryce law", text)
        self.assertTrue(git_blob("ground/OWNER_NOW.md").startswith("59b1fd37"))

    def test_lifted_leftover_tests_still_pass(self) -> None:
        for name in (
            "test_stealable_lanes_occupancy.py",
            "test_grokbuild_pr8365_terminal.py",
            "test_stealable_lanes.py",
            "test_landed_work_feed.py",
            "test_landed_work_feed_readback.py",
            "test_337_no_signature_absent_from_living_sources.py",
        ):
            proc = subprocess.run(
                ["python3", "-m", "unittest", name],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(proc.returncode, 0, msg=name + "\n" + proc.stdout + proc.stderr)

    def test_did_not_remint_unread_unique_packs(self) -> None:
        for rel, prefix in KEEP_UNREAD.items():
            blob = git_blob(rel)
            self.assertTrue(
                blob.startswith(prefix),
                f"{rel} reminted: want {prefix} got {blob[:8]}",
            )
        unpin = UNPIN_RECEIPT.read_text(encoding="utf-8")
        self.assertIn("id: grokbuild-occupancy-landed-work-keep-lift-20260902-01", unpin)
        self.assertIn("721adc44", unpin)
        self.assertIn("cb58ab08", unpin)
        self.assertIn("Did not remint", unpin)
        self.assertIn("#7915", unpin)
        self.assertIn("NOT_MINTED", unpin)
        self.assertFalse((ROOT / "qualify.html").exists())
        self.assertFalse((ROOT / "CLAUDE_CORNER.md").exists())
        self.assertFalse((ROOT / "marketplace.html").exists())


if __name__ == "__main__":
    unittest.main()
