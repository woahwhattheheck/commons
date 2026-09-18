#!/usr/bin/env python3
"""Atomic single-send lease coordination for Muse / OneWriter.

The module coordinates which exact session may attempt one provider mutation.
It does not send anything, authenticate provider receipts, prove buyer action,
or establish contract/payment/cash/revenue truth.

Security properties of this generation:
- ``LEASED``/``SELECTED`` is observation only, never send authority;
- only the successful atomic ``LEASED -> CONSUMED`` transition returns a
  plaintext one-time GO capability;
- the database stores only SHA-256 of that capability, so status/HOLD/duplicate
  paths cannot recover it from retained state;
- every mutation verifies the current lease row is bound to the latest valid
  audit receipt before it can grant or advance authority;
- public ``*_current`` entry points capture process UTC at module initialization;
  explicit-time helpers are private deterministic test surfaces.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import secrets
import sqlite3
import time
import unicodedata
from pathlib import Path
from typing import Any, Callable

SCHEMA = "commons.muse-send-lease/v2"
AUDIT_SCHEMA = "commons.muse-send-lease-audit/v2"
ROW_BINDING_SCHEMA = "commons.muse-send-lease-row-binding/v1"
MAX_TEXT = 512
MIN_TTL_SECONDS = 1
MAX_TTL_SECONDS = 3600

LEASED = "LEASED"
CONSUMED = "CONSUMED"
SENT = "SENT"
HOLD_NEEDS_RECONCILIATION = "HOLD_NEEDS_RECONCILIATION"
HOLD_EXPIRED_UNCONSUMED = "HOLD_EXPIRED_UNCONSUMED"
HOLD_RECONCILED_NO_SEND = "HOLD_RECONCILED_NO_SEND"

TERMINAL_OR_HOLD = {
    SENT,
    HOLD_NEEDS_RECONCILIATION,
    HOLD_EXPIRED_UNCONSUMED,
    HOLD_RECONCILED_NO_SEND,
}

_PRIVATE_ROW_FIELDS = {"go_token_sha256"}


class LeaseError(ValueError):
    pass


def _canonical(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError, UnicodeEncodeError) as exc:
        raise LeaseError("value is not canonical JSON") from exc


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _token_digest(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _text(value: Any, name: str, *, maximum: int = MAX_TEXT) -> str:
    if type(value) is not str or not value or len(value) > maximum:
        raise LeaseError(f"{name} must be non-empty text <= {maximum} chars")
    if value != value.strip():
        raise LeaseError(f"{name} must not have leading/trailing whitespace")
    if unicodedata.normalize("NFC", value) != value:
        raise LeaseError(f"{name} must use NFC-normalized Unicode")
    visible_base = False
    for ch in value:
        category = unicodedata.category(ch)
        if category.startswith("C"):
            raise LeaseError(f"{name} contains a control/format/surrogate codepoint")
        if not ch.isspace() and not category.startswith("M"):
            visible_base = True
    if not visible_base:
        raise LeaseError(f"{name} must contain a visible base character")
    return value


def _integer(value: Any, name: str, *, minimum: int = 0, maximum: int = 2**53 - 1) -> int:
    if type(value) is not int or value < minimum or value > maximum:
        raise LeaseError(f"{name} must be integer in [{minimum},{maximum}]")
    return value


def _identity(operation_key: str, counterparty: str, route: str, purpose: str) -> dict[str, str]:
    return {
        "operation_key": _text(operation_key, "operation_key", maximum=240),
        "counterparty": _text(counterparty, "counterparty"),
        "route": _text(route, "route"),
        "purpose": _text(purpose, "purpose"),
    }


def semantic_key(operation_key: str, counterparty: str, route: str, purpose: str) -> str:
    return _digest({"schema": "commons.muse-send-semantic-key/v1", **_identity(operation_key, counterparty, route, purpose)})


def _connect(db_path: str | os.PathLike[str]) -> sqlite3.Connection:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=30.0, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA busy_timeout=30000")
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS send_leases (
            lease_id TEXT PRIMARY KEY,
            semantic_key TEXT NOT NULL UNIQUE,
            operation_key TEXT NOT NULL,
            counterparty TEXT NOT NULL,
            route TEXT NOT NULL,
            purpose TEXT NOT NULL,
            seat TEXT NOT NULL,
            selected_session TEXT NOT NULL,
            issued_at_s INTEGER NOT NULL,
            expires_at_s INTEGER NOT NULL,
            status TEXT NOT NULL,
            consumed_by_session TEXT,
            consumed_at_s INTEGER,
            go_token_sha256 TEXT UNIQUE,
            provider TEXT,
            provider_message_id TEXT,
            committed_at_s INTEGER,
            reconciliation_note TEXT,
            version INTEGER NOT NULL
        );
        CREATE UNIQUE INDEX IF NOT EXISTS send_lease_provider_receipt_unique
          ON send_leases(provider, provider_message_id)
          WHERE provider IS NOT NULL AND provider_message_id IS NOT NULL;
        CREATE TABLE IF NOT EXISTS send_lease_audit (
            audit_id INTEGER PRIMARY KEY AUTOINCREMENT,
            lease_id TEXT NOT NULL,
            event_type TEXT NOT NULL,
            event_at_s INTEGER NOT NULL,
            session_nonce TEXT,
            previous_status TEXT,
            next_status TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            previous_receipt_sha256 TEXT,
            receipt_sha256 TEXT NOT NULL UNIQUE,
            FOREIGN KEY(lease_id) REFERENCES send_leases(lease_id)
        );
        """
    )
    return conn


