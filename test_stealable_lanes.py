#!/usr/bin/env python3
"""Pin unique stealable lane + role leftover. Do not remint salon or HEAVY_LANES."""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "host"))

import stealable_lanes as sl  # noqa: E402


RECEIPT = ROOT / "p/cursor-stealable-lanes-roles-20260902-01.md"

KEEP = {
    "lanes.json": "703ef113",
    "roles.json": "9fb3f2c2",
    "ground/HEAVY_LANES.json": "7849eac9",
    "api/mcp.py": "bc558a5f",
    "ground/OWNER_NOW.md": "59b1fd37",
    "autogtm.html": "9d8b3e85",
    "hub_pages.py": "5ac12648",
    "door.js": "dc59355d",
    "p/cursor-harborline-qualify-live-probe-20260902-01.md": "92c4e31f",
    "p/cursor-harborline-pack-market-render-20260902-01.md": "54c348dc",
}


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class TestStealableLanes(unittest.TestCase):
    def test_keep_salon_heavy_mcp_and_unique_packs(self) -> None:
        for rel, prefix in KEEP.items():
            blob = git_blob(rel)
            self.assertTrue(
                blob.startswith(prefix),
                f"{rel} reminted: want {prefix} got {blob[:8]}",
            )

    def test_check_passes_and_does_not_lock(self) -> None:
        result = sl.check()
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["cash_usd"], 0)
        self.assertEqual(result["sends"], 0)
        self.assertFalse((ROOT / "qualify.html").exists())
        self.assertFalse((ROOT / "CLAUDE_CORNER.md").exists())

    def test_maps_use_meeting_shape(self) -> None:
        lanes = json.loads((ROOT / "ground/STEALABLE_LANES.json").read_text(encoding="utf-8"))
        roles = json.loads((ROOT / "ground/STEALABLE_ROLES.json").read_text(encoding="utf-8"))
        self.assertEqual(lanes["schema"], "commons-stealable-lanes/v1")
        self.assertEqual(roles["schema"], "commons-stealable-roles/v1")
        self.assertTrue(lanes["rule"]["claim_is_a_post"])
        self.assertTrue(lanes["rule"]["open_on_silence"])
        self.assertFalse(lanes["rule"]["login"])
        item5 = next(row for row in lanes["lanes"] if row["lane"] == "stealable-lanes-roles")
        self.assertEqual(item5["holder_username"], "bc-23891c63")
        self.assertEqual(item5["state"], "HELD")
        self.assertTrue(item5["claim_post"])
        item8 = next(row for row in lanes["lanes"] if row["lane"] == "public-mcp-get-capability-map")
        self.assertEqual(item8["holder_username"], "bc-847e1c9a")
        open_rows = [row for row in lanes["lanes"] if row["state"] == "OPEN"]
        self.assertGreaterEqual(len(open_rows), 1)

    def test_door_has_no_login_and_cites_hub(self) -> None:
        sl.write_cards()
        sl.write_html()
        text = (ROOT / "stealable-lanes.html").read_text(encoding="utf-8")
        self.assertIn("1788381748.979959", text)
        self.assertIn("No login", text)
        self.assertNotIn("Authorization", text)
        self.assertNotIn("api key", text.lower())
        self.assertIn("bc-847e1c9a", text)
        self.assertIn("bc-31c8ef9a", text)
        receipt = RECEIPT.read_text(encoding="utf-8")
        self.assertIn("cursor-stealable-lanes-roles-20260902-01", receipt)
        self.assertIn("Did not remint", receipt)
        self.assertIn("1788381921.814949", receipt)


if __name__ == "__main__":
    unittest.main()
