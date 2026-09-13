"""Capability boundary for Creator Desk operator-only HTTP surfaces.

The plaintext operator key is generated once and never stored in SQLite. The
workspace keeps only a SHA-256 digest. Local filesystem authority can rotate a
lost key with this module's CLI; no remote reset route exists.
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import secrets
import sqlite3
from pathlib import Path

KEY_BYTES = 32
MAX_KEY_CHARS = 256
AUTH_SCHEME = "Bearer "


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8", errors="surrogatepass")).hexdigest()


class OperatorAuth:
    """Persist and verify one per-workspace operator capability."""

    def __init__(self, database: str | Path):
        self.database = str(database)
        Path(self.database).parent.mkdir(parents=True, exist_ok=True)
        self.bootstrap_key = None
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            db.execute("""CREATE TABLE IF NOT EXISTS creator_security(
                name TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )""")
            row = db.execute("SELECT value FROM creator_security WHERE name='operator_sha256'").fetchone()
            if row is None:
                key = secrets.token_urlsafe(KEY_BYTES)
                db.execute("INSERT INTO creator_security(name,value) VALUES('operator_sha256',?)", (_digest(key),))
                self.bootstrap_key = key
            db.commit()

    def _connect(self):
        return sqlite3.connect(self.database, timeout=15)

    def _expected(self) -> str:
        with self._connect() as db:
            row = db.execute("SELECT value FROM creator_security WHERE name='operator_sha256'").fetchone()
        if row is None:
            raise RuntimeError("Creator Desk operator capability is not initialized")
        return row[0]

    def verify(self, candidate) -> bool:
        value = candidate if isinstance(candidate, str) else ""
        if len(value) > MAX_KEY_CHARS:
            value = ""
        return hmac.compare_digest(self._expected(), _digest(value))

    def verify_header(self, authorization) -> bool:
        value = authorization if isinstance(authorization, str) else ""
        if not value.startswith(AUTH_SCHEME):
            return False
        return self.verify(value[len(AUTH_SCHEME):])

    def rotate(self) -> str:
        key = secrets.token_urlsafe(KEY_BYTES)
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            cursor = db.execute("UPDATE creator_security SET value=? WHERE name='operator_sha256'", (_digest(key),))
            if cursor.rowcount != 1:
                raise RuntimeError("Creator Desk operator capability is not initialized")
            db.commit()
        return key


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", required=True, help="Existing Creator Desk SQLite workspace")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("rotate", help="Invalidate the old operator key and print one replacement")
    args = parser.parse_args()
    auth = OperatorAuth(args.db)
    if args.command == "rotate":
        print(auth.rotate())


if __name__ == "__main__":
    main()
