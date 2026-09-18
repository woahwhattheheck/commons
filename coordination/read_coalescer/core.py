"""Process-shared, read-only request coalescing and provider cooldown coordination.

The database must live on one host's local filesystem. Routing metadata is supplied
by a trusted adapter, not by public clients. This library is not an authorization
service, an outreach arbiter, or a distributed/network-filesystem lock.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import sqlite3
import stat
import time
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable, Iterator, Mapping


class InvalidInput(ValueError):
    """Invalid local request/configuration; no provider call should be made."""


class ProviderFailure(Exception):
    """A read failed. The code, rather than raw exception text, may be retained."""

    def __init__(self, code: str = "PROVIDER_ERROR") -> None:
        self.code = code if re.fullmatch(r"[A-Z][A-Z0-9_]{0,63}", code) else "PROVIDER_ERROR"
        super().__init__(self.code)


class RateLimited(ProviderFailure):
    def __init__(self, retry_after_ms: int) -> None:
        self.retry_after_ms = _integer(retry_after_ms, "retry_after_ms", 0, 9_000_000_000_000_000)
        super().__init__("RATE_LIMITED")


def _integer(value: Any, name: str, low: int, high: int) -> int:
    if type(value) is not int or not low <= value <= high:
        raise InvalidInput(f"{name} must be an integer in [{low}, {high}]")
    return value


def _label(value: Any, name: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_.:/@-]{1,256}", value):
        raise InvalidInput(f"invalid {name}")
    if value.lower().startswith(("xoxb-", "xoxp-", "xapp-", "bearer")):
        raise InvalidInput(f"{name} must be non-secret routing metadata")
    return value


def canonical(value: Any, max_bytes: int = 1_048_576) -> str:
    """Bounded exact JSON. No floats, nonfinite values, cycles or custom objects."""
    remaining = 100_000
    active: set[int] = set()

    def walk(item: Any, depth: int = 0) -> None:
        nonlocal remaining
        remaining -= 1
        if remaining < 0 or depth > 32:
            raise InvalidInput("JSON structure exceeds limits")
        if item is None or type(item) is bool:
            return
        if type(item) is int:
            if abs(item) >= 10**30:
                raise InvalidInput("JSON integer too large")
            return
        if type(item) is str:
            try:
                if len(item.encode("utf-8")) > max_bytes:
                    raise InvalidInput("JSON string too large")
            except UnicodeEncodeError as exc:
                raise InvalidInput("invalid Unicode") from exc
            return
        if type(item) not in (dict, list):
            raise InvalidInput("JSON values must use built-in exact types; floats unsupported")
        identity = id(item)
        if identity in active:
            raise InvalidInput("cyclic JSON")
        active.add(identity)
        if type(item) is dict:
            for key, val in item.items():
                if type(key) is not str:
                    raise InvalidInput("JSON object keys must be strings")
                walk(key, depth + 1)
                walk(val, depth + 1)
        else:
            for val in item:
                walk(val, depth + 1)
        active.remove(identity)

    walk(value)
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    if len(encoded.encode("utf-8")) > max_bytes:
        raise InvalidInput("JSON bytes exceed limit")
    return encoded


def strict_loads(raw: str | bytes, max_bytes: int = 1_048_576) -> Any:
    if isinstance(raw, bytes):
        if len(raw) > max_bytes:
            raise InvalidInput("JSON bytes exceed limit")
        try:
            raw = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise InvalidInput("invalid UTF-8") from exc
    if not isinstance(raw, str) or len(raw.encode("utf-8", errors="surrogatepass")) > max_bytes:
        raise InvalidInput("JSON bytes exceed limit")

    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result = {}
        for key, value in items:
            if key in result:
                raise InvalidInput("duplicate JSON key")
            result[key] = value
        return result

    def reject(_: str) -> Any:
        raise InvalidInput("floats and nonfinite values unsupported")

    try:
        value = json.loads(raw, object_pairs_hook=pairs, parse_float=reject, parse_constant=reject)
        canonical(value, max_bytes)
        return value
    except (json.JSONDecodeError, RecursionError, ValueError) as exc:
        if isinstance(exc, InvalidInput):
            raise
        raise InvalidInput("invalid JSON") from exc


def digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class Policy:
    min_interval_ms: int = 1000
    lease_ms: int = 30_000
    failure_backoff_ms: int = 5000
    max_cache_ttl_ms: int = 60_000
    max_inflight_per_bucket: int = 1
    max_payload_bytes: int = 1_048_576
    max_records: int = 10_000
    max_cache_bytes: int = 16_777_216

    def __post_init__(self) -> None:
        bounds = {
            "min_interval_ms": (0, 86_400_000), "lease_ms": (1, 3_600_000),
            "failure_backoff_ms": (1, 86_400_000), "max_cache_ttl_ms": (0, 86_400_000),
            "max_inflight_per_bucket": (1, 64), "max_payload_bytes": (128, 16_777_216),
            "max_records": (1, 1_000_000), "max_cache_bytes": (128, 1_073_741_824),
        }
        for name, (lo, hi) in bounds.items():
            _integer(getattr(self, name), name, lo, hi)
        if self.max_cache_bytes < self.max_payload_bytes:
            raise InvalidInput("cache byte budget must fit one maximum-size payload")


@dataclass(frozen=True)
class ReadRequest:
    provider: str
    app: str
    workspace: str
    method: str
    access_scope: str
    params_json: str

    @classmethod
    def make(cls, *, provider: str, app: str, workspace: str, method: str,
             access_scope: str, params: dict[str, Any]) -> "ReadRequest":
        if type(params) is not dict:
            raise InvalidInput("params must be a JSON object")
        # Provider credentials belong to the adapter, never the request/cache key.
        secret_names = {"token", "authorization", "cookie", "password", "secret", "client_secret", "api_key"}
        def reject_secret_keys(value: Any) -> None:
            if type(value) is dict:
                for key, val in value.items():
                    if isinstance(key, str) and key.lower() in secret_names:
                        raise InvalidInput("credentials cannot be request parameters")
                    reject_secret_keys(val)
            elif type(value) is list:
                for val in value:
                    reject_secret_keys(val)
        encoded = canonical(params, 65_536)  # Validate depth before recursive key walk.
        reject_secret_keys(params)
        return cls(*(_label(v, n) for n, v in (
            ("provider", provider), ("app", app), ("workspace", workspace),
            ("method", method), ("access_scope", access_scope))), encoded)

    def validate(self) -> None:
        for name in ("provider", "app", "workspace", "method", "access_scope"):
            _label(getattr(self, name), name)
        params = strict_loads(self.params_json, 65_536)
        rebuilt = type(self).make(provider=self.provider, app=self.app, workspace=self.workspace,
            method=self.method, access_scope=self.access_scope, params=params)
        if rebuilt.params_json != self.params_json:
            raise InvalidInput("request parameters must be canonical")

    @property
    def key(self) -> str:
        return digest(canonical(asdict(self)))

    @property
    def bucket(self) -> str:
        # Visibility scopes and channels share a provider quota, but not cached data.
        return digest(canonical([self.provider, self.app, self.workspace, self.method]))

    @property
    def params(self) -> dict[str, Any]:
        return strict_loads(self.params_json, 65_536)


@dataclass(frozen=True)
class Page:
    payload: dict[str, Any]
    # Means *this query/cursor chain* ends, never workspace-wide coverage.
    collection_end: bool | None = None
    next_cursor: str | None = None

    def serialize(self, max_bytes: int) -> str:
        if type(self.payload) is not dict:
            raise InvalidInput("provider page payload must be a JSON object")
        if self.collection_end is not None and type(self.collection_end) is not bool:
            raise InvalidInput("collection_end must be bool or unknown")
        if self.next_cursor is not None and (type(self.next_cursor) is not str or
                not 0 < len(self.next_cursor) <= 8192):
            raise InvalidInput("invalid next cursor")
        if self.next_cursor is not None and self.collection_end is not False:
            raise InvalidInput("a next cursor requires collection_end=False")
        if self.payload.get("ok") is False:
            raise InvalidInput("provider errors are not successful pages")
        return canonical(asdict(self), max_bytes)


@dataclass(frozen=True)
class Lease:
    token: str
    request_key: str
    bucket: str
    expires_at_ms: int


@dataclass(frozen=True)
class Result:
    status: str
    request_key: str
    reason: str
    retry_at_ms: int | None = None
    lease: Lease | None = None
    page: Page | None = None
    captured_at_ms: int | None = None
    expires_at_ms: int | None = None
    payload_sha256: str | None = None

    def public_dict(self) -> dict[str, Any]:
        value = asdict(self)
        # Leases are dispatch correlation metadata, not public send permissions.
        value.pop("lease")
        value["send_authorized"] = False
        value["workspace_census_complete"] = False
        return value


SCHEMA = """
CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS quotas(
 bucket TEXT PRIMARY KEY, next_start INTEGER NOT NULL, blocked_until INTEGER NOT NULL, dispatch_after INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS flights(
 request_key TEXT PRIMARY KEY, token TEXT NOT NULL, expires INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS attempts(
 token TEXT PRIMARY KEY, request_key TEXT NOT NULL, bucket TEXT NOT NULL,
 acquired INTEGER NOT NULL, expires INTEGER NOT NULL, state TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS attempts_live ON attempts(bucket,state,expires);
CREATE TABLE IF NOT EXISTS cache(
 request_key TEXT PRIMARY KEY, page TEXT NOT NULL, sha TEXT NOT NULL,
 captured INTEGER NOT NULL, expires INTEGER NOT NULL, size_bytes INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS failures(
 request_key TEXT PRIMARY KEY, retry_at INTEGER NOT NULL, code TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS metrics(name TEXT PRIMARY KEY, value INTEGER NOT NULL);
"""


class Broker:
    def __init__(self, path: str | Path, policy: Policy | None = None,
                 clock: Callable[[], int] | None = None) -> None:
        self.path = str(Path(path).absolute())
        self.policy = policy or Policy()
        self.clock = clock or (lambda: time.time_ns() // 1_000_000)
        parent = Path(self.path).parent
        parent.mkdir(parents=True, mode=0o700, exist_ok=True)
        # A dedicated trusted local directory is required. This is not a sandbox
        # against a malicious local user who controls the database or its parent.
        flags = os.O_RDWR | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
        try:
            descriptor = os.open(self.path, flags, 0o600)
        except FileExistsError:
            info = os.lstat(self.path)
            if not stat.S_ISREG(info.st_mode) or stat.S_IMODE(info.st_mode) & 0o077:
                raise InvalidInput("database must be a private regular file, not a symlink")
        else:
            os.close(descriptor)
        with self._connection() as connection:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.executescript(SCHEMA)
        with self._transaction() as connection:
            supplied = canonical({"schema": 1, "policy": asdict(self.policy)})
            connection.execute("INSERT OR IGNORE INTO settings VALUES('config',?)", (supplied,))
            if connection.execute("SELECT value FROM settings WHERE key='config'").fetchone()[0] != supplied:
                raise InvalidInput("shared database policy differs; workers must agree")

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path, timeout=10, isolation_level=None)
        connection.row_factory = sqlite3.Row
        try:
            connection.execute("PRAGMA busy_timeout=10000")
            yield connection
        finally:
            connection.close()

    @contextmanager
    def _transaction(self) -> Iterator[sqlite3.Connection]:
        with self._connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                yield connection
                connection.commit()
            except BaseException:
                connection.rollback()
                raise

    def _now(self) -> int:
        return _integer(self.clock(), "clock_ms", 0, 8_000_000_000_000_000)

    @staticmethod
    def _metric(connection: sqlite3.Connection, name: str) -> None:
        connection.execute("INSERT INTO metrics VALUES(?,1) ON CONFLICT(name) DO UPDATE SET value=value+1", (name,))

    @staticmethod
    def _attempt(connection: sqlite3.Connection, lease: Lease) -> sqlite3.Row:
        if type(lease) is not Lease:
            raise InvalidInput("expected an issued lease")
        row = connection.execute("SELECT * FROM attempts WHERE token=?", (lease.token,)).fetchone()
        if row is None or (row["request_key"], row["bucket"], row["expires"]) != (
                lease.request_key, lease.bucket, lease.expires_at_ms):
            raise InvalidInput("unknown or changed lease")
        return row

    @staticmethod
    def _owns(connection: sqlite3.Connection, lease: Lease, now: int) -> bool:
        row = connection.execute("SELECT * FROM flights WHERE request_key=?", (lease.request_key,)).fetchone()
        return row is not None and row["token"] == lease.token and now < row["expires"]

    def acquire(self, request: ReadRequest, *, max_age_ms: int | None = None) -> Result:
        request.validate()
        if max_age_ms is not None:
            _integer(max_age_ms, "max_age_ms", 0, self.policy.max_cache_ttl_ms)
        key, bucket = request.key, request.bucket
        with self._transaction() as connection:
            now = self._now()
            cached = connection.execute("SELECT * FROM cache WHERE request_key=?", (key,)).fetchone()
            if cached is not None and cached["captured"] <= now < cached["expires"] and (
                    max_age_ms is None or now - cached["captured"] <= max_age_ms):
                # Detect corruption rather than turn it into a provider-empty response.
                if digest(cached["page"]) != cached["sha"]:
                    raise InvalidInput("cached page digest mismatch")
                page = Page(**strict_loads(cached["page"], self.policy.max_payload_bytes))
                page.serialize(self.policy.max_payload_bytes)
                self._metric(connection, "cache_hits")
                return Result("CACHE", key, "FRESH_PAGE_NOT_CENSUS", page=page,
                    captured_at_ms=cached["captured"], expires_at_ms=cached["expires"],
                    payload_sha256=cached["sha"])
            quota = connection.execute("SELECT * FROM quotas WHERE bucket=?", (bucket,)).fetchone()
            if quota is None:
                if connection.execute("SELECT COUNT(*) FROM quotas").fetchone()[0] >= self.policy.max_records:
                    return Result("ERROR", key, "MAINTENANCE_REQUIRED")
                connection.execute("INSERT INTO quotas VALUES(?,0,0,0)", (bucket,))
                quota = connection.execute("SELECT * FROM quotas WHERE bucket=?", (bucket,)).fetchone()
            failure = connection.execute("SELECT * FROM failures WHERE request_key=?", (key,)).fetchone()
            flight = connection.execute("SELECT * FROM flights WHERE request_key=?", (key,)).fetchone()
            if quota["blocked_until"] > now:
                self._metric(connection, "cooldown_waits")
                return Result("WAIT", key, "PROVIDER_COOLDOWN", retry_at_ms=quota["blocked_until"])
            if failure is not None and failure["retry_at"] > now:
                self._metric(connection, "failure_waits")
                return Result("WAIT", key, failure["code"], retry_at_ms=failure["retry_at"])
            if flight is not None and flight["expires"] > now:
                self._metric(connection, "coalesced_waits")
                return Result("WAIT", key, "SAME_READ_IN_FLIGHT", retry_at_ms=min(flight["expires"], now + 100))
            if quota["next_start"] > now:
                self._metric(connection, "spacing_waits")
                return Result("WAIT", key, "METHOD_START_SPACING", retry_at_ms=quota["next_start"])
            active = connection.execute("SELECT expires FROM attempts WHERE bucket=? AND state IN ('ISSUED','DISPATCHED') AND expires>? ORDER BY expires", (bucket, now)).fetchall()
            if len(active) >= self.policy.max_inflight_per_bucket:
                self._metric(connection, "bucket_waits")
                return Result("WAIT", key, "METHOD_IN_FLIGHT", retry_at_ms=min(active[0][0], now + 100))
            # Bounded live state; offline maintenance clears old rows, not live leases.
            if connection.execute("SELECT COUNT(*) FROM attempts").fetchone()[0] >= self.policy.max_records:
                return Result("ERROR", key, "MAINTENANCE_REQUIRED")
            token, expires = secrets.token_hex(24), now + self.policy.lease_ms
            connection.execute("INSERT INTO attempts VALUES(?,?,?,?,?,'ISSUED')", (token, key, bucket, now, expires))
            connection.execute("INSERT INTO flights VALUES(?,?,?) ON CONFLICT(request_key) DO UPDATE SET token=excluded.token,expires=excluded.expires", (key, token, expires))
            connection.execute("UPDATE quotas SET next_start=? WHERE bucket=?", (now + self.policy.min_interval_ms, bucket))
            self._metric(connection, "leases_issued")
            return Result("ACQUIRED", key, "ONE_READ_LEASE", lease=Lease(token, key, bucket, expires))

    def begin_dispatch(self, lease: Lease) -> bool:
        """Last-inch fence: a newly observed 429 can stop an issued, unstarted read."""
        with self._transaction() as connection:
            now, attempt = self._now(), self._attempt(connection, lease)
            quota = connection.execute("SELECT blocked_until,dispatch_after FROM quotas WHERE bucket=?", (lease.bucket,)).fetchone()
            if attempt["state"] != "ISSUED" or not self._owns(connection, lease, now) or max(quota[0], quota[1]) > now or now < attempt["acquired"]:
                if attempt["state"] == "ISSUED":
                    connection.execute("UPDATE attempts SET state='CANCELED' WHERE token=?", (lease.token,))
                    connection.execute("DELETE FROM flights WHERE request_key=? AND token=?", (lease.request_key, lease.token))
                return False
            connection.execute("UPDATE attempts SET state='DISPATCHED' WHERE token=?", (lease.token,))
            connection.execute("UPDATE quotas SET dispatch_after=?,next_start=MAX(next_start,?) WHERE bucket=?", (now + self.policy.min_interval_ms, now + self.policy.min_interval_ms, lease.bucket))
            self._metric(connection, "provider_dispatches")
            return True

    def publish(self, lease: Lease, page: Page, *, ttl_ms: int) -> Result:
        _integer(ttl_ms, "ttl_ms", 0, self.policy.max_cache_ttl_ms)
        serialized = page.serialize(self.policy.max_payload_bytes)
        with self._transaction() as connection:
            now, attempt = self._now(), self._attempt(connection, lease)
            if attempt["state"] != "DISPATCHED" or not self._owns(connection, lease, now) or now < attempt["acquired"]:
                if attempt["state"] == "DISPATCHED":
                    connection.execute("UPDATE attempts SET state='SUPERSEDED' WHERE token=?", (lease.token,))
                self._metric(connection, "stale_results_discarded")
                return Result("DISCARDED", lease.request_key, "LEASE_EXPIRED_OR_SUPERSEDED")
            expires, sha = now + ttl_ms, digest(serialized)
            size = len(serialized.encode("utf-8"))
            connection.execute("INSERT INTO cache VALUES(?,?,?,?,?,?) ON CONFLICT(request_key) DO UPDATE SET page=excluded.page,sha=excluded.sha,captured=excluded.captured,expires=excluded.expires,size_bytes=excluded.size_bytes", (lease.request_key, serialized, sha, now, expires, size))
            total = connection.execute("SELECT COALESCE(SUM(size_bytes),0) FROM cache").fetchone()[0]
            if total > self.policy.max_cache_bytes:
                oldest = connection.execute("SELECT request_key,size_bytes FROM cache WHERE request_key<>? ORDER BY expires,captured,request_key", (lease.request_key,)).fetchall()
                for item in oldest:
                    if total <= self.policy.max_cache_bytes:
                        break
                    connection.execute("DELETE FROM cache WHERE request_key=?", (item["request_key"],))
                    total -= item["size_bytes"]
                    self._metric(connection, "cache_budget_evictions")
            connection.execute("DELETE FROM failures WHERE request_key=?", (lease.request_key,))
            connection.execute("DELETE FROM flights WHERE request_key=? AND token=?", (lease.request_key, lease.token))
            connection.execute("UPDATE attempts SET state='SUCCESS' WHERE token=?", (lease.token,))
            self._metric(connection, "provider_successes")
            # Return the frozen serialized value, not the caller's mutable dictionary.
            frozen = Page(**strict_loads(serialized, self.policy.max_payload_bytes))
            return Result("FETCHED", lease.request_key, "PROVIDER_PAGE_NOT_CENSUS", page=frozen,
                captured_at_ms=now, expires_at_ms=expires, payload_sha256=sha)

    def fail(self, lease: Lease, error: ProviderFailure) -> Result:
        if not isinstance(error, ProviderFailure):
            raise InvalidInput("expected classified provider failure")
        with self._transaction() as connection:
            now, attempt = self._now(), self._attempt(connection, lease)
            if attempt["state"] != "DISPATCHED":
                return Result("DISCARDED", lease.request_key, "ATTEMPT_ALREADY_TERMINAL")
            delay = error.retry_after_ms if isinstance(error, RateLimited) else self.policy.failure_backoff_ms
            retry = max(now, attempt["acquired"]) + max(delay, self.policy.failure_backoff_ms if delay == 0 else 1)
            # A genuine late 429 still constrains the shared method even if its
            # request lease expired. Recording each attempt once prevents replay
            # of the same 429 from extending the cooldown indefinitely.
            if isinstance(error, RateLimited):
                connection.execute("UPDATE quotas SET blocked_until=MAX(blocked_until,?) WHERE bucket=?", (retry, lease.bucket))
                retry = connection.execute("SELECT blocked_until FROM quotas WHERE bucket=?", (lease.bucket,)).fetchone()[0]
                self._metric(connection, "provider_429s")
            else:
                self._metric(connection, "provider_failures")
            current = self._owns(connection, lease, now)
            if current:
                connection.execute("INSERT INTO failures VALUES(?,?,?) ON CONFLICT(request_key) DO UPDATE SET retry_at=excluded.retry_at,code=excluded.code", (lease.request_key, retry, error.code))
                connection.execute("DELETE FROM flights WHERE request_key=? AND token=?", (lease.request_key, lease.token))
            connection.execute("UPDATE attempts SET state='FAILED' WHERE token=?", (lease.token,))
            return Result("WAIT" if isinstance(error, RateLimited) else "ERROR", lease.request_key,
                error.code, retry_at_ms=retry)

    def read_once(self, request: ReadRequest, reader: Callable[[ReadRequest], Page], *,
                  ttl_ms: int = 5000, max_age_ms: int | None = None) -> Result:
        """At most one synchronous provider read. WAIT never sleeps or retries."""
        _integer(ttl_ms, "ttl_ms", 0, self.policy.max_cache_ttl_ms)
        result = self.acquire(request, max_age_ms=max_age_ms)
        if result.status != "ACQUIRED":
            return result
        lease = result.lease
        if lease is None:  # Ordinary runtime check, retained under python -O.
            raise RuntimeError("acquired request lacks lease")
        if not self.begin_dispatch(lease):
            return Result("WAIT", request.key, "DISPATCH_FENCE_CHANGED")
        try:
            page = reader(request)
            if type(page) is not Page:
                raise ProviderFailure("INVALID_PROVIDER_RESPONSE")
            return self.publish(lease, page, ttl_ms=ttl_ms)
        except ProviderFailure as exc:
            return self.fail(lease, exc)
        except (InvalidInput, ValueError, TypeError):
            return self.fail(lease, ProviderFailure("INVALID_PROVIDER_RESPONSE"))
        except Exception:
            # Do not retain raw errors that may contain request credentials/URLs.
            return self.fail(lease, ProviderFailure("READ_EXCEPTION"))

    def maintain(self, *, retain_ms: int = 3_600_000) -> dict[str, int]:
        """Explicit bounded-state maintenance. Never removes a current lease.

        Expired attempts are kept for retain_ms so late 429 results can still be
        recorded. Older callbacks must stop; their unknown lease is rejected.
        """
        _integer(retain_ms, "retain_ms", self.policy.lease_ms, 604_800_000)
        with self._transaction() as connection:
            now = self._now()
            counts = {}
            for table, condition, cutoff in (
                ("cache", "expires<=?", now), ("failures", "retry_at<=?", now),
                ("flights", "expires<=?", now), ("attempts", "expires<=?", now-retain_ms),
                ("quotas", "MAX(next_start,blocked_until,dispatch_after)<=? AND bucket NOT IN (SELECT bucket FROM attempts)", now),
            ):
                counts[table] = connection.execute(f"DELETE FROM {table} WHERE {condition}", (cutoff,)).rowcount
            return counts

    def stats(self) -> dict[str, Any]:
        with self._connection() as connection:
            return {"counters": dict(connection.execute("SELECT name,value FROM metrics")),
                "rows": {table: connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                         for table in ("cache", "flights", "attempts", "quotas", "failures")},
                "cached_payload_bytes": connection.execute("SELECT COALESCE(SUM(size_bytes),0) FROM cache").fetchone()[0],
                "policy": asdict(self.policy), "scope": "ONE_HOST_SHARED_DATABASE",
                "native_connector_adopted": False, "send_authorized": False}
