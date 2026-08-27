#!/usr/bin/env python3
"""History-preserving Commons MCP tool loop for the live Gemini peers."""

from __future__ import annotations

import argparse
import base64
import datetime as dt
import hashlib
import json
import os
import re
import sqlite3
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable


DEFAULT_UPSTREAM = "http://127.0.0.1:8777"
DEFAULT_MCP = "https://commons-spark-mcp.vercel.app/mcp"
DEFAULT_EVENT_LOG = Path.home() / ".gemini" / "commons_peer_tool_gateway_events.jsonl"
DEFAULT_CALL_DB = Path.home() / ".gemini" / "commons_peer_tool_calls.sqlite3"
MCP_PROTOCOL = "2025-03-26"
TERMINAL = frozenset({"completed", "error"})
CALL_OPEN = "<commons_tool_call>"
CALL_CLOSE = "</commons_tool_call>"
CALL_RE = re.compile(r"^\s*<commons_tool_call>(.*?)</commons_tool_call>\s*$", re.DOTALL)


class GatewayError(RuntimeError):
    pass


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
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            value = json.loads(response.read().decode("utf-8"))
    except (OSError, ValueError, urllib.error.URLError) as exc:
        raise GatewayError(f"POST {url} failed: {exc}") from exc
    if not isinstance(value, dict):
        raise GatewayError(f"POST {url} returned a non-object")
    return value


def _get_json(url: str, *, timeout: float = 15.0) -> dict[str, Any]:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            value = json.loads(response.read().decode("utf-8"))
    except (OSError, ValueError, urllib.error.URLError) as exc:
        raise GatewayError(f"GET {url} failed: {exc}") from exc
    if not isinstance(value, dict):
        raise GatewayError(f"GET {url} returned a non-object")
    return value


class UpstreamClient:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")

    def health(self) -> dict[str, Any]:
        return _get_json(self.base_url + "/health", timeout=10)

    def turn(self, peer: str, message: str) -> str:
        encoded = base64.b64encode(message.encode("utf-8")).decode("ascii")
        response = _post_json(
            self.base_url + "/v1/message",
            {"peer": peer, "message_utf8_base64": encoded},
            timeout=700,
        )
        if not response.get("ok"):
            raise GatewayError("upstream peer turn failed")
        if isinstance(response.get("reply_utf8_base64"), str):
            try:
                return base64.b64decode(response["reply_utf8_base64"], validate=True).decode("utf-8")
            except (ValueError, UnicodeError) as exc:
                raise GatewayError("upstream reply was not byte-safe UTF-8") from exc
        reply = response.get("reply")
        if not isinstance(reply, str):
            raise GatewayError("upstream returned no reply")
        return reply