def _public_row(row: sqlite3.Row) -> dict[str, Any]:
    raw = dict(row)
    for key in _PRIVATE_ROW_FIELDS:
        raw.pop(key, None)
    raw.update(
        {
            "schema": SCHEMA,
            "coordination_only": True,
            "provider_send_independently_verified": False,
            "buyer_acceptance_authority": False,
            "contract_authority": False,
            "payment_authority": False,
            "cash_authority": False,
            "revenue_authority": False,
        }
    )
    return raw


def _row_binding(row: sqlite3.Row) -> str:
    return _digest({"schema": ROW_BINDING_SCHEMA, "row": dict(row)})


def _fetch(conn: sqlite3.Connection, lease_id: str) -> sqlite3.Row:
    lease_id = _text(lease_id, "lease_id", maximum=128)
    row = conn.execute("SELECT * FROM send_leases WHERE lease_id=?", (lease_id,)).fetchone()
    if row is None:
        raise LeaseError("unknown lease_id")
    return row


def _audit(
    conn: sqlite3.Connection,
    *,
    row: sqlite3.Row,
    event_type: str,
    event_at_s: int,
    session_nonce: str | None,
    previous_status: str | None,
    payload: dict[str, Any] | None = None,
) -> str:
    previous = conn.execute(
        "SELECT receipt_sha256 FROM send_lease_audit WHERE lease_id=? ORDER BY audit_id DESC LIMIT 1",
        (row["lease_id"],),
    ).fetchone()
    previous_sha = previous[0] if previous else None
    bound_payload = dict(payload or {})
    bound_payload["row_sha256"] = _row_binding(row)
    event = {
        "schema": AUDIT_SCHEMA,
        "lease_id": row["lease_id"],
        "event_type": event_type,
        "event_at_s": event_at_s,
        "session_nonce": session_nonce,
        "previous_status": previous_status,
        "next_status": row["status"],
        "payload": bound_payload,
        "previous_receipt_sha256": previous_sha,
    }
    receipt = _digest(event)
    conn.execute(
        """INSERT INTO send_lease_audit
           (lease_id,event_type,event_at_s,session_nonce,previous_status,next_status,payload_json,previous_receipt_sha256,receipt_sha256)
           VALUES (?,?,?,?,?,?,?,?,?)""",
        (
            row["lease_id"],
            event_type,
            event_at_s,
            session_nonce,
            previous_status,
            row["status"],
            _canonical(bound_payload).decode("utf-8"),
            previous_sha,
            receipt,
        ),
    )
    return receipt


