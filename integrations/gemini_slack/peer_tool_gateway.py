#!/usr/bin/env python3
"""History-preserving Commons MCP tool loop for the live Gemini peers."""

from __future__ import annotations

import argparse
import base64
import datetime as dt
import hashlib
import http.client
import json
import os
import queue
import re
import sqlite3
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from integrations.shared_equipment.services import CombinedCatalog, redacted
from integrations.shared_equipment.outcomes import effect_uncertain, tool_failed
from integrations.gemini_slack.upstream_turn import UpstreamTurnError, wait_peer_turn
from integrations.gemini_slack.tool_result_boundary import BOUNDARY_VERSION, SOURCE_DATA_RULE, tool_result_prompt


DEFAULT_UPSTREAM = "http://127.0.0.1:8777"
DEFAULT_MCP = "https://commons-spark-mcp.vercel.app/mcp"
DEFAULT_EVENT_LOG = Path.home() / ".gemini" / "commons_peer_tool_gateway_events.jsonl"
DEFAULT_CALL_DB = Path.home() / ".gemini" / "commons_peer_tool_calls.sqlite3"
MCP_PROTOCOL = "2025-03-26"
TERMINAL = frozenset({"completed", "error", "cancelled", "interrupted"})
CALL_OPEN = "<commons_tool_call>"
CALL_CLOSE = "</commons_tool_call>"
CALL_RE = re.compile(r"^\s*<commons_tool_call>(.*?)</commons_tool_call>\s*$", re.DOTALL)

# The only upstream-handle metadata that may ride into an event: anything
# else (from a stale prior event or an UpstreamTurnError's .details) is
# dropped so it cannot collide with reserved event fields like status/message.
UPSTREAM_HANDLE_KEYS = (
    "upstream_request_id",
    "upstream_status_url",
    "upstream_status",
    "upstream_terminal",
    "upstream_error",
)


def _upstream_handle_fields(source: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(source, dict):
        return {}
    return {key: source[key] for key in UPSTREAM_HANDLE_KEYS if key in source}


class GatewayError(RuntimeError):
    def __init__(self, message, *, code="gateway_error", uncertain=False, native_result=None):
        super().__init__(message)
        self.code = code
        self.uncertain = uncertain
        self.native_result = native_result


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


_HTTP = urllib.request.build_opener(_NoRedirect())


def _response_json(response, expected_id=None):
    if "text/event-stream" not in response.headers.get("Content-Type", "").lower():
        return json.loads(response.read().decode("utf-8"))
    # Multi-line SSE frames are source bytes, not one-JSON-object-per-line.
    data_lines = []
    while True:
        raw = response.readline()
        if not raw or not raw.strip():
            if data_lines:
                try:
                    value = json.loads("\n".join(data_lines))
                except ValueError:
                    value = None
                data_lines = []
                if (isinstance(value, dict) and type(value.get("id")) is type(expected_id)
                        and value.get("id") == expected_id):
                    return value
            if not raw:
                raise ValueError("No correlated event-stream response")
        else:
            line = raw.decode("utf-8").rstrip("\r\n")
            if line.startswith("data:"):
                data_lines.append(line[5:].removeprefix(" "))


def _utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")


def _post_json(
    url: str,
    payload: dict[str, Any],
    *,
    headers: dict[str, str] | None = None,
    timeout: float = 120.0,
) -> dict[str, Any]:
    request_headers = {
        "Content-Type": "application/json; charset=utf-8",
        "Accept": "application/json",
    }
    request_headers.update(headers or {})
    request = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8"),
        headers=request_headers,
        method="POST",
    )
    effect = payload.get("jsonrpc") != "2.0" or payload.get("method") == "tools/call"
    try:
        with _HTTP.open(request, timeout=timeout) as response:
            value = _response_json(response, payload.get("id"))
        if not isinstance(value, dict):
            raise ValueError("No result object")
        return value
    except urllib.error.HTTPError as exc:
        status = exc.code
        exc.close()
        raise GatewayError("POST response was HTTP " + str(status), code="post_http_error",
                           uncertain=effect) from None
    except (OSError, ValueError, urllib.error.URLError, http.client.HTTPException):
        raise GatewayError("POST response could not be confirmed", code="post_response_unconfirmed",
                           uncertain=effect) from None


