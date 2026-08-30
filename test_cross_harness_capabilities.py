#!/usr/bin/env python3
"""One call-first Commons capability contract across every named harness."""
from __future__ import annotations

import hashlib
import http.client
import json
import threading
import unittest
from pathlib import Path

import commons_mcp as cm
from api import mcp


ROOT = Path(__file__).resolve().parent
CATALOG_PATH = ROOT / "harnesses" / "catalog.json"
EXPECTED_HARNESSES = {
    "claude-mobile",
    "claude-code-mobile",
    "claude-code-desktop",
    "claude-chat-desktop",
    "gpt-cloud",
    "gpt-desktop",
    "gpt-mobile",
    "cursor-desktop",
    "cursor-cloud",
    "cursor-mobile",
    "gemini-custom",
    "grok-com",
    "grokbot",
    "titan-hands",
}
CLIENT_NAMES = (
    "Claude mobile",
    "Claude Code mobile",
    "Claude Code desktop",
    "Claude chat desktop",
    "GPT cloud",
    "GPT desktop",
    "GPT mobile",
    "Cursor desktop",
    "Cursor cloud",
    "Cursor mobile",
    "Gemini custom MCP",
    "grok.com",
    "Grokbot",
    "TITAN Hands",
)


class RepoTruth:
    def head_sha(self) -> str:
        return "a" * 40

    def read_at_sha(self, path: str, sha: str) -> str | None:
        candidate = (ROOT / path).resolve()
        try:
            candidate.relative_to(ROOT.resolve())
        except ValueError:
            return None
        return candidate.read_text(encoding="utf-8") if candidate.is_file() else None


def rpc(server: cm.MCPServer, method: str, params: dict | None = None, ident: int = 1):
    status, payload = server.handle(
        {"jsonrpc": "2.0", "id": ident, "method": method, "params": params or {}}
    )
    return status, payload


class CrossHarnessCapabilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
        cls.gateway = cm.CommonsGateway(truth=RepoTruth(), timeout=0)
        cls.server = cm.MCPServer(cls.gateway)

    def test_every_named_harness_has_preferred_fallback_and_call_first(self) -> None:
        self.assertEqual(self.catalog["shared"]["authentication"], "none")
        invariant = self.catalog["open_door_invariant"].lower()
        self.assertIn("must not be reported", invariant)
        self.assertIn("no auth", invariant)
        rows = self.catalog["harnesses"]
        self.assertEqual({row["id"] for row in rows}, EXPECTED_HARNESSES)
        roads = set(self.catalog["roads"])
        for row in rows:
            self.assertIn(row["preferred_road"], roads, row["id"])
            self.assertIn(row["fallback_road"], roads, row["id"])
            self.assertEqual(row["call_order"][0], "discover_commons_capabilities", row["id"])
        self.assertNotEqual(
            next(row for row in rows if row["id"] == "grok-com")["surface"],
            next(row for row in rows if row["id"] == "grokbot")["surface"],
        )

    def test_project_configs_offer_public_commons_and_titan_hands(self) -> None:
        configs = {
            ".mcp.json": "url",
            ".cursor/mcp.json": "url",
            ".gemini/settings.json": "httpUrl",
        }
        for rel, url_key in configs.items():
            payload = json.loads((ROOT / rel).read_text(encoding="utf-8"))
            servers = payload["mcpServers"]
            self.assertEqual(servers["commons"][url_key], mcp.PUBLIC_MCP_URL, rel)
            self.assertIn("titan_hands", servers, rel)
            self.assertNotIn("headers", servers["commons"], rel)
            self.assertNotIn("env", servers["commons"], rel)
        gemini = json.loads((ROOT / ".gemini/settings.json").read_text(encoding="utf-8"))
        self.assertTrue(gemini["mcpServers"]["commons"]["trust"])

    def test_tools_and_call_first_instructions_are_client_neutral(self) -> None:
        wanted = {"discover_commons_capabilities", "search_commons", "read_commons_resource"}
        tool_sets = set()
        for name in CLIENT_NAMES:
            status, init = rpc(
                self.server,
                "initialize",
                {
                    "protocolVersion": "2025-03-26",
                    "capabilities": {},
                    "clientInfo": {"name": name, "version": "1"},
                },
            )
            self.assertEqual(status, 200, name)
            self.assertIn("discover_commons_capabilities", init["result"]["instructions"], name)
            status, listed = rpc(self.server, "tools/list")
            self.assertEqual(status, 200, name)
            names = frozenset(row["name"] for row in listed["result"]["tools"])
            self.assertTrue(wanted <= names, name)
            tool_sets.add(names)
        self.assertEqual(len(tool_sets), 1)

    def test_discovery_search_and_read_use_exact_git_truth(self) -> None:
        discovered = self.gateway.discover_commons_capabilities({"harness": "grok.com"})
        self.assertEqual(discovered["git_sha"], "a" * 40)
        self.assertEqual([row["id"] for row in discovered["harnesses"]], ["grok-com"])

        searched = self.gateway.search_commons({"query": "BERNAYS", "limit": 2})
        self.assertLessEqual(len(searched["results"]), 2)
        self.assertEqual(searched["git_sha"], "a" * 40)

        read = self.gateway.read_commons_resource({"path": "harnesses/catalog.json"})
        expected = CATALOG_PATH.read_text(encoding="utf-8")
        self.assertEqual(read["body_sha256"], hashlib.sha256(expected.encode("utf-8")).hexdigest())
        with self.assertRaises(cm.CommonsError):
            self.gateway.read_commons_resource({"path": "../private.txt"})

    def test_http_aliases_serve_the_same_catalog(self) -> None:
        httpd = cm.ThreadingHTTPServer(("127.0.0.1", 0), mcp.handler)
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        connection = http.client.HTTPConnection("127.0.0.1", httpd.server_port, timeout=5)
        try:
            for path in ("/capabilities", "/harnesses", "/.well-known/commons-capabilities.json"):
                connection.request("GET", path)
                response = connection.getresponse()
                payload = json.loads(response.read().decode("utf-8"))
                self.assertEqual(response.status, 200, path)
                self.assertEqual(payload["schema"], self.catalog["schema"], path)
                self.assertEqual({row["id"] for row in payload["harnesses"]}, EXPECTED_HARNESSES, path)
        finally:
            connection.close()
            httpd.shutdown()
            httpd.server_close()

    def test_html_buttons_and_production_rewrites_are_present(self) -> None:
        page = (ROOT / "capabilities.html").read_text(encoding="utf-8")
        self.assertIn('id="copy-mcp"', page)
        self.assertIn("data-copy", page)
        self.assertIn("discover_commons_capabilities", page)
        rewrites = json.loads((ROOT / "vercel.json").read_text(encoding="utf-8"))["rewrites"]
        routes = {row["source"]: row["destination"] for row in rewrites}
        for path in ("/capabilities", "/harnesses", "/carriers", "/carriers/:path*", "/.well-known/commons-capabilities.json"):
            self.assertEqual(routes[path], "/api/mcp", path)


if __name__ == "__main__":
    unittest.main()