def _verify_audit(conn: sqlite3.Connection, row: sqlite3.Row) -> tuple[list[dict[str, Any]], str]:
    events = conn.execute(
        "SELECT audit_id,event_type,event_at_s,session_nonce,previous_status,next_status,payload_json,previous_receipt_sha256,receipt_sha256 "
        "FROM send_lease_audit WHERE lease_id=? ORDER BY audit_id",
        (row["lease_id"],),
    ).fetchall()
    if not events:
        raise LeaseError("lease has no audit origin")
    audit: list[dict[str, Any]] = []
    previous = None
    for event in events:
        item = dict(event)
        if item["previous_receipt_sha256"] != previous:
            raise LeaseError("audit chain predecessor mismatch")
        try:
            payload = json.loads(item.pop("payload_json"))
        except (json.JSONDecodeError, TypeError, ValueError) as exc:
            raise LeaseError("audit payload is not valid JSON") from exc
        replay = {
            "schema": AUDIT_SCHEMA,
            "lease_id": row["lease_id"],
            "event_type": item["event_type"],
            "event_at_s": item["event_at_s"],
            "session_nonce": item["session_nonce"],
            "previous_status": item["previous_status"],
            "next_status": item["next_status"],
            "payload": payload,
            "previous_receipt_sha256": item["previous_receipt_sha256"],
        }
        if _digest(replay) != item["receipt_sha256"]:
            raise LeaseError("audit receipt digest mismatch")
        previous = item["receipt_sha256"]
        item["payload"] = payload
        audit.append(item)
    latest = audit[-1]
    if latest["next_status"] != row["status"]:
        raise LeaseError("lease row status diverges from audit head")
    if latest["payload"].get("row_sha256") != _row_binding(row):
        raise LeaseError("lease row diverges from audit head")
    return audit, previous


def _assert_identity(row: sqlite3.Row, identity: dict[str, str]) -> None:
    for key, value in identity.items():
        if row[key] != value:
            raise LeaseError(f"lease {key} mismatch")


def _issue_at(
    db_path: str | os.PathLike[str],
    *,
    operation_key: str,
    counterparty: str,
    route: str,
    purpose: str,
    seat: str,
    session_nonce: str,
    ttl_seconds: int,
    now_s: int,
) -> dict[str, Any]:
    identity = _identity(operation_key, counterparty, route, purpose)
    seat = _text(seat, "seat", maximum=160)
    session_nonce = _text(session_nonce, "session_nonce", maximum=160)
    ttl_seconds = _integer(ttl_seconds, "ttl_seconds", minimum=MIN_TTL_SECONDS, maximum=MAX_TTL_SECONDS)
    now_s = _integer(now_s, "now_s")
    semantic = semantic_key(**identity)
    conn = _connect(db_path)
    try:
        conn.execute("BEGIN IMMEDIATE")
        existing = conn.execute("SELECT * FROM send_leases WHERE semantic_key=?", (semantic,)).fetchone()
        if existing is not None:
            _verify_audit(conn, existing)
            _assert_identity(existing, identity)
            conn.commit()
            result = _public_row(existing)
            result.update({"decision": "EXISTING_LEASE", "send_gate": "HOLD"})
            return result
        expires = now_s + ttl_seconds
        lease_id = _digest(
            {
                "schema": "commons.muse-send-lease-id/v1",
                "semantic_key": semantic,
                "seat": seat,
                "selected_session": session_nonce,
                "issued_at_s": now_s,
                "expires_at_s": expires,
                "nonce": secrets.token_hex(16),
            }
        )
        conn.execute(
            """INSERT INTO send_leases
               (lease_id,semantic_key,operation_key,counterparty,route,purpose,seat,selected_session,
                issued_at_s,expires_at_s,status,version)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,1)""",
            (
                lease_id,
                semantic,
                identity["operation_key"],
                identity["counterparty"],
                identity["route"],
                identity["purpose"],
                seat,
                session_nonce,
                now_s,
                expires,
                LEASED,
            ),
        )
        row = _fetch(conn, lease_id)
        audit_sha = _audit(
            conn,
            row=row,
            event_type="LEASE_ISSUED",
            event_at_s=now_s,
            session_nonce=session_nonce,
            previous_status=None,
            payload={"semantic_key": semantic, "seat": seat, "expires_at_s": expires},
        )
        conn.commit()
        result = _public_row(row)
        result.update(
            {
                "decision": "LEASE_ISSUED",
                "send_gate": "HOLD_UNTIL_CONSUME_GO",
                "audit_receipt_sha256": audit_sha,
            }
        )
        return result
    except Exception:
        if conn.in_transaction:
            conn.rollback()
        raise
    finally:
        conn.close()


