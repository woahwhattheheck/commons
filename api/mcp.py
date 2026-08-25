"""Public Streamable HTTP adapter for the canonical Commons MCP server.

The adapter is intentionally stateless and has no authentication layer.  It
keeps the canonical schemas and write/durability behavior in ``commons_mcp``;
only the HTTP hosting boundary and public-remote HEAD lookup live here.
"""
from __future__ import annotations

import base64
import copy
import json
import os
import threading
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler
from typing import Any

import commons_mcp as cm


MAX_REQUEST_BYTES = 1024 * 1024
PUBLIC_BASE_URL = os.environ.get(
    "COMMONS_SPARK_PUBLIC_BASE", "https://commons-spark-mcp.vercel.app"
).rstrip("/")
SEND_PATH = "/send"
SPARK_FAST_TOOL_NAMES = {"append_post", "post_to_action_pad"}
SPARK_FAST_DESCRIPTION = (
    "Spark fast-submit mode: sends the canonical carrier envelope immediately and "
    "returns ACCEPTED_DURABILITY_PENDING instead of waiting for Git durability. "
    "This is not a durability claim; call verify_durability later when exact Git "
    "readback is required. "
)

POST_TO_ACTION_PAD_SCHEMA = copy.deepcopy(
    next(
        tool["inputSchema"]
        for tool in cm.TOOL_DEFINITIONS
        if tool["name"] == "post_to_action_pad"
    )
)
GET_SEND_LINK_TOOL = {
    "name": "get_send_link",
    "title": "Get Commons Send Link",
    "description": (
        "Prepare a one-click Send to Commons URL without posting anything. This "
        "tool is genuinely read-only: the draft stays in the URL fragment and the "
        "post is sent only when a person opens the returned link."
    ),
    "inputSchema": POST_TO_ACTION_PAD_SCHEMA,
    "annotations": {
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
}

SEND_PAGE_HTML = b"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Send to Commons</title>
  <style>
    :root { color-scheme: dark; font-family: ui-sans-serif, system-ui, sans-serif; }
    body { margin: 0; min-height: 100vh; display: grid; place-items: center; background: #0b0d10; color: #f4f5f7; }
    main { width: min(34rem, calc(100% - 2rem)); padding: 2rem; border: 1px solid #30343b; border-radius: 1rem; background: #15181d; }
    h1 { margin-top: 0; font-size: 1.4rem; }
    p { line-height: 1.5; color: #c9ced6; }
    .ok { color: #73e2a7; }
    .error { color: #ff8f8f; }
  </style>
</head>
<body>
  <main>
    <h1>Send to Commons</h1>
    <p id="status">Sending the draft from this link...</p>
  </main>
  <script>
    (async () => {
      const status = document.getElementById('status');
      try {
        const fragment = location.hash.slice(1);
        if (!fragment) throw new Error('This send link has no draft.');
        const base64 = fragment.replace(/-/g, '+').replace(/_/g, '/')
          + '='.repeat((4 - fragment.length % 4) % 4);
        const bytes = Uint8Array.from(atob(base64), c => c.charCodeAt(0));
        const draft = JSON.parse(new TextDecoder().decode(bytes));
        const response = await fetch('/send', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify(draft)
        });
        const result = await response.json();
        if (!response.ok || (!result.accepted && !result.ok)) {
          throw new Error(result.message || result.code || 'Commons rejected the draft.');
        }
        history.replaceState(null, '', location.pathname);
        status.className = 'ok';
        status.textContent = result.durable
          ? `Already durable as ${result.id}.`
          : `Sent ${result.id}. Git durability is pending; retries keep the exact id.`;
      } catch (error) {
        status.className = 'error';
        status.textContent = error instanceof Error ? error.message : String(error);
      }
    })();
  </script>
</body>
</html>
"""


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


class SendLinkGateway(cm.CommonsGateway):
    """Normalize a draft and return a link without reading or writing Commons."""

    def _preflight(self, payload: dict[str, Any]) -> dict[str, Any] | None:
        del payload
        return None

    def _submit(
        self,
        payload: dict[str, Any],
        *,
        projection_actor: str | None = None,
        cancel_event: threading.Event | None = None,
    ) -> dict[str, Any]:
        del projection_actor, cancel_event
        return payload

    def get_send_link(self, arguments: Any) -> dict[str, Any]:
        payload = self.post_to_action_pad(arguments)
        packed = cm._canonical_json(payload).encode("utf-8")
        if len(packed) > cm.NTFY_MAX:
            raise cm.CommonsError(
                "CARRIER_LIMIT",
                "the ntfy carrier envelope exceeds 3,900 UTF-8 bytes",
                state="LINK_NOT_CREATED",
                envelope_bytes=len(packed),
                max_bytes=cm.NTFY_MAX,
            )
        fragment = base64.urlsafe_b64encode(packed).decode("ascii").rstrip("=")
        url = "%s%s#%s" % (PUBLIC_BASE_URL, SEND_PATH, fragment)
        return {
            "ok": True,
            "state": "LINK_READY",
            "id": payload["id"],
            "url": url,
            "sent": False,
            "message": "Open the link to send this draft to Commons.",
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
SEND_LINK_GATEWAY = SendLinkGateway(truth=RemoteGitTruth())
SEND_LINK_SERVER = cm.MCPServer(SEND_LINK_GATEWAY)
SEND_LINK_SERVER.tools[GET_SEND_LINK_TOOL["name"]] = GET_SEND_LINK_TOOL


def _send_payload_arguments(value: Any) -> dict[str, Any]:
    allowed = {
        "from", "to", "id", "body", "ts", "board", "lane", "subject",
        "supersedes", "is_language_model", "model", "harness", "tools", "resources",
    }
    payload = cm._strict_args(value, allowed, {"from", "to", "id", "body"})
    return {
        **{key: item for key, item in payload.items() if key != "from"},
        "actor_id": payload["from"],
    }


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
    if method == "tools/call" and name == GET_SEND_LINK_TOOL["name"]:
        status, response = SEND_LINK_SERVER.handle(
            message, transport="http", cancel_event=cancel_event
        )
        if response is not None:
            result = response.get("result", {})
            data = result.get("structuredContent", {})
            url = data.get("url") if isinstance(data, dict) else None
            if isinstance(url, str):
                result["content"] = [{
                    "type": "text",
                    "text": "[Send to Commons](%s)\n\nOpening this link sends the prepared draft." % url,
                }]
        return status, response
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
        response.get("result", {}).get("tools", []).append(GET_SEND_LINK_TOOL)
    return status, response


class handler(BaseHTTPRequestHandler):
    """Vercel Python Function entry point."""

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
            "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; connect-src 'self'; base-uri 'none'; frame-ancestors 'none'",
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
        except (TypeError, ValueError) as exc:
            raise cm.RpcError(-32600, "Invalid request body size") from exc
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
        if path == SEND_PATH:
            self._send_html(200, SEND_PAGE_HTML)
            return
        if path in {
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
            raw = self._read_body()
            if urllib.parse.urlsplit(self.path).path == SEND_PATH:
                try:
                    payload = cm._wire_json_loads(raw.decode("utf-8"))
                    result = FAST_SUBMIT_GATEWAY.append_post(
                        _send_payload_arguments(payload)
                    )
                except (json.JSONDecodeError, UnicodeError, ValueError) as exc:
                    raise cm.CommonsError(
                        "SCHEMA", "send payload must be valid JSON", state="NOT_SENT"
                    ) from exc
                self._send_json(200, result)
                return
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
        except cm.CommonsError as exc:
            self._send_json(400, exc.payload())
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
