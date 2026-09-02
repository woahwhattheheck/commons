#!/usr/bin/env python3
"""Pin since-you-last-looked feed. Do not remint landed-work or grounding."""

from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path

import host.since_you_last_looked as syl

ROOT = Path(__file__).resolve().parent
HELPER = ROOT / "host/since_you_last_looked.py"
RECEIPT = ROOT / "p/cursor-since-you-last-looked-20260902-01.md"
CATALOG = ROOT / "ground/SINCE_YOU_LAST_LOOKED.json"
DOOR = ROOT / "since-you-last-looked.html"

KEEP = {
    "p/cursor-landed-work-feed-20260902-01.md": "d566f495",
    "host/landed_work_feed.py": "0506fd0f",
    "ground/LANDED_WORK_FEED.json": "4c42f69f",
    "landed-work.html": "93cfe179",
    "p/cursor-stealable-lanes-occupancy-20260902-01.md": "9631e869",
    "p/cursor-stealable-lanes-roles-20260902-01.md": "5f1ef25f",
    "host/stealable_lanes.py": "c90284fb",
    "p/cursor-harborline-pack-market-render-20260902-01.md": "54c348dc",
    "host/harborline_pack_market_render.py": "cc9a3320",
    "ground/OWNER_NOW.md": "59b1fd37",
    "p/cursor-owner-now-readback-20260902-01.md": "1b3cd631",
    "autogtm.html": "9d8b3e85",
    "hub_pages.py": "5ac12648",
    "door.js": "dc59355d",
    "api/mcp.py": "bc558a5f",
    "grounding.html": "abb91caf",
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


class TestSinceYouLastLooked(unittest.TestCase):
    def test_keep_item1_occupancy_harborline_and_later_main(self) -> None:
        for rel, prefix in KEEP.items():
            blob = git_blob(rel)
            self.assertTrue(
                blob.startswith(prefix),
                f"{rel} reminted: want {prefix} got {blob[:8]}",
            )

    def test_catalog_is_catchup_not_per_merge(self) -> None:
        data = json.loads(CATALOG.read_text(encoding="utf-8"))
        self.assertEqual(data["id"], "cursor-since-you-last-looked-20260902-01")
        self.assertEqual(data["item"], 2)
        self.assertTrue(data["nothing_dropped"])
        self.assertFalse(data["model_decides_what_matters"])
        self.assertTrue(data["not_per_merge_line"])
        self.assertTrue(data["not_first_visit_grounding"])
        self.assertEqual(data["grouped_by"], ["git", "slack", "commons"])
        self.assertEqual(data["slack_live_token"], "FINDER-FAILED")
        self.assertEqual(data["hub"]["claim_ts"], "1788383811.692339")
        self.assertEqual(data["hub"]["duplicate_later_claim_ts"], "1788383843.564909")
        self.assertEqual(data["bryce"]["user_id"], "U0BR9670G2H")
        pins = [row for row in data["slack_measured"] if row["bryce_pin"]]
        self.assertEqual(len(pins), 1)
        self.assertEqual(pins[0]["ts"], "1788380844.707619")
        self.assertFalse(pins[0]["sent_using"])

    def test_json_groups_surfaces_and_pins_bryce(self) -> None:
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
        slack = packet["surfaces"]["slack"]
        self.assertEqual(slack[0]["ts"], "1788380844.707619")
        self.assertTrue(slack[0]["bryce_pin"])
        self.assertEqual(packet["bryce_pinned"], 1)
        self.assertEqual(packet["dropped"], 0)
        self.assertEqual(packet["slack_live_token"], "FINDER-FAILED")
        self.assertFalse(packet["invented_stripe_urls"])
        self.assertEqual(packet["sends"], 0)
        src = HELPER.read_text(encoding="utf-8")
        self.assertNotIn("BAKE_SUBJECT", src)
        self.assertNotIn("llms.txt+fresh.md", src)

    def test_bryce_sorter_does_not_drop(self) -> None:
        rows = [
            {"ts": "2", "user_id": "U0BR9670G2H", "bot": False, "sent_using": True, "text": "Sent using Cursor"},
            {"ts": "1", "user_id": "U0BR9670G2H", "bot": False, "sent_using": False, "text": "Big things incoming alert the peers"},
            {"ts": "3", "user_id": "U0BR97NKHGD", "bot": True, "sent_using": False, "text": "bot"},
        ]
        ordered = syl.slack_order(rows)
        self.assertEqual(len(ordered), 3)
        self.assertTrue(ordered[0].get("bryce_pin") or syl.is_bryce_post(ordered[0]))
        self.assertEqual(ordered[0]["ts"], "1")

    def test_send_go_refused_and_unknown_finder_failed(self) -> None:
        for flag in ("--send", "--apply", "--go", "--autopilot"):
            proc = run_helper(flag)
            self.assertEqual(proc.returncode, 2, msg=proc.stdout + proc.stderr)
            payload = json.loads(proc.stdout)
            self.assertEqual(payload["sent"], 0)
            self.assertEqual(payload["cash"], 0)
            self.assertEqual(payload["refused"], flag)
        proc = run_helper("--not-a-real-flag")
        self.assertEqual(proc.returncode, 1)
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["verdict"], "FINDER-FAILED")
        self.assertEqual(payload["sent"], 0)
        empty = run_helper("--json", "--since", "2099-01-01T00:00:00Z")
        self.assertEqual(empty.returncode, 0, msg=empty.stdout + empty.stderr)
        packet = json.loads(empty.stdout)
        self.assertTrue(packet["window_empty"])
        self.assertIn("FINDER-FAILED", packet["window_note"])
        self.assertEqual(packet["dropped"], 0)

    def test_receipt_and_door_do_not_steal(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        door = DOOR.read_text(encoding="utf-8")
        self.assertIn("cursor-since-you-last-looked-20260902-01", text)
        self.assertIn("1788383811.692339", text)
        self.assertIn("1788383843.564909", text)
        self.assertIn("Did not remint", text)
        self.assertIn("d566f495", text)
        self.assertIn("9631e869", text)
        self.assertIn("54c348dc", text)
        self.assertIn("59b1fd37", text)
        self.assertNotIn("buy.stripe.com", text)
        self.assertIn("commons-since-you-last-looked-ms", door)
        self.assertIn("col-git", door)
        self.assertIn("col-slack", door)
        self.assertIn("col-commons", door)
        self.assertIn("BRYCE", door)
        self.assertIn("FINDER-FAILED", door)
        self.assertIn("I looked", door)
        self.assertNotIn("https://buy.stripe.com/", door)
        self.assertFalse((ROOT / "marketplace.html").exists())
        self.assertFalse((ROOT / "qualify.html").exists())
        self.assertFalse((ROOT / "CLAUDE_CORNER.md").exists())


if __name__ == "__main__":
    unittest.main()
