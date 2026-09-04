#!/usr/bin/env python3
"""Pin KEEP-lift battery remainder after leftover adapter restore. Do not remint leftover adapter."""

from __future__ import annotations

import json
import subprocess
import unittest
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RECEIPT = ROOT / "p/cursor-webmcp-adapter-keep-lift-battery-20260904-01.md"
LEFTOVER_KEEP_LIFT = ROOT / "p/cursor-webmcp-adapter-keep-lift-20260903-01.md"
REMAINDER = ROOT / "p/cursor-webmcp-contest-20260903-01.md"
ADAPTER = ROOT / "api" / "mcp.py"

KEEP = {
    "api/mcp.py": "9ae34f64",
    "webmcp.html": "f2757068",
    "p/cursor-webmcp-adapter-keep-lift-20260903-01.md": "53700c56",
    "p/cursor-webmcp-contest-20260903-01.md": "98fb6b6f",
    "test_cursor_webmcp_contest.py": "76b8dbae",
    "p/cursor-wire-shared-super-mcp-catalog-readback-20260902-01.md": "593d54bc",
    "p/cursor-wire-super-mcp-marketplace-readback-20260902-01.md": "448eda52",
    "p/latch-wake-super-mcp-pointer-readback-20260902-01.md": "250907c9",
    "p/cursor-webmcp-judge-url-20260903-01.md": "eb52debf",
    "p/cursor-webmcp-adapter-keep-lift-battery-20260904-01.md": "4a3c466c",
    "wire.html": "5b8edbda",
    "catalog.html": "7eb3ca22",
    "boards.html": "c824dc4d",
    "hub_pages.py": "5ac12648",
    "door.js": "dc59355d",
    "test_cursor_webmcp_adapter_keep_lift.py": "5d7a3f5b",
    "test_webmcp_door.py": "21b6993f",
    "test_grokbuild_occupancy_landed_work_keep_lift_readback.py": "67ce7021",
    "test_cursor_goat_pages_super_mcp_land_readback.py": "40d20d47",
}

THIS_SEAT_ADAPTER_TESTS = (
    "test_pack_is_ready_to_run.py",
    "test_pack_quality_dictates_tier.py",
    "test_what_a_pack_is.py",
    "test_since_you_last_looked.py",
    "test_stealable_lanes.py",
    "test_stealable_lanes_occupancy.py",
    "test_merge_on_pr.py",
    "test_commons_slack_full_body.py",
    "test_cursor_mcp_get_grounding_readback.py",
    "test_cursor_since_you_last_looked_readback.py",
)


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class TestCursorWebmcpAdapterKeepLiftBattery(unittest.TestCase):
    def test_keep_leftover_adapter_pad_and_unread_packs(self) -> None:
        for rel, prefix in KEEP.items():
            blob = git_blob(rel)
            self.assertTrue(
                blob.startswith(prefix),
                f"{rel} reminted: want {prefix} got {blob[:8]}",
            )
        self.assertEqual(ADAPTER.stat().st_size, 21414)
        self.assertGreaterEqual(ADAPTER.stat().st_size, 20000)

    def test_this_seat_leftover_tests_pin_restored_adapter(self) -> None:
        for rel in THIS_SEAT_ADAPTER_TESTS:
            text = (ROOT / rel).read_text(encoding="utf-8")
            self.assertIn(
                '"api/mcp.py": "9ae34f64"',
                text,
                f"{rel} missing leftover restored adapter pin",
            )
            self.assertNotIn(
                '"api/mcp.py": "bc558a5f"',
                text,
                f"{rel} still pins leftover pre-restore adapter",
            )
        grokbuild = (
            ROOT / "test_grokbuild_occupancy_landed_work_keep_lift_readback.py"
        ).read_text(encoding="utf-8")
        self.assertIn('"api/mcp.py": "bc558a5f"', grokbuild)
        contest = (ROOT / "test_webmcp_judge_url.py").read_text(encoding="utf-8")
        self.assertIn('"test_cursor_webmcp_contest.py": "76b8dbae"', contest)
        self.assertNotIn('"test_cursor_webmcp_contest.py": "76b8dbae"', contest)

    def test_this_seat_leftover_subset_still_passes(self) -> None:
        leftover = subprocess.run(
            [
                "python3",
                "-m",
                "unittest",
                "test_cursor_webmcp_contest.py",
                "test_since_you_last_looked.py",
                "test_stealable_lanes.py",
                "test_pack_is_ready_to_run.py",
                "test_webmcp_judge_url.py",
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(leftover.returncode, 0, msg=leftover.stdout + leftover.stderr)
        self.assertIn("Ran 25 tests", leftover.stderr)

    def test_public_mcp_initialize_200(self) -> None:
        payload = json.dumps(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-03-26",
                    "capabilities": {},
                    "clientInfo": {
                        "name": "cursor-webmcp-adapter-keep-lift-battery",
                        "version": "1",
                    },
                },
            }
        ).encode("utf-8")
        req = urllib.request.Request(
            "https://commons-spark-mcp.vercel.app/mcp",
            data=payload,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream",
            },
        )
        with urllib.request.urlopen(req, timeout=20) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            self.assertEqual(resp.status, 200)
        info = (body.get("result") or {}).get("serverInfo") or {}
        self.assertEqual(info.get("name"), "commons")
        self.assertEqual(info.get("version"), "1.4.0")

    def test_battery_receipt_exists_and_does_not_steal(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        leftover = LEFTOVER_KEEP_LIFT.read_text(encoding="utf-8")
        remainder = REMAINDER.read_text(encoding="utf-8")
        self.assertIn("cursor-webmcp-adapter-keep-lift-battery-20260904-01", text)
        self.assertIn("33825425167", text)
        self.assertIn("6f73b46f6", text)
        self.assertIn("9ae34f64", text)
        self.assertIn("21414", text)
        self.assertIn("d8ddd02d", text)
        self.assertIn("53700c56", text)
        self.assertIn("98fb6b6f", text)
        self.assertIn("Did **not** remint leftover adapter", text)
        self.assertIn("Did **not** KEEP-lift grokbuild", text)
        self.assertIn("Did **not** remint leftover Hands card", text)
        self.assertNotEqual(text, leftover)
        self.assertNotEqual(text, remainder)
        self.assertNotIn("buy.stripe.com", text)
        self.assertFalse((ROOT / "CLAUDE_CORNER.md").exists())
        self.assertFalse((ROOT / "marketplace.html").exists())
        self.assertFalse(
            (ROOT / "p/cursor-wire-webmcp-challenge-readback-20260903-01.md").exists()
        )


if __name__ == "__main__":
    unittest.main()
