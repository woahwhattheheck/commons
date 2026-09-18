#!/usr/bin/env python3
"""Focused contracts for the Commons MCP conformance product."""
from __future__ import annotations

import hashlib
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import threading
import unittest

from host import mcp_conformance


class _Handler(BaseHTTPRequestHandler):
    calls: list[dict] = []

    def log_message(self, _format, *_args):
        pass

    def _send_json(self, value, *, status=200, session=True):
        body = json.dumps(value, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        if session:
            self.send_header("MCP-Session-Id", "fixture-session")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        length = int(self.headers.get("Content-Length") or 0)
        payload = json.loads(self.rfile.read(length).decode("utf-8"))
        type(self).calls.append(payload)
        method = payload["method"]
        if method == "notifications/initialized":
            self.send_response(202)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        request_id = payload["id"]
        if method == "initialize":
            self._send_json(
                {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "protocolVersion": mcp_conformance.PROTOCOL_VERSION,
                        "serverInfo": {"name": "fixture", "version": "1"},
                        "capabilities": {"tools": {}, "resources": {}},
                    },
                }
            )
            return
        if method == "tools/list":
            result = {
                "tools": [
                    {"name": name, "inputSchema": {"type": "object"}}
                    for name in mcp_conformance.DEFAULT_REQUIRED_TOOLS
                ] + [{"name": "echo_anything", "inputSchema": {"type": "object"}}]
            }
            event = "event: message\ndata: " + json.dumps(
                {"jsonrpc": "2.0", "id": request_id, "result": result},
                ensure_ascii=False,
            ) + "\n\n"
            body = event.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream; charset=utf-8")
            self.send_header("MCP-Session-Id", "fixture-session")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if method == "resources/list":
            self._send_json(
                {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {"resources": [{"name": "carrier catalog", "uri": "commons://carriers"}]},
                }
            )
            return
        if method == "prompts/list":
            self._send_json(
                {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {"code": -32601, "message": "not implemented"},
                }
            )
            return
        if method == "tools/call":
            self._send_json(
                {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": json.dumps(payload["params"], ensure_ascii=False, sort_keys=True),
                            }
                        ],
                        "isError": False,
                    },
                }
            )
            return
        self._send_json(
            {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": -32601, "message": "unknown method"},
            }
        )


class FixtureServer:
    def __enter__(self):
        _Handler.calls = []
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        host, port = self.server.server_address
        self.url = "http://%s:%d/mcp?private_token=never-print" % (host, port)
        return self

    def __exit__(self, *_args):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)


class MCPConformanceTests(unittest.TestCase):
    def test_discovery_records_sse_transport_and_full_commons_tool_parity(self):
        with FixtureServer() as fixture:
            report = mcp_conformance.run_conformance(fixture.url)

        self.assertEqual(report["status"], "PARTIAL")
        self.assertEqual(report["endpoint"], fixture.url.split("?", 1)[0])
        self.assertNotIn("never-print", json.dumps(report))
        self.assertEqual(report["server_info"], {"name": "fixture", "version": "1"})
        self.assertTrue(report["tool_parity"]["complete"])
        self.assertEqual(report["tool_parity"]["missing"], [])
        self.assertEqual(report["discovery"]["tools/list"]["content_type"], "text/event-stream")
        self.assertEqual(report["discovery"]["prompts/list"]["state"], "UNSUPPORTED")
        self.assertEqual(report["resource_names"], ["carrier catalog"])
        self.assertEqual(
            [row["method"] for row in _Handler.calls[:3]],
            ["initialize", "notifications/initialized", "tools/list"],
        )

    def test_explicit_arbitrary_tool_call_hashes_opaque_unicode_result(self):
        arguments = {
            "model_packet": {
                "label": "scratchpad",
                "body": "prefix\u000b\u000c\u001c\u001d\u001e\u0085\u2028\u2029suffix",
            }
        }
        with FixtureServer() as fixture:
            report = mcp_conformance.run_conformance(
                fixture.url,
                required_tools=("append_model_post", "echo_anything"),
                call_tool="echo_anything",
                call_arguments=arguments,
            )

        self.assertEqual(report["status"], "PARTIAL")
        self.assertEqual(report["tool_call"]["state"], "RETURNED")
        self.assertEqual(report["tool_call"]["name"], "echo_anything")
        self.assertNotIn("result", report["tool_call"])
        self.assertRegex(report["tool_call"]["request_sha256"], r"^[0-9a-f]{64}$")
        self.assertRegex(report["tool_call"]["result_sha256"], r"^[0-9a-f]{64}$")
        sent = [row for row in _Handler.calls if row["method"] == "tools/call"][0]
        self.assertEqual(sent["params"]["arguments"], arguments)

    def test_call_result_can_be_included_only_by_explicit_option(self):
        with FixtureServer() as fixture:
            report = mcp_conformance.run_conformance(
                fixture.url,
                required_tools=(),
                call_tool="echo_anything",
                call_arguments={"open": True},
                include_call_result=True,
            )
        self.assertIn("result", report["tool_call"])
        self.assertFalse(report["tool_call"]["result"]["isError"])

    def test_missing_required_tool_is_partial_not_transport_failure(self):
        with FixtureServer() as fixture:
            report = mcp_conformance.run_conformance(
                fixture.url,
                required_tools=("does_not_exist",),
            )
        self.assertEqual(report["status"], "PARTIAL")
        self.assertEqual(report["tool_parity"]["missing"], ["does_not_exist"])
        self.assertFalse(report["tool_parity"]["complete"])

    def test_unreachable_endpoint_returns_shareable_failure_receipt(self):
        report = mcp_conformance.run_conformance(
            "http://127.0.0.1:1/mcp?password=do-not-print",
            timeout=0.2,
        )
        self.assertEqual(report["status"], "FAIL")
        self.assertEqual(report["endpoint"], "http://127.0.0.1:1/mcp")
        self.assertNotIn("do-not-print", json.dumps(report))
        self.assertEqual(report["errors"][0]["code"], "TRANSPORT_ERROR")

    def test_receipt_hash_covers_every_unsigned_byte(self):
        with FixtureServer() as fixture:
            report = mcp_conformance.run_conformance(fixture.url)
        expected = report.pop("receipt_sha256")
        self.assertEqual(
            expected,
            hashlib.sha256(mcp_conformance.canonical_json(report).encode("utf-8")).hexdigest(),
        )


if __name__ == "__main__":
    unittest.main()
