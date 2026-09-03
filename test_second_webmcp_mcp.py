#!/usr/bin/env python3
"""Second WebMCP MCP is a real second server, not a remint of api/mcp.py."""
from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ADAPTER = ROOT / "api" / "webmcp_mcp.py"
COMMONS_ADAPTER = ROOT / "api" / "mcp.py"
HTML = ROOT / "webmcp.html"
VERCEL = ROOT / "vercel.json"
STAGER = ROOT / "stage_spark_mcp_bundle.py"


class SecondWebmcpMcpTests(unittest.TestCase):
    def test_second_adapter_exists_and_names_webmcp(self) -> None:
        text = ADAPTER.read_text(encoding="utf-8")
        self.assertIn('SERVER_NAME = "webmcp"', text)
        self.assertIn('SERVER_VERSION = "1.0.0"', text)
        self.assertIn('"/webmcp/mcp"', text)
        self.assertIn('"discover"', text)
        self.assertIn('"search"', text)
        self.assertIn('"fire"', text)

    def test_commons_adapter_not_truncated(self) -> None:
        size = COMMONS_ADAPTER.stat().st_size
        self.assertGreater(size, 15000)

    def test_html_points_at_second_mcp(self) -> None:
        text = HTML.read_text(encoding="utf-8")
        self.assertIn("/webmcp/mcp", text)
        self.assertNotIn('? "/mcp"', text)

    def test_vercel_routes_second_server(self) -> None:
        data = json.loads(VERCEL.read_text(encoding="utf-8"))
        self.assertIn("api/webmcp_mcp.py", data["functions"])
        by_source = {row["source"]: row["destination"] for row in data["rewrites"]}
        self.assertEqual(by_source["/mcp"], "/api/mcp")
        self.assertEqual(by_source["/webmcp/mcp"], "/api/webmcp_mcp")
        self.assertEqual(by_source["/webmcp"], "/api/webmcp_mcp")

    def test_stager_includes_second_adapter(self) -> None:
        text = STAGER.read_text(encoding="utf-8")
        self.assertIn('"api/webmcp_mcp.py"', text)


if __name__ == "__main__":
    unittest.main()
