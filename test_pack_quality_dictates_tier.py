#!/usr/bin/env python3
"""Pin pack-quality-dictates-tier leftover. Do not remint KEEP/SELL or item 2."""

from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
HELPER = ROOT / "host/pack_quality_dictates_tier.py"
RECEIPT = ROOT / "p/cursor-pack-quality-dictates-tier-20260902-01.md"
CATALOG = ROOT / "ground/PACK_QUALITY_DICTATES_TIER.json"
DOOR = ROOT / "pack-quality-tier.html"

KEEP = {
    "ground/BUSINESS_PACK_KEEP_SELL.json": "4e0e3eb0",
    "host/business_pack_keep_sell.py": "a375adf9",
    "keep-sell.html": "5964bba1",
    "p/cursor-since-you-last-looked-20260902-01.md": "003828c9",
    "host/since_you_last_looked.py": "3578783c",
    "p/cursor-commons-slack-full-body-20260902-01.md": "86f4eddc",
    "host/commons_slack_full_body.py": "16ba0f4c",
    "host/slack_mirror.py": "8d3a5e0b",
    "slack_ingest.py": "0040a726",
    "p/cursor-stealable-lanes-occupancy-20260902-01.md": "9631e869",
    "p/cursor-stealable-lanes-roles-20260902-01.md": "5f1ef25f",
    "p/cursor-stealable-lanes-roles-readback-20260902-01.md": "ada92980",
    "p/cursor-landed-work-feed-20260902-01.md": "d566f495",
    "p/cursor-harborline-pack-market-render-20260902-01.md": "54c348dc",
    "ground/OWNER_NOW.md": "59b1fd37",
    "hub_pages.py": "5ac12648",
    "door.js": "dc59355d",
    "api/mcp.py": "bc558a5f",
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


class TestPackQualityDictatesTier(unittest.TestCase):
    def test_keep_factory_item2_item7_occupancy(self) -> None:
        for rel, prefix in KEEP.items():
            blob = git_blob(rel)
            self.assertTrue(
                blob.startswith(prefix),
                f"{rel} reminted: want {prefix} got {blob[:8]}",
            )

    def test_catalog_floor_and_open_tos(self) -> None:
        data = json.loads(CATALOG.read_text(encoding="utf-8"))
        self.assertEqual(data["id"], "cursor-pack-quality-dictates-tier-20260902-01")
        self.assertEqual(data["item"], 12)
        self.assertTrue(data["quality_dictates_tier"])
        self.assertFalse(data["undercut_to_fit_tier"])
        self.assertEqual(data["floor_usd"], 20)
        self.assertEqual(data["catalog_tiers_usd"], [20, 100, 200, 1000, 10000])
        self.assertEqual(data["fifty_usd_catalog"], "FINDER-FAILED")
        self.assertEqual(data["tos"]["shape"], "OPEN_QUESTION")
        self.assertEqual(data["tos"]["residual_pct"], "FINDER-FAILED")
        self.assertEqual(data["example"]["price_usd"], 200)
        self.assertFalse(data["example"]["undercut"])
        self.assertFalse(data["remint_keep_sell"])

    def test_json_renders_without_inventing_tos(self) -> None:
        proc = run_helper("--json")
        self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
        packet = json.loads(proc.stdout)
        self.assertEqual(packet["verdict"], "RENDER")
        self.assertTrue(packet["quality_dictates_tier"])
        self.assertFalse(packet["undercut_to_fit_tier"])
        self.assertEqual(packet["floor_usd"], 20)
        self.assertEqual(packet["catalog_tiers_usd"], [20, 100, 200, 1000, 10000])
        self.assertEqual(packet["fifty_usd_catalog"], "FINDER-FAILED")
        self.assertEqual(packet["tos_shape"], "OPEN_QUESTION")
        self.assertEqual(packet["tos_residual_pct"], "FINDER-FAILED")
        self.assertEqual(packet["example"]["price_usd"], 200)
        self.assertFalse(packet["example_undercut"])
        self.assertEqual(packet["sends"], 0)
        self.assertFalse(packet["invented_stripe_urls"])

    def test_send_undercut_refused(self) -> None:
        for flag in ("--send", "--apply", "--go", "--autopilot", "--undercut"):
            proc = run_helper(flag)
            self.assertEqual(proc.returncode, 2, msg=proc.stdout + proc.stderr)
            payload = json.loads(proc.stdout)
            self.assertEqual(payload["sent"], 0)
            self.assertEqual(payload["cash"], 0)
            self.assertEqual(payload["refused"], flag)
            self.assertFalse(payload["undercut_to_fit_tier"])
        proc = run_helper("--not-a-real-flag")
        self.assertEqual(proc.returncode, 1)
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["verdict"], "FINDER-FAILED")
        self.assertEqual(payload["sent"], 0)

    def test_receipt_and_door_do_not_steal(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        door = DOOR.read_text(encoding="utf-8")
        self.assertIn("cursor-pack-quality-dictates-tier-20260902-01", text)
        self.assertIn("1788384502.436879", text)
        self.assertIn("Did not remint", text)
        self.assertIn("003828c9", text)
        self.assertIn("86f4eddc", text)
        self.assertIn("4e0e3eb0", text)
        self.assertNotIn("buy.stripe.com", text)
        self.assertIn("$20", door)
        self.assertIn("quality dictates tier", door.lower())
        self.assertIn("FINDER-FAILED", door)
        self.assertIn("Harborline Local Sites", door)
        self.assertNotIn("https://buy.stripe.com/", door)
        self.assertFalse((ROOT / "marketplace.html").exists())
        self.assertFalse((ROOT / "CLAUDE_CORNER.md").exists())


if __name__ == "__main__":
    unittest.main()
