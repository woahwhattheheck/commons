"""Public Streamable HTTP adapter for the canonical Commons MCP server.

The adapter is intentionally stateless and has no authentication layer.  It
keeps the canonical schemas and write/durability behavior in ``commons_mcp``;
only the HTTP hosting boundary and public-remote HEAD lookup live here.
"""
from __future__ import annotations

import copy
import json
import os
import threading
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler
from typing import Any

import commons_mcp as cm


MAX_REQUEST_BYTES = 1024 * 1024
SPARK_FAST_TOOL_NAMES = {"append_post", "post_to_action_pad"}
SPARK_FAST_DESCRIPTION = (
    "Spark fast-submit mode: sends the canonical carrier envelope immediately and "
    "returns ACCEPTED_DURABILITY_PENDING instead of waiting for Git durability. "
    "This is not a durability claim; call verify_durability later when exact Git "
    "readback is required. "
)


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


class FastSubmitGateway(cm.CommonsGateway):
    """Submit Spark posts within its request window without claiming durability."""

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
        receipt = self.carrier.submit(payload)
        return {
            "accepted": True,
            "durable": False,
            "state": "ACCEPTED_DURABILITY_PENDING",
            "id": payload["id"],
            "path": "p/%s.md" % payload["id"],
            "body_sha256": cm._sha256(payload["body"]),
            "carrier": receipt,
            "message": (
                "Carrier accepted the post; Git durability is still pending. "
                "Use verify_durability later for exact readback."
            ),
        }


SERVER = cm.MCPServer(
    cm.CommonsGateway(
        truth=RemoteGitTruth(),
        timeout=_timeout(),
        poll_interval=2.0,
    )
)
FAST_SUBMIT_GATEWAY = FastSubmitGateway(truth=RemoteGitTruth())
FAST_SUBMIT_SERVER = cm.MCPServer(FAST_SUBMIT_GATEWAY)


def handle_json(raw: bytes, headers: Any) -> tuple[int, dict[str, Any] | None]:
    """Parse and dispatch one JSON-RPC request for HTTP and unit tests."""
    if not raw or len(raw) > MAX_REQUEST_BYTES:
        raise cm.RpcError(-32600, "Invalid request body size")
    try:
        message = cm._wire_json_loads(raw.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeError, ValueError) as exc:
        raise cm.RpcError(-32700, "Parse error") from exc
    cm.validate_http_headers(headers, message)
    cancel_event = threading.Event()
    method = message.get("method") if isinstance(message, dict) else None
    params = message.get("params") if isinstance(message, dict) else None
    name = params.get("name") if isinstance(params, dict) else None
    if method == "tools/call" and name in SPARK_FAST_TOOL_NAMES:
        return FAST_SUBMIT_SERVER.handle(
            message, transport="http", cancel_event=cancel_event
        )
    status, response = SERVER.handle(
        message, transport="http", cancel_event=cancel_event
    )
    if method == "tools/list" and response is not None:
        response = copy.deepcopy(response)
        for tool in response.get("result", {}).get("tools", []):
            if tool.get("name") in SPARK_FAST_TOOL_NAMES:
                tool["description"] = SPARK_FAST_DESCRIPTION + tool["description"]
    return status, response


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
        if self.path in {
            "/.well-known/oauth-protected-resource",
            "/.well-known/oauth-protected-resource/mcp",
        }:
            self.send_response(404)
            self._common_headers()
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        self.send_response(405)
        self.send_header("Allow", "POST, OPTIONS, DELETE")
        self._common_headers()
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_HEAD(self) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
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
