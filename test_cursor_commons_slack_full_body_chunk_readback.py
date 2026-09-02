#!/usr/bin/env python3
"""Pin unique-pack readback of item 7 complementary remainder. Do not remint leftover."""

from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RECEIPT = ROOT / "p/cursor-commons-slack-full-body-chunk-readback-20260902-01.md"
LEFTOVER = ROOT / "p/cursor-commons-slack-full-body-chunk-20260902-01.md"
HELPER = ROOT / "host/commons_slack_full_body_chunk.py"
DOOR = ROOT / "commons-slack-chunk.html"

KEEP = {
    "p/cursor-commons-slack-full-body-chunk-20260902-01.md": "94770f41",
    "host/commons_slack_full_body_chunk.py": "f4fef7e6",
    "ground/COMMONS_SLACK_FULL_BODY_CHUNK.json": "5c2b1bf7",
    "test_commons_slack_full_body_chunk.py": "73593be6",
    "commons-slack-chunk.html": "986a1a2c",
    "host/commons_slack_full_body.py": "16ba0f4c",
    "p/cursor-commons-slack-full-body-20260902-01.md": "86f4eddc",
    "ground/COMMONS_SLACK_FULL_BODY.json": "d5dba5e8",
    "test_commons_slack_full_body.py": "7388c998",
    "host/slack_mirror.py": "8d3a5e0b",
    "test_slack_mirror.py": "201bca45",
    "commons-slack.html": "4cbca421",
    "p/cursor-stealable-lanes-occupancy-20260902-01.md": "9631e869",
    "p/cursor-merge-on-pr-20260902-01.md": "22b63e25",
    "p/cursor-merge-on-pr-readback-20260902-01.md": "e160b2c3",
    "p/cursor-pack-quality-dictates-tier-20260902-01.md": "f2054b18",
    "p/cursor-harborline-qualify-live-probe-20260902-01.md": "92c4e31f",
    "p/grokbuild-occupancy-landed-work-keep-lift-readback-20260902-01.md": "892bc4c0",
    "hub_pages.py": "5ac12648",
    "door.js": "dc59355d",
    "api/mcp.py": "bc558a5f",
    "ground/OWNER_NOW.md": "59b1fd37",
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


class TestCursorCommonsSlackFullBodyChunkReadback(unittest.TestCase):
    def test_keep_leftover_chunk_and_unread_packs(self) -> None:
        for rel, prefix in KEEP.items():
            blob = git_blob(rel)
            self.assertTrue(
                blob.startswith(prefix),
                f"{rel} reminted: want {prefix} got {blob[:8]}",
            )
        mirror = (ROOT / "host/slack_mirror.py").read_text(encoding="utf-8")
        self.assertIn("SLACK_LIMIT = 5000", mirror)

    def test_leftover_json_still_renders_4000_without_advancing(self) -> None:
        proc = run_helper("--json")
        self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
        packet = json.loads(proc.stdout)
        self.assertEqual(packet["verdict"], "RENDER")
        self.assertEqual(packet["channel_limit"], 4000)
        self.assertEqual(packet["leftover_slack_limit_keep"], 5000)
        self.assertTrue(packet["remainder_as_thread"])
        self.assertTrue(packet["id_and_sha_first_line"])
        self.assertTrue(packet["cursor_advances_only_after_confirmed_post"])
        self.assertTrue(packet["five_minute_job"])
        self.assertFalse(packet["login"])
        self.assertFalse(packet["gate"])
        self.assertFalse(packet["new_token"])
        self.assertFalse(packet["cursor_advanced"])
        self.assertFalse(packet["confirmed_post"])
        self.assertEqual(packet["sends"], 0)
        self.assertFalse(packet["invented_stripe_urls"] if "invented_stripe_urls" in packet else False)

    def test_leftover_send_go_refused_cursor_stays(self) -> None:
        for flag in ("--send", "--apply", "--go", "--autopilot"):
            proc = run_helper(flag)
            self.assertEqual(proc.returncode, 2, msg=proc.stdout + proc.stderr)
            payload = json.loads(proc.stdout)
            self.assertEqual(payload["sent"], 0)
            self.assertEqual(payload["refused"], flag)
            self.assertFalse(payload["cursor_advanced"])
            self.assertFalse(payload["confirmed_post"])

    def test_leftover_unique_and_item7_tests_still_pass(self) -> None:
        chunk = subprocess.run(
            ["python3", "-m", "unittest", "test_commons_slack_full_body_chunk.py"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(chunk.returncode, 0, msg=chunk.stdout + chunk.stderr)
        self.assertIn("Ran 6 tests", chunk.stderr)
        leftover = subprocess.run(
            ["python3", "-m", "unittest", "test_commons_slack_full_body.py"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(leftover.returncode, 0, msg=leftover.stdout + leftover.stderr)
        self.assertIn("Ran 7 tests", leftover.stderr)
        mirror = subprocess.run(
            ["python3", "-m", "unittest", "test_slack_mirror.py"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(mirror.returncode, 0, msg=mirror.stdout + mirror.stderr)
        self.assertIn("Ran 3 tests", mirror.stderr)

    def test_readback_receipt_exists_and_does_not_steal(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        leftover = LEFTOVER.read_text(encoding="utf-8")
        door = DOOR.read_text(encoding="utf-8")
        self.assertIn("cursor-commons-slack-full-body-chunk-readback-20260902-01", text)
        self.assertIn("5a74718f2", text)
        self.assertIn("94770f41", text)
        self.assertIn("f4fef7e6", text)
        self.assertIn("16ba0f4c", text)
        self.assertIn("8d3a5e0b", text)
        self.assertIn("Did **not** remint leftover id", text)
        self.assertIn("1788387772.635129", text)
        self.assertNotEqual(text, leftover)
        self.assertNotIn("buy.stripe.com", text)
        self.assertIn("No login", door)
        self.assertIn("4000", door)
        self.assertFalse((ROOT / "marketplace.html").exists())
        self.assertFalse((ROOT / "qualify.html").exists())
        self.assertFalse((ROOT / "CLAUDE_CORNER.md").exists())
        self.assertFalse((ROOT / "p/cursor-commons-slack-4000-cursor-20260902-01.md").exists())


if __name__ == "__main__":
    unittest.main()
