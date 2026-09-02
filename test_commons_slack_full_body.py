#!/usr/bin/env python3
"""Pin unique Commons ↔ Slack full-body leftover. Do not remint slack_mirror."""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "host"))

import commons_slack_full_body as cs  # noqa: E402

RECEIPT = ROOT / "p/cursor-commons-slack-full-body-20260902-01.md"
HELPER = ROOT / "host/commons_slack_full_body.py"
DOOR = ROOT / "commons-slack.html"

KEEP = {
    "host/slack_mirror.py": "8d3a5e0b",
    "slack_ingest.py": "0040a726",
    "test_slack_mirror.py": "201bca45",
    "host/landed_work_feed.py": "0506fd0f",
    "repo_pulse.py": "5d716a63",
    "p/cursor-stealable-lanes-roles-20260902-01.md": "5f1ef25f",
    "p/cursor-stealable-lanes-roles-readback-20260902-01.md": "ada92980",
    "p/cursor-stealable-lanes-occupancy-20260902-01.md": "9631e869",
    "p/cursor-landed-work-feed-20260902-01.md": "d566f495",
    "lanes.json": "703ef113",
    "roles.json": "9fb3f2c2",
    "ground/HEAVY_LANES.json": "7849eac9",
    "autogtm.html": "9d8b3e85",
    "hub_pages.py": "5ac12648",
    "door.js": "dc59355d",
    "api/mcp.py": "bc558a5f",
    "p/cursor-harborline-pack-market-render-20260902-01.md": "54c348dc",
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


class TestCommonsSlackFullBody(unittest.TestCase):
    def test_keep_slack_mirror_ingest_and_unique_packs(self) -> None:
        for rel, prefix in KEEP.items():
            blob = git_blob(rel)
            self.assertTrue(
                blob.startswith(prefix),
                f"{rel} reminted: want {prefix} got {blob[:8]}",
            )

    def test_check_passes_two_way_without_lock(self) -> None:
        result = cs.check()
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["cash_usd"], 0)
        self.assertEqual(result["sends"], 0)
        packet = json.loads(run_helper("--json").stdout)
        self.assertEqual(packet["verdict"], "RENDER")
        self.assertTrue(packet["two_way"])
        self.assertTrue(packet["instant"])
        self.assertTrue(packet["posts_not_receipts"])
        self.assertTrue(packet["full_body"])
        self.assertFalse(packet["new_token"])
        self.assertFalse(packet["login"])
        self.assertFalse(packet["gate"])
        self.assertFalse(packet["slack_ts_is_commons_id"])
        self.assertFalse(packet["channel_is_allowlist"])
        self.assertTrue(packet["grok_com_prose_parity"])
        self.assertEqual(packet["default_table"], "C0BRGMDQB6G")
        self.assertEqual(packet["sends"], 0)

    def test_commons_to_slack_is_full_body_via_leftover_formatter(self) -> None:
        packed = cs.commons_to_slack(RECEIPT)
        text = RECEIPT.read_text(encoding="utf-8")
        self.assertIn("PLAIN:", packed["payload"])
        self.assertIn("two-way", packed["payload"])
        self.assertTrue(packed["payload"].endswith(cs.sm.body_of(text)) or packed["body"] in packed["payload"])
        self.assertIn(cs.sm.body_of(text).strip().splitlines()[0], packed["payload"])
        self.assertGreater(packed["char_count"], 200)
        self.assertFalse(packed["new_token"])

    def test_slack_to_commons_preserves_body_and_rejects_ts_as_id(self) -> None:
        body = "PLAIN: full Slack text stays on Commons.\n\nSecond paragraph stays too.\n"
        packed = cs.slack_to_commons(
            text=body,
            post_id="cursor-slack-to-commons-fixture-20260902-01",
            channel="C0BRGMDQB6G",
            ts="1788384217.141669",
        )
        self.assertTrue(packed["ok"], packed)
        self.assertFalse(packed["slack_ts_is_commons_id"])
        self.assertIn("PLAIN: full Slack text stays on Commons.", packed["post"])
        self.assertIn("Second paragraph stays too.", packed["post"])
        self.assertIn("kind: POST", packed["post"])
        self.assertNotEqual(packed["id"], packed["ts"])
        stolen = cs.slack_to_commons(
            text=body,
            post_id="1788384217.141669",
            ts="1788384217.141669",
        )
        self.assertFalse(stolen["ok"])
        self.assertIn("slack-ts-as-commons-id", stolen["errors"])
        empty = cs.slack_to_commons(text="   ", post_id="cursor-slack-empty-body-20260902-01")
        self.assertFalse(empty["ok"])
        self.assertIn("empty-slack-body", empty["errors"])

    def test_send_go_refused(self) -> None:
        for flag in ("--send", "--apply", "--go", "--autopilot"):
            proc = run_helper(flag)
            self.assertEqual(proc.returncode, 2, msg=proc.stdout + proc.stderr)
            payload = json.loads(proc.stdout)
            self.assertEqual(payload["sent"], 0)
            self.assertEqual(payload["cash"], 0)
            self.assertEqual(payload["refused"], flag)
            self.assertFalse(payload["new_token"])

    def test_leftover_slack_mirror_tests_still_pass(self) -> None:
        proc = subprocess.run(
            ["python3", "-m", "unittest", "test_slack_mirror.py"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
        self.assertIn("Ran 3 tests", proc.stderr)

    def test_door_has_no_login_and_receipt_does_not_steal(self) -> None:
        cs.write_html()
        text = DOOR.read_text(encoding="utf-8")
        self.assertIn("No login", text)
        self.assertIn("Possessing the link is enough", text)
        self.assertIn("1788381748.979959", RECEIPT.read_text(encoding="utf-8"))
        self.assertNotIn("Authorization", text)
        self.assertNotIn("api key", text.lower())
        receipt = RECEIPT.read_text(encoding="utf-8")
        self.assertIn("cursor-commons-slack-full-body-20260902-01", receipt)
        self.assertIn("Did **not** remint", receipt)
        self.assertIn("1788384217.141669", receipt)
        self.assertFalse((ROOT / "marketplace.html").exists())
        self.assertFalse((ROOT / "qualify.html").exists())
        self.assertFalse((ROOT / "CLAUDE_CORNER.md").exists())


if __name__ == "__main__":
    unittest.main()
