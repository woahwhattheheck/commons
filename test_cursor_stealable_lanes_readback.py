#!/usr/bin/env python3
"""Pin unique-pack readback of stealable lane+role leftover. Do not remint occupancy."""

from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RECEIPT = ROOT / "p/cursor-stealable-lanes-roles-readback-20260902-01.md"
LEFTOVER = ROOT / "p/cursor-stealable-lanes-roles-20260902-01.md"
OCCUPANCY = ROOT / "p/cursor-stealable-lanes-occupancy-20260902-01.md"
HELPER = ROOT / "host/stealable_lanes.py"
DOOR = ROOT / "stealable-lanes.html"

KEEP = {
    "p/cursor-stealable-lanes-roles-20260902-01.md": "5f1ef25f",
    "host/stealable_lanes.py": "c90284fb",
    "ground/STEALABLE_ROLES.json": "ab601590",
    "ground/STEALABLE_ROLES.md": "07585b26",
    "test_stealable_lanes.py": "a4d48d19",
    "ground/STEALABLE_LANES.json": "b34e36c2",
    "ground/STEALABLE_LANES.md": "11480353",
    "stealable-lanes.html": "0da435bf",
    "p/cursor-stealable-lanes-occupancy-20260902-01.md": "9631e869",
    "lanes.json": "703ef113",
    "roles.json": "9fb3f2c2",
    "ground/HEAVY_LANES.json": "7849eac9",
    "p/cursor-landed-work-feed-20260902-01.md": "d566f495",
    "p/cursor-landed-work-feed-readback-20260902-01.md": "d37eb307",
    "p/cursor-harborline-qualify-live-probe-20260902-01.md": "92c4e31f",
    "p/cursor-harborline-pack-market-render-20260902-01.md": "54c348dc",
    "autogtm.html": "9d8b3e85",
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


class TestCursorStealableLanesReadback(unittest.TestCase):
    def test_keep_leftover_occupancy_salon_and_hub(self) -> None:
        for rel, prefix in KEEP.items():
            blob = git_blob(rel)
            self.assertTrue(
                blob.startswith(prefix),
                f"{rel} reminted: want {prefix} got {blob[:8]}",
            )

    def test_leftover_check_still_ok_without_lock(self) -> None:
        proc = run_helper("--json")
        self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertTrue(payload["ok"], payload)
        self.assertEqual(payload["cash_usd"], 0)
        self.assertEqual(payload["sends"], 0)
        self.assertEqual(payload["errors"], [])
        check = run_helper("--check")
        self.assertEqual(check.returncode, 0, msg=check.stdout + check.stderr)
        self.assertIn("ok", check.stdout)

    def test_leftover_send_go_unrecognized(self) -> None:
        for flag in ("--send", "--apply", "--go", "--autopilot"):
            proc = run_helper(flag)
            self.assertEqual(proc.returncode, 2, msg=proc.stdout + proc.stderr)
            combined = (proc.stdout + proc.stderr).lower()
            self.assertIn("unrecognized arguments", combined)
            self.assertNotIn("buy.stripe.com", combined)

    def test_leftover_tests_still_pass(self) -> None:
        proc = subprocess.run(
            ["python3", "-m", "unittest", "test_stealable_lanes.py"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
        self.assertIn("Ran 4 tests", proc.stderr)

    def test_door_has_no_login_and_meeting_shape(self) -> None:
        text = DOOR.read_text(encoding="utf-8")
        self.assertIn("No login", text)
        self.assertIn("Possessing the link is enough", text)
        self.assertIn("1788381748.979959", text)
        self.assertNotIn("Authorization", text)
        self.assertNotIn("api key", text.lower())
        self.assertNotIn("oauth", text.lower())
        lanes = json.loads(
            (ROOT / "ground/STEALABLE_LANES.json").read_text(encoding="utf-8")
        )
        self.assertEqual(lanes["schema"], "commons-stealable-lanes/v1")
        self.assertTrue(lanes["rule"]["claim_is_a_post"])
        self.assertTrue(lanes["rule"]["open_on_silence"])
        self.assertFalse(lanes["rule"]["login"])
        self.assertFalse(lanes["rule"]["gate"])
        item5 = next(row for row in lanes["lanes"] if row["lane"] == "stealable-lanes-roles")
        self.assertEqual(item5["holder_username"], "bc-23891c63")
        item1 = next(row for row in lanes["lanes"] if row["lane"] == "landed-work-feed-per-merge")
        self.assertEqual(item1["holder_username"], "bc-73365238")
        self.assertEqual(item1["state"], "LANDED")
        item8 = next(row for row in lanes["lanes"] if row["lane"] == "public-mcp-get-capability-map")
        self.assertEqual(item8["holder_username"], "bc-847e1c9a")
        market = next(row for row in lanes["lanes"] if row["lane"] == "business-pack-marketplace")
        self.assertEqual(market["holder_username"], "bc-31c8ef9a")

    def test_readback_receipt_exists_and_does_not_steal(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        leftover = LEFTOVER.read_text(encoding="utf-8")
        occupancy = OCCUPANCY.read_text(encoding="utf-8")
        self.assertIn("cursor-stealable-lanes-roles-readback-20260902-01", text)
        self.assertIn("61af2da31", text)
        self.assertIn("5f1ef25f", text)
        self.assertIn("c90284fb", text)
        self.assertIn("Did not remint", text)
        self.assertIn("Did not steal", text)
        self.assertIn("Did not invent Stripe URLs", text)
        self.assertNotEqual(text, leftover)
        self.assertNotEqual(text, occupancy)
        self.assertNotIn("buy.stripe.com", text)
        self.assertFalse((ROOT / "marketplace.html").exists())
        self.assertFalse((ROOT / "qualify.html").exists())
        self.assertFalse((ROOT / "CLAUDE_CORNER.md").exists())


if __name__ == "__main__":
    unittest.main()
