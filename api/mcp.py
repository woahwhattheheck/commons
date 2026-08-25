"""Public Streamable HTTP adapter for the canonical Commons MCP server.

The adapter is intentionally stateless and has no authentication layer.  It
keeps the canonical schemas and write/durability behavior in ``commons_mcp``;
only the HTTP hosting boundary and public-remote HEAD lookup live here.
"""
from __future__ import annotations

import json
import os
import threading
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler
from typing import Any

import commons_mcp as cm


MAX_REQUEST_BYTES = 1024 * 1024


class RemoteGitTruth(cm.GitTruth):
    """Resolve current Commons HEAD through GitHub's public HTTPS API."""

    def head_sha(self) -> str:
        request = urllib.request.Request(
            cm.GITHUB_API + "/git/ref/heads/main",
            headers={
                "Accept": "application/vnd.github+json",
                "User-Agent": "commons-spark-mcp/%s" % cm.SERVER_VERSION,
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (
            urllib.error.HTTPError,
            urllib.error.URLError,
            TimeoutError,
            OSError,
            UnicodeError,
            json.JSONDecodeError,
        ) as exc:
            raise cm.CommonsError(
                "TRUTH_UNAVAILABLE",
                "could not resolve Commons git HEAD over HTTPS",
                state="UNVERIFIED",
            ) from exc
        sha = str((payload.get("object") or {}).get("sha") or "").lower()
        if not cm.SHA_RE.fullmatch(sha):
            raise cm.CommonsError(
                "TRUTH_UNAVAILABLE",
                "Commons HEAD response was not a commit SHA",
                state="UNVERIFIED",
            )
        return sha


def _timeout() -> float:
    try:
        value = float(os.environ.get("COMMONS_MCP_TIMEOUT", "270"))
    except ValueError:
        value = 270.0
    return min(270.0, max(0.0, value))


SERVER = cm.MCPServer(
    cm.CommonsGateway(
        truth=RemoteGitTruth(),
        timeout=_timeout(),
        poll_interval=2.0,
    )
)


def handle_json(raw: bytes, headers: Any) -> tuple[int, dict[str, Any] | None]:
    """Parse and dispatch one JSON-RPC request for HTTP and unit tests."""
    if not raw or len(raw) > MAX_REQUEST_BYTES:
        raise cm.RpcError(-32600, "Invalid request body size")
    try:
        message = cm._wire_json_loads(raw.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeError, ValueError) as exc:
        raise cm.RpcError(-32700, "Parse error") from exc
    cm.validate_http_headers(headers, message)
    return SERVER.handle(message, transport="http", cancel_event=threading.Event())


class handler(BaseHTTPRequestHandler):
    """Vercel Python Function entry point."""

    protocol_version = "HTTP/1.1"

    def log_message(self, fmt: str, *args: Any) -> None:
        return

    def _common_headers(self) -> None:
        self.send_header("Cache-Control", "no-store")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS, DELETE")
        self.send_header(
            "Access-Control-Allow-Headers",
            "Accept, Content-Type, MCP-Protocol-Version, Mcp-Session-Id",
        )
        self.send_header(
            "Access-Control-Expose-Headers",
            "MCP-Protocol-Version, Mcp-Session-Id",
        )
        self.send_header("MCP-Protocol-Version", cm.PROTOCOL_VERSION)

    def _send_json(self, status: int, value: dict[str, Any] | None) -> None:
        body = b"" if value is None else json.dumps(
            value, ensure_ascii=True, allow_nan=False
        ).encode("utf-8")
        self.send_response(status)
        if body:
            self.send_header("Content-Type", "application/json")
        self._common_headers()
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if body:
            self.wfile.write(body)

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self._common_headers()
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self) -> None:
        self.send_response(405)
        self.send_header("Allow", "POST, OPTIONS, DELETE")
        self._common_headers()
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_DELETE(self) -> None:
        # The canonical server is stateless and does not mint session ids.
        self.send_response(204)
        self._common_headers()
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_POST(self) -> None:
        request_id: Any = None
        try:
            values = self.headers.get_all("Content-Length") or []
            if len(values) != 1 or self.headers.get_all("Transfer-Encoding"):
                raise cm.RpcError(
                    -32600,
                    "Content-Length must appear exactly once and Transfer-Encoding is unsupported",
                )
            try:
                length = int(values[0])
            except (TypeError, ValueError) as exc:
                raise cm.RpcError(-32600, "Invalid request body size") from exc
            if length <= 0 or length > MAX_REQUEST_BYTES:
                raise cm.RpcError(-32600, "Invalid request body size")
            raw = self.rfile.read(length)
            try:
                decoded = cm._wire_json_loads(raw.decode("utf-8"))
                if isinstance(decoded, dict):
                    request_id = decoded.get("id")
            except (json.JSONDecodeError, UnicodeError, ValueError):
                pass
            status, response = handle_json(raw, self.headers)
            self._send_json(status, response)
        except cm.RpcError as exc:
            self._send_json(exc.http_status, cm.error_response(request_id, exc))
        except Exception as exc:
            self._send_json(
                500,
                cm.error_response(
                    request_id,
                    cm.RpcError(
                        -32603,
                        "Internal error",
                        data={"type": type(exc).__name__},
                        http_status=500,
                    ),
                ),
            )

