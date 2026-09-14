"""SQLite generation ownership and schema setup."""

from __future__ import annotations
import os
import sqlite3
import stat
from pathlib import Path
from .codec import now_utc
from .constants import DB_SCHEMA
from .errors import PacemakerError, StoreInvariantError


class StoreBase:
    def __init__(self, path: Path, *, clock=now_utc) -> None:
        self.path = Path(path)
        self.clock = clock
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.exists():
            info = self.path.stat()
            if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
                raise PacemakerError("database must be one ordinary single-link file")
        self._init()

    def _connect(self) -> sqlite3.Connection:
        db = sqlite3.connect(str(self.path), timeout=30, isolation_level=None)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA busy_timeout=30000")
        return db

    def _init(self) -> None:
        db = self._connect()
        try:
            db.executescript("""
            CREATE TABLE IF NOT EXISTS meta(
              singleton INTEGER PRIMARY KEY CHECK(singleton=1), schema TEXT NOT NULL,
              last_claim_at TEXT, cooldown_until TEXT, cooldown_reason TEXT);
            INSERT OR IGNORE INTO meta(singleton,schema)
              VALUES(1,'commons-github-content-write-pacemaker-db/v2');
            CREATE TABLE IF NOT EXISTS mutations(
              seq INTEGER PRIMARY KEY AUTOINCREMENT,
              mutation_key TEXT NOT NULL UNIQUE,
              semantic_sha256 TEXT NOT NULL UNIQUE,
              intent_sha256 TEXT NOT NULL,
              method TEXT NOT NULL, api_path TEXT NOT NULL,
              description TEXT NOT NULL, body_json BLOB NOT NULL,
              body_sha256 TEXT NOT NULL, state TEXT NOT NULL,
              attempts INTEGER NOT NULL DEFAULT 0,
              enqueued_at TEXT NOT NULL, updated_at TEXT NOT NULL,
              claimed_at TEXT, retry_at TEXT, provider_status INTEGER,
              provider_receipt_sha256 TEXT, observation_ref_sha256 TEXT,
              observation_sha256 TEXT, reason TEXT NOT NULL);
            """)
            os.chmod(self.path, 0o600)
            schema = db.execute("SELECT schema FROM meta WHERE singleton=1").fetchone()[0]
            if schema != DB_SCHEMA:
                raise StoreInvariantError("database schema mismatch")
        finally:
            db.close()
