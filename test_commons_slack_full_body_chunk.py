#!/usr/bin/env python3
"""Pin item 7 complementary remainder. Do not remint leftover Slack 5000 split."""

from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
HELPER = ROOT / "host/commons_slack_full_body_chunk.py"
RECEIPT = ROOT / "p/cursor-commons-slack-full-body-chunk-20260902-01.md"
LEFTOVER = ROOT / "p/cursor-commons-slack-full-body-20260902-01.md"
DOOR = ROOT / "commons-slack-chunk.html"

KEEP = {
    "host/commons_slack_full_body.py": "16ba0f4c",
    "p/cursor-commons-slack-full-body-20260902-01.md": "86f4eddc",
    "ground/COMMONS_SLACK_FULL_BODY.json": "d5dba5e8",
    "test_commons_slack_full_body.py": "7388c998",
    "host/slack_mirror.py": "8d3a5e0b",
    "slack_ingest.py": "0040a726",
    "test_slack_mirror.py": "201bca45",
    "commons-slack.html": "4cbca421",
    "p/cursor-stealable-lanes-occupancy-20260902-01.md": "9631e869",
    "p/cursor-merge-on-pr-20260902-01.md": "22b63e25",
    "p/cursor-pack-quality-dictates-tier-20260902-01.md": "f2054b18",
    "p/cursor-harborline-qualify-live-probe-20260902-01.md": "92c4e31f",
    "ground/OWNER_NOW.md": "59b1fd37",
    "host/landed_work_feed.py": "0506fd0f",
    "p/cursor-merge-on-pr-readback-20260902-01.md": "e160b2c3",
    "p/grokbuild-occupancy-landed-work-keep-lift-readback-20260902-01.md": "892bc4c0",
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


class TestCommonsSlackFullBodyChunk(unittest.TestCase):
    def test_keep_leftover_item_7_and_unread_packs(self) -> None:
        for rel, prefix in KEEP.items():
            blob = git_blob(rel)
            self.assertTrue(
                blob.startswith(prefix),
                f"{rel} reminted: want {prefix} got {blob[:8]}",
            )
        mirror = (ROOT / "host/slack_mirror.py").read_text(encoding="utf-8")
        self.assertIn("SLACK_LIMIT = 5000", mirror)

    def test_leftover_item_7_tests_still_pass(self) -> None:
        proc = subprocess.run(
            ["python3", "-m", "unittest", "test_commons_slack_full_body.py"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
        self.assertIn("Ran 7 tests", proc.stderr)

    def test_json_renders_4000_without_advancing_cursor(self) -> None:
        packet = json.loads(run_helper("--json").stdout)
        self.assertEqual(packet["verdict"], "RENDER", packet)
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
        first = packet["sample"]["first_line"]
        self.assertTrue(first.startswith("cursor-commons-slack-full-body-20260902-01 "))
        self.assertTrue(git_blob("p/cursor-commons-slack-full-body-20260902-01.md").startswith(first.split()[1][:8]))

    def test_long_body_splits_channel_and_thread(self) -> None:
        body = "PLAIN: long leftover body.\n\n" + ("word " * 1200)
        text = (
            "---\nfrom: UNSEATED\nto: TABLE\nid: cursor-slack-chunk-fixture-20260902-01\n"
            "kind: POST\nboard: TABLE\nsubject: fixture\n---\n\n"
            + body
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "cursor-slack-chunk-fixture-20260902-01.md"
            path.write_text(text, encoding="utf-8")
            proc = run_helper("--json", "--format", str(path))
            self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
            packed = json.loads(proc.stdout)
            self.assertLessEqual(packed["channel_chars"], 4000)
            self.assertGreater(packed["thread_parts"], 0)
            self.assertTrue(packed["channel"].startswith(packed["first_line"]))
            self.assertIn("cursor-slack-chunk-fixture-20260902-01", packed["first_line"])
            rebuilt = packed["channel"] + "".join(packed["thread_replies"])
            self.assertIn("PLAIN: long leftover body.", rebuilt)
            self.assertFalse(packed["cursor_advanced"])
            self.assertEqual(packed["sends"], 0)

    def test_send_go_refused_cursor_stays(self) -> None:
        for flag in ("--send", "--apply", "--go", "--autopilot"):
            proc = run_helper(flag)
            self.assertEqual(proc.returncode, 2, msg=proc.stdout + proc.stderr)
            payload = json.loads(proc.stdout)
            self.assertEqual(payload["sent"], 0)
            self.assertEqual(payload["cash"], 0)
            self.assertFalse(payload["cursor_advanced"])
            self.assertFalse(payload["confirmed_post"])
            self.assertEqual(payload["refused"], flag)

    def test_door_has_no_login_and_does_not_steal(self) -> None:
        proc = run_helper("--write")
        self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
        text = DOOR.read_text(encoding="utf-8")
        self.assertIn("No login", text)
        self.assertIn("Possessing the link is enough", text)
        self.assertIn("4000", text)
        self.assertNotIn("Authorization", text)
        receipt = RECEIPT.read_text(encoding="utf-8")
        leftover = LEFTOVER.read_text(encoding="utf-8")
        self.assertIn("cursor-commons-slack-full-body-chunk-20260902-01", receipt)
        self.assertIn("Did **not** remint leftover", receipt)
        self.assertIn("4000 vs 5000 is not a remint", receipt)
        self.assertNotEqual(receipt, leftover)
        self.assertIn("Unique leftover unique-pack of this seat leftover stays for other peers", receipt)
        self.assertNotIn("buy.stripe.com", receipt)
        self.assertFalse((ROOT / "marketplace.html").exists())
        self.assertFalse((ROOT / "qualify.html").exists())
        self.assertFalse((ROOT / "CLAUDE_CORNER.md").exists())


if __name__ == "__main__":
    unittest.main()
