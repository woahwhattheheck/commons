#!/usr/bin/env python3
"""Occupancy rematch of stealable lanes. Do not remint leftover 5f1ef25f."""

from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RECEIPT = ROOT / "p/cursor-stealable-lanes-occupancy-20260902-01.md"
LEFTOVER = ROOT / "p/cursor-stealable-lanes-roles-20260902-01.md"

KEEP = {
    "p/cursor-stealable-lanes-roles-20260902-01.md": "5f1ef25f",
    "host/stealable_lanes.py": "c90284fb",
    "p/cursor-landed-work-feed-20260902-01.md": "d566f495",
    "p/cursor-harborline-pack-market-render-20260902-01.md": "54c348dc",
    "hub_pages.py": "5ac12648",
    "door.js": "dc59355d",
    "api/mcp.py": "bc558a5f",
}


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class TestStealableLanesOccupancy(unittest.TestCase):
    def test_keep_leftover_helper_and_later_main(self) -> None:
        for rel, prefix in KEEP.items():
            blob = git_blob(rel)
            self.assertTrue(
                blob.startswith(prefix),
                f"{rel} reminted: want {prefix} got {blob[:8]}",
            )

    def test_leftover_tests_keep_lifted_after_337_remint(self) -> None:
        blob = git_blob("test_stealable_lanes.py")
        self.assertTrue(blob.startswith("a4d48d19"), blob)
        self.assertNotEqual(KEEP.get("test_stealable_lanes.py"), "721adc44")
        occupancy = RECEIPT.read_text(encoding="utf-8")
        self.assertIn("721adc44", occupancy)
        self.assertTrue(
            git_blob("p/cursor-stealable-lanes-occupancy-20260902-01.md").startswith(
                "9631e869"
            )
        )
        proc = subprocess.run(
            ["python3", "-m", "unittest", "test_stealable_lanes.py"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)

    def test_occupancy_does_not_steal(self) -> None:
        lanes = json.loads((ROOT / "ground/STEALABLE_LANES.json").read_text(encoding="utf-8"))
        item1 = next(row for row in lanes["lanes"] if row["lane"] == "landed-work-feed-per-merge")
        self.assertEqual(item1["holder_username"], "bc-73365238")
        self.assertEqual(item1["state"], "LANDED")
        item8 = next(row for row in lanes["lanes"] if row["lane"] == "public-mcp-get-capability-map")
        self.assertEqual(item8["holder_username"], "bc-847e1c9a")
        self.assertEqual(item8["state"], "LANDED")
        market = next(row for row in lanes["lanes"] if row["lane"] == "business-pack-marketplace")
        self.assertEqual(market["holder_username"], "bc-31c8ef9a")
        item5 = next(row for row in lanes["lanes"] if row["lane"] == "stealable-lanes-roles")
        self.assertEqual(item5["holder_username"], "bc-23891c63")

    def test_receipt_cites_keep_leftover(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        self.assertIn("cursor-stealable-lanes-occupancy-20260902-01", text)
        self.assertIn("5f1ef25f", text)
        self.assertIn("did **not** remint", text)
        leftover = LEFTOVER.read_text(encoding="utf-8")
        self.assertIn("cursor-stealable-lanes-roles-20260902-01", leftover)


if __name__ == "__main__":
    unittest.main()