def _expire_locked(conn: sqlite3.Connection, row: sqlite3.Row, now_s: int) -> sqlite3.Row:
    _verify_audit(conn, row)
    if now_s < row["expires_at_s"] or row["status"] in TERMINAL_OR_HOLD:
        return row
    if row["status"] == LEASED:
        next_status = HOLD_EXPIRED_UNCONSUMED
    elif row["status"] == CONSUMED:
        next_status = HOLD_NEEDS_RECONCILIATION
    else:
        return row
    updated = conn.execute(
        "UPDATE send_leases SET status=?,version=version+1 WHERE lease_id=? AND status=? AND version=?",
        (next_status, row["lease_id"], row["status"], row["version"]),
    )
    if updated.rowcount != 1:
        raise LeaseError("lease generation changed during expiry")
    new_row = _fetch(conn, row["lease_id"])
    _audit(
        conn,
        row=new_row,
        event_type="LEASE_EXPIRED",
        event_at_s=now_s,
        session_nonce=row["consumed_by_session"],
        previous_status=row["status"],
        payload={"expires_at_s": row["expires_at_s"]},
    )
    return new_row


def _consume_at(
    db_path: str | os.PathLike[str],
    *,
    lease_id: str,
    operation_key: str,
    counterparty: str,
    route: str,
    purpose: str,
    session_nonce: str,
    now_s: int,
) -> dict[str, Any]:
    identity = _identity(operation_key, counterparty, route, purpose)
    session_nonce = _text(session_nonce, "session_nonce", maximum=160)
    now_s = _integer(now_s, "now_s")
    conn = _connect(db_path)
    try:
        conn.execute("BEGIN IMMEDIATE")
        row = _fetch(conn, lease_id)
        _verify_audit(conn, row)
        _assert_identity(row, identity)
        row = _expire_locked(conn, row, now_s)
        if row["selected_session"] != session_nonce:
            conn.commit()
            result = _public_row(row)
            result.update({"decision": "HOLD_SESSION_MISMATCH", "send_gate": "HOLD"})
            return result
        if row["status"] != LEASED:
            conn.commit()
            result = _public_row(row)
            result.update(
                {
                    "decision": "HOLD_ALREADY_CONSUMED" if row["status"] == CONSUMED else f"HOLD_{row['status']}",
                    "send_gate": "HOLD",
                    "holder": row["consumed_by_session"],
                }
            )
            return result
        go_token = secrets.token_urlsafe(32)
        go_sha = _token_digest(go_token)
        updated = conn.execute(
            """UPDATE send_leases
               SET status=?,consumed_by_session=?,consumed_at_s=?,go_token_sha256=?,version=version+1
               WHERE lease_id=? AND status=? AND version=?""",
            (CONSUMED, session_nonce, now_s, go_sha, row["lease_id"], LEASED, row["version"]),
        )
        if updated.rowcount != 1:
            raise LeaseError("lease consume CAS lost")
        new_row = _fetch(conn, row["lease_id"])
        audit_sha = _audit(
            conn,
            row=new_row,
            event_type="LEASE_CONSUMED_GO",
            event_at_s=now_s,
            session_nonce=session_nonce,
            previous_status=LEASED,
            payload={"capability_issued": True},
        )
        conn.commit()
        result = _public_row(new_row)
        result.update(
            {
                "decision": "GO",
                "send_gate": "GO_ONCE",
                "go_token": go_token,
                "audit_receipt_sha256": audit_sha,
            }
        )
        return result
    except Exception:
        if conn.in_transaction:
            conn.rollback()
        raise
    finally:
        conn.close()