def _get_json(url: str, *, timeout: float = 15.0) -> dict[str, Any]:
    try:
        with _HTTP.open(url, timeout=timeout) as response:
            value = _response_json(response)
        if not isinstance(value, dict):
            raise ValueError("No result object")
        return value
    except urllib.error.HTTPError as exc:
        status = exc.code
        exc.close()
        raise GatewayError("GET response was HTTP " + str(status), code="get_http_error") from None
    except (OSError, ValueError, urllib.error.URLError, http.client.HTTPException):
        raise GatewayError("GET response could not be read", code="get_response_unavailable") from None


class UpstreamClient:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")

    def health(self) -> dict[str, Any]:
        return _get_json(self.base_url + "/health", timeout=10)

    def turn(
        self,
        peer: str,
        message: str,
        *,
        cancelled: Callable[[], bool] | None = None,
        on_submitted: Callable[[dict[str, Any]], None] | None = None,
    ) -> str:
        # Submission is a single async POST that hands back a recoverable
        # upstream handle; the long wait is a poll loop, not a held socket,
        # so a lost local process no longer loses the in-flight operation.
        return wait_peer_turn(
            self.base_url,
            peer,
            message,
            post_json=_post_json,
            get_json=_get_json,
            cancelled=cancelled,
            on_submitted=on_submitted,
        )


