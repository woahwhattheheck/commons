#!/usr/bin/env python3
"""Custody regressions for MCP Conformance transport receipt metadata."""
from __future__ import annotations

import hashlib
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import threading
import unittest

from host import mcp_conformance


ROOT = Path(__file__).resolve().parent
ACCEPTANCE = (
    "successful response transport rows record exact byte length and SHA-256; "
    "failure rows preserve only response hash metadata the runner actually emits"
)


class _ResponseServer:
    def __init__(self, *, status: int, body: bytes, content_type: str = "application/json"):
        self.status = status
        self.body = body
        self.content_type = content_type

    def __enter__(self):
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, _format, *_args):
                pass

            def do_POST(self):
                length = int(self.headers.get("Content-Length") or 0)
                self.rfile.read(length)
                self.send_response(outer.status)
                self.send_header("Content-Type", outer.content_type)
                self.send_header("Content-Length", str(len(outer.body)))
                self.end_headers()
                self.wfile.write(outer.body)

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        host, port = self.server.server_address
        self.url = "http://%s:%d/mcp" % (host, port)
        return self

    def __exit__(self, *_args):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)


class MCPConformanceTransportReceiptTests(unittest.TestCase):
    def test_product_and_contract_bind_transport_acceptance_wording(self):
        product = json.loads((ROOT / "revenue" / "mcp_conformance" / "product.json").read_text(encoding="utf-8"))
        contract = json.loads((ROOT / "revenue" / "mcp_conformance" / "contract.json").read_text(encoding="utf-8"))
        self.assertIn(ACCEPTANCE, product["acceptance"])
        self.assertIn(ACCEPTANCE, contract["acceptance"])

    def test_success_transport_records_exact_response_bytes_and_sha256(self):
        body = b'{"jsonrpc":"2.0","id":1,"result":{"ok":true}}'
        with _ResponseServer(status=200, body=body) as fixture:
            client = mcp_conformance.MCPClient(fixture.url, timeout=2.0)
            response, transport = client._request({"jsonrpc": "2.0", "id": 1, "method": "probe"})

        self.assertEqual(response["result"], {"ok": True})
        self.assertEqual(transport["response_bytes"], len(body))
        self.assertEqual(transport["response_sha256"], hashlib.sha256(body).hexdigest())

    def test_http_error_hashes_body_without_inventing_response_bytes(self):
        body = b'{"error":"not-authorized"}'
        with _ResponseServer(status=403, body=body) as fixture:
            client = mcp_conformance.MCPClient(fixture.url, timeout=2.0)
            with self.assertRaises(mcp_conformance.ConformanceError) as caught:
                client._request({"jsonrpc": "2.0", "id": 1, "method": "probe"})

        self.assertEqual(caught.exception.code, "HTTP_ERROR")
        self.assertEqual(caught.exception.details["http_status"], 403)
        self.assertEqual(caught.exception.details["response_sha256"], hashlib.sha256(body).hexdigest())
        self.assertNotIn("response_bytes", caught.exception.details)

    def test_invalid_json_hashes_body_without_inventing_response_bytes(self):
        body = b"definitely-not-json"
        with _ResponseServer(status=200, body=body) as fixture:
            client = mcp_conformance.MCPClient(fixture.url, timeout=2.0)
            with self.assertRaises(mcp_conformance.ConformanceError) as caught:
                client._request({"jsonrpc": "2.0", "id": 1, "method": "probe"})

        self.assertEqual(caught.exception.code, "INVALID_JSON")
        self.assertEqual(caught.exception.details["response_sha256"], hashlib.sha256(body).hexdigest())
        self.assertNotIn("response_bytes", caught.exception.details)


if __name__ == "__main__":
    unittest.main()
