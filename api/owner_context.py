"""Vercel adapter for the owner-context display host.

Already-connected open host: commons-spark-mcp.vercel.app.
Display only. Never a gate. Never authority. Never returns a raw IP.
Does not remint api/mcp.py.
"""
from __future__ import annotations

import sys
from http.server import BaseHTTPRequestHandler
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "host") not in sys.path:
    sys.path.insert(0, str(ROOT / "host"))

import owner_context as oc  # noqa: E402


class handler(BaseHTTPRequestHandler):
    spec = None

    def _dispatch(self, method: str) -> None:
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length) if length > 0 else b""
        remote = str(self.client_address[0]) if self.client_address else ""
        status, headers, blob = oc.handle_http(
            method,
            self.path,
            self.headers,
            body,
            remote,
            spec=self.spec if self.spec is not None else oc.load_spec(str(ROOT)),
            host_name="vercel",
        )
        self.send_response(status)
        for key, value in headers:
            self.send_header(key, value)
        self.send_header("Content-Length", str(len(blob)))
        self.end_headers()
        if method != "HEAD" and blob:
            self.wfile.write(blob)

    def do_GET(self) -> None:
        self._dispatch("GET")

    def do_POST(self) -> None:
        self._dispatch("POST")

    def do_OPTIONS(self) -> None:
        self._dispatch("OPTIONS")

    def do_HEAD(self) -> None:
        self._dispatch("HEAD")

    def do_PUT(self) -> None:
        self._dispatch("PUT")

    def do_DELETE(self) -> None:
        self._dispatch("DELETE")

    def log_message(self, format, *args) -> None:  # noqa: A002
        return

    def log_request(self, code="-", size="-") -> None:
        return
