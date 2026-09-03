"""Standalone WebMCP contest MCP (second server).

Reuses ``commons_mcp`` as starting-point infra so we do not rebuild the
carrier/gateway twice. This is NOT ``api/mcp.py`` and does NOT replace
live ``/mcp`` (commons 1.4.0). Contest surface: ``/webmcp`` + ``/webmcp/mcp``.
"""
from __future__ import annotations

import copy
import json
import os
import threading
import urllib.parse
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from typing import Any

import commons_mcp as cm


MAX_REQUEST_BYTES = 1024 * 1024
PUBLIC_BASE_URL = os.environ.get(
    "COMMONS_SPARK_PUBLIC_BASE", "https://commons-spark-mcp.vercel.app"
).rstrip("/")
PUBLIC_MCP_URL = "%s/webmcp/mcp" % PUBLIC_BASE_URL
SERVER_NAME = "webmcp"
SERVER_VERSION = "1.0.0"
HTML_NAME = "webmcp.html"

# Public tool names for the contest (no commons_* branding).
TOOL_MAP = {
    "discover": "discover_commons_capabilities",
    "search": "search_commons",
    "read": "read_commons_resource",
    "append": "append_post",
    "fire": "fire_action",
    "post_action": "post_to_action_pad",
}

FAST_TOOLS = {"append", "fire", "post_action"}


