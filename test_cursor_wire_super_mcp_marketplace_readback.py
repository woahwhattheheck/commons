#!/usr/bin/env python3
"""Pin unique-pack readback of leftover WIRE marketplace fold. Do not remint leftover."""

from __future__ import annotations

import json
import subprocess
import unittest
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RECEIPT = ROOT / "p/cursor-wire-super-mcp-marketplace-readback-20260902-01.md"
LEFTOVER = ROOT / "p/cursor-wire-super-mcp-marketplace-20260902-01.md"
MARKET = ROOT / ".agents/plugins/marketplace.json"

KEEP = {
    "p/cursor-wire-super-mcp-marketplace-20260902-01.md": "fbc20c0d",
    "host/wire_super_mcp_marketplace.py": "7b408ed9",
    "test_wire_super_mcp_marketplace.py": "42167891",
    ".agents/plugins/marketplace.json": "97875086",
    "integrations/commons_network_plugin/.codex-plugin/plugin.json": "0bc6fd84",
    "p/wire-super-mcp-fold-20260902-01.md": "cc7fda2e",
    "wire.html": "4ae38ce9",
    "ground/WIRE_SUPER_MCP.md": "f36de0a5",
    "p/wire-shared-super-mcp-catalog-20260902-01.md": "b6cb27ef",
    "super-mcp.html": "36687c0c",
    "host/super_mcp.py": "defaf19f",
    "p/latch-wake-super-mcp-pointer-20260902-01.md": "a35e63c3",
    "p/cursor-wire-super-mcp-fold-readback-20260902-01.md": "63b8221d",
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


class TestCursorWireSuperMcpMarketplaceReadback(unittest.TestCase):
    def test_keep_leftover_marketplace_and_unread_packs(self) -> None:
        for rel, prefix in KEEP.items():
            blob = git_blob(rel)
            self.assertTrue(
                blob.startswith(prefix),
                f"{rel} reminted: want {prefix} got {blob[:8]}",
            )

    def test_leftover_network_beside_grok_cloud_one_mcp(self) -> None:
        market = json.loads(MARKET.read_text(encoding="utf-8"))
        names = [row["name"] for row in market["plugins"]]
        self.assertEqual(names[0], "commons-grok-cloud")
        self.assertIn("commons-network", names)
        network = next(row for row in market["plugins"] if row["name"] == "commons-network")
        self.assertEqual(
            network["source"]["path"], "./integrations/commons_network_plugin"
        )
        self.assertEqual(network["policy"]["installation"], "AVAILABLE")
        self.assertNotIn("authentication", network["policy"])
        leftover = LEFTOVER.read_text(encoding="utf-8")
        self.assertIn("wire-super-mcp-fold-20260902-01", leftover)
        self.assertIn("commons-network", leftover)
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

    def test_leftover_marketplace_tests_still_pass(self) -> None:
        leftover = subprocess.run(
            ["python3", "-m", "unittest", "test_wire_super_mcp_marketplace.py"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(leftover.returncode, 0, msg=leftover.stdout + leftover.stderr)
        self.assertIn("Ran 7 tests", leftover.stderr)

    def test_readback_receipt_exists_and_does_not_steal(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        leftover = LEFTOVER.read_text(encoding="utf-8")
        self.assertIn("cursor-wire-super-mcp-marketplace-readback-20260902-01", text)
        self.assertIn("2fad5a546", text)
        self.assertIn("fbc20c0d", text)
        self.assertIn("7b408ed9", text)
        self.assertIn("97875086", text)
        self.assertIn("Did **not** remint leftover id", text)
        self.assertNotEqual(text, leftover)
        self.assertNotIn("buy.stripe.com", text)
        self.assertFalse((ROOT / "marketplace.html").exists())
        self.assertFalse((ROOT / "CLAUDE_CORNER.md").exists())


if __name__ == "__main__":
    unittest.main()
