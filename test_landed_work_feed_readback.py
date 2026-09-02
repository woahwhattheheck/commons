#!/usr/bin/env python3
"""Pin unique-pack readback of landed-work feed leftover. Do not remint repo-pulse."""

from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RECEIPT = ROOT / "p/cursor-landed-work-feed-readback-20260902-01.md"
LEFTOVER = ROOT / "p/cursor-landed-work-feed-20260902-01.md"
HELPER = ROOT / "host/landed_work_feed.py"

KEEP = {
    "p/cursor-landed-work-feed-20260902-01.md": "d566f495",
    "host/landed_work_feed.py": "0506fd0f",
    "ground/LANDED_WORK_FEED.json": "4c42f69f",
    "test_landed_work_feed.py": "3f7919e0",
    "landed-work.html": "93cfe179",
    "repo_pulse.py": "5d716a63",
    "ground/OWNER_NOW.md": "59b1fd37",
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


class TestLandedWorkFeedReadback(unittest.TestCase):
    def test_keep_leftover_and_repo_pulse(self) -> None:
        for rel, prefix in KEEP.items():
            blob = git_blob(rel)
            self.assertTrue(
                blob.startswith(prefix),
                f"{rel} reminted: want {prefix} got {blob[:8]}",
            )

    def test_leftover_json_still_per_merge(self) -> None:
        proc = run_helper("--json", "--limit", "3")
        self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
        packet = json.loads(proc.stdout)
        self.assertEqual(packet["verdict"], "RENDER")
        self.assertEqual(packet["cadence"], "per-merge")
        self.assertTrue(packet["not_per_day"])
        self.assertEqual(packet["channel"], "C0BTVA3C0G3")
        self.assertEqual(packet["ride"], "commons-ship-enforcer")
        self.assertEqual(packet["sends"], 0)
        self.assertFalse(packet["invented_stripe_urls"])
        self.assertEqual(packet["unnamed_remainder"], "FINDER-FAILED")
        self.assertGreaterEqual(packet["count"], 1)
        first = packet["lines"][0]
        self.assertIn("woahwhattheheck/commons", first)
        self.assertIn("harness=", first)
        self.assertIn("paths=", first)

    def test_leftover_send_go_refused(self) -> None:
        for flag in ("--send", "--apply", "--go", "--autopilot"):
            proc = run_helper(flag)
            self.assertEqual(proc.returncode, 2, msg=proc.stdout + proc.stderr)
            payload = json.loads(proc.stdout)
            self.assertEqual(payload["sent"], 0)
            self.assertEqual(payload["cash"], 0)
            self.assertEqual(payload["refused"], flag)

    def test_leftover_tests_still_pass(self) -> None:
        proc = subprocess.run(
            ["python3", "-m", "unittest", "test_landed_work_feed.py"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
        self.assertIn("Ran 5 tests", proc.stderr)

    def test_readback_receipt_exists_and_does_not_steal(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        leftover = LEFTOVER.read_text(encoding="utf-8")
        self.assertIn("cursor-landed-work-feed-readback-20260902-01", text)
        self.assertIn("e53555ec3", text)
        self.assertIn("d566f495", text)
        self.assertIn("0506fd0f", text)
        self.assertIn("C0BTVA3C0G3", text)
        self.assertIn("Did not remint", text)
        self.assertIn("Did not invent Stripe URLs", text)
        self.assertNotEqual(text, leftover)
        self.assertNotIn("buy.stripe.com", text)
        self.assertFalse((ROOT / "marketplace.html").exists())
        self.assertFalse((ROOT / "qualify.html").exists())
        self.assertFalse((ROOT / "CLAUDE_CORNER.md").exists())


if __name__ == "__main__":
    unittest.main()