class McpCatalog:
    def __init__(self, url: str, *, ttl_seconds: float = 300.0) -> None:
        self.url = url
        self.ttl_seconds = ttl_seconds
        self._tools: list[dict[str, Any]] = []
        self._expires = 0.0
        self._lock = threading.Lock()

    def _rpc(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        identifier = uuid.uuid4().hex
        response = _post_json(
            self.url,
            {"jsonrpc": "2.0", "id": identifier, "method": method, "params": params},
            headers={
                "Accept": "application/json, text/event-stream",
                "MCP-Protocol-Version": MCP_PROTOCOL,
            },
        )
        effect = method == "tools/call"
        if (response.get("jsonrpc") != "2.0" or type(response.get("id")) is not type(identifier)
                or response.get("id") != identifier or ("error" in response) == ("result" in response)):
            raise GatewayError("Commons MCP returned an uncorrelated response",
                               code="mcp_response_invalid", uncertain=effect)
        if "error" in response:
            error = response["error"]
            code = error.get("code") if isinstance(error, dict) else None
            uncertain = effect and (effect_uncertain(error) or effect_uncertain(error.get("data") if isinstance(error, dict) else None) or type(code) is not int
                                    or code not in (-32600, -32601, -32602))
            raise GatewayError("Commons MCP returned a request error", code="mcp_request_error",
                               uncertain=uncertain, native_result=response)
        result = response.get("result")
        if not isinstance(result, dict):
            raise GatewayError("Commons MCP returned no result object",
                               code="mcp_response_invalid", uncertain=effect)
        return result

    def tools(self, *, force: bool = False) -> list[dict[str, Any]]:
        with self._lock:
            if not force and self._tools and time.monotonic() < self._expires:
                return list(self._tools)
            tools = self._rpc("tools/list", {}).get("tools")
            if not isinstance(tools, list) or not tools:
                raise GatewayError("Commons MCP tools/list returned no tools")
            clean = []
            for item in tools:
                if isinstance(item, dict) and isinstance(item.get("name"), str):
                    clean.append(
                        {
                            "name": item["name"],
                            "description": str(item.get("description") or ""),
                            "inputSchema": item.get("inputSchema")
                            if isinstance(item.get("inputSchema"), dict)
                            else {},
                        }
                    )
            if not clean:
                raise GatewayError("Commons MCP tools/list contained no named tools")
            self._tools = clean
            self._expires = time.monotonic() + self.ttl_seconds
            return list(clean)

    def call(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        return self._rpc("tools/call", {"name": name, "arguments": arguments})


class ToolCallStore:
    """Per-request duplicate suppression with honest crash ambiguity."""

    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self._lock = threading.RLock()
        self._db = sqlite3.connect(path, check_same_thread=False)
        self._db.row_factory = sqlite3.Row
        with self._db:
            self._db.execute(
                """
                CREATE TABLE IF NOT EXISTS tool_calls(
                    request_id TEXT NOT NULL,
                    call_id TEXT NOT NULL,
                    tool_name TEXT NOT NULL,
                    arguments_sha256 TEXT NOT NULL,
                    state TEXT NOT NULL CHECK(state IN ('started','completed','error')),
                    result_json TEXT,
                    updated_at REAL NOT NULL,
                    PRIMARY KEY(request_id, call_id)
                )
                """
            )

    def close(self) -> None:
        with self._lock:
            self._db.close()

    def execute_journaled(
        self,
        request_id: str,
        call_id: str,
        name: str,
        arguments: dict[str, Any],
        runner: Callable[[str, dict[str, Any]], dict[str, Any]],
    ) -> dict[str, Any]:
        arg_bytes = json.dumps(
            arguments, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")
        digest = hashlib.sha256(arg_bytes).hexdigest()
        with self._lock, self._db:
            row = self._db.execute(
                "SELECT * FROM tool_calls WHERE request_id=? AND call_id=?",
                (request_id, call_id),
            ).fetchone()
            if row:
                if row["tool_name"] != name or row["arguments_sha256"] != digest:
                    return {"isError": True, "uncertain": False, "error": "call_id_reused_with_different_arguments"}
                if row["result_json"]:
                    previous = json.loads(row["result_json"])
                    if row["state"] == "error" and not tool_failed(previous):
                        previous.setdefault("isError", True)
                    if row["state"] == "started" and not effect_uncertain(previous):
                        previous.update(isError=True, uncertain=True)
                    return previous
                return {
                    "isError": True,
                    "uncertain": True,
                    "error": "tool_effect_unknown_after_interruption",
                    "call_id": call_id,
                    "reconciliation": "inspect Commons before deciding whether to issue a new call",
                }
            self._db.execute(
                "INSERT INTO tool_calls VALUES(?,?,?,?,?,?,?)",
                (request_id, call_id, name, digest, "started", None, time.time()),
            )
        try:
            result = runner(name, arguments)
            if not isinstance(result, dict):
                result = {"result": result}
            state = "started" if effect_uncertain(result) else "error" if tool_failed(result) else "completed"
        except Exception as exc:
            result = {"isError": True, "error": type(exc).__name__, "message": redacted(str(exc)),
                      "code": getattr(exc, "code", type(exc).__name__),
                      "uncertain": bool(getattr(exc, "uncertain", False))}
            if getattr(exc, "native_result", None) is not None:
                result["result"] = exc.native_result
            state = "started" if result["uncertain"] else "error"
        encoded = json.dumps(result, ensure_ascii=False, separators=(",", ":"))
        with self._lock, self._db:
            self._db.execute(
                "UPDATE tool_calls SET state=?, result_json=?, updated_at=? "
                "WHERE request_id=? AND call_id=?",
                (state, encoded, time.time(), request_id, call_id),
            )
        return result


def _tool_prompt(message: str, tools: list[dict[str, Any]]) -> str:
    catalog = json.dumps(tools, ensure_ascii=False, separators=(",", ":"))
    return (
        "You are connected to the full live public Commons MCP and private shared Slack/GitHub equipment through a history-preserving outer tool loop. "
        "You may use any listed tool. When a tool is needed, reply with exactly one envelope and no "
        "surrounding text:\n"
        f"{CALL_OPEN}{{\"call_id\":\"a unique id\",\"name\":\"tool name\",\"arguments\":{{}}}}{CALL_CLOSE}\n"
        "After a result arrives, continue normally or issue another exact envelope. If no tool is needed, "
        "reply normally. Do not invent tool names. Private equipment uses existing service account access; "
        "direct credential retrieval returns ciphertext for an ephemeral key retained by your requesting runtime; "
        "decrypt and use values there, keeping plaintext and private keys out of this captured conversation. "
        "Service responses may have pagination; follow it when needed.\n\nAVAILABLE_COMMONS_TOOLS_JSON:\n"
        + catalog
        + "\n\n"
        + SOURCE_DATA_RULE
        + "\n\nMESSAGE:\n"
        + message
    )


def _parse_call(reply: str) -> tuple[dict[str, Any] | None, bool]:
    marker_present = CALL_OPEN in reply or CALL_CLOSE in reply
    match = CALL_RE.fullmatch(reply)
    if not match:
        return None, marker_present
    try:
        value = json.loads(match.group(1))
    except json.JSONDecodeError:
        return None, True
    if not isinstance(value, dict):
        return None, True
    if not isinstance(value.get("call_id"), str) or not value["call_id"]:
        return None, True
    if not isinstance(value.get("name"), str) or not value["name"]:
        return None, True
    if not isinstance(value.get("arguments"), dict):
        return None, True
    return value, True


class ToolLoop:
    def __init__(
        self,
        upstream: UpstreamClient,
        catalog: McpCatalog,
        calls: ToolCallStore,
        *,
        max_steps: int = 16,
        max_protocol_retries: int = 4,
    ) -> None:
        self.upstream = upstream
        self.catalog = catalog
        self.calls = calls
        self.max_steps = max_steps
        self.max_protocol_retries = max_protocol_retries

    def run(
        self,
        request_id: str,
        peer: str,
        message: str,
        cancelled: threading.Event | None = None,
        on_submitted: Callable[[dict[str, Any]], None] | None = None,
    ) -> str:
        tools = self.catalog.tools()
        names = {item["name"] for item in tools}
        prompt = _tool_prompt(message, tools)
        tool_calls = 0
        protocol_retries = 0
        is_cancelled = cancelled.is_set if cancelled is not None else None
        while True:
            if cancelled is not None and cancelled.is_set():
                raise InterruptedError("request cancelled before next model/tool operation")
            reply = self.upstream.turn(
                peer, prompt, cancelled=is_cancelled, on_submitted=on_submitted
            )
            if cancelled is not None and cancelled.is_set():
                raise InterruptedError("request cancelled after in-flight model turn returned")
            call, had_marker = _parse_call(reply)
            if call is None and not had_marker:
                return reply
            if call is None:
                protocol_retries += 1
                if protocol_retries > self.max_protocol_retries:
                    raise GatewayError(
                        f"peer exceeded {self.max_protocol_retries} malformed tool-envelope retries"
                    )
                prompt = (
                    "That tool envelope was malformed. Emit exactly one valid JSON object between "
                    f"{CALL_OPEN} and {CALL_CLOSE}, or reply normally without either marker."
                )
                continue
            if tool_calls >= self.max_steps:
                raise GatewayError(f"peer exceeded {self.max_steps} Commons tool calls")
            tool_calls += 1
            if call["name"] not in names:
                result = {
                    "error": "unknown_tool",
                    "name": call["name"],
                    "available": sorted(names),
                }
            else:
                result = self.calls.execute_journaled(
                    request_id,
                    call["call_id"],
                    call["name"],
                    call["arguments"],
                    self.catalog.call,
                )
            prompt = tool_result_prompt(call["call_id"], call["name"], result)


class EventStore:
    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self._condition = threading.Condition(threading.RLock())
        self._events: list[dict[str, Any]] = []
        self._latest: dict[str, dict[str, Any]] = {}
        self._next = 1
        if path.exists():
            try:
                for line in path.read_text(encoding="utf-8").splitlines():
                    value = json.loads(line)
                    if isinstance(value, dict) and isinstance(value.get("event_id"), int):
                        self._remember(value)
            except (OSError, ValueError):
                pass

    def _remember(self, event: dict[str, Any]) -> None:
        self._events.append(event)
        self._events = self._events[-5000:]
        if event.get("request_id"):
            self._latest[str(event["request_id"])] = event
        self._next = max(self._next, int(event["event_id"]) + 1)

    def append(self, **fields: Any) -> dict[str, Any]:
        with self._condition:
            event = {"event_id": self._next, "ts": _utc_now(), **fields}
            with self.path.open("a", encoding="utf-8", newline="\n") as handle:
                handle.write(json.dumps(event, ensure_ascii=False, separators=(",", ":")) + "\n")
                handle.flush()
                os.fsync(handle.fileno())
            self._remember(event)
            self._condition.notify_all()
            return event

    def request(self, request_id: str, wait_ms: int) -> dict[str, Any] | None:
        deadline = time.monotonic() + wait_ms / 1000
        with self._condition:
            while True:
                event = self._latest.get(request_id)
                if event and (event.get("status") in TERMINAL or wait_ms <= 0):
                    return event
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return event
                self._condition.wait(remaining)

    def after(
        self,
        cursor: int,
        peer: str | None,
        limit: int,
        wait_ms: int,
    ) -> list[dict[str, Any]]:
        deadline = time.monotonic() + wait_ms / 1000
        with self._condition:
            while True:
                found = [
                    event
                    for event in self._events
                    if int(event["event_id"]) > cursor
                    and (peer is None or event.get("peer") == peer)
                ]
                if found or wait_ms <= 0:
                    return found[:limit]
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return []
                self._condition.wait(remaining)

    def last(self, peer: str) -> dict[str, Any] | None:
        with self._condition:
            for event in reversed(self._events):
                if event.get("peer") == peer and event.get("status") in TERMINAL:
                    return event
            return None

    @property
    def cursor(self) -> int:
        return self._next - 1


class QueuedTurn:
    def __init__(self, request_id: str, peer: str, message: str) -> None:
        self.request_id = request_id
        self.peer = peer
        self.message = message
        self.done = threading.Event()
        self.result: dict[str, Any] | None = None


class ToolGateway(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(
        self,
        address: tuple[str, int],
        loop: ToolLoop,
        events: EventStore,
        upstream: UpstreamClient,
        catalog: McpCatalog,
    ) -> None:
        super().__init__(address, Handler)
        self.loop = loop
        self.events = events
        self.upstream = upstream
        self.catalog = catalog
        self._peer_state_lock = threading.RLock()
        self._peer_queues: dict[str, queue.Queue[QueuedTurn]] = {}
        self._cancellations: dict[str, threading.Event] = {}
        # Report interrupted execution honestly; never replay a possibly applied
        # service write or restart an old conversation automatically.
        for event in list(events._latest.values()):
            if event.get("status") not in TERMINAL:
                events.append(
                    request_id=event["request_id"],
                    peer=event.get("peer"),
                    status="interrupted",
                    message="gateway restarted; remote work may continue at the retained upstream handle",
                    **{
                        **_upstream_handle_fields(event),
                        # Restart means this process lost track of the turn, not
                        # that the upstream operation was told to stop.
                        "upstream_status": "unknown",
                        "upstream_terminal": False,
                    },
                )

    @staticmethod
    def normalize_peer(value: Any) -> str:
        peer = str(value or "").strip().upper()
        if not peer:
            raise ValueError("peer must be a nonempty name")
        return peer

    def _queue_for(self, peer: str) -> queue.Queue[QueuedTurn]:
        with self._peer_state_lock:
            existing = self._peer_queues.get(peer)
            if existing is not None:
                return existing
            created: queue.Queue[QueuedTurn] = queue.Queue()
            self._peer_queues[peer] = created
            threading.Thread(
                target=self._peer_worker,
                args=(created,),
                name=f"gemini-commons-tools-{peer.lower()}",
                daemon=True,
            ).start()
            return created

    def _peer_worker(self, work: queue.Queue[QueuedTurn]) -> None:
        while True:
            item = work.get()
            try:
                item.result = self.execute(item.request_id, item.peer, item.message)
            finally:
                item.done.set()
                work.task_done()

    def submit(self, peer: str, message: str) -> QueuedTurn:
        if not isinstance(message, str) or not message.strip():
            raise ValueError("message must be nonempty UTF-8 text")
        with self._peer_state_lock:
            request_id = uuid.uuid4().hex
            raw = message.encode("utf-8")
            self.events.append(
                request_id=request_id,
                peer=peer,
                status="queued",
                message_bytes=len(raw),
                message_sha256=hashlib.sha256(raw).hexdigest(),
            )
            item = QueuedTurn(request_id, peer, message)
            self._cancellations[request_id] = threading.Event()
            self._queue_for(peer).put(item)
            return item

    def execute(self, request_id: str, peer: str, message: str) -> dict[str, Any]:
        started = time.monotonic()
        # Latest recoverable upstream handle for this request; carried into
        # whichever terminal event eventually closes it out, so a lost local
        # process (or a cancellation) still leaves behind where to look upstream.
        handle: dict[str, Any] = {}

        def on_submitted(info: dict[str, Any]) -> None:
            handle.update(
                upstream_request_id=info.get("upstream_request_id"),
                upstream_status_url=info.get("upstream_status_url"),
            )
            self.events.append(
                request_id=request_id,
                peer=peer,
                status="running",
                **handle,
            )

        try:
            self.events.append(request_id=request_id, peer=peer, status="running")
            reply = self.loop.run(
                request_id,
                peer,
                message,
                self._cancellations.get(request_id),
                on_submitted,
            )
            raw = reply.encode("utf-8")
            return self._terminal_event(
                request_id=request_id,
                peer=peer,
                status="completed",
                elapsed_ms=round((time.monotonic() - started) * 1000),
                reply=reply,
                reply_utf8_base64=base64.b64encode(raw).decode("ascii"),
                reply_bytes=len(raw),
                **handle,
            )
        except UpstreamTurnError as exc:
            details = _upstream_handle_fields(getattr(exc, "details", None))
            return self._terminal_event(
                request_id=request_id,
                peer=peer,
                status="error",
                elapsed_ms=round((time.monotonic() - started) * 1000),
                error=type(exc).__name__,
                message=str(exc),
                **{**handle, **details},
            )
        except InterruptedError as exc:
            return self._terminal_event(request_id=request_id, peer=peer, status="cancelled",
                elapsed_ms=round((time.monotonic() - started) * 1000), message=str(exc), **handle)
        except Exception as exc:
            return self._terminal_event(
                request_id=request_id,
                peer=peer,
                status="error",
                elapsed_ms=round((time.monotonic() - started) * 1000),
                error=type(exc).__name__,
                message=str(exc),
                **handle,
            )

    def _terminal_event(self, **fields) -> dict:
        with self._peer_state_lock:
            return self.events.append(**fields)

    def cancel(self, request_id: str) -> dict:
        with self._peer_state_lock:
            event = self.events.request(request_id, 0)
            if event is None:
                return {"ok": False, "error": "request_not_found"}
            if event["status"] in TERMINAL:
                return {"ok": True, "event": event, "already_terminal": True}
            self._cancellations[request_id].set()
            event = self.events.append(request_id=request_id, peer=event.get("peer"),
                status="cancel_requested", message="cooperative cancellation; in-flight provider turn may finish, then no further tool effects",
                **_upstream_handle_fields(event))
            return {"ok": True, "event": event}

class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server: ToolGateway

    def log_message(self, _format: str, *_args: Any) -> None:
        return

    def _send(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Connection", "close")
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass

    @staticmethod
    def _query_int(query: dict[str, list[str]], name: str, default: int) -> int:
        return int((query.get(name) or [default])[0])

    def do_GET(self) -> None:
        parsed = urllib.parse.urlsplit(self.path)
        query = urllib.parse.parse_qs(parsed.query)
        try:
            if parsed.path == "/v1/tools":
                self._send(200, {"ok": True, "tools": self.server.catalog.tools()})
                return
            if parsed.path in ("/", "/health", "/v1/peers"):
                upstream = self.server.upstream.health()
                tools = self.server.catalog.tools()
                self._send(
                    200,
                    {
                        "ok": True,
                        "service": "commons-gemini-peer-tool-gateway",
                        "mode": "history-preserving-tool-sidecar",
                        "tool_result_boundary": BOUNDARY_VERSION,
                        "upstream": self.server.upstream.base_url,
                        "upstream_ok": bool(upstream.get("ok")),
                        "peers": upstream.get("peers"),
                        "tool_count": len(tools),
                        "tools": [item["name"] for item in tools],
                        "event_cursor": self.server.events.cursor,
                        "slack_carrier": getattr(getattr(self.server, "carrier", None), "status", {"phase": "not_configured"}),
                    },
                )
                return
            if parsed.path == "/v1/events":
                cursor = max(0, self._query_int(query, "after", 0))
                limit = min(200, max(1, self._query_int(query, "limit", 50)))
                wait_ms = min(55_000, max(0, self._query_int(query, "wait_ms", 0)))
                peer = (query.get("peer") or [None])[0]
                if peer is not None:
                    peer = str(peer).upper()
                events = self.server.events.after(cursor, peer, limit, wait_ms)
                next_cursor = max([cursor] + [int(event["event_id"]) for event in events])
                self._send(200, {"ok": True, "events": events, "next_cursor": next_cursor})
                return
            if parsed.path == "/v1/last":
                peer = self.server.normalize_peer((query.get("peer") or [""])[0])
                event = self.server.events.last(peer)
                if event is None:
                    self._send(404, {"ok": False, "error": "reply_not_found"})
                else:
                    self._send(200, {"ok": True, "event": event})
                return
            prefix = "/v1/requests/"
            if parsed.path.startswith(prefix):
                request_id = parsed.path[len(prefix):]
                wait_ms = min(55_000, max(0, self._query_int(query, "wait_ms", 0)))
                event = self.server.events.request(request_id, wait_ms)
                if event is None:
                    self._send(404, {"ok": False, "error": "request_not_found"})
                else:
                    self._send(200, {"ok": True, "request_id": request_id, "event": event})
                return
            self._send(404, {"ok": False, "error": "not_found"})
        except Exception as exc:
            self._send(502, {"ok": False, "error": type(exc).__name__, "message": str(exc)})

    def do_POST(self) -> None:
        route = urllib.parse.urlsplit(self.path).path
        if route.startswith("/v1/requests/") and route.endswith("/cancel"):
            request_id = route[len("/v1/requests/"):-len("/cancel")]
            self._send(200, self.server.cancel(request_id))
            return
        if urllib.parse.urlsplit(self.path).path == "/v1/tools/call":
            try:
                size = int(self.headers.get("Content-Length", "0"))
                payload = json.loads(self.rfile.read(size).decode("utf-8"))
                for field in ("request_id", "call_id", "name"):
                    if not isinstance(payload.get(field), str) or not payload[field].strip():
                        raise ValueError(field + " must be a nonempty string")
                arguments = payload.get("arguments", {})
                if not isinstance(arguments, dict):
                    raise ValueError("arguments must be an object")
                result = self.server.loop.calls.execute_journaled(
                    "equipment:" + payload["request_id"], payload["call_id"],
                    payload["name"], arguments, self.server.catalog.call)
                self._send(200, {"ok": not tool_failed(result), "request_id": payload["request_id"],
                    "call_id": payload["call_id"], "result": redacted(result),
                    "uncertain": effect_uncertain(result)})
            except Exception as exc:
                self._send(400, {"ok": False, "error": type(exc).__name__, "message": redacted(str(exc))})
            return
        if urllib.parse.urlsplit(self.path).path != "/v1/message":
            self._send(404, {"ok": False, "error": "not_found"})
            return
        try:
            size = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(size).decode("utf-8"))
            peer = self.server.normalize_peer(payload.get("peer"))
            if isinstance(payload.get("message_utf8_base64"), str):
                message = base64.b64decode(
                    payload["message_utf8_base64"], validate=True
                ).decode("utf-8")
            else:
                message = payload.get("message")
            if not isinstance(message, str) or not message.strip():
                raise ValueError("message must be nonempty UTF-8 text")
            item = self.server.submit(peer, message)
            if payload.get("async"):
                self._send(
                    202,
                    {"ok": True, "request_id": item.request_id, "status": "queued"},
                )
                return
            item.done.wait()
            event = item.result
            if event is None:
                raise GatewayError("queued peer turn completed without a result")
            self._send(
                200 if event["status"] == "completed" else 502,
                {"ok": event["status"] == "completed", **event},
            )
        except Exception as exc:
            self._send(400, {"ok": False, "error": type(exc).__name__, "message": str(exc)})


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8778)
    parser.add_argument("--upstream", default=DEFAULT_UPSTREAM)
    parser.add_argument("--mcp-url", default=DEFAULT_MCP)
    parser.add_argument("--event-log", type=Path, default=DEFAULT_EVENT_LOG)
    parser.add_argument("--call-db", type=Path, default=DEFAULT_CALL_DB)
    parser.add_argument("--cache-ttl", type=float, default=300.0)
    parser.add_argument("--max-tool-steps", type=int, default=16)
    parser.add_argument("--max-protocol-retries", type=int, default=4)
    parser.add_argument("--equipment-config", type=Path, default=Path.home() / ".commons" / "equipment.json")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    upstream = UpstreamClient(args.upstream)
    catalog = CombinedCatalog(McpCatalog(args.mcp_url, ttl_seconds=args.cache_ttl))
    calls = ToolCallStore(args.call_db)
    events = EventStore(args.event_log)
    loop = ToolLoop(
        upstream,
        catalog,
        calls,
        max_steps=args.max_tool_steps,
        max_protocol_retries=args.max_protocol_retries,
    )
    server = ToolGateway(("127.0.0.1", args.port), loop, events, upstream, catalog)
    from integrations.shared_equipment.peers import GeminiEquipment, GrokBotEquipment
    catalog.extensions.append(GeminiEquipment(server))
    catalog.extensions.append(GrokBotEquipment())
    carrier = None
    if args.equipment_config.is_file():
        from integrations.shared_equipment.slack_carrier import SlackEquipmentCarrier
        config = json.loads(args.equipment_config.read_text(encoding="utf-8"))
        route = config.get("slack_carrier")
        if route:
            carrier = SlackEquipmentCarrier(catalog, calls, route,
                args.equipment_config.with_name("equipment_slack_cursor.json"))
            carrier.start()
    server.carrier = carrier
    print(
        json.dumps(
            {
                "ready": True,
                "listen": f"http://127.0.0.1:{args.port}",
                "upstream": args.upstream,
            }
        )
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        return 0
    finally:
        if carrier is not None:
            carrier.stop()
        server.server_close()
        calls.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