class McpCatalog:
    def __init__(self, url: str, *, ttl_seconds: float = 300.0) -> None:
        self.url = url
        self.ttl_seconds = ttl_seconds
        self._tools: list[dict[str, Any]] = []
        self._expires = 0.0
        self._lock = threading.Lock()

    def _rpc(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        response = _post_json(
            self.url,
            {"jsonrpc": "2.0", "id": uuid.uuid4().hex, "method": method, "params": params},
            headers={
                "Accept": "application/json, text/event-stream",
                "MCP-Protocol-Version": MCP_PROTOCOL,
            },
        )
        if response.get("error"):
            raise GatewayError(f"Commons MCP error: {response['error']}")
        result = response.get("result")
        if not isinstance(result, dict):
            raise GatewayError("Commons MCP returned no result object")
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
    """Exactly-once call-id journal. Arguments are retained only as a hash."""

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

    def execute_once(
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
                    return {"error": "call_id_reused_with_different_arguments"}
                if row["result_json"]:
                    return json.loads(row["result_json"])
                return {"error": "tool_call_incomplete_after_restart", "call_id": call_id}
            self._db.execute(
                "INSERT INTO tool_calls VALUES(?,?,?,?,?,?,?)",
                (request_id, call_id, name, digest, "started", None, time.time()),
            )
        try:
            result = runner(name, arguments)
            if not isinstance(result, dict):
                result = {"result": result}
            state = "completed"
        except Exception as exc:
            result = {"error": type(exc).__name__, "message": str(exc)}
            state = "error"
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
        "You are connected to the full live public Commons MCP through a history-preserving outer tool loop. "
        "You may use any listed tool. When a tool is needed, reply with exactly one envelope and no "
        "surrounding text:\n"
        f"{CALL_OPEN}{{\"call_id\":\"a unique id\",\"name\":\"tool name\",\"arguments\":{{}}}}{CALL_CLOSE}\n"
        "After a result arrives, continue normally or issue another exact envelope. If no tool is needed, "
        "reply normally. Do not invent tool names.\n\nAVAILABLE_COMMONS_TOOLS_JSON:\n"
        + catalog
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
    ) -> None:
        self.upstream = upstream
        self.catalog = catalog
        self.calls = calls
        self.max_steps = max_steps

    def run(self, request_id: str, peer: str, message: str) -> str:
        tools = self.catalog.tools()
        names = {item["name"] for item in tools}
        prompt = _tool_prompt(message, tools)
        for _ in range(self.max_steps + 1):
            reply = self.upstream.turn(peer, prompt)
            call, had_marker = _parse_call(reply)
            if call is None and not had_marker:
                return reply
            if call is None:
                prompt = (
                    "That tool envelope was malformed. Emit exactly one valid JSON object between "
                    f"{CALL_OPEN} and {CALL_CLOSE}, or reply normally without either marker."
                )
                continue
            if call["name"] not in names:
                result = {
                    "error": "unknown_tool",
                    "name": call["name"],
                    "available": sorted(names),
                }
            else:
                result = self.calls.execute_once(
                    request_id,
                    call["call_id"],
                    call["name"],
                    call["arguments"],
                    self.catalog.call,
                )
            prompt = (
                "Commons MCP returned this exact result. Continue the same response. Use another exact "
                "tool envelope if useful; otherwise answer normally.\n<commons_tool_result>"
                + json.dumps(
                    {"call_id": call["call_id"], "name": call["name"], "result": result},
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
                + "</commons_tool_result>"
            )
        raise GatewayError(f"peer exceeded {self.max_steps} Commons tool calls")


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
        self.peer_locks = {"TESSERA": threading.Lock(), "MERIDIAN": threading.Lock()}

    def submit(self, peer: str, message: str) -> str:
        request_id = uuid.uuid4().hex
        raw = message.encode("utf-8")
        self.events.append(
            request_id=request_id,
            peer=peer,
            status="queued",
            message_bytes=len(raw),
            message_sha256=hashlib.sha256(raw).hexdigest(),
        )
        return request_id

    def execute(self, request_id: str, peer: str, message: str) -> dict[str, Any]:
        started = time.monotonic()
        try:
            with self.peer_locks[peer]:
                self.events.append(request_id=request_id, peer=peer, status="running")
                reply = self.loop.run(request_id, peer, message)
            raw = reply.encode("utf-8")
            return self.events.append(
                request_id=request_id,
                peer=peer,
                status="completed",
                elapsed_ms=round((time.monotonic() - started) * 1000),
                reply=reply,
                reply_utf8_base64=base64.b64encode(raw).decode("ascii"),
                reply_bytes=len(raw),
            )
        except Exception as exc:
            return self.events.append(
                request_id=request_id,
                peer=peer,
                status="error",
                elapsed_ms=round((time.monotonic() - started) * 1000),
                error=type(exc).__name__,
                message=str(exc),
            )

    def execute_background(self, request_id: str, peer: str, message: str) -> None:
        threading.Thread(
            target=self.execute,
            args=(request_id, peer, message),
            name=f"gemini-commons-tools-{peer.lower()}-{request_id[:8]}",
            daemon=True,
        ).start()


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
            if parsed.path in ("/", "/health", "/v1/peers"):
                upstream = self.server.upstream.health()
                tools = self.server.catalog.tools()
                self._send(
                    200,
                    {
                        "ok": True,
                        "service": "commons-gemini-peer-tool-gateway",
                        "mode": "history-preserving-tool-sidecar",
                        "upstream": self.server.upstream.base_url,
                        "upstream_ok": bool(upstream.get("ok")),
                        "peers": upstream.get("peers"),
                        "tool_count": len(tools),
                        "tools": [item["name"] for item in tools],
                        "event_cursor": self.server.events.cursor,
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
                peer = str((query.get("peer") or [""])[0]).upper()
                if peer not in self.server.peer_locks:
                    raise ValueError("peer must be TESSERA or MERIDIAN")
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
        if urllib.parse.urlsplit(self.path).path != "/v1/message":
            self._send(404, {"ok": False, "error": "not_found"})
            return
        try:
            size = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(size).decode("utf-8"))
            peer = str(payload.get("peer") or "").upper()
            if peer not in self.server.peer_locks:
                raise ValueError("peer must be TESSERA or MERIDIAN")
            if isinstance(payload.get("message_utf8_base64"), str):
                message = base64.b64decode(
                    payload["message_utf8_base64"], validate=True
                ).decode("utf-8")
            else:
                message = payload.get("message")
            if not isinstance(message, str) or not message.strip():
                raise ValueError("message must be nonempty UTF-8 text")
            request_id = self.server.submit(peer, message)
            if payload.get("async"):
                self.server.execute_background(request_id, peer, message)
                self._send(202, {"ok": True, "request_id": request_id, "status": "queued"})
                return
            event = self.server.execute(request_id, peer, message)
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
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    upstream = UpstreamClient(args.upstream)
    catalog = McpCatalog(args.mcp_url, ttl_seconds=args.cache_ttl)
    calls = ToolCallStore(args.call_db)
    events = EventStore(args.event_log)
    loop = ToolLoop(upstream, catalog, calls, max_steps=args.max_tool_steps)
    server = ToolGateway(("127.0.0.1", args.port), loop, events, upstream, catalog)
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
        server.server_close()
        calls.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