class RemoteGitTruth(cm.GitTruth):
    def head_sha(self) -> str:
        import urllib.error
        import urllib.request

        request = urllib.request.Request(
            cm.GITHUB_API + "/git/ref/heads/main",
            headers={
                "Accept": "application/vnd.github+json",
                "User-Agent": "webmcp-contest/%s" % SERVER_VERSION,
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except Exception as exc:  # noqa: BLE001 — surface as TRUTH_UNAVAILABLE
            raise cm.CommonsError(
                "TRUTH_UNAVAILABLE",
                "could not resolve git HEAD over HTTPS",
                state="UNVERIFIED",
            ) from exc
        sha = str((payload.get("object") or {}).get("sha") or "").lower()
        if not cm.SHA_RE.fullmatch(sha):
            raise cm.CommonsError(
                "TRUTH_UNAVAILABLE",
                "HEAD response was not a commit SHA",
                state="UNVERIFIED",
            )
        return sha


def _timeout() -> float:
    try:
        value = float(os.environ.get("COMMONS_MCP_TIMEOUT", "270"))
    except ValueError:
        value = 270.0
    return min(270.0, max(0.0, value))


class FastSubmitGateway(cm.CommonsGateway):
    def _submit(
        self,
        payload: dict[str, Any],
        *,
        projection_actor: str | None = None,
        cancel_event: threading.Event | None = None,
    ) -> dict[str, Any]:
        del projection_actor
        if cancel_event is not None and cancel_event.is_set():
            raise cm.CommonsError(
                "CANCELLED", "request cancelled before carrier submission", state="NOT_SENT"
            )
        validate = getattr(self.carrier, "validate", None)
        if callable(validate):
            validate(payload)
        receipt = self.carrier.submit(payload)
        return {
            "ok": True,
            "accepted": True,
            "durable": False,
            "state": "ACCEPTED_DURABILITY_PENDING",
            "id": payload["id"],
            "path": "p/%s.md" % payload["id"],
            "body_sha256": cm._sha256(payload["body"]),
            "carrier": receipt,
            "message": (
                "Carrier accepted; durability pending. Verify later for exact readback."
            ),
        }

    def _await_action_result(
        self,
        ident: str,
        durable: dict[str, Any],
        *,
        cancel_event: threading.Event | None = None,
    ) -> dict[str, Any]:
        del cancel_event
        return {
            **durable,
            "ok": True,
            "accepted": True,
            "id": ident,
            "action_result_pending": True,
            "verify_tool": "verify_durability",
            "message": (
                "Action envelope accepted; durable page and executor result pending."
            ),
        }


GATEWAY = cm.CommonsGateway(truth=RemoteGitTruth(), timeout=_timeout(), poll_interval=2.0)
SERVER = cm.MCPServer(GATEWAY)
FAST_GATEWAY = FastSubmitGateway(truth=RemoteGitTruth())
FAST_SERVER = cm.MCPServer(FAST_GATEWAY)


def _tool_defs() -> list[dict[str, Any]]:
    by_name = {tool["name"]: tool for tool in cm.TOOL_DEFINITIONS}
    out: list[dict[str, Any]] = []
    for public, internal in TOOL_MAP.items():
        base = copy.deepcopy(by_name[internal])
        base["name"] = public
        # Strip commons-specific title noise for contest packet.
        title = str(base.get("title") or public).replace("Commons ", "").replace("commons ", "")
        base["title"] = title
        desc = str(base.get("description") or "")
        desc = desc.replace("Commons ", "").replace("commons ", "")
        base["description"] = desc
        out.append(base)
    return out


PUBLIC_TOOLS = _tool_defs()


def capability_map() -> dict[str, Any]:
    return {
        "name": SERVER_NAME,
        "version": SERVER_VERSION,
        "protocol": cm.PROTOCOL_VERSION,
        "transport": "streamable-http",
        "auth": "none",
        "url": PUBLIC_MCP_URL,
        "tools": [t["name"] for t in PUBLIC_TOOLS],
        "toolCount": len(PUBLIC_TOOLS),
        "instructions": (
            "Standalone WebMCP contest MCP. GET returns this map. "
            "POST JSON-RPC initialize, then tools/list or tools/call. No login."
        ),
    }


def handle_json(raw: bytes, headers: Any) -> tuple[int, dict[str, Any] | None]:
    if not raw or len(raw) > MAX_REQUEST_BYTES:
        raise cm.RpcError(-32600, "Invalid request body size")
    try:
        message = cm._wire_json_loads(raw.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeError, ValueError) as visc:
        raise cm.RpcError(-32700, "Parse error") from visc
    cm.validate_http_headers(headers, message)
    if not isinstance(message, dict):
        raise cm.RpcError(-32600, "Invalid request")

    method = message.get("method")
    params = message.get("params") if isinstance(message.get("params"), dict) else {}
    cancel_event = threading.Event()

    if method == "initialize":
        result = {
            "protocolVersion": cm.PROTOCOL_VERSION,
            "capabilities": {"tools": {}},
            "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
            "instructions": capability_map()["instructions"],
        }
        return 200, {"jsonrpc": "2.0", "id": message.get("id"), "result": result}

    if method == "notifications/initialized":
        return 202, None

    if method == "tools/list":
        return 200, {
            "jsonrpc": "2.0",
            "id": message.get("id"),
            "result": {"tools": PUBLIC_TOOLS},
        }

    if method == "tools/call":
        public = params.get("name")
        internal = TOOL_MAP.get(public) if isinstance(public, str) else None
        if not internal:
            raise cm.RpcError(-32601, "Unknown tool")
        forwarded = copy.deepcopy(message)
        forwarded["params"] = {
            "name": internal,
            "arguments": params.get("arguments") or {},
        }
        server = FAST_SERVER if public in FAST_TOOLS else SERVER
        return server.handle(forwarded, transport="http", cancel_event=cancel_event)

    # Fall through to canonical server for anything else (ping, resources, …)
    return SERVER.handle(message, transport="http", cancel_event=cancel_event)


class handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt: str, *args: Any) -> None:
        return

    def _common_headers(self) -> None:
        self.send_header("Cache-Control", "no-store")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, HEAD, POST, OPTIONS, DELETE")
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

    def _send_html(self, status: int, body: bytes) -> None:
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; "
            "connect-src 'self'; base-uri 'none'; frame-ancestors 'none'",
        )
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if body:
            self.wfile.write(body)

    def _read_body(self) -> bytes:
        values = self.headers.get_all("Content-Length") or []
        if len(values) != 1 or self.headers.get_all("Transfer-Encoding"):
            raise cm.RpcError(
                -32600,
                "Content-Length must appear exactly once and Transfer-Encoding is unsupported",
            )
        try:
            length = int(values[0])
        except (TypeError, ValueError) as visc:
            raise cm.RpcError(-32600, "Invalid request body size") from visc
        if length <= 0 or length > MAX_REQUEST_BYTES:
            raise cm.RpcError(-32600, "Invalid request body size")
        return self.rfile.read(length)

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self._common_headers()
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self) -> None:
        path = urllib.parse.urlsplit(self.path).path
        if path in {"/webmcp", "/webmcp.html", "/"}:
            html_path = Path(__file__).resolve().parent.parent / HTML_NAME
            try:
                body = html_path.read_bytes()
            except OSError:
                self.send_response(404)
                self._common_headers()
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
            self._send_html(200, body)
            return
        if path in {"/webmcp/mcp", "/mcp"}:
            self._send_json(200, capability_map())
            return
        self.send_response(404)
        self._common_headers()
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_HEAD(self) -> None:
        path = urllib.parse.urlsplit(self.path).path
        if path in {"/webmcp", "/webmcp.html"}:
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
        else:
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
        self._common_headers()
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_DELETE(self) -> None:
        self.send_response(204)
        self._common_headers()
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_POST(self) -> None:
        request_id: Any = None
        try:
            raw = self._read_body()
            try:
                decoded = cm._wire_json_loads(raw.decode("utf-8"))
                if isinstance(decoded, dict):
                    request_id = decoded.get("id")
            except (json.JSONDecodeError, UnicodeError, ValueError):
                pass
            status, response = handle_json(raw, self.headers)
            self._send_json(status, response)
        except cm.RpcError as visc:
            self._send_json(visc.http_status, cm.error_response(request_id, visc))
        except cm.CommonsError as visc:
            self._send_json(400, visc.payload())
        except Exception as visc:  # noqa: BLE001
            self._send_json(
                500,
                cm.error_response(
                    request_id,
                    cm.RpcError(
                        -32603,
                        "Internal error",
                        data={"type": type(visc).__name__},
                        http_status=500,
                    ),
                ),
            )
