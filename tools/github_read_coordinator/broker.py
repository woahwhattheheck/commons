"""Cross-process coordination for bounded, read-only GitHub API calls."""
from __future__ import annotations

import hashlib
import json
import math
import re
import secrets
import sqlite3
import time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

MAX_REQUEST = 32768
MAX_RESPONSE = 1048576
MAX_AGE = 300
MAX_COOLDOWN = 86400
BURST_INTERVAL = 0.5

ROUTES = {
    "repo.get": {"owner", "repo"},
    "contents.get": {"owner", "repo", "path", "ref"},
    "pull.get": {"owner", "repo", "number"},
    "pull.files": {"owner", "repo", "number", "page", "per_page"},
    "commit.get": {"owner", "repo", "ref"},
    "issues.list": {"owner", "repo", "state", "labels", "sort", "direction", "page", "per_page"},
    "actions.runs": {"owner", "repo", "branch", "event", "status", "head_sha", "page", "per_page"},
    "search.issues": {"q", "page", "per_page", "sort", "order"},
    "search.code": {"q", "page", "per_page", "sort", "order"},
}
SEARCH_ROUTES = {"search.issues", "search.code"}
OWNER_RE = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})")
REPO_RE = re.compile(r"[A-Za-z0-9_.-]{1,100}")
HEX64_RE = re.compile(r"[a-f0-9]{64}")


def dumps(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)


def loads(raw: str | bytes) -> Any:
    def pairs(items):
        out = {}
        for key, value in items:
            if key in out:
                raise ValueError("duplicate JSON key")
            out[key] = value
        return out

    def constant(_):
        raise ValueError("nonfinite JSON value")

    if isinstance(raw, bytes):
        raw = raw.decode("utf-8")
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=constant)


def _safe_text(value: Any, *, maximum: int = 4096) -> str:
    if not isinstance(value, str) or not value or len(value) > maximum:
        raise ValueError("invalid string parameter")
    if any(ord(c) < 32 or ord(c) == 127 for c in value):
        raise ValueError("control character in string parameter")
    return value


def _safe_path(value: Any) -> str:
    value = _safe_text(value, maximum=4096)
    if value.startswith("/") or value.endswith("/") or "\\" in value:
        raise ValueError("path must be repository-relative")
    pieces = value.split("/")
    if any(piece in {"", ".", ".."} for piece in pieces):
        raise ValueError("path traversal is not allowed")
    return value


def route_bucket(route: str) -> str:
    return "search" if route in SEARCH_ROUTES else "core"


def normalize(route: str, params: dict) -> dict:
    if not isinstance(route, str) or route not in ROUTES:
        raise ValueError("read route is not allowed")
    if not isinstance(params, dict) or set(params) - ROUTES[route]:
        raise ValueError("unsupported parameters")
    out = dict(params)

    if route.startswith(("repo.", "contents.", "pull.", "commit.", "issues.", "actions.")):
        if not {"owner", "repo"} <= out.keys():
            raise ValueError("owner and repo are required")
    if "owner" in out:
        if not isinstance(out["owner"], str) or OWNER_RE.fullmatch(out["owner"]) is None:
            raise ValueError("invalid owner")
    if "repo" in out:
        if not isinstance(out["repo"], str) or REPO_RE.fullmatch(out["repo"]) is None:
            raise ValueError("invalid repo")
    if route == "contents.get":
        if "path" not in out:
            raise ValueError("path is required")
        out["path"] = _safe_path(out["path"])
    if route.startswith("pull.") and "number" not in out:
        raise ValueError("pull number is required")
    if route == "commit.get" and "ref" not in out:
        raise ValueError("ref is required")
    if route.startswith("search.") and "q" not in out:
        raise ValueError("search query is required")

    for key in ("number", "page", "per_page"):
        if key not in out:
            continue
        value = out[key]
        if type(value) is not int:
            raise ValueError("integer parameter required")
        if key == "number" and not 1 <= value <= 2_147_483_647:
            raise ValueError("invalid pull number")
        if key == "page" and not 1 <= value <= 1000:
            raise ValueError("invalid page")
        if key == "per_page" and not 1 <= value <= 100:
            raise ValueError("invalid page size")

    for key in ("ref", "branch", "event", "status", "head_sha", "labels", "q", "sort", "order", "state", "direction"):
        if key in out:
            out[key] = _safe_text(out[key], maximum=1024 if key == "q" else 255)

    if "state" in out and out["state"] not in {"open", "closed", "all"}:
        raise ValueError("invalid state")
    if "direction" in out and out["direction"] not in {"asc", "desc"}:
        raise ValueError("invalid direction")
    if "order" in out and out["order"] not in {"asc", "desc"}:
        raise ValueError("invalid order")
    if "sort" in out:
        allowed = {"created", "updated", "comments"} if route == "search.issues" else {"indexed"} if route == "search.code" else {"created", "updated", "comments"}
        if out["sort"] not in allowed:
            raise ValueError("invalid sort")

    if route in {"pull.files", "issues.list", "actions.runs", "search.issues", "search.code"}:
        out.setdefault("per_page", 30)
        out.setdefault("page", 1)
    if len(dumps(out).encode()) > MAX_REQUEST:
        raise ValueError("request too large")
    return out


