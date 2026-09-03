#!/usr/bin/env python3
"""Pin unique-pack readback of leftover WIRE shared super MCP catalog. Do not remint leftover."""

from __future__ import annotations

import json
import subprocess
import unittest
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RECEIPT = ROOT / "p/cursor-wire-shared-super-mcp-catalog-readback-20260902-01.md"
LEFTOVER = ROOT / "p/wire-shared-super-mcp-catalog-20260902-01.md"
DOOR = ROOT / "super-mcp.html"

KEEP = {
    "p/wire-shared-super-mcp-catalog-20260902-01.md": "b6cb27ef",
    "super-mcp.html": "36687c0c",
    "host/super_mcp.py": "defaf19f",
    "super-mcp/catalog.json": "f087937c",
    "test_super_mcp.py": "29cdec41",
    ".agents/skills/super-mcp/SKILL.md": "1f959520",
    "ground/tokens/super-mcp.md": "716526ba",
    "p/wire-super-mcp-fold-20260902-01.md": "cc7fda2e",
    "wire.html": "4ae38ce9",
    "ground/WIRE_SUPER_MCP.md": "f36de0a5",
    "p/cursor-wire-super-mcp-marketplace-20260902-01.md": "fbc20c0d",
    "p/latch-wake-super-mcp-pointer-20260902-01.md": "a35e63c3",
    "p/goat-pages-super-mcp-land-20260902-01.md": "171e0daaf",
    "catalog.html": "154b7b67",
    "p/cursor-wire-super-mcp-fold-readback-20260902-01.md": "63b8221d",
    "p/cursor-google-ai-mode-hall-pass-readback-20260902-01.md": "42e9e750",
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


class TestCursorWireSharedSuperMcpCatalogReadback(unittest.TestCase):
    def test_keep_leftover_catalog_and_unread_packs(self) -> None:
        for rel, prefix in KEEP.items():
            blob = git_blob(rel)
            self.assertTrue(
                blob.startswith(prefix),
                f"{rel} reminted: want {prefix} got {blob[:8]}",
            )

    def test_leftover_door_is_one_mcp_zero_auth(self) -> None:
        door = DOOR.read_text(encoding="utf-8")
        leftover = LEFTOVER.read_text(encoding="utf-8")
        self.assertIn("https://commons-spark-mcp.vercel.app/mcp", door)
        self.assertIn("super-mcp/catalog.json", door)
        self.assertIn("wire.html", door)
        self.assertIn("discover_commons_capabilities", door)
        self.assertIn("wire-super-mcp-fold-20260902-01", leftover)
        self.assertIn("host/super_mcp.py", leftover)
        self.assertNotIn("buy.stripe.com", door)
        self.assertNotIn("buy.stripe.com", leftover)

    def test_leftover_route_browser_is_no_login(self) -> None:
        leftover = subprocess.run(
            ["python3", "host/super_mcp.py", "route", "--need", "browser"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(leftover.returncode, 0, msg=leftover.stdout + leftover.stderr)
        self.assertIn("google.com", leftover.stdout)
        self.assertIn("no login", leftover.stdout)
        self.assertIn("https://commons-spark-mcp.vercel.app/mcp", leftover.stdout)

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
        self.assertEqual(packet.get("toolCount"), 17)

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
        self.assertIn("cursor-wire-shared-super-mcp-catalog-readback-20260902-01", text)
        self.assertIn("3c89b707e", text)
        self.assertIn("b6cb27ef", text)
        self.assertIn("36687c0c", text)
        self.assertIn("defaf19f", text)
        self.assertIn("Did **not** remint leftover id", text)
        self.assertNotEqual(text, leftover)
        self.assertNotIn("buy.stripe.com", text)
        self.assertFalse((ROOT / "marketplace.html").exists())
        self.assertFalse((ROOT / "CLAUDE_CORNER.md").exists())


if __name__ == "__main__":
    unittest.main()
