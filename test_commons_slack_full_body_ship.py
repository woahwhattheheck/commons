#!/usr/bin/env python3
"""SHIP leftover Commons ↔ Slack full-body. Do not remint leftover or slack_mirror."""

from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
HELPER = ROOT / "host/commons_slack_full_body_ship.py"
RECEIPT = ROOT / "p/cursor-commons-slack-full-body-ship-20260902-01.md"
LEFTOVER = ROOT / "p/cursor-commons-slack-full-body-20260902-01.md"

KEEP = {
    "p/cursor-commons-slack-full-body-20260902-01.md": "86f4eddc",
    "host/commons_slack_full_body.py": "16ba0f4c",
    "test_commons_slack_full_body.py": "7388c998",
    "ground/COMMONS_SLACK_FULL_BODY.json": "d5dba5e8",
    "ground/COMMONS_SLACK_FULL_BODY.md": "f23df2ec",
    "commons-slack.html": "4cbca421",
    "host/slack_mirror.py": "8d3a5e0b",
    "slack_ingest.py": "0040a726",
    "test_slack_mirror.py": "201bca45",
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


class TestCommonsSlackFullBodyShip(unittest.TestCase):
    def test_keep_leftover_and_slack_mirror_exact(self) -> None:
        for rel, prefix in KEEP.items():
            blob = git_blob(rel)
            self.assertTrue(
                blob.startswith(prefix),
                f"{rel} reminted: want {prefix} got {blob[:8]}",
            )

    def test_ship_receipt_cites_leftover_without_remint(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        leftover = LEFTOVER.read_text(encoding="utf-8")
        self.assertIn("cursor-commons-slack-full-body-ship-20260902-01", text)
        self.assertIn("cursor-commons-slack-full-body-20260902-01", text)
        self.assertIn("cee208ea8", text)
        self.assertIn("86f4eddc", text)
        self.assertIn("2416", text)
        self.assertIn("2aaecb01", text)
        self.assertIn("8d3a5e0b", text)
        self.assertIn("7/7", text)
        self.assertIn("bc-7e34a47c", text)
        self.assertIn("bc-73365238", text)
        self.assertIn("two-way", text)
        self.assertIn("Did not remint", text)
        self.assertIn("NOT_MINTED", text)
        self.assertIn("Sends 0", text)
        self.assertIn("No login", text)
        self.assertNotEqual(text, leftover)
        self.assertNotIn("buy.stripe.com", text)
        self.assertFalse((ROOT / "marketplace.html").exists())
        self.assertFalse((ROOT / "CLAUDE_CORNER.md").exists())

    def test_send_apply_go_refused(self) -> None:
        for flag in ("--send", "--apply", "--go", "--autopilot"):
            proc = run_helper(flag)
            self.assertEqual(proc.returncode, 2, msg=proc.stdout + proc.stderr)
            payload = json.loads(proc.stdout)
            self.assertEqual(payload["sent"], 0)
            self.assertEqual(payload["cash"], 0)
            self.assertEqual(payload["refused"], flag)
            self.assertFalse(payload["new_token"])

    def test_unknown_args_finder_failed_not_zero(self) -> None:
        proc = run_helper("--not-a-real-flag")
        self.assertEqual(proc.returncode, 1)
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["sent"], 0)
        self.assertEqual(payload["verdict"], "FINDER-FAILED")

    def test_ship_classifies_leftover_on_current_main(self) -> None:
        proc = run_helper("--json")
        self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertTrue(payload["ship_ok"])
        self.assertEqual(payload["verdict"], "SHIP")
        self.assertEqual(
            payload["leftover_id"],
            "cursor-commons-slack-full-body-20260902-01",
        )
        self.assertEqual(payload["land"], "cee208ea8")
        self.assertEqual(payload["leftover_tests"], "7/7")
        self.assertEqual(payload["send_rc"], 2)
        self.assertEqual(payload["go_rc"], 2)
        self.assertEqual(payload["sent"], 0)
        self.assertEqual(payload["cash"], 0)
        self.assertEqual(payload["checkout"], "NOT_MINTED")
        self.assertTrue(payload["two_way"])
        self.assertTrue(payload["instant"])
        self.assertTrue(payload["posts_not_receipts"])
        self.assertTrue(payload["full_body"])
        self.assertFalse(payload["new_token"])
        self.assertFalse(payload["login"])
        self.assertFalse(payload["gate"])
        self.assertTrue(payload["did_not_remint_leftover"])
        self.assertTrue(payload["did_not_remint_slack_mirror"])
        self.assertEqual(payload["keep_blobs"]["host/slack_mirror.py"], "8d3a5e0b")


if __name__ == "__main__":
    unittest.main()