def retry_after_seconds(value: Any) -> int | None:
    text = str(value).strip()
    if not re.fullmatch(r"[0-9]{1,10}", text):
        return None
    return min(MAX_COOLDOWN, max(1, int(text)))


def reset_delay(reset_value: Any, now: float) -> int | None:
    text = str(reset_value).strip()
    if not re.fullmatch(r"[0-9]{1,12}", text):
        return None
    target = int(text)
    if target <= now:
        return 1
    return min(MAX_COOLDOWN, max(1, math.ceil(target - now)))


@dataclass(frozen=True)
class Lease:
    key: str
    nonce: str
    route: str
    params: dict
    bucket: str
    expires_at: float


@dataclass(frozen=True)
class Upstream:
    status: int
    payload: Any = None
    retry_after: Any = None
    rate_remaining: Any = None
    rate_reset: Any = None
    secondary_limited: bool = False


class Broker:
    def __init__(self, path: str | Path, principal: str, *, clock: Callable[[], float] = time.time,
                 lease_seconds: float = 45, max_entries: int = 256, burst_interval: float = BURST_INTERVAL):
        if not isinstance(principal, str) or HEX64_RE.fullmatch(principal) is None:
            raise ValueError("credential fingerprint required, never a raw token")
        if type(max_entries) is not int or not 1 <= max_entries <= 4096:
            raise ValueError("invalid max entries")
        for name, value in (("lease_seconds", lease_seconds), ("burst_interval", burst_interval)):
            if type(value) not in (int, float) or not math.isfinite(value) or value <= 0:
                raise ValueError(f"invalid {name}")
        self.path = str(path)
        self.clock = clock
        self.namespace = "api.github.com:" + principal
        self.scope = self.namespace
        self.lease_seconds = float(lease_seconds)
        self.max_entries = max_entries
        self.burst_interval = float(burst_interval)
        with self.connect() as db:
            version = db.execute("PRAGMA user_version").fetchone()[0]
            if version not in (0, 1):
                raise ValueError("unsupported database version")
            db.execute("PRAGMA journal_mode=WAL")
            db.executescript("""
                CREATE TABLE IF NOT EXISTS cache (
                  namespace TEXT, key TEXT, fetched REAL, payload TEXT,
                  PRIMARY KEY(namespace,key));
                CREATE TABLE IF NOT EXISTS flight (
                  namespace TEXT, key TEXT, nonce TEXT, expires REAL,
                  PRIMARY KEY(namespace,key));
                CREATE TABLE IF NOT EXISTS rate (
                  scope TEXT, bucket TEXT, next_at REAL,
                  PRIMARY KEY(scope,bucket));
                CREATE TABLE IF NOT EXISTS blocked (
                  namespace TEXT PRIMARY KEY, reason TEXT);
                PRAGMA user_version=1;
            """)

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=5, isolation_level=None)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def now(self) -> float:
        value = self.clock()
        if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
            raise ValueError("invalid clock")
        return float(value)

    @staticmethod
    def envelope(state: str, **fields):
        return {"state": state, "provider_write_authority": False, **fields}

    def _cooldown(self, db, bucket: str, now: float) -> int | None:
        rows = db.execute(
            "SELECT bucket,next_at FROM rate WHERE scope=? AND bucket IN (?,?,?)",
            (self.scope, "secondary", "burst", bucket),
        ).fetchall()
        future = [row["next_at"] for row in rows if row["next_at"] > now]
        return max(1, math.ceil(max(future) - now)) if future else None

    def acquire(self, route: str, params: dict, max_age_seconds: int = 30):
        params = normalize(route, params)
        if type(max_age_seconds) is not int or not 0 <= max_age_seconds <= MAX_AGE:
            raise ValueError("invalid cache age")
        key = hashlib.sha256(dumps([route, params]).encode()).hexdigest()
        now = self.now()
        bucket = route_bucket(route)
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            blocked = db.execute("SELECT reason FROM blocked WHERE namespace=?", (self.namespace,)).fetchone()
            if blocked:
                return self.envelope("AUTH_BLOCKED", error=blocked[0])
            db.execute("DELETE FROM cache WHERE fetched<?", (now - MAX_AGE,))
            db.execute("DELETE FROM flight WHERE expires<=?", (now,))
            row = db.execute("SELECT fetched,payload FROM cache WHERE namespace=? AND key=?", (self.namespace, key)).fetchone()
            if row and max_age_seconds > 0 and 0 <= now - row["fetched"] <= max_age_seconds:
                return self.envelope("CACHED", fetched_at=row["fetched"], age_seconds=now-row["fetched"], data=loads(row["payload"]))
            flight = db.execute("SELECT expires FROM flight WHERE namespace=? AND key=?", (self.namespace, key)).fetchone()
            if flight:
                return self.envelope("BUSY", retry_after_seconds=max(1, math.ceil(flight["expires"] - now)))
            cooldown = self._cooldown(db, bucket, now)
            if cooldown is not None:
                return self.envelope("COOLDOWN", retry_after_seconds=cooldown)
            if db.execute("SELECT count(*) FROM flight").fetchone()[0] >= self.max_entries:
                return self.envelope("BUSY", retry_after_seconds=1)
            nonce = secrets.token_hex(24)
            expires = now + self.lease_seconds
            db.execute("INSERT INTO flight VALUES (?,?,?,?)", (self.namespace, key, nonce, expires))
            db.execute(
                "INSERT INTO rate VALUES (?,?,?) ON CONFLICT(scope,bucket) DO UPDATE SET next_at=max(rate.next_at,excluded.next_at)",
                (self.scope, "burst", now + self.burst_interval),
            )
            return Lease(key, nonce, route, params, bucket, expires)

    def _extend(self, db, bucket: str, next_at: float):
        db.execute(
            "INSERT INTO rate VALUES (?,?,?) ON CONFLICT(scope,bucket) DO UPDATE SET next_at=max(rate.next_at,excluded.next_at)",
            (self.scope, bucket, next_at),
        )

    def finish(self, lease: Lease, result: Upstream):
        now = self.now()
        if not isinstance(result, Upstream):
            result = Upstream(502)
        secondary = type(result.secondary_limited) is bool and result.secondary_limited
        retry = retry_after_seconds(result.retry_after)
        remaining_zero = str(result.rate_remaining).strip() == "0"
        primary_limited = result.status in {403, 429} and remaining_zero
        generic_429 = result.status == 429 and not secondary
        limited = secondary or primary_limited or generic_429
        if secondary:
            delay = retry or 60
            limit_bucket = "secondary"
        elif primary_limited:
            delay = retry or reset_delay(result.rate_reset, now) or 60
            limit_bucket = lease.bucket
        elif generic_429:
            # GitHub may signal secondary throttling with a bare 429 and no
            # parseable body/header distinction. Fail conservatively across
            # all routes for this credential instead of stampeding another bucket.
            delay = retry or 60
            limit_bucket = "secondary"
        else:
            delay = None
            limit_bucket = None

        payload_text = None
        if result.status == 200:
            try:
                encoded = dumps(result.payload)
                if len(encoded.encode()) <= MAX_RESPONSE:
                    payload_text = encoded
            except (ValueError, TypeError, RecursionError):
                pass

        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            if limited:
                self._extend(db, limit_bucket, now + delay)
            # The final permitted request can succeed while exhausting its
            # primary quota. Preserve that response, but prevent subsequent
            # uncached calls in the same bucket until the reset. Persist this
            # observation even if its lease expired while the response arrived.
            if result.status == 200 and remaining_zero:
                primary_delay = max(retry or 0, reset_delay(result.rate_reset, now) or 0) or 60
                self._extend(db, lease.bucket, now + primary_delay)
            if result.status == 401:
                db.execute("INSERT OR REPLACE INTO blocked VALUES (?,?)", (self.namespace, "bad_credentials"))
                db.execute("DELETE FROM cache WHERE namespace=?", (self.namespace,))
            row = db.execute("SELECT nonce,expires FROM flight WHERE namespace=? AND key=?", (self.namespace, lease.key)).fetchone()
            if not row or row["nonce"] != lease.nonce or row["expires"] <= now:
                return self.envelope("DISCARDED", retry_after_seconds=1)
            db.execute("DELETE FROM flight WHERE namespace=? AND key=? AND nonce=?", (self.namespace, lease.key, lease.nonce))
            blocked = db.execute("SELECT reason FROM blocked WHERE namespace=?", (self.namespace,)).fetchone()
            if blocked:
                return self.envelope("AUTH_BLOCKED", error=blocked[0])
            if limited:
                db.execute("DELETE FROM cache WHERE namespace=? AND key=?", (self.namespace, lease.key))
                wait = self._cooldown(db, lease.bucket, now) or delay
                return self.envelope("COOLDOWN", retry_after_seconds=wait)
            if payload_text is None:
                db.execute("DELETE FROM cache WHERE namespace=? AND key=?", (self.namespace, lease.key))
                safe = "not_found" if result.status == 404 else "forbidden" if result.status == 403 else "upstream_error"
                return self.envelope("UPSTREAM_ERROR", error=safe)
            db.execute("INSERT OR REPLACE INTO cache VALUES (?,?,?,?)", (self.namespace, lease.key, now, payload_text))
            db.execute(
                "DELETE FROM cache WHERE rowid IN (SELECT rowid FROM cache ORDER BY fetched DESC,namespace,key LIMIT -1 OFFSET ?)",
                (self.max_entries,),
            )
            return self.envelope("FETCHED", fetched_at=now, age_seconds=0, data=loads(payload_text))

    def read(self, route: str, params: dict, provider: Callable, max_age_seconds: int = 30):
        decision = self.acquire(route, params, max_age_seconds)
        if not isinstance(decision, Lease):
            return decision
        try:
            result = provider(decision.route, decision.params)
            if not isinstance(result, Upstream):
                result = Upstream(502)
        except Exception:
            result = Upstream(502)
        return self.finish(decision, result)
