#!/usr/bin/env python3
"""Pin WebMCP contest remainder. Do not remint leftover adapter or leftover pad."""

from __future__ import annotations

import json
import subprocess
import unittest
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RECEIPT = ROOT / "p/cursor-webmcp-contest-20260903-01.md"
LEFTOVER = ROOT / "p/wire-webmcp-challenge-20260903-01.md"
ADAPTER = ROOT / "api" / "mcp.py"
DOOR = ROOT / "webmcp.html"
WORKFLOW = ROOT / ".github" / "workflows" / "spark-mcp-production.yml"

KEEP = {
    "p/wire-webmcp-challenge-20260903-01.md": "0e815c6d",
    "webmcp.html": "b18ec98e",
    "api/mcp.py": "9ae34f64",
    "stage_spark_mcp_bundle.py": "8b2045c9",
    "p/wire-super-mcp-fold-20260902-01.md": "cc7fda2e",
    "wire.html": "4ae38ce9",
    "ground/WIRE_SUPER_MCP.md": "f36de0a5",
    "p/cursor-wire-shared-super-mcp-catalog-readback-20260902-01.md": "593d54bc",
    "p/cursor-wire-super-mcp-marketplace-readback-20260902-01.md": "448eda52",
    "p/latch-wake-super-mcp-pointer-readback-20260902-01.md": "250907c9",
    "hub_pages.py": "5ac12648",
    "door.js": "dc59355d",
}


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class TestCursorWebmcpContest(unittest.TestCase):
    def test_keep_leftover_adapter_and_pad(self) -> None:
        for rel, prefix in KEEP.items():
            blob = git_blob(rel)
            self.assertTrue(
                blob.startswith(prefix),
                f"{rel} reminted: want {prefix} got {blob[:8]}",
            )
        self.assertEqual(ADAPTER.stat().st_size, 21414)
        self.assertGreaterEqual(ADAPTER.stat().st_size, 20000)

    def test_wait_step_requires_live_webmcp_html(self) -> None:
        text = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("https://commons-spark-mcp.vercel.app/webmcp", text)
        self.assertIn("text/html", text)
        self.assertIn("document.modelContext", text)
        self.assertIn("LIVE_WEBMCP_HTML", text)
        self.assertIn("LIVE_SOURCE_PARITY", text)

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
                    "clientInfo": {"name": "cursor-webmcp-contest", "version": "1"},
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

    def test_readback_receipt_exists_and_does_not_steal(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        leftover = LEFTOVER.read_text(encoding="utf-8")
        door = DOOR.read_text(encoding="utf-8")
        self.assertIn("cursor-webmcp-contest-20260903-01", text)
        self.assertIn("9ae34f64", text)
        self.assertIn("21414", text)
        self.assertIn("33796486138", text)
        self.assertIn("Did **not** remint leftover id", text)
        self.assertIn("document.modelContext", door)
        self.assertIn("fire_action", door)
        self.assertNotEqual(text, leftover)
        self.assertNotIn("buy.stripe.com", text)
        self.assertFalse((ROOT / "CLAUDE_CORNER.md").exists())
        self.assertFalse((ROOT / "marketplace.html").exists())


if __name__ == "__main__":
    unittest.main()
