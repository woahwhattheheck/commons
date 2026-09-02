#!/usr/bin/env python3
"""Pin unique-pack readback of GOAT Pages leftover. Do not remint leftover."""

from __future__ import annotations

import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RECEIPT = ROOT / "p/cursor-goat-pages-super-mcp-land-readback-20260902-01.md"
LEFTOVER = ROOT / "p/goat-pages-super-mcp-land-20260902-01.md"
CATALOG = ROOT / "catalog.html"
BOARDS = ROOT / "boards.html"
HUB = ROOT / "hub_pages.py"


KEEP = {
    "p/goat-pages-super-mcp-land-20260902-01.md": "171e0daaf",
    "catalog.html": "154b7b67",
    "boards.html": "3fa79f12",
    "wire.html": "4ae38ce9",
    "ground/WIRE_SUPER_MCP.md": "f36de0a5",
    "p/wire-super-mcp-fold-20260902-01.md": "cc7fda2e",
    "p/latch-wake-super-mcp-pointer-20260902-01.md": "a35e63c3",
    "p/wire-shared-super-mcp-catalog-20260902-01.md": "b6cb27ef",
    "super-mcp.html": "36687c0c",
    "hub_pages.py": "5ac12648",
    "door.js": "dc59355d",
    "p/cursor-claude-commerce-agents-20260902-01.md": "3e48f691",
    "host/commerce_agents.py": "8d2ddf29",
    "test_commerce_agents.py": "78a158b3",
    "p/cursor-big-huge-commerce-agents-20260902-01.md": "fddb5a7c",
    "host/commerce_agents_same_loop.py": "c90f6e50",
    "test_commerce_agents_same_loop.py": "623e99e8",
    "p/cursor-claude-commerce-agents-readback-20260902-01.md": "0153924f",
    "p/cursor-harborline-commerce-compose-readback-20260902-01.md": "b33e2e24",
    "p/cursor-harborline-commerce-compose-keep-lift-20260902-01.md": "668dd5c4",
    "ground/OWNER_NOW.md": "59b1fd37",
}


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class TestCursorGoatPagesSuperMcpLandReadback(unittest.TestCase):
    def test_keep_leftover_catalog_fold_and_hub(self) -> None:
        for rel, prefix in KEEP.items():
            blob = git_blob(rel)
            self.assertTrue(
                blob.startswith(prefix),
                f"{rel} reminted: want {prefix} got {blob[:8]}",
            )

    def test_leftover_catalog_still_points_at_one_mcp(self) -> None:
        text = CATALOG.read_text(encoding="utf-8")
        leftover = LEFTOVER.read_text(encoding="utf-8")
        self.assertIn('href="./wire.html"', text)
        self.assertIn("https://commons-spark-mcp.vercel.app/mcp", text)
        self.assertIn("goat-pages-super-mcp-land-20260902-01", text)
        self.assertIn("55714fd6", text)
        self.assertIn("Not a second MCP", text)
        self.assertIn("Shared super MCP", leftover)
        self.assertIn("./wire.html", leftover)
        self.assertIn("catalog.html", leftover)
        self.assertNotIn("buy.stripe.com", text)
        self.assertNotIn("buy.stripe.com", leftover)

    def test_boards_row_hit_generator_keep_unread(self) -> None:
        boards = BOARDS.read_text(encoding="utf-8")
        hub = HUB.read_text(encoding="utf-8")
        leftover = LEFTOVER.read_text(encoding="utf-8")
        self.assertIn('boards.html row "Shared super MCP"', leftover)
        self.assertIn('href="./grounding.html">first visit</a>', boards)
        self.assertIn('href="./wire.html">Shared super MCP</a>', boards)
        self.assertIn("goat-pages-super-mcp-land-20260902-01", boards)
        self.assertIn("Not a second MCP", boards)
        self.assertNotIn('href="./wire.html"', hub)
        self.assertNotIn("Shared super MCP", hub)

    def test_leftover_commerce_tests_still_pass(self) -> None:
        leftover = subprocess.run(
            ["python3", "-m", "unittest", "test_commerce_agents.py"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(leftover.returncode, 0, msg=leftover.stdout + leftover.stderr)
        self.assertIn("Ran 5 tests", leftover.stderr)
        remainder = subprocess.run(
            ["python3", "-m", "unittest", "test_commerce_agents_same_loop.py"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(
            remainder.returncode, 0, msg=remainder.stdout + remainder.stderr
        )
        self.assertIn("Ran 12 tests", remainder.stderr)

    def test_readback_receipt_exists_and_does_not_steal(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        leftover = LEFTOVER.read_text(encoding="utf-8")
        self.assertIn("cursor-goat-pages-super-mcp-land-readback-20260902-01", text)
        self.assertIn("25d54fcc4", text)
        self.assertIn("171e0daaf", text)
        self.assertIn("154b7b67", text)
        self.assertIn("5ac12648", text)
        self.assertIn("FINDER-FAILED", text)
        self.assertIn("Did **not** remint leftover id", text)
        self.assertNotEqual(text, leftover)
        self.assertNotIn("buy.stripe.com", text)
        self.assertFalse((ROOT / "marketplace.html").exists())
        self.assertFalse((ROOT / "qualify.html").exists())
        self.assertFalse((ROOT / "CLAUDE_CORNER.md").exists())
        self.assertTrue(
            (ROOT / "p/cursor-big-huge-commerce-agents-readback-20260902-01.md").exists()
        )
        self.assertTrue(
            (
                ROOT
                / "p/cursor-harborline-commerce-compose-keep-lift-readback-20260902-01.md"
            ).exists()
        )


if __name__ == "__main__":
    unittest.main()
