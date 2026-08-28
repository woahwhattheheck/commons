#!/usr/bin/env python3
"""Slack Socket Mode transport for the existing grok.com Commons revenue road.

This connector owns Slack claim, ACK, crash recovery, and final thread
delivery. Model work goes through the public Commons MCP, the existing
route_grokcom_revenue_work INTAKE packet, fire_action exactly once, and the
shared GrokExecutorQueue. SQLite keeps routing and delivery metadata only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sqlite3
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


SCHEMA = "commons-grok-slack-connector/v1"
FINAL_DELIVERY_OWNER = "grok_slack_bridge"
CONNECTOR_ORIGIN = "COMMONS_GROKCOM_REVENUE"
DEFAULT_MCP_URL = "https://commons-spark-mcp.vercel.app/mcp"
DEFAULT_GITHUB_OWNER = "woahwhattheheck"
DEFAULT_GITHUB_REPO = "commons"
DEFAULT_CHANNEL = "C0BRGMDQB6G"
DEFAULT_STATE_DB = Path.home() / ".commons" / "grok_slack.sqlite3"
SLACK_TEXT_LIMIT = 3_800
GROK_URL_RE = re.compile(r"^https://grok\.com/c/([A-Za-z0-9_-]+)(?:[/?#].*)?$")
MCP_PROTOCOL = "2025-03-26"
REQUIRED_TOOLS = ("route_grokcom_revenue_work", "fire_action")
PHASES = (
    "CLAIMED",
    "INTAKE",
    "JOB_PERSISTED",
    "SUBMITTED",
    "OBSERVING",
    "RESULT",
    "DELIVERING",
    "DELIVERED",
    "FAILED",
    "EVENT_ID_COLLISION",
    "NO_SUBMIT",
    "ECHO_SUPPRESSED",
    "DELIVERY_UNKNOWN",
    "FIRE_ACTION_UNKNOWN",
)
PRE_SUBMIT_PHASES = frozenset({"CLAIMED", "INTAKE", "JOB_PERSISTED"})
POST_SUBMIT_PHASES = frozenset({
    "SUBMITTED", "OBSERVING", "RESULT", "DELIVERING", "DELIVERED",
    "DELIVERY_UNKNOWN", "FIRE_ACTION_UNKNOWN",
})
SECRET_ENV = ("SLACK_BOT_TOKEN", "SLACK_APP_TOKEN")
RETRY_BUDGET = 4
POLL_BUDGET = 12


class BridgeError(RuntimeError):
    """Expected connector or upstream failure."""


class RuntimeUnconfigured(BridgeError):
    """Slack credentials are missing. Zero Slack or provider calls."""

    state = "RUNTIME_UNCONFIGURED"


@dataclass
class SlackSendResult:
    state: str
    slack_ts: str = ""
    client_msg_id: str = ""
    status: int | None = None
    retry_after: float | None = None
    ambiguous: bool = False


@dataclass
class ClaimResult:
    accepted: bool
    disposition: str
    event_id: str
    source_key: str
    text_sha256: str
    phase: str = "CLAIMED"


@dataclass
class PendingWork:
    event_id: str
    channel: str
    message_ts: str
    thread_ts: str
    author: str
    phase: str
    task_id: str = ""
    job_id: str = ""
    run_key: str = ""
    durable_path: str = ""
    result_id: str = ""
    conversation_rid: str = ""
    text_sha256: str = ""
    source_key: str = ""
    fire_action_calls: int = 0
    extras: dict[str, Any] = field(default_factory=dict)


def _now() -> float:
    return time.time()


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_text(text: str) -> str:
    return _sha256_bytes(text.encode("utf-8"))


def source_key(channel: str, message_ts: str) -> str:
    return f"{channel}\0{message_ts}"


def delivery_key(event_id: str, phase: str, index: int, chunk: str) -> str:
    return f"{event_id}:{phase}:{index}:{_sha256_text(chunk)}"


def client_msg_id_for(key: str) -> str:
    return "gsb-" + _sha256_text(key)[:40]


def canonical_grok_url(value: str) -> str:
    text = value.strip() if isinstance(value, str) else ""
    match = GROK_URL_RE.fullmatch(text)
    if not match:
        return ""
    return "https://grok.com/c/" + match.group(1)


def chunk_text(text: str, limit: int = SLACK_TEXT_LIMIT) -> list[str]:
    """Split below Slack's practical bound without dropping any UTF-8 bytes."""
    if len(text) <= limit:
        return [text]
    pieces: list[str] = []
    remaining = text
    while remaining:
        if len(remaining) <= limit:
            pieces.append(remaining)
            break
        split_at = remaining.rfind("\n", 0, limit)
        if split_at < 1:
            split_at = remaining.rfind(" ", 0, limit)
        if split_at < 1:
            split_at = limit
        pieces.append(remaining[:split_at])
        remaining = remaining[split_at:]
    return pieces


def reconstruct(pieces: list[str]) -> str:
    return "".join(pieces)


def file_references(event: dict[str, Any]) -> list[dict[str, str]]:
    files = event.get("files") or []
    refs: list[dict[str, str]] = []
    if not isinstance(files, list):
        return refs
    for item in files:
        if not isinstance(item, dict):
            continue
        refs.append({
            "id": str(item.get("id") or ""),
            "name": str(item.get("name") or ""),
            "mimetype": str(item.get("mimetype") or ""),
            "permalink": str(item.get("permalink") or item.get("url_private") or ""),
        })
    return refs


def slack_event_contract(event_id: str, event: dict[str, Any]) -> dict[str, Any]:
    channel = str(event.get("channel") or "")
    message_ts = str(event.get("ts") or event.get("message_ts") or "")
    thread_ts = str(event.get("thread_ts") or message_ts)
    author = str(event.get("user") or event.get("bot_id") or event.get("author") or "UNSEATED")
    text = event.get("text")
    if not isinstance(text, str):
        text = ""
    payload = {
        "event_id": event_id,
        "channel": channel,
        "message_ts": message_ts,
        "thread_ts": thread_ts,
        "author": author,
        "text": text,
        "connector_origin": str(event.get("connector_origin") or ""),
        "files": file_references(event),
    }
    return payload


def is_direct_message(event: dict[str, Any]) -> bool:
    return event.get("channel_type") in {"im", "mpim"} or str(event.get("channel") or "").startswith("D")


def is_own_connector_message(event: dict[str, Any], bot_user_id: str | None) -> bool:
    if bot_user_id and event.get("user") == bot_user_id:
        return True
    if event.get("connector_origin") == CONNECTOR_ORIGIN:
        return True
    return False


def is_edit_or_delete(event: dict[str, Any]) -> bool:
    return event.get("subtype") in {"message_changed", "message_deleted"}


def credential_presence(env: dict[str, str] | None = None) -> dict[str, str]:
    source = env if env is not None else os.environ
    return {name: ("present" if source.get(name) else "missing") for name in SECRET_ENV}