def _commit_at(
    db_path: str | os.PathLike[str],
    *,
    lease_id: str,
    session_nonce: str,
    go_token: str,
    provider: str,
    provider_message_id: str,
    now_s: int,
) -> dict[str, Any]:
    session_nonce = _text(session_nonce, "session_nonce", maximum=160)
    go_token = _text(go_token, "go_token", maximum=128)
    go_sha = _token_digest(go_token)
    provider = _text(provider, "provider", maximum=80)
    provider_message_id = _text(provider_message_id, "provider_message_id", maximum=240)
    now_s = _integer(now_s, "now_s")
    conn = _connect(db_path)
    try:
        conn.execute("BEGIN IMMEDIATE")
        row = _fetch(conn, lease_id)
        _verify_audit(conn, row)
        if row["status"] == SENT:
            same = (
                row["consumed_by_session"] == session_nonce
                and row["go_token_sha256"] == go_sha
                and row["provider"] == provider
                and row["provider_message_id"] == provider_message_id
            )
            if not same:
                raise LeaseError("terminal SENT commit tuple mismatch")
            conn.commit()
            result = _public_row(row)
            result.update({"decision": "COMMIT_ALREADY_RECORDED", "send_gate": "TERMINAL_SENT"})
            return result
        row = _expire_locked(conn, row, now_s)
        if row["status"] == HOLD_NEEDS_RECONCILIATION:
            conn.commit()
            result = _public_row(row)
            result.update({"decision": "HOLD_NEEDS_RECONCILIATION", "send_gate": "HOLD"})
            return result
        if row["status"] != CONSUMED:
            raise LeaseError("lease is not in CONSUMED state")
        if row["consumed_by_session"] != session_nonce or row["go_token_sha256"] != go_sha:
            raise LeaseError("commit session/go token mismatch")
        try:
            updated = conn.execute(
                """UPDATE send_leases
                   SET status=?,provider=?,provider_message_id=?,committed_at_s=?,version=version+1
                   WHERE lease_id=? AND status=? AND version=?""",
                (SENT, provider, provider_message_id, now_s, row["lease_id"], CONSUMED, row["version"]),
            )
        except sqlite3.IntegrityError as exc:
            raise LeaseError("provider receipt already bound to another lease") from exc
        if updated.rowcount != 1:
            raise LeaseError("lease commit CAS lost")
        new_row = _fetch(conn, row["lease_id"])
        audit_sha = _audit(
            conn,
            row=new_row,
            event_type="PROVIDER_RECEIPT_COMMITTED",
            event_at_s=now_s,
            session_nonce=session_nonce,
            previous_status=CONSUMED,
            payload={"provider": provider, "provider_message_id": provider_message_id},
        )
        conn.commit()
        result = _public_row(new_row)
        result.update(
            {
                "decision": "COMMIT_RECORDED",
                "send_gate": "TERMINAL_SENT",
                "provider_receipt_claim_recorded": True,
                "audit_receipt_sha256": audit_sha,
            }
        )
        return result
    except Exception:
        if conn.in_transaction:
            conn.rollback()
        raise
    finally:
        conn.close()


def _expire_at(db_path: str | os.PathLike[str], *, lease_id: str, now_s: int) -> dict[str, Any]:
    now_s = _integer(now_s, "now_s")
    conn = _connect(db_path)
    try:
        conn.execute("BEGIN IMMEDIATE")
        row = _fetch(conn, lease_id)
        _verify_audit(conn, row)
        row = _expire_locked(conn, row, now_s)
        conn.commit()
        result = _public_row(row)
        result.update(
            {
                "decision": "EXPIRE_EVALUATED",
                "send_gate": "HOLD" if row["status"] != SENT else "TERMINAL_SENT",
            }
        )
        return result
    except Exception:
        if conn.in_transaction:
            conn.rollback()
        raise
    finally:
        conn.close()


