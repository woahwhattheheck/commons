#!/usr/bin/env python3
"""Offline evidence gate for Muse atomic runtime adoption.

This module diagnoses whether one retained transcript is internally consistent with
one session-bound SELECTED -> LEASED -> CONSUMED -> GO sequence.  It never grants
send authority and never independently authenticates the live Muse runtime or a
provider send.
"""
from __future__ import annotations

import argparse as _argparse
import hashlib as _hashlib
import json as _json
import os as _os
import stat as _stat
import sys as _sys
import time as _time
import unicodedata as _unicodedata
from datetime import datetime as _datetime, timezone as _timezone
from pathlib import Path as _Path
from typing import Any as _Any

_INPUT_SCHEMA = "commons.muse-runtime-adoption-evidence/v1"
_OUTPUT_SCHEMA = "commons.muse-runtime-adoption-diagnostic/v1"
_VERIFY_SCHEMA = "commons.muse-runtime-adoption-verification/v1"
_MAX_INPUT_BYTES = 1_048_576
_MAX_TEXT = 512
_MAX_EVENTS = 128
_MAX_DEPTH = 20
_MAX_INT = 2**53 - 1
_MAX_FRESHNESS_SECONDS = 86_400
_EVENT_CLASSES = frozenset({"SELECTED", "LEASED", "CONSUMED", "GO", "COMMIT"})
_POSITIVE_SEQUENCE = ("SELECTED", "LEASED", "CONSUMED", "GO")
_STATUS = frozenset(
    {
        "ATOMIC_SEQUENCE_OBSERVED",
        "HOLD_SELECTED_ONLY",
        "HOLD_NO_CONSUME",
        "HOLD_NO_GO",
        "HOLD_DUPLICATE_GO",
        "HOLD_WRONG_SESSION",
        "HOLD_SCOPE_DRIFT",
        "HOLD_RUNTIME_DRIFT",
        "HOLD_STALE_CAPTURE",
        "HOLD_EVIDENCE",
    }
)
_AUTHORITY = {
    "send_authorized": False,
    "muse_authorized": False,
    "provider_action_authorized": False,
    "provider_send_proven": False,
    "buyer_acceptance": False,
    "contract_signed": False,
    "payment_authorized": False,
    "cash_proven": False,
    "receivable_asserted": False,
    "revenue_recognized": False,
}


class AdoptionGateError(ValueError):
    """Stable domain error for malformed or untrusted evidence."""


