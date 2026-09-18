"""Private first-load authority for Muse send-lease policy and trust primitives.

Public compatibility constants in muse_send_lease are intentionally not
authority. This module is imported once and retained across ordinary reloads of
the public facade. Deliberate mutation, reload, or function surgery of this
private module is outside the cooperative-process threat boundary.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import secrets
import sqlite3
import time
import unicodedata
from typing import Any, Callable


@dataclass(frozen=True, slots=True)
class RuntimeAuthority:
    schema: str
    audit_schema: str
    row_binding_schema: str
    min_ttl_seconds: int
    max_ttl_seconds: int
    leased: str
    consumed: str
    sent: str
    hold_needs_reconciliation: str
    hold_expired_unconsumed: str
    hold_reconciled_no_send: str
    terminal_or_hold: frozenset[str]
    json_dumps: Callable[..., str]
    json_loads: Callable[..., Any]
    sha256: Callable[..., Any]
    token_hex: Callable[[int], str]
    token_urlsafe: Callable[[int], str]
    sqlite_connect: Callable[..., sqlite3.Connection]
    sqlite_integrity_error: type[BaseException]
    unicode_normalize: Callable[[str, str], str]
    unicode_category: Callable[[str], str]
    time_ns: Callable[[], int]


RUNTIME = RuntimeAuthority(
    schema="commons.muse-send-lease/v2",
    audit_schema="commons.muse-send-lease-audit/v2",
    row_binding_schema="commons.muse-send-lease-row-binding/v1",
    min_ttl_seconds=1,
    max_ttl_seconds=3600,
    leased="LEASED",
    consumed="CONSUMED",
    sent="SENT",
    hold_needs_reconciliation="HOLD_NEEDS_RECONCILIATION",
    hold_expired_unconsumed="HOLD_EXPIRED_UNCONSUMED",
    hold_reconciled_no_send="HOLD_RECONCILED_NO_SEND",
    terminal_or_hold=frozenset(
        {
            "SENT",
            "HOLD_NEEDS_RECONCILIATION",
            "HOLD_EXPIRED_UNCONSUMED",
            "HOLD_RECONCILED_NO_SEND",
        }
    ),
    json_dumps=json.dumps,
    json_loads=json.loads,
    sha256=hashlib.sha256,
    token_hex=secrets.token_hex,
    token_urlsafe=secrets.token_urlsafe,
    sqlite_connect=sqlite3.connect,
    sqlite_integrity_error=sqlite3.IntegrityError,
    unicode_normalize=unicodedata.normalize,
    unicode_category=unicodedata.category,
    time_ns=time.time_ns,
)
