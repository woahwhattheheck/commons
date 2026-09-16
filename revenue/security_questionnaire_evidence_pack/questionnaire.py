#!/usr/bin/env python3
"""Deterministic, evidence-bound enterprise security questionnaire compiler."""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import stat
from pathlib import Path, PurePosixPath
import re
import sys
from typing import Any

SCHEMA = "security-questionnaire-evidence-v1"
REPORT_SCHEMA = "security-questionnaire-report-v1"
MAX_EVIDENCE = 300
MAX_QUESTIONS = 150
MAX_ARTIFACT_BYTES = 2_000_000
ID_RE = re.compile(r"^[A-Z][A-Z0-9_.-]{0,63}$")
SHA_RE = re.compile(r"^[0-9a-f]{64}$")
STATUSES = (
    "SUPPORTED",
    "PARTIAL",
    "HOLD_MISSING_EVIDENCE",
    "HOLD_STALE_EVIDENCE",
    "NOT_APPLICABLE",
)
AUTHORITY = {
    "certifies_compliance": False,
    "attests_soc2": False,
    "attests_hipaa": False,
    "buyer_contact_authorized": False,
    "contract_acceptance_authorized": False,
    "payment_authorized": False,
    "revenue_recognition_authorized": False,
}
OFFER = {
    "fixed_sprint_usd_cents": 1_500_000,
    "optional_quarterly_refresh_usd_cents": 200_000,
    "commercial_state": "PROPOSED_NOT_ACCEPTED",
}


class PackError(ValueError):
    """Closed validation/verification failure for this evidence pack."""


def _reject_float(value: str) -> None:
    raise PackError(f"floating-point JSON is not allowed: {value}")


def _reject_constant(value: str) -> None:
    raise PackError(f"non-finite JSON is not allowed: {value}")


def _pairs_no_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise PackError(f"duplicate JSON key: {key}")
        out[key] = value
    return out


def loads_strict(raw: bytes) -> Any:
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise PackError("input must be UTF-8") from exc
    try:
        return json.loads(
            text,
            object_pairs_hook=_pairs_no_duplicates,
            parse_float=_reject_float,
            parse_constant=_reject_constant,
        )
    except PackError:
        raise
    except (json.JSONDecodeError, ValueError) as exc:
        raise PackError(f"invalid JSON: {exc}") from exc


def canonical_bytes(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise PackError(f"value is not canonical JSON: {exc}") from exc


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _keys(obj: Any, required: set[str], optional: set[str], where: str) -> dict[str, Any]:
    if type(obj) is not dict:
        raise PackError(f"{where} must be an object")
    actual = set(obj)
    missing = required - actual
    extra = actual - required - optional
    if missing or extra:
        raise PackError(f"{where} keys invalid: missing={sorted(missing)} extra={sorted(extra)}")
    return obj


def _text(value: Any, where: str, *, max_len: int = 1000) -> str:
    if type(value) is not str or not value.strip() or len(value) > max_len:
        raise PackError(f"{where} must be a non-empty string <= {max_len} chars")
    return value


def _id(value: Any, where: str) -> str:
    text = _text(value, where, max_len=64)
    if not ID_RE.fullmatch(text):
        raise PackError(f"{where} has invalid identifier syntax")
    return text


def _timestamp(value: Any, where: str) -> dt.datetime:
    text = _text(value, where, max_len=40)
    if not text.endswith("Z"):
        raise PackError(f"{where} must be an explicit UTC Z timestamp")
    try:
        parsed = dt.datetime.fromisoformat(text[:-1] + "+00:00")
    except ValueError as exc:
        raise PackError(f"{where} is not a valid timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() != dt.timedelta(0):
        raise PackError(f"{where} must be UTC")
    return parsed


def _artifact_path(value: Any, where: str) -> str:
    text = _text(value, where, max_len=240)
    if "\\" in text:
        raise PackError(f"{where} must use POSIX separators")
    pure = PurePosixPath(text)
    if pure.is_absolute() or any(part in ("", ".", "..") for part in pure.parts):
        raise PackError(f"{where} must be a clean relative path")
    return pure.as_posix()