def _build_api():
    # Capture trust-bearing primitives and semantic constants once. Public module
    # rebinding after import cannot steer this generation of the exported API.
    input_schema = _INPUT_SCHEMA
    output_schema = _OUTPUT_SCHEMA
    verify_schema = _VERIFY_SCHEMA
    max_input_bytes = _MAX_INPUT_BYTES
    max_text = _MAX_TEXT
    max_events = _MAX_EVENTS
    max_depth = _MAX_DEPTH
    max_int = _MAX_INT
    max_freshness_seconds = _MAX_FRESHNESS_SECONDS
    event_classes = frozenset(_EVENT_CLASSES)
    positive_sequence = tuple(_POSITIVE_SEQUENCE)
    status_values = frozenset(_STATUS)
    authority_items = tuple(sorted(_AUTHORITY.items()))
    error_cls = AdoptionGateError
    path_cls = _Path
    sha256_ctor = _hashlib.sha256
    normalize = _unicodedata.normalize
    category = _unicodedata.category
    dt_cls = _datetime
    utc = _timezone.utc
    time_ns = _time.time_ns
    json_decoder_cls = _json.JSONDecoder
    quote_json = _json.encoder.encode_basestring_ascii
    os_open = _os.open
    os_read = _os.read
    os_fstat = _os.fstat
    os_close = _os.close
    os_flags = {
        "O_RDONLY": _os.O_RDONLY,
        "O_CLOEXEC": getattr(_os, "O_CLOEXEC", 0),
        "O_NOFOLLOW": getattr(_os, "O_NOFOLLOW", 0),
    }
    s_isreg = _stat.S_ISREG

    def fail(message: str) -> None:
        raise error_cls(message)

    def bounded_int_token(token: str) -> int:
        # Bound parser work before int() sees attacker-sized text.
        if len(token) > 16:
            fail("integer token exceeds bounded length")
        try:
            value = int(token, 10)
        except ValueError as exc:  # pragma: no cover - JSON lexer normally filters
            raise error_cls("invalid integer token") from exc
        if value < -max_int or value > max_int:
            fail("integer exceeds safe range")
        return value

    def reject_float(_token: str):
        fail("floating-point JSON is not admitted")

    def reject_constant(_token: str):
        fail("non-finite JSON is not admitted")

    def object_pairs(pairs):
        out = {}
        for key, value in pairs:
            if key in out:
                fail(f"duplicate JSON key: {key}")
            out[key] = value
        return out

    decoder = json_decoder_cls(
        object_pairs_hook=object_pairs,
        parse_int=bounded_int_token,
        parse_float=reject_float,
        parse_constant=reject_constant,
        strict=True,
    )
    raw_decode = decoder.raw_decode

    def walk_plain(value: _Any, depth: int = 0) -> None:
        if depth > max_depth:
            fail("JSON nesting exceeds limit")
        if value is None or type(value) in (bool, int, str):
            if type(value) is int and (value < -max_int or value > max_int):
                fail("integer exceeds safe range")
            if type(value) is str:
                try:
                    value.encode("utf-8")
                except UnicodeEncodeError as exc:
                    raise error_cls("lone surrogate is not admitted") from exc
            return
        if type(value) is list:
            if len(value) > max_events * 4:
                fail("array exceeds limit")
            for item in value:
                walk_plain(item, depth + 1)
            return
        if type(value) is dict:
            if len(value) > 128:
                fail("object exceeds key limit")
            for key, item in value.items():
                if type(key) is not str:
                    fail("object keys must be text")
                walk_plain(key, depth + 1)
                walk_plain(item, depth + 1)
            return
        fail("JSON value is not an exact built-in plain type")

    def loads_strict(data: str | bytes) -> _Any:
        if type(data) is bytes:
            if len(data) > max_input_bytes:
                fail("input exceeds byte limit")
            try:
                text = data.decode("utf-8")
            except UnicodeDecodeError as exc:
                raise error_cls("input must be UTF-8") from exc
        elif type(data) is str:
            try:
                encoded = data.encode("utf-8")
            except UnicodeEncodeError as exc:
                raise error_cls("input contains invalid Unicode") from exc
            if len(encoded) > max_input_bytes:
                fail("input exceeds byte limit")
            text = data
        else:
            fail("JSON input must be str or bytes")
        try:
            value, end = raw_decode(text)
        except (ValueError, RecursionError) as exc:
            if isinstance(exc, error_cls):
                raise
            raise error_cls("invalid JSON") from exc
        if text[end:].strip():
            fail("trailing JSON content is not admitted")
        walk_plain(value)
        return value

    def canonical(value: _Any) -> bytes:
        walk_plain(value)

        def enc(v: _Any, depth: int = 0) -> str:
            if depth > max_depth:
                fail("canonical JSON nesting exceeds limit")
            if v is None:
                return "null"
            if v is True:
                return "true"
            if v is False:
                return "false"
            if type(v) is int:
                return str(v)
            if type(v) is str:
                return quote_json(v)
            if type(v) is list:
                return "[" + ",".join(enc(x, depth + 1) for x in v) + "]"
            if type(v) is dict:
                parts = []
                for key in sorted(v):
                    parts.append(quote_json(key) + ":" + enc(v[key], depth + 1))
                return "{" + ",".join(parts) + "}"
            fail("unsupported canonical JSON type")
            raise AssertionError

        return enc(value).encode("utf-8")

    def digest(value: _Any) -> str:
        return sha256_ctor(canonical(value)).hexdigest()

    def text(value: _Any, name: str, *, maximum: int = max_text) -> str:
        if type(value) is not str or not value or len(value) > maximum:
            fail(f"{name} must be non-empty text <= {maximum} chars")
        if value != value.strip():
            fail(f"{name} must not have leading/trailing whitespace")
        if normalize("NFC", value) != value:
            fail(f"{name} must use NFC Unicode")
        try:
            value.encode("utf-8")
        except UnicodeEncodeError as exc:
            raise error_cls(f"{name} contains invalid Unicode") from exc
        visible = False
        for ch in value:
            cat = category(ch)
            if cat.startswith("C"):
                fail(f"{name} contains a control/format/surrogate codepoint")
            if not ch.isspace() and not cat.startswith("M"):
                visible = True
        if not visible:
            fail(f"{name} must contain a visible base character")
        return value

    def sha(value: _Any, name: str) -> str:
        value = text(value, name, maximum=64)
        if len(value) != 64 or any(ch not in "0123456789abcdef" for ch in value):
            fail(f"{name} must be lowercase SHA-256 hex")
        return value

    def integer(value: _Any, name: str, *, minimum: int = 0, maximum: int = max_int) -> int:
        if type(value) is not int or value < minimum or value > maximum:
            fail(f"{name} must be integer in [{minimum},{maximum}]")
        return value

    def exact_keys(value: _Any, name: str, keys: set[str]) -> dict[str, _Any]:
        if type(value) is not dict:
            fail(f"{name} must be an object")
        actual = set(value)
        if actual != keys:
            missing = sorted(keys - actual)
            extra = sorted(actual - keys)
            fail(f"{name} schema mismatch missing={missing} extra={extra}")
        return value

    def parse_utc(value: _Any, name: str) -> tuple[str, int]:
        value = text(value, name, maximum=32)
        if not value.endswith("Z"):
            fail(f"{name} must be canonical UTC ending in Z")
        try:
            dt = dt_cls.fromisoformat(value[:-1] + "+00:00")
        except ValueError as exc:
            raise error_cls(f"{name} is not valid UTC") from exc
        if dt.tzinfo != utc or dt.microsecond != 0:
            fail(f"{name} must be whole-second UTC")
        canonical_text = dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        if canonical_text != value:
            fail(f"{name} must be canonical whole-second UTC")
        return value, int(dt.timestamp())

    def utc_fro