#!/usr/bin/env python3
"""Pin unique-pack readback of item 12 complementary remainder. Do not remint leftover."""

from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RECEIPT = ROOT / "p/cursor-pack-is-ready-to-run-readback-20260902-01.md"
LEFTOVER = ROOT / "p/cursor-pack-is-ready-to-run-20260902-01.md"
HELPER = ROOT / "host/pack_is_ready_to_run.py"
DOOR = ROOT / "pack-is-ready-to-run.html"

KEEP = {
    "p/cursor-pack-is-ready-to-run-20260902-01.md": "897b00ba",
    "host/pack_is_ready_to_run.py": "aab508cf",
    "ground/PACK_IS_READY_TO_RUN.json": "69a67ee1",
    "test_pack_is_ready_to_run.py": "226b7d6d",
    "pack-is-ready-to-run.html": "17195463",
    "p/cursor-pack-quality-dictates-tier-20260902-01.md": "f2054b18",
    "host/pack_quality_dictates_tier.py": "74d36b0a",
    "ground/PACK_QUALITY_DICTATES_TIER.json": "fa45160f",
    "pack-quality-tier.html": "2443aebe",
    "p/cursor-pack-quality-dictates-tier-readback-20260902-01.md": "aa5f6bbd",
    "p/cursor-what-a-pack-is-20260902-01.md": "a4e4dd89",
    "host/what_a_pack_is.py": "3de395af",
    "ground/WHAT_A_PACK_IS.json": "2f473414",
    "test_what_a_pack_is.py": "9a593d17",
    "what-a-pack-is.html": "520fbf5f",
    "p/cursor-commons-slack-full-body-chunk-20260902-01.md": "94770f41",
    "p/cursor-commons-slack-full-body-chunk-readback-20260902-01.md": "364ae3a4",
    "host/commons_slack_full_body.py": "16ba0f4c",
    "host/slack_mirror.py": "8d3a5e0b",
    "p/cursor-commons-slack-full-body-20260902-01.md": "86f4eddc",
    "p/cursor-stealable-lanes-occupancy-20260902-01.md": "9631e869",
    "host/stealable_lanes.py": "c90284fb",
    "p/cursor-merge-on-pr-20260902-01.md": "22b63e25",
    "p/cursor-merge-on-pr-readback-20260902-01.md": "e160b2c3",
    "p/cursor-harborline-pack-market-render-20260902-01.md": "54c348dc",
    "p/cursor-harborline-qualify-live-probe-20260902-01.md": "92c4e31f",
    "p/cursor-landed-work-feed-20260902-01.md": "d566f495",
    "ground/BUSINESS_PACK_KEEP_SELL.json": "4e0e3eb0",
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


class TestCursorPackIsReadyToRunReadback(unittest.TestCase):
    def test_keep_leftover_and_unread_packs(self) -> None:
        for rel, prefix in KEEP.items():
            blob = git_blob(rel)
            self.assertTrue(
                blob.startswith(prefix),
                f"{rel} reminted: want {prefix} got {blob[:8]}",
            )

    def test_leftover_json_still_renders_without_inventing_tos(self) -> None:
        proc = run_helper("--json")
        self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
        packet = json.loads(proc.stdout)
        self.assertEqual(packet["verdict"], "RENDER")
        self.assertEqual(packet["pack_kind"], "ready_to_run_business")
        self.assertTrue(packet["not_instructions"])
        self.assertEqual(packet["withheld"], "access_to_the_build_pack")
        self.assertEqual(packet["public"], "descriptions_and_methods")
        self.assertFalse(packet["budget_go_buy"])
        self.assertEqual(
            packet["only_extra_buy"],
            "supporting_product_or_service_from_tjlabs",
        )
        self.assertFalse(packet["commons_is_store"])
        self.assertEqual(packet["tos_shape"], "OPEN_QUESTION")
        self.assertEqual(packet["tos_residual_pct"], "FINDER-FAILED")
        self.assertEqual(packet["tos_buyout"], "FINDER-FAILED")
        self.assertEqual(packet["tos_per_tier"], "FINDER-FAILED")
        self.assertFalse(packet["peer_tos_opinions"])
        self.assertTrue(packet["quality_dictates_tier"])
        self.assertFalse(packet["login"])
        self.assertFalse(packet["gate"])
        self.assertEqual(packet["sends"], 0)
        self.assertFalse(packet["invented_stripe_urls"])
        self.assertEqual(packet["checkout"], "FINDER-FAILED")

    def test_leftover_send_go_budget_tos_refused(self) -> None:
        for flag in ("--send", "--apply", "--go", "--autopilot", "--budget", "--tos"):
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

    def test_leftover_unique_and_parallel_tests_still_pass(self) -> None:
        leftover = subprocess.run(
            ["python3", "-m", "unittest", "test_pack_is_ready_to_run.py"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(leftover.returncode, 0, msg=leftover.stdout + leftover.stderr)
        self.assertIn("Ran 5 tests", leftover.stderr)
        quality = subprocess.run(
            ["python3", "-m", "unittest", "test_pack_quality_dictates_tier.py"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(quality.returncode, 0, msg=quality.stdout + quality.stderr)
        self.assertIn("Ran 5 tests", quality.stderr)
        parallel = subprocess.run(
            ["python3", "-m", "unittest", "test_what_a_pack_is.py"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(parallel.returncode, 0, msg=parallel.stdout + parallel.stderr)
        self.assertIn("Ran 6 tests", parallel.stderr)

    def test_readback_receipt_exists_and_does_not_steal(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        leftover = LEFTOVER.read_text(encoding="utf-8")
        door = DOOR.read_text(encoding="utf-8")
        self.assertIn("cursor-pack-is-ready-to-run-readback-20260902-01", text)
        self.assertIn("3e634c97a", text)
        self.assertIn("897b00ba", text)
        self.assertIn("aab508cf", text)
        self.assertIn("69a67ee1", text)
        self.assertIn("226b7d6d", text)
        self.assertIn("17195463", text)
        self.assertIn("f2054b18", text)
        self.assertIn("74d36b0a", text)
        self.assertIn("a4e4dd89", text)
        self.assertIn("Did **not** remint leftover id", text)
        self.assertIn("1788387675.053019", text)
        self.assertNotEqual(text, leftover)
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
