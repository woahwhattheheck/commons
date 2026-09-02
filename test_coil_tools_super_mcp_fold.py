#!/usr/bin/env python3
"""Regression for COIL PR 8476 fold + MANUAL.md thin super_mcp pointer leftover.

Do not remint tools.json / manual.html / the COIL receipt. The pointer is the
named follow-up that the honest land list deferred.
"""

from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path

import manual_build

ROOT = Path(__file__).resolve().parent
TOOLS = ROOT / "tools.json"
MANUAL_HTML = ROOT / "manual.html"
MANUAL_MD = ROOT / "ground" / "MANUAL.md"
BUILDER = ROOT / "manual_build.py"
RECEIPT = ROOT / "p/coil-tools-super-mcp-fold-20260902-01.md"
PUBLIC_MCP = "https://commons-spark-mcp.vercel.app/mcp"

KEEP = {
    "tools.json": "d5d124bd",
    "manual.html": "d9a06857",
    "p/coil-tools-super-mcp-fold-20260902-01.md": "6948bdc1",
}


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class TestCoilToolsSuperMcpFold(unittest.TestCase):
    def test_keep_pr8476_catalog_bytes(self) -> None:
        for rel, prefix in KEEP.items():
            blob = git_blob(rel)
            self.assertTrue(
                blob.startswith(prefix),
                f"{rel} reminted: want {prefix} got {blob[:8]}",
            )

    def test_tools_json_super_mcp_one_public_mcp(self) -> None:
        data = json.loads(TOOLS.read_text(encoding="utf-8"))
        mcp = data.get("super_mcp") or {}
        share = data.get("share") or ""
        self.assertEqual(mcp.get("url"), PUBLIC_MCP)
        self.assertEqual(mcp.get("door"), "wire.html")
        self.assertEqual(mcp.get("law"), "ground/WIRE_SUPER_MCP.md")
        self.assertEqual(mcp.get("insights"), "insights.html")
        self.assertIn("Do not remint a second /mcp", mcp.get("note") or "")
        self.assertNotIn("fire 337", share)
        self.assertIn("inject 0x01", share)
        self.assertIn("pulse 78", share)
        self.assertIn("light 7913", share)

    def test_manual_html_nav_and_shared_paragraph(self) -> None:
        text = MANUAL_HTML.read_text(encoding="utf-8")
        self.assertIn('href="./wire.html">wire (shared MCP)</a>', text)
        self.assertIn('href="./insights.html">insights</a>', text)
        self.assertIn('href="./gemini-mcp.html">gemini-mcp</a>', text)
        self.assertIn("One shared super MCP is commons-spark-mcp", text)
        self.assertIn("ground/WIRE_SUPER_MCP.md", text)
        self.assertNotIn("337 NO", text)
        self.assertNotIn("fire 337", text)

    def test_receipt_honest_land_list_does_not_claim_manual_md(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        self.assertIn("coil-tools-super-mcp-fold-20260902-01", text)
        self.assertIn("wire-super-mcp-fold-20260902-01", text)
        self.assertIn("latch-wake-super-mcp-pointer-20260902-01", text)
        self.assertIn("No second MCP", text)
        self.assertIn("`tools.json` top-level `super_mcp`", text)
        self.assertIn("`manual.html` nav", text)
        self.assertNotIn("`ground/MANUAL.md` thin one-line super_mcp pointer only.", text)

    def test_manual_md_thin_pointer_and_builder_emit(self) -> None:
        manual = MANUAL_MD.read_text(encoding="utf-8")
        builder = BUILDER.read_text(encoding="utf-8")
        data = json.loads(TOOLS.read_text(encoding="utf-8"))
        line = manual_build.super_mcp_pointer_line(data)
        self.assertIsNotNone(line)
        self.assertIn(PUBLIC_MCP, line)
        self.assertIn("[wire.html](../wire.html)", line)
        self.assertIn("[WIRE_SUPER_MCP.md](./WIRE_SUPER_MCP.md)", line)
        self.assertIn("Do not remint a second `/mcp`", line)
        self.assertIn(line, manual)
        self.assertIn("super_mcp_pointer_line", builder)
        self.assertIn("do not fire 337", manual.lower())
        self.assertNotIn("337 yes", manual.lower())
        self.assertNotIn("buy.stripe.com", manual)
        self.assertNotIn("buy.stripe.com", line)


if __name__ == "__main__":
    unittest.main()
