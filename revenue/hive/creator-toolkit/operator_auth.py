"""Capability boundary for Creator Desk operator-only HTTP surfaces.

The plaintext operator key is never stored in SQLite or emitted by the server.
Initialize or rotate it explicitly with this module's local CLI. The workspace
keeps only a SHA-256 digest; there is no remote reset route.
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


class OperatorSetupRequired(RuntimeError):
    pass


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8", errors="surrogatepass")).hexdigest()


class OperatorAuth:
    """Verify one per-workspace operator capability without retaining plaintext."""

    def __init__(self, database: str | Path):
        self.database = str(database)
        Path(self.database).parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS creator_security(
                name TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )""")
            row = db.execute("SELECT value FROM creator_security WHERE name='operator_sha256'").fetchone()
        if row is None:
            raise OperatorSetupRequired(
                "Operator capability is not initialized. Run operator_auth.py --db <workspace> init before serving it."
            )

    @classmethod
    def initialize(cls, database: str | Path) -> str:
        """Create the capability once and return plaintext only to this caller."""
        database = str(database)
        Path(database).parent.mkdir(parents=True, exist_ok=True)
        key = secrets.token_urlsafe(KEY_BYTES)
        with sqlite3.connect(database, timeout=15) as db:
            db.execute("BEGIN IMMEDIATE")
            db.execute("""CREATE TABLE IF NOT EXISTS creator_security(
                name TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )""")
            row = db.execute("SELECT value FROM creator_security WHERE name='operator_sha256'").fetchone()
            if row is not None:
                raise RuntimeError("Creator Desk operator capability is already initialized; use rotate to replace it")
            db.execute("INSERT INTO creator_security(name,value) VALUES('operator_sha256',?)", (_digest(key),))
            db.commit()
        return key

    def _connect(self):
        return sqlite3.connect(self.database, timeout=15)

    def _expected(self) -> str:
        with self._connect() as db:
            row = db.execute("SELECT value FROM creator_security WHERE name='operator_sha256'").fetchone()
        if row is None:
            raise OperatorSetupRequired("Creator Desk operator capability is not initialized")
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
        """Invalidate the prior key and return one replacement to this caller."""
        key = secrets.token_urlsafe(KEY_BYTES)
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            cursor = db.execute("UPDATE creator_security SET value=? WHERE name='operator_sha256'", (_digest(key),))
            if cursor.rowcount != 1:
                raise OperatorSetupRequired("Creator Desk operator capability is not initialized")
            db.commit()
        return key


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", required=True, help="Creator Desk SQLite workspace")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("init", help="Initialize auth and print the one-time operator key")
    sub.add_parser("rotate", help="Invalidate the old operator key and print one replacement")
    args = parser.parse_args()
    if args.command == "init":
        print(OperatorAuth.initialize(args.db))
    else:
        print(OperatorAuth(args.db).rotate())


if __name__ == "__main__":
    main()