def _reconcile_at(
    db_path: str | os.PathLike[str],
    *,
    lease_id: str,
    provider_seen: bool,
    provider: str | None,
    provider_message_id: str | None,
    note: str,
    now_s: int,
) -> dict[str, Any]:
    if type(provider_seen) is not bool:
        raise LeaseError("provider_seen must be bool")
    note = _text(note, "note")
    now_s = _integer(now_s, "now_s")
    if provider_seen:
        provider = _text(provider, "provider", maximum=80)
        provider_message_id = _text(provider_message_id, "provider_message_id", maximum=240)
    elif provider is not None or provider_message_id is not None:
        raise LeaseError("provider tuple must be absent when provider_seen=false")
    conn = _connect(db_path)
    try:
        conn.execute("BEGIN IMMEDIATE")
        row = _fetch(conn, lease_id)
        _verify_audit(conn, row)
        row = _expire_locked(conn, row, now_s)
        if row["status"] != HOLD_NEEDS_RECONCILIATION:
            raise LeaseError("reconciliation is only valid from HOLD_NEEDS_RECONCILIATION")
        next_status = SENT if provider_seen else HOLD_RECONCILED_NO_SEND
        try:
            updated = conn.execute(
                """UPDATE send_leases SET status=?,provider=?,provider_message_id=?,committed_at_s=?,
                   reconciliation_note=?,version=version+1 WHERE lease_id=? AND status=? AND version=?""",
                (
                    next_status,
                    provider,
                    provider_message_id,
                    now_s if provider_seen else None,
                    note,
                    row["lease_id"],
                    HOLD_NEEDS_RECONCILIATION,
                    row["version"],
                ),
            )
        except sqlite3.IntegrityError as exc:
            raise LeaseError("provider receipt already bound to another lease") from exc
        if updated.rowcount != 1:
            raise LeaseError("reconciliation CAS lost")
        new_row = _fetch(conn, row["lease_id"])
        audit_sha = _audit(
            conn,
            row=new_row,
            event_type="PROVIDER_CENSUS_RECONCILED",
            event_at_s=now_s,
            session_nonce=row["consumed_by_session"],
            previous_status=HOLD_NEEDS_RECONCILIATION,
            payload={
                "provider_seen": provider_seen,
                "provider": provider,
                "provider_message_id": provider_message_id,
                "note": note,
                "authority": "OPERATOR_RETAINED_PROVIDER_CENSUS_ASSERTION_ONLY",
            },
        )
        conn.commit()
        result = _public_row(new_row)
        result.update(
            {
                "decision": "RECONCILED_PROVIDER_SEEN" if provider_seen else "RECONCILED_NO_SEND_OBSERVED",
                "send_gate": "TERMINAL_SENT" if provider_seen else "HOLD_NEW_GENERATION_REQUIRED",
                "provider_receipt_claim_recorded": provider_seen,
                "audit_receipt_sha256": audit_sha,
            }
        )
        return result
    except Exception:
        if conn.in_transaction:
            conn.rollback()
        raise
    finally:
        conn.close()


def status(db_path: str | os.PathLike[str], *, lease_id: str) -> dict[str, Any]:
    conn = _connect(db_path)
    try:
        row = _fetch(conn, lease_id)
        audit, head = _verify_audit(conn, row)
        result = _public_row(row)
        result["audit"] = audit
        result["audit_head_sha256"] = head
        result["send_gate"] = "TERMINAL_SENT" if row["status"] == SENT else "HOLD"
        return result
    finally:
        conn.close()


