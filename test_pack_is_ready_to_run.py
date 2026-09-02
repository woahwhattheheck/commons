#!/usr/bin/env python3
"""Pin pack-is-ready-to-run leftover. Do not remint pack-quality leftover."""

from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
HELPER = ROOT / "host/pack_is_ready_to_run.py"
RECEIPT = ROOT / "p/cursor-pack-is-ready-to-run-20260902-01.md"
CATALOG = ROOT / "ground/PACK_IS_READY_TO_RUN.json"
DOOR = ROOT / "pack-is-ready-to-run.html"

KEEP = {
    "p/cursor-pack-quality-dictates-tier-20260902-01.md": "f2054b18",
    "host/pack_quality_dictates_tier.py": "74d36b0a",
    "ground/PACK_QUALITY_DICTATES_TIER.json": "fa45160f",
    "pack-quality-tier.html": "2443aebe",
    "p/cursor-pack-quality-dictates-tier-readback-20260902-01.md": "aa5f6bbd",
    "ground/BUSINESS_PACK_KEEP_SELL.json": "4e0e3eb0",
    "p/cursor-harborline-pack-market-render-20260902-01.md": "54c348dc",
    "p/cursor-harborline-qualify-live-probe-20260902-01.md": "92c4e31f",
    "p/cursor-stealable-lanes-occupancy-20260902-01.md": "9631e869",
    "host/stealable_lanes.py": "c90284fb",
    "p/cursor-merge-on-pr-20260902-01.md": "22b63e25",
    "p/cursor-merge-on-pr-readback-20260902-01.md": "e160b2c3",
    "p/cursor-commons-slack-full-body-20260902-01.md": "86f4eddc",
    "host/slack_mirror.py": "8d3a5e0b",
    "p/cursor-landed-work-feed-20260902-01.md": "d566f495",
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


class TestPackIsReadyToRun(unittest.TestCase):
    def test_keep_quality_harborline_occupancy_item6(self) -> None:
        for rel, prefix in KEEP.items():
            blob = git_blob(rel)
            self.assertTrue(
                blob.startswith(prefix),
                f"{rel} reminted: want {prefix} got {blob[:8]}",
            )

    def test_catalog_ready_to_run_not_budget_list(self) -> None:
        data = json.loads(CATALOG.read_text(encoding="utf-8"))
        self.assertEqual(data["id"], "cursor-pack-is-ready-to-run-20260902-01")
        self.assertEqual(data["item"], 12)
        self.assertEqual(data["pack"]["kind"], "ready_to_run_business")
        self.assertTrue(data["pack"]["not_instructions"])
        self.assertEqual(data["pack"]["withheld"], "access_to_the_build_pack")
        self.assertEqual(data["pack"]["public"], "descriptions_and_methods")
        self.assertEqual(
            data["pack"]["never_contains"],
            "you_need_a_budget_of_X_go_buy_this",
        )
        self.assertEqual(
            data["pack"]["only_extra_buy"],
            "supporting_product_or_service_from_tjlabs",
        )
        self.assertFalse(data["commons_is_store"])
        self.assertEqual(data["tos"]["shape"], "OPEN_QUESTION")
        self.assertEqual(data["tos"]["residual_pct"], "FINDER-FAILED")
        self.assertFalse(data["tos"]["peer_opinions"])
        self.assertFalse(data["remint_quality_leftover"])

    def test_json_renders_without_inventing_tos(self) -> None:
        proc = run_helper("--json")
        self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
        packet = json.loads(proc.stdout)
        self.assertEqual(packet["verdict"], "RENDER")
        self.assertEqual(packet["pack_kind"], "ready_to_run_business")
        self.assertTrue(packet["not_instructions"])
        self.assertFalse(packet["budget_go_buy"])
        self.assertFalse(packet["budget_leak"])
        self.assertEqual(packet["tos_shape"], "OPEN_QUESTION")
        self.assertEqual(packet["tos_residual_pct"], "FINDER-FAILED")
        self.assertFalse(packet["peer_tos_opinions"])
        self.assertFalse(packet["commons_is_store"])
        self.assertFalse(packet["invented_stripe_urls"])
        self.assertEqual(packet["sends"], 0)

    def test_send_budget_tos_refused(self) -> None:
        for flag in ("--send", "--go", "--budget", "--tos"):
            proc = run_helper(flag)
            self.assertEqual(proc.returncode, 2, msg=proc.stdout + proc.stderr)
            payload = json.loads(proc.stdout)
            self.assertEqual(payload["sent"], 0)
            self.assertEqual(payload["refused"], flag)
        proc = run_helper("--not-a-real-flag")
        self.assertEqual(proc.returncode, 1)
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["verdict"], "FINDER-FAILED")
        self.assertEqual(payload["sent"], 0)

    def test_receipt_and_door_do_not_steal(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        door = DOOR.read_text(encoding="utf-8")
        self.assertIn("cursor-pack-is-ready-to-run-20260902-01", text)
        self.assertIn("1788387675.053019", text)
        self.assertIn("Did **not** remint quality leftover", text)
        self.assertIn("f2054b18", text)
        self.assertNotIn("buy.stripe.com", text)
        self.assertIn("No login", door)
        self.assertIn("ready-to-run business", door.lower())
        self.assertIn("Possessing the link is enough", door)
        self.assertNotIn("https://buy.stripe.com/", door)
        self.assertNotIn("oauth", door.lower())
        self.assertNotIn("api key", door.lower())
        self.assertFalse((ROOT / "marketplace.html").exists())
        self.assertFalse((ROOT / "qualify.html").exists())
        self.assertFalse((ROOT / "CLAUDE_CORNER.md").exists())


if __name__ == "__main__":
    unittest.main()
