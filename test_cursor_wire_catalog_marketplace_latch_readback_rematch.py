#!/usr/bin/env python3
"""Later-main rematch of leftover unique-pack leftover WIRE catalog + marketplace + Latch."""

from __future__ import annotations

import json
import subprocess
import unittest
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RECEIPT = ROOT / "p/cursor-wire-catalog-marketplace-latch-readback-rematch-20260903-01.md"
CATALOG_PACK = ROOT / "p/cursor-wire-shared-super-mcp-catalog-readback-20260902-01.md"
MARKET_PACK = ROOT / "p/cursor-wire-super-mcp-marketplace-readback-20260902-01.md"
LATCH_PACK = ROOT / "p/latch-wake-super-mcp-pointer-readback-20260902-01.md"
CATALOG_LEFTOVER = ROOT / "p/wire-shared-super-mcp-catalog-20260902-01.md"
MARKET_LEFTOVER = ROOT / "p/cursor-wire-super-mcp-marketplace-20260902-01.md"
LATCH_LEFTOVER = ROOT / "p/latch-wake-super-mcp-pointer-20260902-01.md"

KEEP = {
    "p/cursor-wire-shared-super-mcp-catalog-readback-20260902-01.md": "593d54bc",
    "p/cursor-wire-super-mcp-marketplace-readback-20260902-01.md": "448eda52",
    "p/latch-wake-super-mcp-pointer-readback-20260902-01.md": "250907c9",
    "test_cursor_wire_shared_super_mcp_catalog_readback.py": "8aef89f7",
    "test_cursor_wire_super_mcp_marketplace_readback.py": "dc347aae",
    "test_latch_wake_super_mcp_pointer_readback.py": "0b116a7d",
    "p/wire-shared-super-mcp-catalog-20260902-01.md": "b6cb27ef",
    "super-mcp.html": "36687c0c",
    "host/super_mcp.py": "defaf19f",
    "super-mcp/catalog.json": "f087937c",
    "test_super_mcp.py": "29cdec41",
    "p/cursor-wire-super-mcp-marketplace-20260902-01.md": "fbc20c0d",
    "host/wire_super_mcp_marketplace.py": "7b408ed9",
    "test_wire_super_mcp_marketplace.py": "42167891",
    ".agents/plugins/marketplace.json": "97875086",
    "p/latch-wake-super-mcp-pointer-20260902-01.md": "a35e63c3",
    "wakeup.html": "087a3ba1",
    "reach.html": "bc27c217",
    "p/wire-super-mcp-fold-20260902-01.md": "cc7fda2e",
    "wire.html": "4ae38ce9",
    "ground/WIRE_SUPER_MCP.md": "f36de0a5",
    "p/cursor-wire-super-mcp-fold-readback-20260902-01.md": "63b8221d",
    "p/cursor-big-huge-commerce-agents-readback-20260902-01.md": "2a5ce894",
    "p/cursor-harborline-commerce-compose-keep-lift-readback-20260902-01.md": "7155141f",
}


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class TestCursorWireCatalogMarketplaceLatchReadbackRematch(unittest.TestCase):
    def test_keep_leftover_unique_packs_fold_and_peer_packs(self) -> None:
        for rel, prefix in KEEP.items():
            blob = git_blob(rel)
            self.assertTrue(
                blob.startswith(prefix),
                f"{rel} reminted: want {prefix} got {blob[:8]}",
            )

    def test_independently_leftover_catalog_tests_14(self) -> None:
        leftover = subprocess.run(
            ["python3", "-m", "unittest", "test_super_mcp.py"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(leftover.returncode, 0, msg=leftover.stdout + leftover.stderr)
        self.assertIn("Ran 14 tests", leftover.stderr)

    def test_independently_leftover_marketplace_tests_7(self) -> None:
        leftover = subprocess.run(
            ["python3", "-m", "unittest", "test_wire_super_mcp_marketplace.py"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(leftover.returncode, 0, msg=leftover.stdout + leftover.stderr)
        self.assertIn("Ran 7 tests", leftover.stderr)

    def test_independently_spark_mcp_get_200(self) -> None:
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
        self.assertEqual(packet.get("auth"), "none")

    def test_rematch_receipt_exists_and_does_not_steal(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        catalog_pack = CATALOG_PACK.read_text(encoding="utf-8")
        market_pack = MARKET_PACK.read_text(encoding="utf-8")
        latch_pack = LATCH_PACK.read_text(encoding="utf-8")
        catalog_leftover = CATALOG_LEFTOVER.read_text(encoding="utf-8")
        market_leftover = MARKET_LEFTOVER.read_text(encoding="utf-8")
        latch_leftover = LATCH_LEFTOVER.read_text(encoding="utf-8")
        self.assertIn(
            "cursor-wire-catalog-marketplace-latch-readback-rematch-20260903-01",
            text,
        )
        self.assertIn("593d54bc", text)
        self.assertIn("448eda52", text)
        self.assertIn("250907c9", text)
        self.assertIn("b86e95355", text)
        self.assertIn("14/14", text)
        self.assertIn("7/7", text)
        self.assertIn("1.4.0", text)
        self.assertIn("4ae38ce9", text)
        self.assertIn("f36de0a5", text)
        self.assertIn("2a5ce894", text)
        self.assertIn("7155141f", text)
        self.assertIn("Did **not** remint leftover fold", text)
        self.assertIn("KEEP peer unique-packs", text)
        self.assertIn("No HOLD", text)
        self.assertIn("bc-d5c99f0c", text)
        self.assertIn("bc-73365238", text)
        self.assertNotEqual(text, catalog_pack)
        self.assertNotEqual(text, market_pack)
        self.assertNotEqual(text, latch_pack)
        self.assertNotEqual(text, catalog_leftover)
        self.assertNotEqual(text, market_leftover)
        self.assertNotEqual(text, latch_leftover)
        self.assertNotIn("buy.stripe.com", text)
        self.assertFalse((ROOT / "marketplace.html").exists())
        self.assertFalse((ROOT / "CLAUDE_CORNER.md").exists())
        self.assertFalse(
            (ROOT / "p/latch-hub-eyes-wake-habit-readback-20260902-01.md").exists()
        )


if __name__ == "__main__":
    unittest.main()
