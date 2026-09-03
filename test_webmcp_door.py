#!/usr/bin/env python3
"""WebMCP door is a page-tool wrap of live spark MCP, not a second server."""
from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
HTML = ROOT / "webmcp.html"
ADAPTER = ROOT / "api" / "mcp.py"
STAGER = ROOT / "stage_spark_mcp_bundle.py"
VERCEL = ROOT / "vercel.json"
WORKFLOW = ROOT / ".github" / "workflows" / "spark-mcp-production.yml"

TOOLS = (
    "discover_commons_capabilities",
    "search_commons",
    "read_commons_resource",
    "append_post",
    "post_to_action_pad",
    "fire_action",
)


class WebmcpDoorTests(unittest.TestCase):
    def test_html_registers_document_model_context_tools(self) -> None:
        text = HTML.read_text(encoding="utf-8")
        self.assertIn("document.modelContext", text)
        self.assertIn("navigator.modelContext", text)
        self.assertIn("registerTool", text)
        for name in TOOLS:
            self.assertIn(name, text)
        self.assertIn("chrome://flags/#enable-webmcp-testing", text)
        self.assertIn("fire_action", text)

    def test_adapter_serves_webmcp_html_without_stealing_mcp(self) -> None:
        text = ADAPTER.read_text(encoding="utf-8")
        self.assertIn('"/webmcp"', text)
        self.assertIn('"/webmcp.html"', text)
        self.assertIn("webmcp.html", text)
        self.assertIn('"/mcp"', text)

    def test_bundle_and_vercel_route_webmcp_through_adapter(self) -> None:
        stager = STAGER.read_text(encoding="utf-8")
        self.assertIn('"webmcp.html"', stager)
        rewrites = json.loads(VERCEL.read_text(encoding="utf-8"))["rewrites"]
        by_source = {row["source"]: row["destination"] for row in rewrites}
        self.assertEqual(by_source["/mcp"], "/api/mcp")
        self.assertEqual(by_source["/webmcp"], "/api/webmcp_mcp")
        self.assertEqual(by_source["/webmcp.html"], "/api/webmcp_mcp")
        self.assertEqual(by_source["/webmcp/mcp"], "/api/webmcp_mcp")

    def test_production_workflow_watches_the_door(self) -> None:
        text = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("webmcp.html", text)
        self.assertIn("test_webmcp_door.py", text)


if __name__ == "__main__":
    unittest.main()
