#!/usr/bin/env python3
"""Deterministic evidence gate for regulated/high-consequence logistics handoffs.

The module evaluates *evidence completeness only*. PASS_EVIDENCE never authorizes
release, clinical use, regulatory compliance, routing, dispatch, or buyer acceptance.
"""
from __future__ import annotations

import hashlib
import json
import math
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any

SCHEMA_VERSION = 1
RECEIPT_SCHEMA = "regulated-handoff-evidence-receipt/v1"
BUNDLE_SCHEMA = "regulated-handoff-evidence-bundle/v1"
EVENT_KINDS = frozenset({"custody_transfer", "temperature", "exception_open", "exception_resolve", "checkpoint"})


class EvidenceError(ValueError):
    """Structured fail-closed input/conflict error."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def _fail(code: str, message: str) -> None:
    raise EvidenceError(code, message)


def _obj(value: Any, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        _fail("INVALID_INPUT", f"{field} must be an object")
    return value


def _text(value: Any, field: str, *, min_len: int = 1, max_len: int = 300) -> str:
    if not isinstance(value, str):
        _fail("INVALID_INPUT", f"{field} must be text")
    normalized = " ".join(value.strip().split())
    if not (min_len <= len(normalized) <= max_len):
        _fail("INVALID_INPUT", f"{field} length out of bounds")
    return normalized


def _sha(value: Any, field: str) -> str:
    digest = _text(value, field, min_len=64, max_len=64).lower()
    if any(ch not in "0123456789abcdef" for ch in digest):
        _fail("INVALID_INPUT", f"{field} must be SHA-256 hex")
    return digest


def _boolean(value: Any, field: str) -> bool:
    if not isinstance(value, bool):
        _fail("INVALID_INPUT", f"{field} must be boolean")
    return value


def _integer(value: Any, field: str, *, minimum: int = 0, maximum: int | None = None) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        _fail("INVALID_INPUT", f"{field} must be an integer")
    if value < minimum or (maximum is not None and value > maximum):
        _fail("INVALID_INPUT", f"{field} out of bounds")
    return value


def _decimal(value: Any, field: str) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, (str, int, float, Decimal)):
        _fail("INVALID_INPUT", f"{field} must be decimal-compatible")
    if isinstance(value, float) and not math.isfinite(value):
        _fail("INVALID_INPUT", f"{field} must be finite")
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, ValueError):
        _fail("INVALID_INPUT", f"{field} must be decimal-compatible")
    if not parsed.is_finite():
        _fail("INVALID_INPUT", f"{field} must be finite")
    return parsed


def _decimal_text(value: Decimal) -> str:
    value = value.normalize()
    if value == 0:
        return "0"
    text = format(value, "f")
    return text.rstrip("0").rstrip(".") if "." in text else text


def _timestamp(value: Any, field: str) -> tuple[str, datetime]:
    raw = _text(value, field, min_len=20, max_len=40)
    candidate = raw[:-1] + "+00:00" if raw.endswith("Z") else raw
    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError:
        _fail("INVALID_INPUT", f"{field} must be RFC3339")
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        _fail("INVALID_INPUT", f"{field} must include an offset")
    utc = parsed.astimezone(timezone.utc)
    return utc.isoformat(timespec="microseconds").replace("+00:00", "Z"), utc


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()

