"""Creator reward campaign public entry point with fail-closed startup database identity.

The implementation remains byte-for-byte in engine.py.  This wrapper is deliberately
small: it validates every pre-existing non-empty database read-only against the exact
schema emitted by that engine *before* the engine is allowed to run CREATE TABLE IF NOT
EXISTS.  New and zero-byte files remain explicit initialization paths.
"""
from contextlib import closing as _closing
from pathlib import Path as _Path
from tempfile import TemporaryDirectory as _TemporaryDirectory

import engine as _engine
from engine import *  # noqa: F401,F403 - preserve the documented single-file public surface

_EngineDesk = _engine.Desk
_EXPECTED_SCHEMA = None


def _schema_signature(db):
    """Return the complete code-owned user-schema SQL, excluding SQLite internals."""
    return tuple(db.execute(
        "SELECT type,name,tbl_name,sql FROM sqlite_master "
        "WHERE name NOT LIKE 'sqlite_%' AND sql IS NOT NULL "
        "ORDER BY type,name,tbl_name,sql"
    ).fetchall())


def _expected_schema_signature():
    """Derive the accepted format from the preserved implementation itself, not a second schema copy."""
    global _EXPECTED_SCHEMA
    if _EXPECTED_SCHEMA is None:
        with _TemporaryDirectory() as directory:
            reference = _Path(directory) / 'creator-reward-reference.sqlite3'
            _EngineDesk(reference)
            with _closing(_engine.sqlite3.connect(reference)) as db:
                _EXPECTED_SCHEMA = _schema_signature(db)
    return _EXPECTED_SCHEMA


def _validate_existing_database(target):
    """Prove a non-empty existing file is this desk format without writing a byte to it."""
    # mode=ro prevents SQLite from creating or changing the database. immutable=1 also
    # prevents journal/WAL side effects while we perform the startup identity read.
    uri = target.resolve(strict=True).as_uri() + '?mode=ro&immutable=1'
    try:
        with _closing(_engine.sqlite3.connect(uri, uri=True)) as db:
            if db.execute('PRAGMA quick_check').fetchone() != ('ok',):
                raise _engine.DeskError('database path holds a damaged SQLite database; it is left untouched')
            actual = _schema_signature(db)
    except _engine.DeskError:
        raise
    except _engine.sqlite3.DatabaseError as exc:
        raise _engine.DeskError('database path does not hold a SQLite database; it is left untouched') from exc
    if actual != _expected_schema_signature():
        raise _engine.DeskError('database path holds a SQLite database that is not a creator reward desk database; it is left untouched')


class Desk(_EngineDesk):
    """The public desk, adding only a pre-DDL identity gate to the preserved engine."""
    def __init__(self, path):
        target = _Path(path)
        if target.is_symlink() or (target.exists() and not target.is_file()):
            raise _engine.DeskError('database path must be a regular file (existing or new), never a link or a special file')
        if target.exists() and target.stat().st_size:
            _validate_existing_database(target)
        super().__init__(path)


# engine.main resolves Desk from engine's module globals at call time.  Patch that one
# symbol so CLI, demo loading, HTTP construction and direct ``server.Desk`` users share
# the exact same pre-DDL gate; every other implementation symbol remains untouched.
_engine.Desk = Desk


if __name__ == '__main__':
    raise SystemExit(_engine.main())
