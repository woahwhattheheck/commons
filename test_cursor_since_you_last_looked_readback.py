#!/usr/bin/env python3
"""Pin unique-pack readback of since-you-last-looked leftover. Do not remint Harborline paths."""

from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RECEIPT = ROOT / "p/cursor-since-you-last-looked-readback-20260902-01.md"
LEFTOVER = ROOT / "p/cursor-since-you-last-looked-20260902-01.md"
HELPER = ROOT / "host/since_you_last_looked.py"
DOOR = ROOT / "since-you-last-looked.html"

KEEP = {
    "p/cursor-since-you-last-looked-20260902-01.md": "003828c9",
    "host/since_you_last_looked.py": "3578783c",
    "ground/SINCE_YOU_LAST_LOOKED.json": "749c8220",
    "test_since_you_last_looked.py": "7a7cbdec",
    "since-you-last-looked.html": "286328ed",
    "p/cursor-landed-work-feed-20260902-01.md": "d566f495",
    "host/landed_work_feed.py": "0506fd0f",
    "p/cursor-stealable-lanes-occupancy-20260902-01.md": "9631e869",
    "p/cursor-stealable-lanes-roles-20260902-01.md": "5f1ef25f",
    "p/cursor-stealable-lanes-roles-readback-20260902-01.md": "ada92980",
    "p/cursor-commons-slack-full-body-20260902-01.md": "86f4eddc",
    "p/cursor-harborline-pack-market-render-20260902-01.md": "54c348dc",
    "ground/OWNER_NOW.md": "59b1fd37",
    "grounding.html": "abb91caf",
    "autogtm.html": "9d8b3e85",
    "hub_pages.py": "5ac12648",
    "door.js": "dc59355d",
    "api/mcp.py": "bc558a5f",
    "repo_pulse.py": "5d716a63",
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


class TestCursorSinceYouLastLookedReadback(unittest.TestCase):
    def test_keep_leftover_and_unread_packs(self) -> None:
        for rel, prefix in KEEP.items():
            blob = git_blob(rel)
            self.assertTrue(
                blob.startswith(prefix),
                f"{rel} reminted: want {prefix} got {blob[:8]}",
            )

    def test_leftover_json_still_groups_and_pins_bryce(self) -> None:
        proc = run_helper("--json", "--limit", "8")
        self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
        packet = json.loads(proc.stdout)
        self.assertEqual(packet["verdict"], "RENDER")
        self.assertEqual(packet["grouped_by"], ["git", "slack", "commons"])
        self.assertTrue(packet["nothing_dropped"])
        self.assertFalse(packet["model_decides_what_matters"])
        self.assertTrue(packet["not_per_merge_line"])
        self.assertGreaterEqual(packet["counts"]["git"], 1)
        self.assertGreaterEqual(packet["counts"]["slack"], 5)
        self.assertGreaterEqual(packet["counts"]["commons"], 1)
        self.assertEqual(packet["surfaces"]["slack"][0]["ts"], "1788380844.707619")
        self.assertTrue(packet["surfaces"]["slack"][0]["bryce_pin"])
        self.assertEqual(packet["bryce_pinned"], 1)
        self.assertEqual(packet["dropped"], 0)
        self.assertEqual(packet["slack_live_token"], "FINDER-FAILED")
        self.assertEqual(packet["sends"], 0)
        self.assertFalse(packet["invented_stripe_urls"])

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
            ["python3", "-m", "unittest", "test_since_you_last_looked.py"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
        self.assertIn("Ran 6 tests", proc.stderr)

    def test_readback_receipt_exists_and_does_not_steal(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        leftover = LEFTOVER.read_text(encoding="utf-8")
        door = DOOR.read_text(encoding="utf-8")
        self.assertIn("cursor-since-you-last-looked-readback-20260902-01", text)
        self.assertIn("15986f8a0", text)
        self.assertIn("003828c9", text)
        self.assertIn("3578783c", text)
        self.assertIn("Did **not** remint", text)
        self.assertIn("Did **not** take item 11", text)
        self.assertNotEqual(text, leftover)
        self.assertNotIn("buy.stripe.com", text)
        self.assertIn("I looked", door)
        self.assertIn("col-git", door)
        self.assertIn("col-slack", door)
        self.assertIn("col-commons", door)
        self.assertFalse((ROOT / "marketplace.html").exists())
        self.assertFalse((ROOT / "qualify.html").exists())
        self.assertFalse((ROOT / "CLAUDE_CORNER.md").exists())


if __name__ == "__main__":
    unittest.main()
