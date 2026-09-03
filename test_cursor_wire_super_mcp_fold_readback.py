#!/usr/bin/env python3
"""Pin unique-pack readback of WIRE fold leftover. Do not remint leftover."""

from __future__ import annotations

import json
import subprocess
import unittest
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RECEIPT = ROOT / "p/cursor-wire-super-mcp-fold-readback-20260902-01.md"
LEFTOVER = ROOT / "p/wire-super-mcp-fold-20260902-01.md"
DOOR = ROOT / "wire.html"
LAW = ROOT / "ground/WIRE_SUPER_MCP.md"

KEEP = {
    "p/wire-super-mcp-fold-20260902-01.md": "cc7fda2e",
    "wire.html": "4ae38ce9",
    "ground/WIRE_SUPER_MCP.md": "f36de0a5",
    "p/wire-shared-super-mcp-catalog-20260902-01.md": "b6cb27ef",
    "super-mcp.html": "36687c0c",
    "p/latch-wake-super-mcp-pointer-20260902-01.md": "a35e63c3",
    "p/goat-pages-super-mcp-land-20260902-01.md": "171e0daaf",
    "catalog.html": "154b7b67",
    "p/cursor-goat-pages-super-mcp-land-readback-20260902-01.md": "f98887bf",
    "p/cursor-wire-shared-super-mcp-catalog-readback-20260902-01.md": "593d54bc",
    "p/cursor-wire-super-mcp-marketplace-readback-20260902-01.md": "448eda52",
    "p/latch-wake-super-mcp-pointer-readback-20260902-01.md": "250907c9",
    "p/cursor-google-ai-mode-hall-pass-20260902-01.md": "4bb8b78d",
    "p/cursor-claude-commerce-agents-20260902-01.md": "3e48f691",
    "host/commerce_agents.py": "8d2ddf29",
    "p/cursor-big-huge-commerce-agents-20260902-01.md": "fddb5a7c",
    "p/cursor-big-huge-commerce-agents-readback-20260902-01.md": "2a5ce894",
    "p/cursor-harborline-commerce-compose-keep-lift-readback-20260902-01.md": "7155141f",
    "api/mcp.py": "bc558a5f",
    "hub_pages.py": "5ac12648",
    "door.js": "dc59355d",
    "ground/OWNER_NOW.md": "59b1fd37",
}


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class TestCursorWireSuperMcpFoldReadback(unittest.TestCase):
    def test_keep_leftover_fold_and_unread_packs(self) -> None:
        for rel, prefix in KEEP.items():
            blob = git_blob(rel)
            self.assertTrue(
                blob.startswith(prefix),
                f"{rel} reminted: want {prefix} got {blob[:8]}",
            )

    def test_leftover_door_is_one_mcp_zero_auth(self) -> None:
        door = DOOR.read_text(encoding="utf-8")
        law = LAW.read_text(encoding="utf-8")
        leftover = LEFTOVER.read_text(encoding="utf-8")
        self.assertIn("https://commons-spark-mcp.vercel.app/mcp", door)
        self.assertIn("Zero auth", door)
        self.assertIn("not</em> a second MCP", door)
        self.assertIn("One public MCP", law)
        self.assertIn("wire.html", law)
        self.assertIn("wire-gemini-mcp-all-carriers-20260826-01", leftover)
        self.assertNotIn("buy.stripe.com", door)
        self.assertNotIn("buy.stripe.com", leftover)

    def test_public_mcp_get_200(self) -> None:
        req = urllib.request.Request(
            "https://commons-spark-mcp.vercel.app/mcp",
            method="GET",
        )
        with urllib.request.urlopen(req, timeout=20) as resp:
            body = resp.read()
            self.assertEqual(resp.status, 200)
        packet = json.loads(body.decode("utf-8"))
        self.assertEqual(packet.get("name"), "commons")
        self.assertEqual(packet.get("version"), "1.4.0")

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

    def test_readback_receipt_exists_and_does_not_steal(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        leftover = LEFTOVER.read_text(encoding="utf-8")
        self.assertIn("cursor-wire-super-mcp-fold-readback-20260902-01", text)
        self.assertIn("55714fd6", text)
        self.assertIn("cc7fda2e", text)
        self.assertIn("4ae38ce9", text)
        self.assertIn("f36de0a5", text)
        self.assertIn("bc558a5f", text)
        self.assertIn("Did **not** remint leftover id", text)
        self.assertNotEqual(text, leftover)
        self.assertNotIn("buy.stripe.com", text)
        self.assertFalse((ROOT / "marketplace.html").exists())
        self.assertFalse((ROOT / "CLAUDE_CORNER.md").exists())
        self.assertTrue(
            (
                ROOT
                / "p/cursor-wire-shared-super-mcp-catalog-readback-20260902-01.md"
            ).is_file()
        )
        self.assertTrue(
            (
                ROOT
                / "p/cursor-wire-super-mcp-marketplace-readback-20260902-01.md"
            ).is_file()
        )
        self.assertTrue(
            (
                ROOT
                / "p/latch-wake-super-mcp-pointer-readback-20260902-01.md"
            ).is_file()
        )


if __name__ == "__main__":
    unittest.main()