class BridgeStore:
    """Crash-recovery routing state. Content and secrets are never stored."""

    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self._lock = threading.RLock()
        self._connection = sqlite3.connect(path, check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        with self._connection:
            self._connection.executescript(
                """
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS slack_events (
                    event_id TEXT PRIMARY KEY,
                    source_key TEXT NOT NULL,
                    text_sha256 TEXT NOT NULL,
                    channel TEXT NOT NULL,
                    message_ts TEXT NOT NULL,
                    thread_ts TEXT NOT NULL,
                    author TEXT NOT NULL,
                    has_files INTEGER NOT NULL DEFAULT 0,
                    task_id TEXT,
                    job_id TEXT,
                    run_key TEXT,
                    durable_path TEXT,
                    result_id TEXT,
                    conversation_rid TEXT,
                    phase TEXT NOT NULL,
                    fire_action_calls INTEGER NOT NULL DEFAULT 0,
                    delivery_owner TEXT NOT NULL DEFAULT 'grok_slack_bridge',
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                );
                CREATE INDEX IF NOT EXISTS slack_events_source ON slack_events(source_key);
                CREATE INDEX IF NOT EXISTS slack_events_phase ON slack_events(phase, updated_at);
                CREATE TABLE IF NOT EXISTS owned_threads (
                    thread_key TEXT PRIMARY KEY,
                    root_message_ts TEXT NOT NULL,
                    updated_at REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS deliveries (
                    delivery_key TEXT PRIMARY KEY,
                    event_id TEXT NOT NULL,
                    phase TEXT NOT NULL,
                    chunk_index INTEGER NOT NULL,
                    chunk_count INTEGER NOT NULL,
                    body_sha256 TEXT NOT NULL,
                    channel TEXT NOT NULL,
                    thread_ts TEXT NOT NULL,
                    slack_ts TEXT,
                    client_msg_id TEXT,
                    state TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                );
                """
            )

    def close(self) -> None:
        with self._lock:
            self._connection.close()

    def claim(
        self,
        event_id: str,
        channel: str,
        message_ts: str,
        thread_ts: str,
        author: str,
        text: str,
        *,
        has_files: bool = False,
    ) -> ClaimResult:
        digest = _sha256_text(text)
        key = source_key(channel, message_ts)
        now = _now()
        with self._lock, self._connection:
            existing = self._connection.execute(
                "SELECT event_id, text_sha256, phase FROM slack_events WHERE event_id = ?",
                (event_id,),
            ).fetchone()
            if existing is not None:
                if str(existing["text_sha256"]) != digest:
                    self._connection.execute(
                        "UPDATE slack_events SET phase = ?, updated_at = ? WHERE event_id = ?",
                        ("EVENT_ID_COLLISION", now, event_id),
                    )
                    return ClaimResult(False, "EVENT_ID_COLLISION", event_id, key, digest, "EVENT_ID_COLLISION")
                return ClaimResult(False, "RETRY_DUPLICATE", event_id, key, digest, str(existing["phase"]))
            source_row = self._connection.execute(
                "SELECT event_id, phase FROM slack_events WHERE source_key = ? LIMIT 1",
                (key,),
            ).fetchone()
            if source_row is not None:
                return ClaimResult(
                    False,
                    "SOURCE_COLLAPSE",
                    str(source_row["event_id"]),
                    key,
                    digest,
                    str(source_row["phase"]),
                )
            self._connection.execute(
                """
                INSERT INTO slack_events (
                    event_id, source_key, text_sha256, channel, message_ts, thread_ts,
                    author, has_files, phase, delivery_owner, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'CLAIMED', ?, ?, ?)
                """,
                (event_id, key, digest, channel, message_ts, thread_ts, author, 1 if has_files else 0, FINAL_DELIVERY_OWNER, now, now),
            )
            return ClaimResult(True, "CLAIMED", event_id, key, digest, "CLAIMED")

    def remember_thread(self, channel: str, thread_ts: str, root_message_ts: str) -> None:
        now = _now()
        with self._lock, self._connection:
            self._connection.execute(
                """
                INSERT INTO owned_threads(thread_key, root_message_ts, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(thread_key) DO UPDATE SET updated_at = excluded.updated_at
                """,
                (f"{channel}:{thread_ts}", root_message_ts, now),
            )

    def owns_thread(self, channel: str, thread_ts: str) -> bool:
        with self._lock:
            row = self._connection.execute(
                "SELECT 1 FROM owned_threads WHERE thread_key = ?",
                (f"{channel}:{thread_ts}",),
            ).fetchone()
        return row is not None

    def set_phase(self, event_id: str, phase: str, **fields: Any) -> None:
        if phase not in PHASES:
            raise ValueError("unknown phase")
        assignments = ["phase = ?", "updated_at = ?"]
        values: list[Any] = [phase, _now()]
        allowed = {
            "task_id", "job_id", "run_key", "durable_path", "result_id",
            "conversation_rid", "fire_action_calls",
        }
        for key, value in fields.items():
            if key not in allowed:
                raise ValueError("unsupported event field")
            assignments.append(f"{key} = ?")
            values.append(value)
        values.append(event_id)
        with self._lock, self._connection:
            self._connection.execute(
                f"UPDATE slack_events SET {', '.join(assignments)} WHERE event_id = ?",
                values,
            )

    def increment_fire_action(self, event_id: str) -> int:
        with self._lock, self._connection:
            self._connection.execute(
                "UPDATE slack_events SET fire_action_calls = fire_action_calls + 1, updated_at = ? WHERE event_id = ?",
                (_now(), event_id),
            )
            row = self._connection.execute(
                "SELECT fire_action_calls FROM slack_events WHERE event_id = ?",
                (event_id,),
            ).fetchone()
        return int(row["fire_action_calls"]) if row else 0

    def get(self, event_id: str) -> PendingWork | None:
        with self._lock:
            row = self._connection.execute(
                "SELECT * FROM slack_events WHERE event_id = ?",
                (event_id,),
            ).fetchone()
        if row is None:
            return None
        return self._row_to_work(row)

    def pending(self) -> list[PendingWork]:
        with self._lock:
            rows = self._connection.execute(
                """
                SELECT * FROM slack_events
                WHERE phase NOT IN ('DELIVERED', 'FAILED', 'EVENT_ID_COLLISION', 'NO_SUBMIT', 'ECHO_SUPPRESSED')
                ORDER BY created_at
                """
            ).fetchall()
        return [self._row_to_work(row) for row in rows]

    def owns_client_msg_id(self, client_msg_id: str) -> bool:
        with self._lock:
            row = self._connection.execute(
                "SELECT 1 FROM deliveries WHERE client_msg_id = ? LIMIT 1",
                (client_msg_id,),
            ).fetchone()
        return row is not None

    def get_delivery(self, key: str) -> dict[str, Any] | None:
        with self._lock:
            row = self._connection.execute(
                "SELECT * FROM deliveries WHERE delivery_key = ?",
                (key,),
            ).fetchone()
        return dict(row) if row else None

    def upsert_delivery(
        self,
        key: str,
        event_id: str,
        phase: str,
        index: int,
        count: int,
        body_sha256: str,
        channel: str,
        thread_ts: str,
        client_msg_id: str,
        state: str,
        slack_ts: str = "",
    ) -> None:
        now = _now()
        with self._lock, self._connection:
            self._connection.execute(
                """
                INSERT INTO deliveries (
                    delivery_key, event_id, phase, chunk_index, chunk_count, body_sha256,
                    channel, thread_ts, slack_ts, client_msg_id, state, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(delivery_key) DO UPDATE SET
                    slack_ts = excluded.slack_ts,
                    state = excluded.state,
                    updated_at = excluded.updated_at
                """,
                (key, event_id, phase, index, count, body_sha256, channel, thread_ts, slack_ts, client_msg_id, state, now, now),
            )

    def dump_text(self) -> str:
        with self._lock:
            return "\n".join(self._connection.iterdump())

    def _row_to_work(self, row: sqlite3.Row) -> PendingWork:
        return PendingWork(
            event_id=str(row["event_id"]),
            channel=str(row["channel"]),
            message_ts=str(row["message_ts"]),
            thread_ts=str(row["thread_ts"]),
            author=str(row["author"]),
            phase=str(row["phase"]),
            task_id=str(row["task_id"] or ""),
            job_id=str(row["job_id"] or ""),
            run_key=str(row["run_key"] or ""),
            durable_path=str(row["durable_path"] or ""),
            result_id=str(row["result_id"] or ""),
            conversation_rid=str(row["conversation_rid"] or ""),
            text_sha256=str(row["text_sha256"] or ""),
            source_key=str(row["source_key"] or ""),
            fire_action_calls=int(row["fire_action_calls"] or 0),
        )


class CommonsMcpClient:
    """Public Streamable HTTP client. Does not import Commons private logic."""

    def __init__(self, url: str = DEFAULT_MCP_URL, *, opener: Callable[..., Any] | None = None) -> None:
        self.url = url
        self._opener = opener or urlopen
        self._next_id = 1
        self.calls: list[tuple[str, Any]] = []

    def initialize(self) -> dict[str, Any]:
        return self._rpc("initialize", {
            "protocolVersion": MCP_PROTOCOL,
            "capabilities": {},
            "clientInfo": {"name": "grok-slack-connector", "version": "1"},
        })

    def tools_list(self) -> list[str]:
        result = self._rpc("tools/list", {})
        tools = result.get("tools") or []
        names = [str(row.get("name")) for row in tools if isinstance(row, dict)]
        return names

    def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        self.calls.append((name, arguments))
        result = self._rpc("tools/call", {"name": name, "arguments": arguments})
        if isinstance(result.get("structuredContent"), dict):
            return result["structuredContent"]
        if isinstance(result, dict) and "state" in result:
            return result
        return result

    def _rpc(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        ident = self._next_id
        self._next_id += 1
        payload = {"jsonrpc": "2.0", "id": ident, "method": method, "params": params}
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = Request(
            self.url,
            data=body,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream",
            },
            method="POST",
        )
        try:
            with self._opener(request, timeout=30) as response:
                raw = response.read().decode("utf-8")
        except HTTPError as exc:
            raise BridgeError(f"mcp HTTP {exc.code}") from exc
        except (URLError, TimeoutError, OSError) as exc:
            raise BridgeError("mcp unavailable") from exc
        decoded = _decode_mcp_body(raw)
        if "error" in decoded:
            raise BridgeError("mcp error")
        result = decoded.get("result")
        if not isinstance(result, dict):
            raise BridgeError("mcp returned a non-object result")
        return result


def _decode_mcp_body(raw: str) -> dict[str, Any]:
    text = raw.strip()
    if not text:
        raise BridgeError("mcp returned empty body")
    if text.startswith("{"):
        try:
            decoded = json.loads(text)
        except json.JSONDecodeError as exc:
            raise BridgeError("mcp returned invalid JSON") from exc
        if not isinstance(decoded, dict):
            raise BridgeError("mcp returned a non-object response")
        return decoded
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("data:"):
            blob = line[5:].strip()
            if not blob or blob == "[DONE]":
                continue
            try:
                decoded = json.loads(blob)
            except json.JSONDecodeError:
                continue
            if isinstance(decoded, dict):
                return decoded
    raise BridgeError("mcp returned invalid JSON")


class GitHubReadback:
    """SHA-pinned Contents reads of current main. Never uses raw/main or Pages."""

    def __init__(
        self,
        owner: str = DEFAULT_GITHUB_OWNER,
        repo: str = DEFAULT_GITHUB_REPO,
        *,
        opener: Callable[..., Any] | None = None,
    ) -> None:
        self.owner = owner
        self.repo = repo
        self._opener = opener or urlopen

    def current_main_sha(self) -> str:
        payload = self._get(f"/repos/{self.owner}/{self.repo}/commits/main")
        sha = payload.get("sha")
        if not isinstance(sha, str) or len(sha) != 40:
            raise BridgeError("github main SHA unavailable")
        return sha

    def read_path(self, path: str, sha: str) -> bytes:
        payload = self._get(f"/repos/{self.owner}/{self.repo}/contents/{path}", {"ref": sha})
        encoding = payload.get("encoding")
        content = payload.get("content")
        if encoding == "base64" and isinstance(content, str):
            import base64
            return base64.b64decode(content)
        if isinstance(payload.get("download_url"), str):
            request = Request(payload["download_url"], headers={"Accept": "application/octet-stream", "User-Agent": "commons-grok-slack-connector"})
            with self._opener(request, timeout=30) as response:
                return response.read()
        raise BridgeError("github path unavailable")

    def _get(self, path: str, query: dict[str, str] | None = None) -> dict[str, Any]:
        url = "https://api.github.com" + path
        if query:
            from urllib.parse import urlencode
            url += "?" + urlencode(query)
        request = Request(url, headers={"Accept": "application/vnd.github+json", "User-Agent": "commons-grok-slack-connector"})
        try:
            with self._opener(request, timeout=30) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            if exc.code == 404:
                raise FileNotFoundError(path) from exc
            raise BridgeError(f"github HTTP {exc.code}") from exc
        except (URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
            raise BridgeError("github unavailable") from exc


class SlackTransport:
    """Slack Web API poster with 429 budget, timeout reconcile, and no blind repost."""

    def __init__(
        self,
        web_client: Any,
        store: BridgeStore,
        *,
        retry_budget: int = RETRY_BUDGET,
        sleeper: Callable[[float], None] = time.sleep,
    ) -> None:
        self.web_client = web_client
        self.store = store
        self.retry_budget = retry_budget
        self.sleeper = sleeper
        self.posts: list[dict[str, Any]] = []

    def post_chunk(
        self,
        channel: str,
        thread_ts: str,
        text: str,
        *,
        event_id: str,
        phase: str,
        index: int,
        count: int,
    ) -> SlackSendResult:
        key = delivery_key(event_id, phase, index, text)
        existing = self.store.get_delivery(key)
        if existing and existing["state"] == "SENT":
            return SlackSendResult("SENT", slack_ts=str(existing.get("slack_ts") or ""), client_msg_id=str(existing.get("client_msg_id") or ""))
        msg_id = str((existing or {}).get("client_msg_id") or client_msg_id_for(key))
        if existing and existing["state"] == "PENDING":
            reconciled = self._reconcile(channel, thread_ts, key, msg_id, event_id, phase, index, count, text)
            if reconciled.state == "SENT":
                return reconciled
        if existing and existing["state"] == "DELIVERY_UNKNOWN":
            return SlackSendResult("DELIVERY_UNKNOWN", client_msg_id=msg_id, ambiguous=True)
        self.store.upsert_delivery(
            key, event_id, phase, index, count, _sha256_text(text),
            channel, thread_ts, msg_id, "PENDING",
        )
        last = SlackSendResult("FAILED", client_msg_id=msg_id)
        for attempt in range(self.retry_budget):
            try:
                response = self.web_client.chat_postMessage(
                    channel=channel,
                    thread_ts=thread_ts,
                    text=text,
                    unfurl_links=False,
                    unfurl_media=False,
                    client_msg_id=msg_id,
                )
            except Exception as exc:
                last = self._from_exception(exc, msg_id)
                if last.status == 429 and last.retry_after is not None and attempt + 1 < self.retry_budget:
                    self.sleeper(max(0.0, last.retry_after))
                    continue
                if last.ambiguous:
                    return self._reconcile(channel, thread_ts, key, msg_id, event_id, phase, index, count, text)
                if last.status is not None and last.status >= 400 and last.status != 429:
                    break
                if last.status is None and not last.ambiguous:
                    backoff = min(2 ** attempt, 8)
                    if attempt + 1 < self.retry_budget:
                        self.sleeper(backoff)
                        continue
                break
            else:
                slack_ts = ""
                if isinstance(response, dict):
                    slack_ts = str(response.get("ts") or "")
                    ok = bool(response.get("ok", True))
                else:
                    slack_ts = str(getattr(response, "ts", "") or "")
                    ok = bool(getattr(response, "ok", True))
                if ok:
                    self.store.upsert_delivery(
                        key, event_id, phase, index, count, _sha256_text(text),
                        channel, thread_ts, msg_id, "SENT", slack_ts,
                    )
                    self.posts.append({"channel": channel, "thread_ts": thread_ts, "ts": slack_ts, "phase": phase, "index": index})
                    return SlackSendResult("SENT", slack_ts=slack_ts, client_msg_id=msg_id)
                last = SlackSendResult("FAILED", client_msg_id=msg_id)
                break
        self.store.upsert_delivery(
            key, event_id, phase, index, count, _sha256_text(text),
            channel, thread_ts, msg_id, last.state, last.slack_ts,
        )
        return last

    def _from_exception(self, exc: Exception, msg_id: str) -> SlackSendResult:
        status = getattr(exc, "status", None)
        if status is None:
            response = getattr(exc, "response", None)
            status = getattr(response, "status_code", None)
        retry_after = None
        headers = {}
        response = getattr(exc, "response", None)
        if response is not None:
            headers = getattr(response, "headers", {}) or {}
        if "Retry-After" in headers:
            try:
                retry_after = float(headers["Retry-After"])
            except (TypeError, ValueError):
                retry_after = 1.0
        ambiguous = isinstance(exc, (TimeoutError, TimeoutError)) or type(exc).__name__ in {"TimeoutError", "SlackClientError"} and "timeout" in str(exc).casefold()
        if type(exc).__name__ == "TimeoutError" or isinstance(exc, TimeoutError):
            ambiguous = True
        return SlackSendResult(
            "DELIVERY_UNKNOWN" if ambiguous else "FAILED",
            client_msg_id=msg_id,
            status=int(status) if isinstance(status, int) else None,
            retry_after=retry_after,
            ambiguous=ambiguous,
        )

    def _reconcile(
        self,
        channel: str,
        thread_ts: str,
        key: str,
        msg_id: str,
        event_id: str,
        phase: str,
        index: int,
        count: int,
        text: str,
    ) -> SlackSendResult:
        try:
            history = self.web_client.conversations_replies(channel=channel, ts=thread_ts)
        except Exception:
            self.store.upsert_delivery(
                key, event_id, phase, index, count, _sha256_text(text),
                channel, thread_ts, msg_id, "DELIVERY_UNKNOWN",
            )
            return SlackSendResult("DELIVERY_UNKNOWN", client_msg_id=msg_id, ambiguous=True)
        messages = history.get("messages") if isinstance(history, dict) else getattr(history, "messages", None)
        if not isinstance(messages, list):
            self.store.upsert_delivery(
                key, event_id, phase, index, count, _sha256_text(text),
                channel, thread_ts, msg_id, "DELIVERY_UNKNOWN",
            )
            return SlackSendResult("DELIVERY_UNKNOWN", client_msg_id=msg_id, ambiguous=True)
        for item in messages:
            if not isinstance(item, dict):
                continue
            if item.get("client_msg_id") == msg_id:
                slack_ts = str(item.get("ts") or "")
                self.store.upsert_delivery(
                    key, event_id, phase, index, count, _sha256_text(text),
                    channel, thread_ts, msg_id, "SENT", slack_ts,
                )
                return SlackSendResult("SENT", slack_ts=slack_ts, client_msg_id=msg_id)
        self.store.upsert_delivery(
            key, event_id, phase, index, count, _sha256_text(text),
            channel, thread_ts, msg_id, "DELIVERY_UNKNOWN",
        )
        return SlackSendResult("DELIVERY_UNKNOWN", client_msg_id=msg_id, ambiguous=True)


class GrokSlackBridge:
    """Claim Slack events, compose the existing Grok road, deliver once."""

    def __init__(
        self,
        store: BridgeStore,
        mcp: Any,
        github: Any,
        sink: SlackTransport,
        *,
        bot_user_id: str | None = None,
        poll_budget: int = POLL_BUDGET,
        sleeper: Callable[[float], None] | None = None,
        clock: Callable[[], float] | None = None,
        executor_slack: Any | None = None,
        grok_provider: Any | None = None,
    ) -> None:
        self.store = store
        self.mcp = mcp
        self.github = github
        self.sink = sink
        self.bot_user_id = bot_user_id
        self.poll_budget = poll_budget
        self.sleeper = sleeper or (lambda _seconds: None)
        self.clock = clock or time.time
        self.executor_slack = executor_slack
        self.grok_provider = grok_provider
        self.ack_log: list[str] = []
        self.work_log: list[str] = []
        self.delivery_owner = FINAL_DELIVERY_OWNER

    def handle_event(self, event_id: str, event: dict[str, Any]) -> dict[str, Any]:
        self.work_log.append("handle_event")
        if is_direct_message(event):
            return {"ok": True, "state": "NO_SUBMIT", "reason": "DM_OMITTED"}
        if is_edit_or_delete(event):
            return {"ok": True, "state": "NO_SUBMIT", "reason": "EDIT_IGNORED"}
        contract = slack_event_contract(event_id, event)
        if not contract["channel"] or not contract["message_ts"]:
            return {"ok": False, "state": "NO_SUBMIT", "reason": "INCOMPLETE_EVENT"}
        if is_own_connector_message(event, self.bot_user_id):
            return {"ok": True, "state": "ECHO_SUPPRESSED"}
        client_msg_id = str(event.get("client_msg_id") or "")
        if client_msg_id and self.store.owns_client_msg_id(client_msg_id):
            return {"ok": True, "state": "ECHO_SUPPRESSED", "reason": "OWN_RECEIPT"}
        thread_ts = contract["thread_ts"]
        owned = self.store.owns_thread(contract["channel"], thread_ts)
        if event.get("type") == "app_mention":
            self.store.remember_thread(contract["channel"], thread_ts, contract["message_ts"])
        elif event.get("type") == "message" and not owned:
            return {"ok": True, "state": "NO_SUBMIT", "reason": "NOT_OWNED_THREAD"}
        if not isinstance(contract["text"], str):
            return {"ok": False, "state": "NO_SUBMIT", "reason": "INCOMPLETE_EVENT"}
        if not contract["text"].strip() and not contract["files"]:
            return {"ok": False, "state": "NO_SUBMIT", "reason": "EMPTY_TEXT"}
        claim = self.store.claim(
            event_id,
            contract["channel"],
            contract["message_ts"],
            thread_ts,
            contract["author"],
            contract["text"],
            has_files=bool(contract["files"]),
        )
        if claim.disposition == "EVENT_ID_COLLISION":
            return {"ok": True, "state": "EVENT_ID_COLLISION", "submit": False}
        if claim.disposition == "SOURCE_COLLAPSE":
            return {"ok": True, "state": "SOURCE_COLLAPSE", "event_id": claim.event_id, "submit": False}
        if claim.disposition == "RETRY_DUPLICATE":
            row = self.store.get(event_id)
            if row is None:
                return {"ok": True, "state": "RETRY_DUPLICATE", "submit": False}
            if row.phase in {"DELIVERED", "ECHO_SUPPRESSED", "NO_SUBMIT", "FAILED", "EVENT_ID_COLLISION"}:
                return {"ok": True, "state": row.phase, "submit": False}
            if row.phase in POST_SUBMIT_PHASES:
                return self._resume_output_only(row)
            return self._run_claimed(event_id, contract)
        return self._run_claimed(event_id, contract)

    def recover_pending(self) -> int:
        recovered = 0
        for item in self.store.pending():
            try:
                if item.phase in POST_SUBMIT_PHASES or item.phase == "JOB_PERSISTED":
                    result = self._resume_output_only(item)
                else:
                    result = self._resume_pre_submit(item)
            except Exception:
                continue
            if result.get("state") in {"DELIVERED", "DELIVERY_UNKNOWN", "FAILED", "NO_SUBMIT"}:
                recovered += 1
        return recovered

    def _run_claimed(self, event_id: str, contract: dict[str, Any]) -> dict[str, Any]:
        packet = self._intake(event_id, contract)
        if packet.get("state") == "ECHO_PROCESSED" or packet.get("connector", {}).get("post_reply") is False:
            self.store.set_phase(event_id, "ECHO_SUPPRESSED")
            return {"ok": True, "state": "ECHO_SUPPRESSED", "task_id": packet.get("task_id")}
        if packet.get("connector", {}).get("post_reply") and packet.get("slack_reply"):
            self._post_status(event_id, contract, str(packet["slack_reply"]), phase="status")
        grokcom = packet.get("grokcom") or {}
        executor_job = grokcom.get("executor_job") or {}
        task_id = str(packet.get("task_id") or "")
        job_id = str(executor_job.get("job_id") or "")
        run_key = str(executor_job.get("run_key") or grokcom.get("run_key") or "")
        durable_path = str(executor_job.get("durable_path") or (f"wake_jobs/{job_id}.json" if job_id else ""))
        self.store.set_phase(
            event_id,
            "JOB_PERSISTED",
            task_id=task_id,
            job_id=job_id,
            run_key=run_key,
            durable_path=durable_path,
        )
        arguments = executor_job.get("arguments")
        if not isinstance(arguments, dict):
            self.store.set_phase(event_id, "FAILED")
            return {"ok": False, "state": "FAILED", "reason": "NO_EXECUTOR_JOB"}
        submitted = self._fire_once(event_id, job_id, arguments)
        if submitted["state"] in {"FIRE_ACTION_UNKNOWN", "FAILED"}:
            self.store.set_phase(event_id, submitted["state"])
            return submitted
        return self._observe_and_deliver(event_id, contract, packet, submitted)

    def _intake(self, event_id: str, contract: dict[str, Any]) -> dict[str, Any]:
        self.work_log.append("mcp:route_grokcom_revenue_work")
        event = {
            "event_id": contract["event_id"],
            "channel": contract["channel"],
            "message_ts": contract["message_ts"],
            "thread_ts": contract["thread_ts"],
            "author": contract["author"],
            "text": contract["text"],
            "files": contract.get("files") or [],
        }
        if contract.get("connector_origin"):
            event["connector_origin"] = contract["connector_origin"]
        packet = self.mcp.call_tool("route_grokcom_revenue_work", {"stage": "INTAKE", "mode": "AUTO", "event": event})
        self.store.set_phase(event_id, "INTAKE", task_id=str(packet.get("task_id") or ""))
        return packet

    def _fire_once(self, event_id: str, job_id: str, arguments: dict[str, Any]) -> dict[str, Any]:
        row = self.store.get(event_id)
        if row and row.phase in POST_SUBMIT_PHASES:
            return {"ok": True, "state": "SUBMITTED", "job_id": job_id, "submit": False}
        inspected = self._inspect_job(job_id)
        if inspected is not None:
            self.store.set_phase(event_id, "SUBMITTED")
            return {"ok": True, "state": "SUBMITTED", "job_id": job_id, "submit": False, "inspected": True}
        try:
            self.work_log.append("mcp:fire_action")
            self.store.increment_fire_action(event_id)
            result = self.mcp.call_tool("fire_action", arguments)
        except Exception as exc:
            inspected = self._inspect_job(job_id)
            if inspected is not None:
                self.store.set_phase(event_id, "SUBMITTED")
                return {"ok": True, "state": "SUBMITTED", "job_id": job_id, "submit": False, "inspected": True}
            if _is_ambiguous(exc):
                self.store.set_phase(event_id, "FIRE_ACTION_UNKNOWN")
                return {"ok": False, "state": "FIRE_ACTION_UNKNOWN", "job_id": job_id, "submit": False}
            self.store.set_phase(event_id, "FAILED")
            return {"ok": False, "state": "FAILED", "job_id": job_id}
        self.store.set_phase(event_id, "SUBMITTED")
        return {"ok": True, "state": "SUBMITTED", "job_id": job_id, "submit": True, "result": result}

    def _inspect_job(self, job_id: str) -> dict[str, Any] | None:
        if not job_id:
            return None
        try:
            sha = self.github.current_main_sha()
            blob = self.github.read_path(f"wake_jobs/{job_id}.json", sha)
        except (FileNotFoundError, BridgeError, OSError):
            return None
        try:
            job = json.loads(blob.decode("utf-8"))
        except (UnicodeError, json.JSONDecodeError):
            return None
        if isinstance(job, dict):
            return job
        return None

    def _observe_and_deliver(
        self,
        event_id: str,
        contract: dict[str, Any],
        packet: dict[str, Any],
        submitted: dict[str, Any],
    ) -> dict[str, Any]:
        self.store.set_phase(event_id, "OBSERVING")
        job_id = str(submitted.get("job_id") or packet.get("grokcom", {}).get("executor_job", {}).get("job_id") or "")
        job = None
        for attempt in range(self.poll_budget):
            job = self._inspect_job(job_id)
            if job and _job_is_terminal(job):
                break
            if self.grok_provider is not None:
                # Requester never clicks grok.com. Provider submission stays
                # behind PREPARE_SUBMISSION on the existing executor road.
                pass
            self.sleeper(min(2 ** attempt, 8) if attempt else 0)
        if job is None or not _job_is_terminal(job):
            return {"ok": True, "state": "OBSERVING", "job_id": job_id, "task_id": packet.get("task_id")}
        if _job_submission_open(job):
            return {"ok": True, "state": "OBSERVING", "reason": "PREPARE_SUBMISSION_PENDING", "job_id": job_id}
        capture = _job_capture(job)
        conversation_url = canonical_grok_url(str(capture.get("conversation_url") or ""))
        rid = conversation_url.rsplit("/", 1)[-1] if conversation_url else ""
        run_key = str(capture.get("run_key") or packet.get("grokcom", {}).get("run_key") or "")
        if run_key and packet.get("grokcom", {}).get("run_key") and run_key != packet["grokcom"]["run_key"]:
            self.store.set_phase(event_id, "FAILED")
            return {"ok": False, "state": "FAILED", "reason": "RUN_KEY_MISMATCH"}
        self.store.set_phase(event_id, "RESULT", conversation_rid=rid, run_key=run_key)
        artifact = {
            "run_key": run_key,
            "conversation_url": conversation_url,
            "origin": capture.get("origin") or {
                "task_id": packet.get("task_id"),
                "session_id": contract["event_id"],
                "thread_id": contract["thread_ts"],
                "event_id": contract["event_id"],
            },
            "completion_state": capture.get("completion_state") or "COMPLETED",
        }
        if contract.get("text"):
            self.work_log.append("mcp:route_grokcom_revenue_work:GROKCOM_RESULT")
            result_packet = self.mcp.call_tool("route_grokcom_revenue_work", {
                "stage": "GROKCOM_RESULT",
                "event": {
                    "event_id": contract["event_id"],
                    "channel": contract["channel"],
                    "message_ts": contract["message_ts"],
                    "thread_ts": contract["thread_ts"],
                    "author": contract["author"],
                    "text": contract["text"],
                },
                "artifact": artifact,
            })
            if result_packet.get("connector", {}).get("post_reply") and result_packet.get("slack_reply"):
                self._post_status(event_id, contract, str(result_packet["slack_reply"]), phase="built")
        envelope = _slack_receipt_envelope(capture, contract, packet, conversation_url)
        delivered = self._deliver_result(event_id, contract, envelope)
        landed = self._maybe_landed(event_id, contract, packet, capture, conversation_url)
        if delivered.state == "DELIVERY_UNKNOWN":
            self.store.set_phase(event_id, "DELIVERY_UNKNOWN")
            return {"ok": True, "state": "DELIVERY_UNKNOWN", "task_id": packet.get("task_id"), "job_id": job_id, "delivery_owner": FINAL_DELIVERY_OWNER, "run_key": run_key, "conversation_url": conversation_url}
        if delivered.state != "SENT":
            self.store.set_phase(event_id, "DELIVERING")
            return {"ok": True, "state": "DELIVERING", "task_id": packet.get("task_id"), "job_id": job_id, "delivery_owner": FINAL_DELIVERY_OWNER}
        self.store.set_phase(event_id, "DELIVERED", result_id=str(envelope.get("dedupe_key") or ""))
        row = self.store.get(event_id)
        return {
            "ok": True,
            "state": "DELIVERED",
            "task_id": packet.get("task_id"),
            "job_id": job_id,
            "run_key": run_key,
            "conversation_url": conversation_url,
            "delivery_owner": FINAL_DELIVERY_OWNER,
            "landed": landed,
            "fire_action_calls": 0 if row is None else row.fire_action_calls,
        }

    def _resume_pre_submit(self, item: PendingWork) -> dict[str, Any]:
        contract = {
            "event_id": item.event_id,
            "channel": item.channel,
            "message_ts": item.message_ts,
            "thread_ts": item.thread_ts,
            "author": item.author,
            "text": "",
            "files": [],
        }
        # Recovery never replays prompt bytes from SQLite; INTAKE is
        # reconstructed from stable ids only when the orchestrator still
        # has the live Slack event. After JOB_PERSISTED, fire_action is
        # inspected rather than resent blindly.
        if item.phase == "JOB_PERSISTED" and item.job_id:
            inspected = self._inspect_job(item.job_id)
            if inspected is not None:
                self.store.set_phase(item.event_id, "SUBMITTED")
                packet = {"task_id": item.task_id, "grokcom": {"run_key": item.run_key, "executor_job": {"job_id": item.job_id, "run_key": item.run_key, "durable_path": item.durable_path}}, "connector": {"post_reply": False}}
                return self._observe_and_deliver(item.event_id, contract, packet, {"job_id": item.job_id, "state": "SUBMITTED"})
            return {"ok": True, "state": "JOB_PERSISTED", "reason": "WAITING_JOB_RECORD"}
        return {"ok": True, "state": item.phase}

    def _resume_output_only(self, item: PendingWork) -> dict[str, Any]:
        if self.grok_provider is not None:
            raise AssertionError("recovery must not invoke a provider after SUBMITTING")
        contract = {
            "event_id": item.event_id,
            "channel": item.channel,
            "message_ts": item.message_ts,
            "thread_ts": item.thread_ts,
            "author": item.author,
            "text": "",
            "files": [],
        }
        packet = {
            "task_id": item.task_id,
            "grokcom": {
                "run_key": item.run_key,
                "executor_job": {"job_id": item.job_id, "run_key": item.run_key, "durable_path": item.durable_path},
            },
            "connector": {"post_reply": False},
        }
        return self._observe_and_deliver(item.event_id, contract, packet, {"job_id": item.job_id, "state": "SUBMITTED"})

    def _post_status(self, event_id: str, contract: dict[str, Any], text: str, *, phase: str) -> SlackSendResult:
        pieces = chunk_text(text)
        last = SlackSendResult("FAILED")
        for index, piece in enumerate(pieces):
            last = self.sink.post_chunk(
                contract["channel"],
                contract["thread_ts"],
                piece,
                event_id=event_id,
                phase=phase,
                index=index,
                count=len(pieces),
            )
            if last.state != "SENT":
                return last
        return last

    def _deliver_result(self, event_id: str, contract: dict[str, Any], envelope: dict[str, Any]) -> SlackSendResult:
        if self.executor_slack is not None:
            # Executor automation is not the final Slack owner.
            pass
        message = str(envelope.get("message") or "")
        pieces = chunk_text(message)
        last = SlackSendResult("SENT")
        for index, piece in enumerate(pieces):
            last = self.sink.post_chunk(
                str(envelope.get("channel") or contract["channel"]),
                str(envelope.get("thread_ts") or contract["thread_ts"]),
                piece,
                event_id=event_id,
                phase="result",
                index=index,
                count=len(pieces),
            )
            if last.state != "SENT":
                return last
        return last

    def _maybe_landed(
        self,
        event_id: str,
        contract: dict[str, Any],
        packet: dict[str, Any],
        capture: dict[str, Any],
        conversation_url: str,
    ) -> dict[str, Any]:
        result_id = str(capture.get("result_id") or capture.get("commons_post_id") or "")
        main_sha = ""
        try:
            main_sha = self.github.current_main_sha()
        except BridgeError:
            return {"state": "LANDED_BLOCKED", "reason": "MAIN_SHA_UNAVAILABLE"}
        if not conversation_url:
            return {"state": "LANDED_BLOCKED", "reason": "MISSING_GROK_URL"}
        if not result_id:
            return {"state": "LANDED_BLOCKED", "reason": "MISSING_RESULT_ID"}
        path = f"p/{result_id}.md"
        try:
            blob = self.github.read_path(path, main_sha)
        except (FileNotFoundError, BridgeError):
            return {"state": "LANDED_BLOCKED", "reason": "RESULT_NOT_ON_MAIN", "sha": main_sha}
        digest = _sha256_bytes(blob)
        expected = str(capture.get("result_sha256") or "")
        if expected and expected != digest:
            return {"state": "LANDED_BLOCKED", "reason": "RESULT_HASH_MISMATCH", "sha": main_sha}
        landing = capture.get("landing") if isinstance(capture.get("landing"), dict) else None
        if landing:
            blobs = landing.get("blobs") or {}
            if isinstance(blobs, dict):
                for rel, want in blobs.items():
                    try:
                        got = _sha256_bytes(self.github.read_path(str(rel), main_sha))
                    except (FileNotFoundError, BridgeError):
                        return {"state": "LANDED_BLOCKED", "reason": "BLOB_NOT_ON_MAIN", "path": rel, "sha": main_sha}
                    if got != str(want):
                        return {"state": "LANDED_BLOCKED", "reason": "BLOB_HASH_MISMATCH", "path": rel, "sha": main_sha}
        task_id = str(packet.get("task_id") or "")
        text = f"LANDED {task_id} | main {main_sha[:12]} | {conversation_url} | {path}"
        posted = self._post_status(event_id, contract, text, phase="landed")
        return {"state": "LANDED" if posted.state == "SENT" else posted.state, "sha": main_sha, "path": path, "sha256": digest}


def _is_ambiguous(exc: Exception) -> bool:
    if isinstance(exc, TimeoutError):
        return True
    name = type(exc).__name__.casefold()
    return "timeout" in name or "timeout" in str(exc).casefold()


def _job_is_terminal(job: dict[str, Any]) -> bool:
    status = str(job.get("status") or "").upper()
    if status in {"DONE", "FAILED", "CANCELLED", "EXPIRED"}:
        return True
    checkpoint = job.get("checkpoint") if isinstance(job.get("checkpoint"), dict) else {}
    execution = checkpoint.get("execution") if isinstance(checkpoint.get("execution"), dict) else {}
    return str(execution.get("submission_state") or "") in {"RESULT_CAPTURED"} or str(execution.get("state") or "") in {"DONE", "RESULT_CAPTURED"}


def _job_submission_open(job: dict[str, Any]) -> bool:
    checkpoint = job.get("checkpoint") if isinstance(job.get("checkpoint"), dict) else {}
    execution = checkpoint.get("execution") if isinstance(checkpoint.get("execution"), dict) else {}
    state = str(execution.get("submission_state") or "")
    return state in {"NOT_SUBMITTED", "CAPTURE_STARTED"}


def _job_capture(job: dict[str, Any]) -> dict[str, Any]:
    checkpoint = job.get("checkpoint") if isinstance(job.get("checkpoint"), dict) else {}
    result = checkpoint.get("result") if isinstance(checkpoint.get("result"), dict) else {}
    origin = checkpoint.get("origin") if isinstance(checkpoint.get("origin"), dict) else {}
    extras = job.get("capture") if isinstance(job.get("capture"), dict) else {}
    merged = dict(result)
    merged.update(extras)
    merged.setdefault("run_key", checkpoint.get("run_key"))
    merged.setdefault("origin", origin)
    if "conversation_url" not in merged:
        merged["conversation_url"] = checkpoint.get("conversation_url") or result.get("conversation_url")
    return merged


def _slack_receipt_envelope(
    capture: dict[str, Any],
    contract: dict[str, Any],
    packet: dict[str, Any],
    conversation_url: str,
) -> dict[str, Any]:
    existing = capture.get("slack_receipt")
    if isinstance(existing, dict) and existing.get("message"):
        envelope = dict(existing)
        envelope.setdefault("channel", contract["channel"])
        envelope.setdefault("thread_ts", contract["thread_ts"])
        envelope.setdefault("delivery_owner", FINAL_DELIVERY_OWNER)
        return envelope
    task_id = str(packet.get("task_id") or "")
    rid = conversation_url.rsplit("/", 1)[-1] if conversation_url else ""
    result = capture.get("exact_final_result")
    body = capture.get("receipt_message")
    if not isinstance(body, str) or not body:
        lines = [
            f"GROK RESULT — {task_id}",
            f"conversation: {conversation_url}",
            f"run_key: {capture.get('run_key') or ''}",
            f"rid: {rid}",
            f"delivery_owner: {FINAL_DELIVERY_OWNER}",
        ]
        if isinstance(result, str) and result:
            lines.extend(["lossless_result:", result])
        body = "\n".join(lines)
    return {
        "channel": contract["channel"],
        "thread_ts": contract["thread_ts"],
        "dedupe_key": str(capture.get("result_id") or task_id or contract["event_id"]),
        "message": body,
        "delivery_owner": FINAL_DELIVERY_OWNER,
    }


def acknowledge_then_schedule(
    envelope_id: str,
    event_id: str,
    event: dict[str, Any],
    *,
    ack: Callable[[str], None],
    schedule: Callable[[str, dict[str, Any]], None],
    order: list[str] | None = None,
) -> None:
    """ACK Slack immediately, then schedule model work. Order is the contract."""
    if order is not None:
        order.append("ack")
    ack(envelope_id)
    if order is not None:
        order.append("schedule")
    schedule(event_id, event)


def doctor(
    args: argparse.Namespace,
    *,
    env: dict[str, str] | None = None,
    mcp: Any | None = None,
    github: Any | None = None,
    store_factory: Callable[[Path], BridgeStore] | None = None,
) -> tuple[int, dict[str, Any]]:
    source = env if env is not None else os.environ
    presence = credential_presence(source)
    report: dict[str, Any] = {
        "schema": SCHEMA,
        "state": "NOT_READY",
        "slack_bot_token": presence["SLACK_BOT_TOKEN"],
        "slack_app_token": presence["SLACK_APP_TOKEN"],
        "state_db": {"path": str(args.state_db), "usable": False},
        "mcp": {"url": getattr(args, "mcp_url", DEFAULT_MCP_URL), "initialize": False},
        "github_readback": {"ok": False},
        "secrets_in_config": False,
        "socket_mode": True,
        "dm_scope": False,
        "final_delivery_owner": FINAL_DELIVERY_OWNER,
        "ready": False,
    }
    missing = presence["SLACK_BOT_TOKEN"] == "missing" or presence["SLACK_APP_TOKEN"] == "missing"
    if missing:
        report["state"] = "RUNTIME_UNCONFIGURED"
    try:
        factory = store_factory or BridgeStore
        store = factory(Path(args.state_db))
        store.close()
        report["state_db"]["usable"] = True
    except Exception as exc:
        report["state_db"]["error"] = type(exc).__name__
    client = mcp or CommonsMcpClient(getattr(args, "mcp_url", DEFAULT_MCP_URL))
    try:
        client.initialize()
        names = client.tools_list()
        report["mcp"] = {
            "url": getattr(client, "url", DEFAULT_MCP_URL),
            "initialize": True,
            "tools": names,
            "has_route_grokcom_revenue_work": "route_grokcom_revenue_work" in names,
            "has_fire_action": "fire_action" in names,
        }
    except Exception as exc:
        report["mcp"]["error"] = type(exc).__name__
    reader = github or GitHubReadback()
    try:
        sha = reader.current_main_sha()
        reader.read_path("carriers/catalog.json", sha)
        report["github_readback"] = {"ok": True, "main_sha": sha}
    except Exception as exc:
        report["github_readback"] = {"ok": False, "error": type(exc).__name__}
    mcp_ok = bool(report["mcp"].get("initialize") and report["mcp"].get("has_route_grokcom_revenue_work") and report["mcp"].get("has_fire_action"))
    ready = (
        not missing
        and report["state_db"]["usable"]
        and mcp_ok
        and bool(report["github_readback"].get("ok"))
        and not report["secrets_in_config"]
    )
    report["ready"] = ready
    if ready:
        report["state"] = "READY"
    elif not missing:
        report["state"] = "NOT_READY"
    return (0 if ready else 2, report)


def serve(args: argparse.Namespace) -> int:
    presence = credential_presence()
    if presence["SLACK_BOT_TOKEN"] == "missing" or presence["SLACK_APP_TOKEN"] == "missing":
        payload = {"state": "RUNTIME_UNCONFIGURED", "slack_bot_token": presence["SLACK_BOT_TOKEN"], "slack_app_token": presence["SLACK_APP_TOKEN"]}
        print(json.dumps(payload, sort_keys=True))
        return 2
    try:
        from slack_sdk import WebClient
        from slack_sdk.socket_mode import SocketModeClient
        from slack_sdk.socket_mode.response import SocketModeResponse
    except ImportError as exc:
        raise BridgeError("install integrations/grok_slack/requirements.txt first") from exc
    bot_token = os.environ.get("SLACK_BOT_TOKEN")
    app_token = os.environ.get("SLACK_APP_TOKEN")
    store = BridgeStore(Path(args.state_db))
    mcp = CommonsMcpClient(getattr(args, "mcp_url", DEFAULT_MCP_URL))
    github = GitHubReadback()
    web_client = WebClient(token=bot_token)
    identity = web_client.auth_test()
    bot_user_id = identity.get("user_id")
    sink = SlackTransport(web_client, store)
    bridge = GrokSlackBridge(store, mcp, github, sink, bot_user_id=str(bot_user_id) if bot_user_id else None)
    bridge.recover_pending()
    executor = ThreadPoolExecutor(max_workers=args.workers, thread_name_prefix="grok-slack")
    socket_client = SocketModeClient(app_token=app_token, web_client=web_client)
    recovery_stop = threading.Event()

    def recover_loop() -> None:
        while not recovery_stop.is_set():
            bridge.recover_pending()
            recovery_stop.wait(args.recovery_interval)

    def process_request(client: Any, request: Any) -> None:
        if request.type != "events_api":
            return
        client.send_socket_mode_response(SocketModeResponse(envelope_id=request.envelope_id))
        payload = request.payload or {}
        event = payload.get("event") or {}
        event_id = payload.get("event_id")
        if not isinstance(event_id, str) or not isinstance(event, dict):
            return
        executor.submit(bridge.handle_event, event_id, event)

    socket_client.socket_mode_request_listeners.append(process_request)
    recovery_thread = threading.Thread(target=recover_loop, name="grok-slack-recovery", daemon=True)
    recovery_thread.start()
    socket_client.connect()
    print(json.dumps({"ready": True, "state_db": str(args.state_db), "delivery_owner": FINAL_DELIVERY_OWNER}))
    try:
        threading.Event().wait()
    except KeyboardInterrupt:
        return 0
    finally:
        recovery_stop.set()
        recovery_thread.join(timeout=max(2.0, args.recovery_interval + 1))
        socket_client.disconnect()
        executor.shutdown(wait=True, cancel_futures=False)
        store.close()
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("serve", "doctor"), nargs="?", default="serve")
    parser.add_argument("--json", action="store_true", help="doctor prints JSON (always on for doctor)")
    parser.add_argument("--state-db", type=Path, default=DEFAULT_STATE_DB)
    parser.add_argument("--mcp-url", default=DEFAULT_MCP_URL)
    parser.add_argument("--delivery-deadline", type=float, default=900.0)
    parser.add_argument("--recovery-interval", type=float, default=15.0)
    parser.add_argument("--workers", type=int, default=4)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "doctor":
            code, report = doctor(args)
            print(json.dumps(report, indent=2, sort_keys=True))
            return code
        return serve(args)
    except RuntimeUnconfigured:
        print(json.dumps({"state": "RUNTIME_UNCONFIGURED"}, sort_keys=True))
        return 2
    except BridgeError as exc:
        print(f"grok-slack: {type(exc).__name__}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
