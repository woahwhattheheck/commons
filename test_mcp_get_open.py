#!/usr/bin/env python3
"""GET /mcp is an open capability map. 405 was the bug, not the spec."""
from __future__ import annotations

import http.client
import json
import threading
import unittest
from pathlib import Path
from unittest import mock

import commons_mcp as cm
from api import mcp


ROOT = Path(__file__).resolve().parent
PUBLIC_URL = "https://commons-spark-mcp.vercel.app/mcp"


class PublicMcpGetOpenTests(unittest.TestCase):
    def test_capability_map_has_no_login(self) -> None:
        core = cm.public_mcp_capability_map()
        self.assertEqual(core["name"], "commons")
        self.assertEqual(core["version"], cm.SERVER_VERSION)
        self.assertEqual(core["auth"], "none")
        self.assertTrue(core["open_door"])
        self.assertIsNone(core["session"])
        self.assertFalse(core["login"])
        self.assertFalse(core["oauth"])
        self.assertIn("discover_commons_capabilities", core["tools"])
        self.assertNotIn("get_send_link", core["tools"])
        public = cm.public_mcp_capability_map(
            extra_tools=(mcp.GET_SEND_LINK_TOOL["name"],),
            url=PUBLIC_URL,
        )
        self.assertIn("get_send_link", public["tools"])
        self.assertEqual(public["toolCount"], 17)
        self.assertEqual(public["url"], PUBLIC_URL)
        blob = json.dumps(public)
        self.assertNotIn("password", blob.lower())
        self.assertNotIn("api-key", blob.lower())

    def test_adapter_get_mcp_returns_200_map(self) -> None:
        httpd = cm.ThreadingHTTPServer(("127.0.0.1", 0), mcp.handler)
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        connection = http.client.HTTPConnection(
            "127.0.0.1", httpd.server_port, timeout=5
        )
        try:
            connection.request("GET", "/mcp")
            response = connection.getresponse()
            payload = json.loads(response.read().decode("utf-8"))
            self.assertEqual(response.status, 200)
            self.assertEqual(payload["auth"], "none")
            self.assertTrue(payload["open_door"])
            self.assertEqual(payload["toolCount"], 17)
            self.assertIn("get_send_link", payload["tools"])
            allow = response.getheader("Access-Control-Allow-Origin")
            self.assertEqual(allow, "*")

            connection.request("GET", "/mcp?probe=1")
            again = connection.getresponse()
            body = json.loads(again.read().decode("utf-8"))
            self.assertEqual(again.status, 200)
            self.assertEqual(body["name"], "commons")
        finally:
            connection.close()
            httpd.shutdown()
            httpd.server_close()

    def test_core_http_get_mcp_returns_200_map(self) -> None:
        server = cm.MCPServer(mock.Mock())
        handler = cm.make_http_handler(server)
        httpd = cm.ThreadingHTTPServer(("127.0.0.1", 0), handler)
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        connection = http.client.HTTPConnection(
            "127.0.0.1", httpd.server_port, timeout=5
        )
        try:
            connection.request("GET", "/mcp")
            response = connection.getresponse()
            payload = json.loads(response.read().decode("utf-8"))
            self.assertEqual(response.status, 200)
            self.assertEqual(payload["name"], "commons")
            self.assertTrue(payload["open_door"])
            self.assertNotIn("get_send_link", payload["tools"])
        finally:
            connection.close()
            httpd.shutdown()
            httpd.server_close()

    def test_docs_retired_405_as_spec(self) -> None:
        catalog = json.loads((ROOT / "carriers" / "catalog.json").read_text(encoding="utf-8"))
        self.assertEqual(catalog["live"]["GET /mcp"], 200)
        self.assertEqual(catalog["live"]["measured_20260902"]["GET /mcp"], 200)
        self.assertEqual(catalog["live"]["measured_20260826"]["GET /mcp"], 405)
        contract = (ROOT / ".agents/skills/grok-web-commons/references/connector-contract.md").read_text(encoding="utf-8")
        self.assertIn("200 (open capability map, no login)", contract)
        self.assertNotIn("| GET `/mcp` | 405 |", contract)
        spark = (ROOT / "docs" / "spark-mcp.md").read_text(encoding="utf-8")
        self.assertIn("GET /mcp", spark)
        self.assertNotIn("stream `GET` returns `405`", spark)
        gemini = (ROOT / "docs" / "gemini-mcp.md").read_text(encoding="utf-8")
        self.assertIn("| `GET /mcp` | **200** |", gemini)
        self.assertNotIn("| `GET /mcp` | **405** |", gemini)


if __name__ == "__main__":
    unittest.main()