def _process_clock_factory(_time_ns: Callable[[], int] = time.time_ns) -> Callable[[], int]:
    def sample() -> int:
        return _integer(_time_ns() // 1_000_000_000, "process_now_s")

    return sample


def _bind_current_api(clock: Callable[[], int]):
    issue_impl, consume_impl, commit_impl, expire_impl, reconcile_impl = (
        _issue_at,
        _consume_at,
        _commit_at,
        _expire_at,
        _reconcile_at,
    )

    def issue_current(db_path, *, operation_key, counterparty, route, purpose, seat, session_nonce, ttl_seconds=300):
        return issue_impl(
            db_path,
            operation_key=operation_key,
            counterparty=counterparty,
            route=route,
            purpose=purpose,
            seat=seat,
            session_nonce=session_nonce,
            ttl_seconds=ttl_seconds,
            now_s=clock(),
        )

    def consume_current(db_path, *, lease_id, operation_key, counterparty, route, purpose, session_nonce):
        return consume_impl(
            db_path,
            lease_id=lease_id,
            operation_key=operation_key,
            counterparty=counterparty,
            route=route,
            purpose=purpose,
            session_nonce=session_nonce,
            now_s=clock(),
        )

    def commit_current(db_path, *, lease_id, session_nonce, go_token, provider, provider_message_id):
        return commit_impl(
            db_path,
            lease_id=lease_id,
            session_nonce=session_nonce,
            go_token=go_token,
            provider=provider,
            provider_message_id=provider_message_id,
            now_s=clock(),
        )

    def expire_current(db_path, *, lease_id):
        return expire_impl(db_path, lease_id=lease_id, now_s=clock())

    def reconcile_current(db_path, *, lease_id, provider_seen, provider=None, provider_message_id=None, note):
        return reconcile_impl(
            db_path,
            lease_id=lease_id,
            provider_seen=provider_seen,
            provider=provider,
            provider_message_id=provider_message_id,
            note=note,
            now_s=clock(),
        )

    return issue_current, consume_current, commit_current, expire_current, reconcile_current


issue_current, consume_current, commit_current, expire_current, reconcile_current = _bind_current_api(_process_clock_factory())


def _emit(value: dict[str, Any]) -> None:
    print(_canonical(value).decode("utf-8"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Atomic Muse/OneWriter provider-send lease coordinator")
    parser.add_argument("--db", required=True)
    subs = parser.add_subparsers(dest="command", required=True)

    issue = subs.add_parser("issue")
    for name in ("operation-key", "counterparty", "route", "purpose", "seat", "session"):
        issue.add_argument(f"--{name}", required=True)
    issue.add_argument("--ttl", type=int, default=300)

    consume = subs.add_parser("consume")
    for name in ("lease-id", "operation-key", "counterparty", "route", "purpose", "session"):
        consume.add_argument(f"--{name}", required=True)

    commit = subs.add_parser("commit")
    for name in ("lease-id", "session", "go-token", "provider", "provider-message-id"):
        commit.add_argument(f"--{name}", required=True)

    expire = subs.add_parser("expire")
    expire.add_argument("--lease-id", required=True)

    stat = subs.add_parser("status")
    stat.add_argument("--lease-id", required=True)

    reconcile = subs.add_parser("reconcile")
    reconcile.add_argument("--lease-id", required=True)
    reconcile.add_argument("--provider-seen", choices=("yes", "no"), required=True)
    reconcile.add_argument("--provider")
    reconcile.add_argument("--provider-message-id")
    reconcile.add_argument("--note", required=True)

    args = parser.parse_args(argv)
    try:
        if args.command == "issue":
            result = issue_current(
                args.db,
                operation_key=args.operation_key,
                counterparty=args.counterparty,
                route=args.route,
                purpose=args.purpose,
                seat=args.seat,
                session_nonce=args.session,
                ttl_seconds=args.ttl,
            )
        elif args.command == "consume":
            result = consume_current(
                args.db,
                lease_id=args.lease_id,
                operation_key=args.operation_key,
                counterparty=args.counterparty,
                route=args.route,
                purpose=args.purpose,
                session_nonce=args.session,
            )
        elif args.command == "commit":
            result = commit_current(
                args.db,
                lease_id=args.lease_id,
                session_nonce=args.session,
                go_token=args.go_token,
                provider=args.provider,
                provider_message_id=args.provider_message_id,
            )
        elif args.command == "expire":
            result = expire_current(args.db, lease_id=args.lease_id)
        elif args.command == "status":
            result = status(args.db, lease_id=args.lease_id)
        else:
            result = reconcile_current(
                args.db,
                lease_id=args.lease_id,
                provider_seen=args.provider_seen == "yes",
                provider=args.provider,
                provider_message_id=args.provider_message_id,
                note=args.note,
            )
        _emit({"ok": True, **result})
        return 0
    except (LeaseError, sqlite3.Error, OSError) as exc:
        _emit({"ok": False, "error": str(exc)})
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
