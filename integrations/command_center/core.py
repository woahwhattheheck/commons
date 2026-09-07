"""Shared command-center state and exact-operation journal; Python stdlib only.

Tool arguments/results are never written to disk. A repeated tool operation returns
its durable status, not its original result. Unknown transport outcomes are never
automatically replayed. Every peer and the human use the same methods.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import sqlite3
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from contextlib import contextmanager
from pathlib import Path


class CoreError(Exception):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = int(status)
        self.message = str(message)


def _now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _json(value):
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True,
                          separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError):
        raise CoreError(400, "Payload must contain finite JSON values.") from None


def _age(timestamp):
    if not timestamp:
        return float("inf")
    try:
        return time.time() - datetime.fromisoformat(
            timestamp.replace("Z", "+00:00")).timestamp()
    except (ValueError, TypeError):
        return float("inf")


_SECRET_KEYS = re.compile(
    r"^(?:password|passwd|secret|token|api[_-]?key|authorization|cookie|"
    r"private[_-]?key|recovery[_-]?code|credential[_-]?value|access[_-]?token|"
    r"refresh[_-]?token|client[_-]?secret)$", re.I)
_SECRET_TEXT = re.compile(
    r"(?:\bsk-[A-Za-z0-9_-]{12,}|\b(?:ghp|gho|ghu|ghs|github_pat)_[A-Za-z0-9_-]{8,}"
    r"|\bxox[bpars]-[A-Za-z0-9-]{8,}"
    r"|\bBearer\s+[A-Za-z0-9._~+/-]{8,}"
    r"|-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----"
    r"|\b(?:password|api[_-]?key|access[_-]?token|refresh[_-]?token)"
    r"\s*[:=]\s*[^\s,;]+)", re.I)


def _text(value, limit=4000):
    if value is None:
        return ""
    if not isinstance(value, (str, int, float, bool)):
        raise CoreError(400, "Expected a scalar metadata value.")
    return _SECRET_TEXT.sub("[redacted]", str(value))[:limit]


def _identifier(value, label="id"):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_.:/-]{1,180}", value):
        raise CoreError(400, label + " must be a nonempty stable identifier.")
    return value


def _no_secret_fields(value):
    if isinstance(value, dict):
        for key, item in value.items():
            if _SECRET_KEYS.fullmatch(str(key)):
                raise CoreError(400, "Credential values belong in the shared secure facility, not metadata.")
            _no_secret_fields(item)
    elif isinstance(value, list):
        for item in value:
            _no_secret_fields(item)


def _metadata(value, depth=0):
    """Bounded JSON metadata with common credential forms redacted."""
    if depth > 8:
        raise CoreError(400, "Metadata is nested too deeply.")
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        if not math.isfinite(value):
            raise CoreError(400, "Metadata numbers must be finite.")
        return value
    if isinstance(value, str):
        return _text(value)
    if isinstance(value, list):
        if len(value) > 100:
            raise CoreError(400, "Metadata lists are limited to 100 entries.")
        return [_metadata(item, depth + 1) for item in value]
    if isinstance(value, dict):
        if len(value) > 100:
            raise CoreError(400, "Metadata objects are limited to 100 fields.")
        return {_text(key, 120): _metadata(item, depth + 1)
                for key, item in value.items()}
    raise CoreError(400, "Unsupported metadata value.")


def _url(value, gateway=False):
    value = _text(value, 4000).strip()
    if not value:
        return ""
    parsed = urllib.parse.urlsplit(value)
    if parsed.scheme not in ("http", "https") or not parsed.hostname or parsed.username or parsed.password:
        raise CoreError(400, "URLs must be HTTP(S) without embedded credentials.")
    if gateway and (parsed.query or parsed.fragment):
        raise CoreError(400, "A runtime gateway URL cannot contain a query or fragment.")
    for key, _ in urllib.parse.parse_qsl(parsed.query):
        if _SECRET_KEYS.fullmatch(key):
            raise CoreError(400, "Credential-bearing URLs cannot be stored as metadata.")
    if "[redacted]" in value:
        raise CoreError(400, "Credential-bearing URLs cannot be stored as metadata.")
    return value.rstrip("/") if gateway else value


def _public_tool(tool, runtime_id):
    """Preserve callable schema, omit provider examples/default values."""
    def clean(value):
        if isinstance(value, dict):
            return {str(k): clean(v) for k, v in value.items()
                    if k not in ("default", "example", "examples")}
        if isinstance(value, list):
            return [clean(v) for v in value]
        if isinstance(value, str):
            return _text(value, 30000)
        return value

    if not isinstance(tool, dict) or not isinstance(tool.get("name"), str):
        return None
    return {
        "name": _text(tool["name"], 300),
        "description": _text(tool.get("description", ""), 30000),
        "inputSchema": clean(tool.get("inputSchema", tool.get("input_schema", {}))),
        "annotations": clean(tool.get("annotations", {})),
        "runtime_id": runtime_id,
    }


class CommandCenter:
    SOURCE_TTL = 300
    RUNTIME_TTL = 60
    SOURCE_PATHS = (
        ("resource-ledger", "ground/RESOURCE_LEDGER.json", False),
        ("connected-capabilities", "inventory/resources/connected_capabilities.json", False),
        ("titan", "revenue/kaggriculture/command-center-adapter/adapter.json", True),
    )

    def __init__(self, state_dir: Path, gateway_url="http://127.0.0.1:8878",
                 repo="woahwhattheheck/commons", fetcher=None):
        if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo):
            raise CoreError(400, "Expected an owner/repository reference.")
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.database = self.state_dir / "command-center.sqlite3"
        self.repo = repo
        self.gateway_url = _url(gateway_url, gateway=True)
        self.fetcher = fetcher or self._fetch_http
        with self._db() as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.executescript("""
                CREATE TABLE IF NOT EXISTS sources (
                    id TEXT PRIMARY KEY, path TEXT, sha TEXT, observed_at TEXT,
                    attempted_at TEXT, status TEXT, error TEXT, data TEXT
                );
                CREATE TABLE IF NOT EXISTS records (
                    kind TEXT NOT NULL, id TEXT NOT NULL, data TEXT NOT NULL,
                    PRIMARY KEY(kind,id)
                );
                CREATE TABLE IF NOT EXISTS operations (
                    id TEXT PRIMARY KEY, payload_hash TEXT NOT NULL, kind TEXT NOT NULL,
                    name TEXT NOT NULL, runtime TEXT, status TEXT NOT NULL,
                    started_at TEXT NOT NULL, finished_at TEXT, summary TEXT, error TEXT
                );
                CREATE TABLE IF NOT EXISTS moderation (
                    event_id TEXT PRIMARY KEY, hidden INTEGER NOT NULL,
                    reason TEXT NOT NULL, peer TEXT NOT NULL, observed_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS source_events (
                    id TEXT PRIMARY KEY, observed_at TEXT NOT NULL, data TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS source_events_observed
                    ON source_events(observed_at DESC);
            """)
            initial = {"id": "shared-equipment", "label": "Shared equipment",
                       "gateway_url": self.gateway_url, "observed_at": _now()}
            db.execute("INSERT OR IGNORE INTO records(kind,id,data) VALUES(?,?,?)",
                       ("runtimes", initial["id"], _json(initial)))

    @contextmanager
    def _db(self):
        db = sqlite3.connect(str(self.database), timeout=30)
        db.row_factory = sqlite3.Row
        try:
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    @staticmethod
    def _fetch_http(method, url, payload=None):
        data = None if payload is None else _json(payload).encode("utf-8")
        request = urllib.request.Request(
            url, data=data, method=method,
            headers={"Accept": "application/json", "User-Agent": "Commons-Command-Center/1",
                     "Content-Type": "application/json"})
        with urllib.request.urlopen(request, timeout=15) as response:
            raw = response.read(8 * 1024 * 1024 + 1)
            if len(raw) > 8 * 1024 * 1024:
                raise CoreError(502, "Provider response exceeded the size limit.")
            return json.loads(raw.decode("utf-8"))

    @staticmethod
    def _failure(exc):
        # Never persist str(exc), provider response bodies, request URLs, or headers.
        if isinstance(exc, urllib.error.HTTPError):
            return "HTTP " + str(exc.code)
        if isinstance(exc, CoreError):
            return "Provider request failed (" + str(exc.status) + ")"
        return "Provider request failed (" + type(exc).__name__ + ")"

    def _get_records(self, kind):
        with self._db() as db:
            return [json.loads(row["data"]) for row in db.execute(
                "SELECT data FROM records WHERE kind=? ORDER BY id", (kind,))]

    def _source(self, source_id):
        with self._db() as db:
            row = db.execute("SELECT * FROM sources WHERE id=?", (source_id,)).fetchone()
        if not row:
            return None
        result = dict(row)
        result["data"] = json.loads(result["data"]) if result["data"] else None
        return result

    def _save_source(self, source_id, path, sha, data=None, error=None, missing=False,
                     partial=False):
        previous = self._source(source_id)
        attempted_at = _now()
        if error:
            result = {
                "id": source_id, "path": path, "sha": previous["sha"] if previous else sha,
                "observed_at": attempted_at if partial else (previous["observed_at"] if previous else None),
                "attempted_at": attempted_at,
                "status": "degraded" if partial else (
                    "stale" if previous and previous["data"] is not None else
                    ("unavailable" if missing else "error")),
                "error": error, "data": data if data is not None else (previous["data"] if previous else None),
            }
        else:
            result = {"id": source_id, "path": path, "sha": sha,
                      "observed_at": attempted_at, "attempted_at": attempted_at,
                      "status": "live", "error": None, "data": data}
        with self._db() as db:
            db.execute("""INSERT INTO sources VALUES(?,?,?,?,?,?,?,?)
                ON CONFLICT(id) DO UPDATE SET path=excluded.path,sha=excluded.sha,
                observed_at=excluded.observed_at,attempted_at=excluded.attempted_at,
                status=excluded.status,error=excluded.error,data=excluded.data""",
                (result["id"], result["path"], result["sha"], result["observed_at"],
                 result["attempted_at"], result["status"], result["error"],
                 _json(result["data"]) if result["data"] is not None else None))
        self._append_source_event(result)
        return result

    def _append_source_event(self, source):
        """Retain immutable observation metadata and an exact source reference.

        Canonical document history stays at its pinned GitHub SHA; full documents
        are not copied into an ever-growing event mirror. Runtime observations
        retain only safe names/health metadata, never tool arguments or results.
        """
        source_id = source["id"]
        data = source.get("data")
        if source_id.startswith("runtime:"):
            source_url = source["path"]
            runtime_data = data if isinstance(data, dict) else {}
            snapshot = {
                "tool_names": [t["name"] for t in runtime_data.get("tools", [])],
                "health": runtime_data.get("health"),
                "tools_observed_at": runtime_data.get("tools_observed_at"),
                "health_observed_at": runtime_data.get("health_observed_at"),
                "tools_error": runtime_data.get("tools_error"),
                "health_error": runtime_data.get("health_error"),
            }
        elif source_id == "github-main":
            source_url = ("https://github.com/" + self.repo + "/commit/" + source["sha"]
                          if source.get("sha") else source["path"])
            snapshot = {"sha": source.get("sha"), "repo": self.repo}
        else:
            source_url = ("https://github.com/" + self.repo + "/blob/" +
                          source["sha"] + "/" + source["path"]) if source.get("sha") else ""
            snapshot = {"sha": source.get("sha"), "path": source["path"], "url": source_url}
        if data is not None:
            snapshot["content_sha256"] = hashlib.sha256(_json(data).encode("utf-8")).hexdigest()
        event = {
            "kind": "source", "source_id": source_id,
            "title": source_id + " — " + source["status"],
            "body": source["error"] or "Source observation refreshed.",
            "source_url": source_url, "observed_at": source["attempted_at"],
            "source_observed_at": source["observed_at"], "snapshot": snapshot,
            "source_status": source["status"],
        }
        event["id"] = "source-event:" + hashlib.sha256(_json(event).encode("utf-8")).hexdigest()[:32]
        with self._db() as db:
            db.execute("INSERT OR IGNORE INTO source_events VALUES(?,?,?)",
                       (event["id"], event["observed_at"], _json(event)))

    def _refresh_sources(self, force=False):
        head = self._source("github-main")
        if not force and head and _age(head["attempted_at"]) < self.SOURCE_TTL:
            return
        head_url = "https://api.github.com/repos/" + self.repo + "/commits/main"
        try:
            response = self.fetcher("GET", head_url)
            sha = response.get("sha") if isinstance(response, dict) else None
            if not isinstance(sha, str) or not re.fullmatch(r"[0-9a-fA-F]{40}", sha):
                raise CoreError(502, "GitHub did not return a valid commit SHA.")
            self._save_source("github-main", head_url, sha, {"sha": sha, "repo": self.repo})
        except Exception as exc:
            error = self._failure(exc)
            self._save_source("github-main", head_url, None, error=error)
            for source_id, path, _ in self.SOURCE_PATHS:
                self._save_source(source_id, path, None,
                                  error="Pinned main unavailable: " + error)
            return
        for source_id, path, optional in self.SOURCE_PATHS:
            url = "https://raw.githubusercontent.com/" + self.repo + "/" + sha + "/" + path
            try:
                data = self.fetcher("GET", url)
                if not isinstance(data, (dict, list)):
                    raise CoreError(502, "Canonical source must be a JSON object or array.")
                self._save_source(source_id, path, sha, data)
            except Exception as exc:
                missing = optional and isinstance(exc, urllib.error.HTTPError) and exc.code == 404
                self._save_source(source_id, path, sha, error=self._failure(exc), missing=missing)

    def _runtimes(self, force=False, runtime_id=None):
        results = []
        for runtime in self._get_records("runtimes"):
            if runtime_id is not None and runtime["id"] != runtime_id:
                continue
            source_id = "runtime:" + runtime["id"]
            snapshot = self._source(source_id)
            if force or not snapshot or _age(snapshot["attempted_at"]) >= self.RUNTIME_TTL:
                old = snapshot.get("data") if snapshot else None
                data = dict(old or {"tools": [], "health": None})
                errors, successes = [], 0
                for endpoint in ("tools", "health"):
                    url = runtime["gateway_url"] + ("/v1/tools" if endpoint == "tools" else "/health")
                    try:
                        response = self.fetcher("GET", url)
                        if endpoint == "tools":
                            raw_tools = response.get("tools") if isinstance(response, dict) else response
                            if not isinstance(raw_tools, list):
                                raise CoreError(502, "Runtime tool catalog must be a list.")
                            data["tools"] = [
                                t for t in (_public_tool(v, runtime["id"]) for v in raw_tools) if t]
                        else:
                            if not isinstance(response, dict):
                                raise CoreError(502, "Runtime health response must be an object.")
                            data["health"] = {key: _metadata(response[key]) for key in
                                ("ok", "status", "service", "version", "tool_count", "uptime_seconds")
                                if key in response}
                        data[endpoint + "_observed_at"] = _now()
                        data[endpoint + "_error"] = None
                        successes += 1
                    except Exception as exc:
                        error = self._failure(exc)
                        data[endpoint + "_error"] = error
                        errors.append(endpoint + ": " + error)
                # Each successful component is durable even if its sibling failed.
                snapshot = self._save_source(
                    source_id, runtime["gateway_url"], None, data=data,
                    error="; ".join(errors) if errors else None, partial=bool(successes))
            data = snapshot.get("data") or {}
            catalog_live = bool(data.get("tools_observed_at")) and not data.get("tools_error")
            results.append(dict(
                runtime, status=snapshot["status"], observed_at=snapshot["observed_at"],
                attempted_at=snapshot["attempted_at"], tools=data.get("tools", []),
                health=data.get("health"), catalog_live=catalog_live,
                tools_observed_at=data.get("tools_observed_at"),
                health_observed_at=data.get("health_observed_at"),
                tools_error=data.get("tools_error"), health_error=data.get("health_error"),
                error=snapshot["error"]))
        return results

    def tools(self):
        runtimes = self._runtimes(force=True)
        return {"tools": [tool for runtime in runtimes for tool in runtime["tools"]],
                "runtimes": runtimes}

    @staticmethod
    def _operation(row):
        item = dict(row)
        item.pop("payload_hash", None)
        item["operation_id"] = item["id"]
        item["runtime_id"] = item["runtime"]
        item["summary"] = json.loads(item["summary"]) if item.get("summary") else None
        return item

    def _reserve(self, operation_id, payload_hash, kind, name, runtime=None):
        with self._db() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT * FROM operations WHERE id=?", (operation_id,)).fetchone()
            if row:
                if row["payload_hash"] != payload_hash:
                    raise CoreError(409, "Operation ID already exists with different content.")
                return self._operation(row)
            db.execute("""INSERT INTO operations
                (id,payload_hash,kind,name,runtime,status,started_at)
                VALUES(?,?,?,?,?,'dispatching',?)""",
                (operation_id, payload_hash, kind, name, runtime, _now()))
        return None

    def _finish(self, operation_id, status, summary, error=None):
        with self._db() as db:
            db.execute("""UPDATE operations SET status=?,finished_at=?,summary=?,error=?
                WHERE id=?""", (status, _now(), _json(summary), error, operation_id))
            row = db.execute("SELECT * FROM operations WHERE id=?", (operation_id,)).fetchone()
        return self._operation(row)

    def call_tool(self, payload):
        if not isinstance(payload, dict):
            raise CoreError(400, "Tool request must be an object.")
        operation_id = _identifier(payload.get("operation_id"), "operation_id")
        name = _identifier(payload.get("name"), "name")
        runtime_id = _identifier(payload.get("runtime_id", "shared-equipment"), "runtime_id")
        arguments = payload.get("arguments", {})
        if not isinstance(arguments, dict):
            raise CoreError(400, "Tool arguments must be an object.")
        # The hash is the only persisted representation of arguments.
        semantic = {"runtime_id": runtime_id, "name": name, "arguments": arguments}
        payload_hash = hashlib.sha256(_json(semantic).encode("utf-8")).hexdigest()
        with self._db() as db:
            row = db.execute("SELECT * FROM operations WHERE id=?", (operation_id,)).fetchone()
        if row:
            if row["payload_hash"] != payload_hash:
                raise CoreError(409, "Operation ID already exists with different content.")
            return {"operation_id": operation_id, "status": row["status"], "replayed": True,
                    "result_available": False, "result": None, "retry_blocked": True,
                    "operation": self._operation(row)}
        runtime = next(iter(self._runtimes(force=True, runtime_id=runtime_id)), None)
        if runtime is None:
            raise CoreError(404, "Runtime is not registered.")
        if not runtime["catalog_live"]:
            raise CoreError(503, "Runtime discovery is unavailable; no tool call was sent.")
        if name not in {tool["name"] for tool in runtime["tools"]}:
            raise CoreError(404, "Tool is not in the current runtime catalog.")
        existing = self._reserve(operation_id, payload_hash, "tool", name, runtime_id)
        if existing:
            return {"operation_id": operation_id, "status": existing["status"], "replayed": True,
                    "result_available": False, "result": None, "retry_blocked": True,
                    "operation": existing}
        # Calling this center through its advertised equipment tools shares this
        # same journal. Namespace only a colliding inner metadata-operation ID;
        # preserve the original semantic hash, parent call_id and all service IDs.
        dispatch_arguments = arguments
        child_operation_id = None
        center_metadata_tools = {
            "command_center_focus", "command_center_session", "command_center_budget",
            "command_center_runtime", "command_center_janny", "command_center_note",
            "command_center_moderate",
        }
        if name in center_metadata_tools and arguments.get("operation_id") == operation_id:
            child_operation_id = "nested-" + hashlib.sha256(
                _json({"parent": operation_id, "name": name}).encode("utf-8")).hexdigest()[:40]
            dispatch_arguments = dict(arguments, operation_id=child_operation_id)
        child_summary = {"child_operation_id": child_operation_id} if child_operation_id else {}
        envelope = {"request_id": "command-center", "call_id": operation_id,
                    "name": name, "arguments": dispatch_arguments}
        try:
            result = self.fetcher("POST", runtime["gateway_url"] + "/v1/tools/call", envelope)
        except Exception as exc:
            operation = self._finish(operation_id, "uncertain",
                {"receipt_received": False, "automatic_retry": False, **child_summary},
                self._failure(exc))
            return {"operation_id": operation_id, "status": "uncertain", "replayed": False,
                    "result_available": False, "result": None, "retry_blocked": True,
                    "operation": operation}
        status = self._receipt_status(result, operation_id)
        failed = status == "failed"
        provider_refs = self._provider_refs(result)
        # Never journal provider text, arbitrary result keys, excerpts or arguments.
        operation = self._finish(operation_id, status,
                                 {"receipt_received": True, "provider_reported_error": failed,
                                  "execution_complete": status in ("succeeded", "failed", "cancelled"),
                                  "provider_refs": provider_refs, **child_summary})
        return {"operation_id": operation_id, "status": status, "replayed": False,
                "result_available": True, "result": result, "retry_blocked": True,
                "operation": operation}

    @staticmethod
    def _provider_refs(result):
        """Retain only bounded reconciliation handles, never arbitrary results."""
        keys = {"request_id", "provider_request_id", "run_id", "job_id", "session_id",
                "thread_id", "task_id", "operation_id", "artifact_id", "html_url", "url"}
        refs, seen = [], set()

        def keep(key, value, path):
            if len(refs) >= 40 or isinstance(value, bool) or value is None:
                return
            if key in ("url", "html_url"):
                if not isinstance(value, str):
                    return
                try:
                    value = _url(value)
                    parsed = urllib.parse.urlsplit(value)
                    # Never retain signed/callback/auth URLs or opaque query values.
                    safe_query_keys = {"page", "per_page", "tab", "line", "thread_ts", "cid"}
                    if not value or any(k not in safe_query_keys for k, _ in
                                        urllib.parse.parse_qsl(parsed.query)):
                        return
                    if parsed.fragment and not re.fullmatch(r"[A-Za-z0-9_.:-]{1,180}", parsed.fragment):
                        return
                except CoreError:
                    return
            else:
                if isinstance(value, int):
                    value = str(value)
                if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_.:/-]{1,240}", value):
                    return
                if _SECRET_TEXT.search(value):
                    return
            identity = (path, key, value)
            if identity not in seen:
                refs.append({"path": path + "." + key, "key": key, "value": value})
                seen.add(identity)

        def inspect(value, path="gateway", depth=0):
            if depth > 6 or len(refs) >= 40:
                return
            if isinstance(value, list):
                for index, item in enumerate(value[:10]):
                    inspect(item, path + "[" + str(index) + "]", depth + 1)
                return
            if not isinstance(value, dict):
                return
            for key in keys:
                if key in value:
                    keep(key, value[key], path)
            for key in ("result", "structuredContent", "data"):
                inspect(value.get(key), path + "." + key, depth + 1)
            content = value.get("content")
            for index, item in enumerate(content[:10] if isinstance(content, list) else []):
                if isinstance(item, dict) and item.get("type") == "text":
                    raw = item.get("text")
                    if isinstance(raw, str) and len(raw) < 1000000:
                        try:
                            inspect(json.loads(raw), path + ".content[" + str(index) + "].json", depth + 1)
                        except (ValueError, TypeError):
                            pass

        inspect(result)
        return refs

    @staticmethod
    def _receipt_status(result, operation_id=None):
        """Classify explicit receipts; transport acceptance is not completion."""
        flags = {"uncertain": False, "failed": False, "cancelled": False,
                 "pending": False, "explicit": False}
        pending = {"accepted", "pending", "queued", "running", "dispatching", "received",
                   "in_progress", "in-progress", "submitted", "started", "processing",
                   "scheduled", "received_pending_projection", "paused", "awaiting_input",
                   "needs_attention"}
        failed = {"failed", "failure", "error", "rejected", "denied"}
        cancelled = {"cancelled", "canceled", "aborted"}
        uncertain = {"uncertain", "unknown_outcome", "unknown", "interrupted",
                     "timeout", "timed_out", "lost_response"}
        completed = {"succeeded", "success", "completed", "complete", "done"}

        def inspect(value, depth=0):
            if depth > 6 or not isinstance(value, dict):
                return
            if isinstance(value.get("ok"), bool) or isinstance(value.get("isError"), bool):
                flags["explicit"] = True
            flags["uncertain"] |= value.get("uncertain") is True
            flags["failed"] |= value.get("isError") is True or value.get("ok") is False
            for key in ("state", "status"):
                label = value.get(key)
                if isinstance(label, str):
                    normalized = label.lower().strip()
                    flags["pending"] |= normalized in pending
                    flags["failed"] |= normalized in failed
                    flags["cancelled"] |= normalized in cancelled
                    flags["uncertain"] |= normalized in uncertain
                    flags["explicit"] |= normalized in (pending | failed | cancelled | uncertain | completed)
            for key in ("result", "structuredContent", "data"):
                inspect(value.get(key), depth + 1)
            for item in value.get("content", []) if isinstance(value.get("content"), list) else []:
                if isinstance(item, dict) and item.get("type") == "text":
                    text = item.get("text")
                    if isinstance(text, str) and len(text) < 1000000:
                        try:
                            inspect(json.loads(text), depth + 1)
                        except (ValueError, TypeError):
                            pass

        inspect(result)
        if isinstance(result, dict):
            if result.get("request_id") not in (None, "command-center"):
                flags["uncertain"] = True
            if operation_id is not None and result.get("call_id") not in (None, operation_id):
                flags["uncertain"] = True
        if flags["uncertain"] or not flags["explicit"]:
            return "uncertain"
        if flags["cancelled"]:
            return "cancelled"
        if flags["failed"]:
            return "failed"
        if flags["pending"]:
            return "pending"
        return "succeeded"

    def mutate(self, kind, payload):
        aliases = {"session": "sessions", "budget": "budgets", "runtime": "runtimes",
                   "feed/moderate": "moderate"}
        kind = aliases.get(kind, kind)
        if kind not in ("focus", "sessions", "budgets", "runtimes", "janny", "feed", "moderate"):
            raise CoreError(404, "Unknown metadata operation.")
        if not isinstance(payload, dict):
            raise CoreError(400, "Metadata request must be an object.")
        operation_id = _identifier(payload.get("operation_id"), "operation_id")
        _no_secret_fields(payload)
        body = {k: v for k, v in payload.items() if k != "operation_id"}
        # Validate all fields before opening the transaction.
        record_id, record, moderation = "current", None, None
        if kind == "focus":
            record = {key: _text(body.get(key, "")) for key in
                      ("objective", "next_action", "status", "notes")}
        elif kind == "sessions":
            item = body.get("session", body)
            if not isinstance(item, dict):
                raise CoreError(400, "session must be an object.")
            record_id = _identifier(item.get("id"), "session.id")
            keys = ("id", "label", "url", "provider", "model", "cpu", "ram_gib", "gpu",
                    "disk_gib", "disk_free_gib", "workspace", "observed_at", "status",
                    "objective", "resource_id", "origin", "capabilities", "tools", "egress",
                    "artifact_transport", "expires_at", "lifetime", "notes", "cost_source")
            record = {key: _metadata(item[key]) for key in keys if key in item}
            if "url" in record:
                record["url"] = _url(record["url"])
        elif kind == "budgets":
            item = body.get("budget", body)
            if not isinstance(item, dict):
                raise CoreError(400, "budget must be an object.")
            record_id = _identifier(item.get("id"), "budget.id")
            keys = ("id", "label", "limit", "used", "balance", "remaining", "committed",
                    "unit", "period", "observed_at",
                    "source_url", "provider", "kind", "currency", "notes")
            record = {key: _metadata(item[key]) for key in keys if key in item}
            for key in ("limit", "used", "balance", "remaining", "committed"):
                if key in record and record[key] is not None and (
                        isinstance(record[key], bool) or not isinstance(record[key], (int, float))
                        or record[key] < 0):
                    raise CoreError(400, key + " must be a nonnegative number or null.")
            if "source_url" in record:
                record["source_url"] = _url(record["source_url"])
            record.setdefault("kind", "manual_observation")
        elif kind == "runtimes":
            item = body.get("runtime", body)
            if not isinstance(item, dict):
                raise CoreError(400, "runtime must be an object.")
            record_id = _identifier(item.get("id"), "runtime.id")
            gateway_url = _url(item.get("gateway_url", ""), gateway=True)
            if not gateway_url:
                raise CoreError(400, "Runtime registration requires gateway_url.")
            record = {"id": record_id, "label": _text(item.get("label", record_id), 300),
                      "gateway_url": gateway_url}
        elif kind == "janny":
            record = {"peer": _text(body.get("peer", body.get("peer_id", "")), 300),
                      "status": _text(body.get("status", "active"), 100),
                      "responsibility": "Reversible moderation of the derived feed; no access grants."}
        elif kind == "feed":
            record_id = "note:" + operation_id
            source_url = _url(body.get("source_url", ""))
            record = {"id": record_id, "kind": "note",
                      "title": _text(body.get("title", "Operation note"), 300),
                      "body": _text(body.get("body", body.get("text", "")), 4000),
                      "source_url": source_url,
                      "source_ref": _text(body.get("source_ref", ""), 1000)}
        else:
            event_id = _identifier(body.get("event_id", body.get("item_id")), "event_id")
            hidden = body.get("hidden")
            if "hidden" not in body:
                legacy = body.get("action")
                if legacy == "hide":
                    hidden = True
                elif legacy == "restore":
                    hidden = False
            if not isinstance(hidden, bool):
                raise CoreError(400, "Moderation hidden must be a boolean.")
            reason = _text(body.get("reason", ""), 1000).strip()
            if not reason:
                raise CoreError(400, "Moderation needs a reason.")
            self.event(event_id)  # Originals remain addressable outside the latest feed view.
            moderation = {"event_id": event_id, "hidden": hidden,
                          "reason": reason, "peer": _text(body.get("peer", ""), 300)}
        payload_hash = hashlib.sha256(
            _json({"kind": kind, "content": body}).encode("utf-8")).hexdigest()
        with self._db() as db:
            db.execute("BEGIN IMMEDIATE")
            previous = db.execute("SELECT * FROM operations WHERE id=?", (operation_id,)).fetchone()
            if previous:
                if previous["payload_hash"] != payload_hash:
                    raise CoreError(409, "Operation ID already exists with different content.")
                return {"ok": True, "operation_id": operation_id, "replayed": True,
                        "operation": self._operation(previous)}
            timestamp = _now()
            if record is not None:
                record.setdefault("observed_at", None if kind == "sessions" else timestamp)
                record["updated_at"] = timestamp
                db.execute("""INSERT INTO records VALUES(?,?,?)
                    ON CONFLICT(kind,id) DO UPDATE SET data=excluded.data""",
                    (kind, record_id, _json(record)))
                if kind == "runtimes":
                    db.execute("DELETE FROM sources WHERE id=?", ("runtime:" + record_id,))
            else:
                moderation["observed_at"] = timestamp
                db.execute("""INSERT INTO moderation VALUES(?,?,?,?,?)
                    ON CONFLICT(event_id) DO UPDATE SET hidden=excluded.hidden,
                    reason=excluded.reason,peer=excluded.peer,observed_at=excluded.observed_at""",
                    (moderation["event_id"], int(moderation["hidden"]), moderation["reason"],
                     moderation["peer"], timestamp))
            summary = {"record_id": record_id} if record is not None else {
                "event_id": moderation["event_id"], "action": action}
            db.execute("""INSERT INTO operations
                (id,payload_hash,kind,name,runtime,status,started_at,finished_at,summary)
                VALUES(?,?,?,? ,NULL,'succeeded',?,?,?)""",
                (operation_id, payload_hash, kind, kind, timestamp, timestamp, _json(summary)))
            row = db.execute("SELECT * FROM operations WHERE id=?", (operation_id,)).fetchone()
        return {"ok": True, "operation_id": operation_id, "replayed": False,
                "record": record if record is not None else moderation,
                "operation": self._operation(row)}

    @staticmethod
    def _operation_event(row):
        event = CommandCenter._operation(row)
        return {"id": "operation:" + event["id"], "kind": "operation",
                "title": event["name"] + " — " + event["status"],
                "body": "Runtime: " + (event["runtime"] or "command center") +
                        ". Status: " + event["status"] + ".",
                "source_url": "", "observed_at": event["finished_at"] or event["started_at"],
                "operation_id": event["id"], "summary": event["summary"],
                "provider_refs": (event["summary"] or {}).get("provider_refs", [])}

    def event(self, event_id):
        """Read any retained event, including originals outside the 300-item view."""
        event_id = _identifier(event_id, "event_id")
        with self._db() as db:
            if event_id.startswith("operation:"):
                row = db.execute("SELECT * FROM operations WHERE id=?",
                                 (event_id[len("operation:"):],)).fetchone()
                event = self._operation_event(row) if row else None
            else:
                row = db.execute("SELECT data FROM source_events WHERE id=?", (event_id,)).fetchone()
                if not row:
                    row = db.execute("SELECT data FROM records WHERE kind='feed' AND id=?",
                                     (event_id,)).fetchone()
                event = json.loads(row["data"]) if row else None
            if event is None:
                raise CoreError(404, "Feed event does not exist.")
            mod = db.execute("SELECT * FROM moderation WHERE event_id=?", (event_id,)).fetchone()
        event["hidden"] = bool(mod["hidden"]) if mod else False
        event["moderation"] = dict(mod) if mod else None
        return event

    def _feed(self):
        with self._db() as db:
            operations = db.execute(
                "SELECT * FROM operations ORDER BY started_at DESC LIMIT 300").fetchall()
            source_events = db.execute(
                "SELECT data FROM source_events ORDER BY observed_at DESC LIMIT 300").fetchall()
            moderation = {row["event_id"]: dict(row)
                          for row in db.execute("SELECT * FROM moderation")}
        feed = self._get_records("feed")
        feed.extend(self._operation_event(row) for row in operations)
        feed.extend(json.loads(row["data"]) for row in source_events)
        for event in feed:
            mod = moderation.get(event["id"])
            event["hidden"] = bool(mod["hidden"]) if mod else False
            event["moderation"] = mod
        return sorted(feed, key=lambda item: item.get("observed_at") or "", reverse=True)[:300]



    def _merged_sessions(self, sources):
        """Merge actual observations by their own timestamps, never fetch time."""
        def observed_time(item):
            value = item.get("observed_at")
            if not isinstance(value, str) or not value:
                return None
            try:
                stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
                return stamp.timestamp() if stamp.tzinfo is not None else None
            except (ValueError, OverflowError):
                return None

        by_id = {}
        titan = next((source for source in sources if source["id"] == "titan"), None)
        adapter = titan.get("data") if titan else None
        raw_sessions = adapter.get("sessions", []) if isinstance(adapter, dict) else []
        allowed = ("id", "label", "url", "provider", "model", "cpu", "ram_gib", "gpu",
                   "disk_gib", "disk_free_gib", "workspace", "observed_at", "status",
                   "objective", "resource_id", "origin", "capabilities", "tools", "egress",
                   "artifact_transport", "expires_at", "lifetime", "notes", "cost_source")
        if isinstance(raw_sessions, list):
            for item in raw_sessions:
                if not isinstance(item, dict):
                    continue
                try:
                    _identifier(item.get("id"), "session.id")
                    _no_secret_fields(item)
                    session = {key: _metadata(item[key]) for key in allowed if key in item}
                    if "url" in session:
                        session["url"] = _url(session["url"])
                    session.update(source_id="titan", source_status=titan["status"],
                                   source_observed_at=titan["observed_at"])
                    by_id[session["id"]] = session
                except CoreError:
                    continue
        measurement_fields = ("cpu", "ram_gib", "gpu", "disk_gib", "disk_free_gib",
                              "workspace", "observed_at", "status", "objective",
                              "capabilities", "tools", "egress")
        binding_fields = ("url", "provider", "model", "resource_id", "origin",
                          "artifact_transport", "expires_at", "lifetime", "cost_source")
        for local in self._get_records("sessions"):
            adapter_session = by_id.get(local["id"])
            if adapter_session is None:
                by_id[local["id"]] = local
                continue
            local_time, adapter_time = observed_time(local), observed_time(adapter_session)
            adapter_wins = adapter_time is not None and (local_time is None or adapter_time > local_time)
            winner = adapter_session if adapter_wins else local
            merged = {**adapter_session, **local}
            # Do not stamp an old hardware measurement with a newer observation date.
            for key in measurement_fields:
                merged.pop(key, None)
                if key in winner:
                    merged[key] = winner[key]
            for key in binding_fields:
                if key in winner:
                    merged[key] = winner[key]
            merged["telemetry_source"] = "titan" if adapter_wins else "local-session"
            merged["telemetry_observed_at"] = winner.get("observed_at")
            merged["adapter_source"] = {
                "source_id": "titan", "source_status": adapter_session.get("source_status"),
                "fetched_at": adapter_session.get("source_observed_at"),
                "observed_at": adapter_session.get("observed_at")}
            merged["local_metadata"] = {key: local[key] for key in
                                       ("label", "notes", "updated_at") if key in local}
            by_id[local["id"]] = merged
        return list(by_id.values())

    def state(self, refresh=False):
        self._refresh_sources(force=refresh)
        runtimes = self._runtimes(force=refresh)
        with self._db() as db:
            source_ids = [row["id"] for row in db.execute(
                "SELECT id FROM sources WHERE id NOT LIKE 'runtime:%' ORDER BY id")]
            operations = [self._operation(row) for row in db.execute(
                "SELECT * FROM operations ORDER BY started_at DESC LIMIT 300")]
        sources = [self._source(source_id) for source_id in source_ids]
        ledger = next((s for s in sources if s["id"] == "resource-ledger"), None)
        catalog = next((s for s in sources if s["id"] == "connected-capabilities"), None)
        ledger_data = ledger["data"] if ledger and isinstance(ledger["data"], dict) else {}
        catalog_data = catalog["data"] if catalog and isinstance(catalog["data"], dict) else {}
        resources = [dict(item, id=item.get("id", item.get("name", "")),
                          source_id="resource-ledger", source_observed_at=ledger["observed_at"],
                          source_status=ledger["status"])
                     for item in ledger_data.get("surfaces", []) if isinstance(item, dict)]
        connections = [dict(item, source_id="connected-capabilities",
                            source_observed_at=catalog["observed_at"],
                            source_status=catalog["status"])
                       for item in catalog_data.get("providers", []) if isinstance(item, dict)]
        sessions = self._merged_sessions(sources)
        focus = self._get_records("focus")
        janny = self._get_records("janny")
        return {"observed_at": _now(), "sources": sources, "resources": resources,
                "connections": connections, "runtimes": runtimes,
                "sessions": sessions, "budgets": self._get_records("budgets"),
                "operations": operations,
                "focus": focus[0] if focus else {"objective": "", "next_action": ""},
                "feed": self._feed(),
                "janny": janny[0] if janny else {"peer": "", "status": "unassigned",
                    "responsibility": "Reversible derived-feed moderation; no access grants."}}
