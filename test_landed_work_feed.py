#!/usr/bin/env python3
"""Pin per-merge landed-work feed leftover. Do not remint repo-pulse."""

from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
HELPER = ROOT / "host/landed_work_feed.py"
RECEIPT = ROOT / "p/cursor-landed-work-feed-20260902-01.md"
CATALOG = ROOT / "ground/LANDED_WORK_FEED.json"
DOOR = ROOT / "landed-work.html"

KEEP = {
    "p/cursor-owner-now-readback-20260902-01.md": "1b3cd631",
    "p/cursor-owner-now-revenue-20260902-01.md": "fe5ba035",
    "p/cursor-owner-now-revenue-readback-20260902-01.md": "3449da29",
    "p/cursor-big-things-incoming-alert-20260902-01.md": "fde94226",
    "p/cursor-big-things-incoming-shots-20260902-01.md": "60b24eff",
    "p/cursor-big-things-incoming-shots-readback-20260902-01.md": "3cabb764",
    "p/cursor-incoming-models-hub-payload-20260902-01.md": "63aa4736",
    "p/cursor-incoming-models-hub-payload-readback-20260902-01.md": "2d297673",
    "p/cursor-harborline-pack-market-render-20260902-01.md": "54c348dc",
    "p/cursor-harborline-pack-market-render-readback-20260902-01.md": "6efbac54",
    "autogtm.html": "9d8b3e85",
    "hub_pages.py": "5ac12648",
    "repo_pulse.py": "5d716a63",
    "p/cursor-harborline-qualify-live-probe-20260902-01.md": "92c4e31f",
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


class TestLandedWorkFeed(unittest.TestCase):
    def test_keep_unique_packs_and_repo_pulse(self) -> None:
        for rel, prefix in KEEP.items():
            blob = git_blob(rel)
            self.assertTrue(
                blob.startswith(prefix),
                f"{rel} reminted: want {prefix} got {blob[:8]}",
            )

    def test_catalog_is_per_merge_not_per_day(self) -> None:
        data = json.loads(CATALOG.read_text(encoding="utf-8"))
        self.assertEqual(data["cadence"], "per-merge")
        self.assertTrue(data["not_per_day"])
        self.assertFalse(data["gate"])
        self.assertFalse(data["commons_admission"])
        self.assertEqual(data["channel"], "C0BTVA3C0G3")
        self.assertEqual(data["ride"], "commons-ship-enforcer")
        self.assertEqual(data["unnamed_remainder"], "FINDER-FAILED")
        self.assertFalse(data["twelve_named_here"])
        self.assertEqual(data["repos_named_here"], 6)

    def test_json_emits_one_line_per_merge(self) -> None:
        proc = run_helper("--json", "--limit", "3")
        self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
        packet = json.loads(proc.stdout)
        self.assertEqual(packet["verdict"], "RENDER")
        self.assertEqual(packet["cadence"], "per-merge")
        self.assertTrue(packet["not_per_day"])
        self.assertGreaterEqual(packet["count"], 1)
        self.assertEqual(len(packet["lines"]), packet["count"])
        first = packet["lines"][0]
        self.assertIn("woahwhattheheck/commons", first)
        self.assertIn("harness=", first)
        self.assertIn("paths=", first)
        self.assertNotIn("llms.txt+fresh.md", first)
        self.assertFalse(packet["invented_stripe_urls"])
        self.assertEqual(packet["sends"], 0)

    def test_send_go_refused(self) -> None:
        for flag in ("--send", "--apply", "--go", "--autopilot"):
            proc = run_helper(flag)
            self.assertEqual(proc.returncode, 2, msg=proc.stdout + proc.stderr)
            payload = json.loads(proc.stdout)
            self.assertEqual(payload["sent"], 0)
            self.assertEqual(payload["cash"], 0)
            self.assertEqual(payload["refused"], flag)

    def test_receipt_and_door_do_not_steal(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        door = DOOR.read_text(encoding="utf-8")
        self.assertIn("cursor-landed-work-feed-20260902-01", text)
        self.assertIn("per merge", text)
        self.assertIn("not per day", text)
        self.assertIn("C0BTVA3C0G3", text)
        self.assertIn("commons-ship-enforcer", text)
        self.assertIn("Did not remint", text)
        self.assertNotIn("buy.stripe.com", text)
        self.assertIn("per merge", door)
        self.assertNotIn("https://buy.stripe.com/", door)
        self.assertFalse((ROOT / "qualify.html").exists())
        self.assertFalse((ROOT / "marketplace.html").exists())
        self.assertFalse((ROOT / "CLAUDE_CORNER.md").exists())


if __name__ == "__main__":
    unittest.main()
