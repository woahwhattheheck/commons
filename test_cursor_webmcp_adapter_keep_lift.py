#!/usr/bin/env python3
"""Pin KEEP-lift of unique-pack tests after leftover adapter restore. Do not remint leftover adapter."""

from __future__ import annotations

import json
import subprocess
import unittest
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RECEIPT = ROOT / "p/cursor-webmcp-adapter-keep-lift-20260903-01.md"
LEFTOVER = ROOT / "p/wire-webmcp-challenge-20260903-01.md"
REMAINDER = ROOT / "p/cursor-webmcp-contest-20260903-01.md"
ADAPTER = ROOT / "api" / "mcp.py"

KEEP = {
    "p/wire-webmcp-challenge-20260903-01.md": "0e815c6d",
    "webmcp.html": "f2757068",
    "api/mcp.py": "9ae34f64",
    "p/cursor-webmcp-contest-20260903-01.md": "98fb6b6f",
    "p/cursor-webmcp-judge-url-20260903-01.md": "eb52debf",
    "p/cursor-webmcp-ship-20260903-01.md": "15831799",
    "p/cursor-wire-shared-super-mcp-catalog-readback-20260902-01.md": "593d54bc",
    "p/cursor-wire-super-mcp-marketplace-readback-20260902-01.md": "448eda52",
    "p/latch-wake-super-mcp-pointer-readback-20260902-01.md": "250907c9",
    "p/cursor-wire-catalog-marketplace-latch-readback-rematch-20260903-01.md": "f23e1db8",
    "p/cursor-wire-hall-pass-unique-pack-ship-20260902-01.md": "7900eaba",
    "p/cursor-harborline-commerce-compose-keep-lift-readback-20260902-01.md": "7155141f",
    "p/wire-super-mcp-fold-20260902-01.md": "cc7fda2e",
    "wire.html": "5b8edbda",
    "ground/WIRE_SUPER_MCP.md": "f36de0a5",
    "hub_pages.py": "5ac12648",
    "door.js": "dc59355d",
}


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class TestCursorWebmcpAdapterKeepLift(unittest.TestCase):
    def test_keep_leftover_adapter_pad_and_unread_packs(self) -> None:
        for rel, prefix in KEEP.items():
            blob = git_blob(rel)
            self.assertTrue(
                blob.startswith(prefix),
                f"{rel} reminted: want {prefix} got {blob[:8]}",
            )
        self.assertEqual(ADAPTER.stat().st_size, 21414)
        self.assertGreaterEqual(ADAPTER.stat().st_size, 20000)

    def test_leftover_unique_pack_tests_pass_after_keep_lift(self) -> None:
        leftover = subprocess.run(
            [
                "python3",
                "-m",
                "unittest",
                "test_cursor_wire_shared_super_mcp_catalog_readback.py",
                "test_cursor_wire_super_mcp_marketplace_readback.py",
                "test_latch_wake_super_mcp_pointer_readback.py",
                "test_cursor_wire_super_mcp_fold_readback.py",
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(leftover.returncode, 0, msg=leftover.stdout + leftover.stderr)
        self.assertIn("Ran 20 tests", leftover.stderr)

    def test_leftover_rematch_and_hall_pass_ship_tests_pass(self) -> None:
        leftover = subprocess.run(
            [
                "python3",
                "-m",
                "unittest",
                "test_cursor_wire_catalog_marketplace_latch_readback_rematch.py",
                "test_cursor_wire_hall_pass_unique_pack_ship.py",
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(leftover.returncode, 0, msg=leftover.stdout + leftover.stderr)
        self.assertIn("Ran 10 tests", leftover.stderr)

    def test_leftover_contest_remainder_tests_pass(self) -> None:
        leftover = subprocess.run(
            ["python3", "-m", "unittest", "test_cursor_webmcp_contest.py"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(leftover.returncode, 0, msg=leftover.stdout + leftover.stderr)
        self.assertIn("Ran 5 tests", leftover.stderr)

    def test_leftover_door_tests_still_pass(self) -> None:
        leftover = subprocess.run(
            ["python3", "-m", "unittest", "test_webmcp_door.py"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(leftover.returncode, 0, msg=leftover.stdout + leftover.stderr)
        self.assertIn("Ran 4 tests", leftover.stderr)

    def test_public_mcp_initialize_200(self) -> None:
        payload = json.dumps(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-03-26",
                    "capabilities": {},
                    "clientInfo": {"name": "cursor-webmcp-adapter-keep-lift", "version": "1"},
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

    def test_keep_lift_receipt_exists_and_does_not_steal(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        leftover = LEFTOVER.read_text(encoding="utf-8")
        remainder = REMAINDER.read_text(encoding="utf-8")
        self.assertIn("cursor-webmcp-adapter-keep-lift-20260903-01", text)
        self.assertIn("9ae34f64", text)
        self.assertIn("21414", text)
        self.assertIn("92bd1901", text)
        self.assertIn("3adb5a73", text)
        self.assertIn("14fced50", text)
        self.assertIn("c59733d0", text)
        self.assertIn("Did **not** remint leftover adapter", text)
        self.assertIn("cursor-webmcp-judge-url-20260903-01", text)
        self.assertNotEqual(text, leftover)
        self.assertNotEqual(text, remainder)
        self.assertNotIn("buy.stripe.com", text)
        self.assertFalse((ROOT / "CLAUDE_CORNER.md").exists())
        self.assertFalse((ROOT / "marketplace.html").exists())
        self.assertFalse(
            (ROOT / "p/cursor-wire-webmcp-challenge-readback-20260903-01.md").exists()
        )
        self.assertTrue(
            (ROOT / "p/cursor-webmcp-judge-url-20260903-01.md").is_file()
        )


if __name__ == "__main__":
    unittest.main()
