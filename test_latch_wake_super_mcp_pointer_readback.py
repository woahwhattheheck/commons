#!/usr/bin/env python3
"""Pin unique-pack readback of leftover Latch wake/reach super MCP pointer. Do not remint leftover."""

from __future__ import annotations

import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RECEIPT = ROOT / "p/latch-wake-super-mcp-pointer-readback-20260902-01.md"
LEFTOVER = ROOT / "p/latch-wake-super-mcp-pointer-20260902-01.md"
WAKEUP = ROOT / "wakeup.html"
REACH = ROOT / "reach.html"

KEEP = {
    "p/latch-wake-super-mcp-pointer-20260902-01.md": "a35e63c3",
    "wakeup.html": "087a3ba1",
    "reach.html": "bc27c217",
    "p/wire-super-mcp-fold-20260902-01.md": "cc7fda2e",
    "wire.html": "4ae38ce9",
    "ground/WIRE_SUPER_MCP.md": "f36de0a5",
    "p/wire-shared-super-mcp-catalog-20260902-01.md": "b6cb27ef",
    "super-mcp.html": "36687c0c",
    "p/cursor-wire-super-mcp-marketplace-20260902-01.md": "fbc20c0d",
    "p/goat-pages-super-mcp-land-20260902-01.md": "171e0daaf",
    "p/latch-hub-eyes-wake-habit-20260902-01.md": "dc83d42c",
    "p/cursor-wire-super-mcp-fold-readback-20260902-01.md": "63b8221d",
    "p/cursor-big-huge-commerce-agents-20260902-01.md": "fddb5a7c",
    "api/mcp.py": "bc558a5f",
    "hub_pages.py": "5ac12648",
    "door.js": "dc59355d",
    "ground/OWNER_NOW.md": "59b1fd37",
}


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class TestLatchWakeSuperMcpPointerReadback(unittest.TestCase):
    def test_keep_leftover_pointer_and_unread_packs(self) -> None:
        for rel, prefix in KEEP.items():
            blob = git_blob(rel)
            self.assertTrue(
                blob.startswith(prefix),
                f"{rel} reminted: want {prefix} got {blob[:8]}",
            )

    def test_leftover_wakeup_and_reach_point_at_one_mcp(self) -> None:
        wakeup = WAKEUP.read_text(encoding="utf-8")
        reach = REACH.read_text(encoding="utf-8")
        leftover = LEFTOVER.read_text(encoding="utf-8")
        for text in (wakeup, reach):
            self.assertIn("https://commons-spark-mcp.vercel.app/mcp", text)
            self.assertIn("wire.html", text)
            self.assertIn("wire-super-mcp-fold-20260902-01", text)
            self.assertIn("No second MCP", text)
            self.assertNotIn("buy.stripe.com", text)
        self.assertIn("https://commons-spark-mcp.vercel.app/mcp", leftover)
        self.assertIn("wire.html", leftover)
        self.assertIn("wire-super-mcp-fold-20260902-01", leftover)
        self.assertIn("no second MCP", leftover)
        self.assertNotIn("buy.stripe.com", leftover)
        self.assertIn("latch-wake-super-mcp-pointer-20260902-01", wakeup)
        self.assertIn("latch-wake-super-mcp-pointer-20260902-01", reach)
        self.assertIn("./wire.html", wakeup)
        self.assertIn("./wire.html", reach)

    def test_leftover_catalog_tests_still_pass(self) -> None:
        leftover = subprocess.run(
            ["python3", "-m", "unittest", "test_super_mcp.py"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(leftover.returncode, 0, msg=leftover.stdout + leftover.stderr)
        self.assertIn("Ran 14 tests", leftover.stderr)

    def test_readback_receipt_exists_and_does_not_steal(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        leftover = LEFTOVER.read_text(encoding="utf-8")
        self.assertIn("latch-wake-super-mcp-pointer-readback-20260902-01", text)
        self.assertIn("5bec2c9ef", text)
        self.assertIn("2aa5c1df", text)
        self.assertIn("a35e63c3", text)
        self.assertIn("087a3ba1", text)
        self.assertIn("bc27c217", text)
        self.assertIn("Did **not** remint leftover id", text)
        self.assertNotEqual(text, leftover)
        self.assertNotIn("buy.stripe.com", text)
        self.assertFalse((ROOT / "marketplace.html").exists())
        self.assertFalse((ROOT / "CLAUDE_CORNER.md").exists())
        self.assertFalse(
            (ROOT / "p/cursor-big-huge-commerce-agents-readback-20260902-01.md").exists()
        )
        self.assertFalse(
            (
                ROOT
                / "p/cursor-harborline-commerce-compose-keep-lift-readback-20260902-01.md"
            ).exists()
        )
        self.assertFalse(
            (
                ROOT
                / "p/latch-hub-eyes-wake-habit-readback-20260902-01.md"
            ).exists()
        )


if __name__ == "__main__":
    unittest.main()
