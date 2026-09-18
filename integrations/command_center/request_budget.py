"""Durable cooldowns for command-center provider reads.

The existing refresh OS lock remains the refresh singleflight. This small SQLite
ledger lets later collector instances honor a provider's Retry-After without
sleeping through the collection deadline or blocking unrelated providers.
"""
from __future__ import annotations

import math
import sqlite3
import threading
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path


def _iso(value):
    if value is None:
        return None
    return datetime.fromtimestamp(value, timezone.utc).isoformat().replace("+00:00", "Z")


def retry_seconds(value, now, fallback):
    """Parse a provider delay/date; malformed values use an explicit local policy."""
    if not isinstance(value, bool) and value is not None:
        try:
            seconds = float(value)
            if math.isfinite(seconds) and 0 <= seconds <= 3153600000:
                return seconds, "provider"
        except (ValueError, TypeError, OverflowError):
            pass
        if isinstance(value, str):
            try:
                stamp = parsedate_to_datetime(value)
                if stamp.tzinfo is not None:
                    seconds = stamp.timestamp() - now
                    if math.isfinite(seconds) and 0 <= seconds <= 3153600000:
                        return seconds, "provider"
            except (ValueError, TypeError, OverflowError):
                pass
    return fallback, "configured_fallback"


class RequestDeferred(RuntimeError):
    def __init__(self, scope, retry_at, reason):
        super().__init__("collector_read_deferred")
        self.code = "collector_read_deferred"
        self.scope = scope
        self.retry_not_before = _iso(retry_at)
        self.reason = reason


class RequestBudget:
    def __init__(self, state_dir=None, *, clock=time.time, fallback_seconds=60):
        if (isinstance(fallback_seconds, bool) or not isinstance(fallback_seconds, (int, float))
                or not math.isfinite(fallback_seconds) or not 1 <= fallback_seconds <= 3600):
            raise ValueError("rate_limit_fallback_seconds must be from 1 to 3600.")
        self.clock, self.fallback_seconds = clock, fallback_seconds
        self.path = Path(state_dir) / "request-budget.sqlite3" if state_dir is not None else None
        self._lock = threading.RLock()
        self._memory = sqlite3.connect(":memory:", check_same_thread=False) if self.path is None else None
        self._attempts = self._deferred = self._limited = 0
        with self._transaction() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS read_budget(
                scope TEXT PRIMARY KEY, retry_until REAL NOT NULL DEFAULT 0, last_attempt REAL,
                last_limited REAL, attempts INTEGER NOT NULL DEFAULT 0,
                deferred INTEGER NOT NULL DEFAULT 0, limited INTEGER NOT NULL DEFAULT 0,
                retry_basis TEXT)""")

    @contextmanager
    def _transaction(self):
        with self._lock:
            db = self._memory or sqlite3.connect(str(self.path), timeout=10)
            db.row_factory = sqlite3.Row
            try:
                db.execute("PRAGMA busy_timeout=10000")
                db.execute("BEGIN IMMEDIATE")
                yield db
                db.commit()
            except Exception:
                db.rollback()
                raise
            finally:
                if self._memory is None:
                    db.close()

    @staticmethod
    def _row(db, scope):
        db.execute("INSERT OR IGNORE INTO read_budget(scope) VALUES(?)", (scope,))
        return db.execute("SELECT * FROM read_budget WHERE scope=?", (scope,)).fetchone()

    def acquire(self, scope):
        deferred = None
        with self._transaction() as db:
            now = self.clock()
            row = self._row(db, scope)
            until = row["retry_until"]
            if now < until:
                db.execute("UPDATE read_budget SET deferred=deferred+1 WHERE scope=?", (scope,))
                self._deferred += 1
                deferred = RequestDeferred(scope, until, "rate_limited")
            else:
                db.execute("""UPDATE read_budget SET attempts=attempts+1,
                    last_attempt=? WHERE scope=?""", (now, scope))
                self._attempts += 1
        if deferred is not None:
            raise deferred

    def rate_limited(self, scope, retry_after=None, reset_at=None):
        with self._transaction() as db:
            now = self.clock()
            seconds, basis = retry_seconds(retry_after, now, self.fallback_seconds)
            if (not isinstance(reset_at, bool) and isinstance(reset_at, (int, float))
                    and math.isfinite(reset_at) and now <= reset_at <= now + 3153600000):
                seconds = max(reset_at - now, seconds if basis == "provider" else 0)
                basis = "provider_retry_and_reset" if basis == "provider" else "provider_reset"
            if seconds < 1:
                seconds, basis = 1, basis + "_minimum_delay"
            row = self._row(db, scope)
            until = now + seconds
            if row["retry_until"] >= until:
                # Keep the reason for the deadline that still governs this read.
                until, basis = row["retry_until"], row["retry_basis"] or basis
            db.execute("""UPDATE read_budget SET retry_until=?,last_limited=?,
                limited=limited+1,retry_basis=? WHERE scope=?""", (until, now, basis, scope))
            self._limited += 1
        return {"scope": scope, "retry_not_before": _iso(until),
                "retry_after_seconds": max(0, until - now), "retry_basis": basis}

    def metrics(self):
        with self._transaction() as db:
            now = self.clock()
            scopes = []
            for row in db.execute("SELECT * FROM read_budget ORDER BY retry_until DESC,scope LIMIT 100"):
                until = row["retry_until"]
                scopes.append({"scope": row["scope"],
                    "state": "rate_limited" if now < until else "ready",
                    "retry_not_before": _iso(until) if until else None,
                    "retry_remaining_seconds": max(0, until - now),
                    "last_attempt_at": _iso(row["last_attempt"]),
                    "last_rate_limit_at": _iso(row["last_limited"]),
                    "retry_basis": row["retry_basis"],
                    "total_observed_attempts": row["attempts"],
                    "total_deferred_reads": row["deferred"],
                    "total_rate_limit_responses": row["limited"]})
            scope_count = db.execute("SELECT COUNT(*) FROM read_budget").fetchone()[0]
            return {"observed_attempts": self._attempts, "deferred_reads": self._deferred,
                    "scope_count": scope_count, "scopes_truncated": scope_count > len(scopes),
                    "rate_limit_responses": self._limited, "scopes": scopes,
                    "persistence": "state_directory" if self.path is not None else "instance_only"}
