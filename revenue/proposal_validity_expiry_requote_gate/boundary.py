from __future__ import annotations

import datetime as _dt
import hashlib
import json
import re
from typing import Any

MAX_SAFE_INT = 9_007_199_254_740_991
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class GateError(ValueError):
    pass


def unicode_scalar(text: str, label: str) -> str:
    try:
        text.encode("utf-8", "strict")
    except UnicodeEncodeError as exc:
        raise GateError(f"{label}: invalid Unicode scalar") from exc
    return text


def text(value: Any, label: str) -> str:
    if type(value) is not str or not value.strip():
        raise GateError(f"{label}: expected non-empty text")
    unicode_scalar(value, label)
    if any(ord(ch) < 32 for ch in value):
        raise GateError(f"{label}: control characters are not allowed")
    return value


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if type(key) is not str:
            raise GateError("JSON object key must be text")
        unicode_scalar(key, "JSON object key")
        if key in out:
            raise GateError("duplicate JSON key")
        out[key] = value
    return out


def _int(token: str) -> int:
    digits = token[1:] if token.startswith("-") else token
    if not digits or len(digits) > 16:
        raise GateError("unsafe JSON integer")
    try:
        value = int(token, 10)
    except ValueError as exc:
        raise GateError("invalid JSON integer") from exc
    if not (-MAX_SAFE_INT <= value <= MAX_SAFE_INT):
        raise GateError("unsafe JSON integer")
    return value


def _float(_: str) -> None:
    raise GateError("JSON floats are not allowed")


def _constant(_: str) -> None:
    raise GateError("non-finite JSON numbers are not allowed")


def validate_tree(value: Any, label: str) -> None:
    stack: list[tuple[Any, str, int]] = [(value, label, 0)]
    while stack:
        current, current_label, depth = stack.pop()
        if depth > 256:
            raise GateError(f"{label}: JSON nesting exceeds 256")
        if current is None or type(current) is bool:
            continue
        if type(current) is str:
            unicode_scalar(current, current_label)
            continue
        if type(current) is int:
            if not (-MAX_SAFE_INT <= current <= MAX_SAFE_INT):
                raise GateError(f"{current_label}: integer exceeds safe range")
            continue
        if isinstance(current, float):
            raise GateError(f"{current_label}: floats are not allowed")
        if isinstance(current, list):
            stack.extend((item, f"{current_label}[{idx}]", depth + 1) for idx, item in enumerate(current))
            continue
        if isinstance(current, dict):
            for key, item in current.items():
                text(key, f"{current_label} key")
                stack.append((item, f"{current_label}.{key}", depth + 1))
            continue
        raise GateError(f"{current_label}: unsupported value type")


def strict_json_loads(raw: str) -> Any:
    if type(raw) is not str:
        raise GateError("JSON input must be text")
    try:
        value = json.loads(raw, object_pairs_hook=_pairs, parse_int=_int, parse_float=_float, parse_constant=_constant)
    except GateError:
        raise
    except (json.JSONDecodeError, UnicodeError, RecursionError, ValueError, OverflowError) as exc:
        raise GateError("invalid JSON runtime boundary") from exc
    try:
        validate_tree(value, "JSON")
    except GateError:
        raise
    except (UnicodeError, RecursionError, ValueError, OverflowError) as exc:
        raise GateError("invalid JSON runtime boundary") from exc
    return value


def canonical(value: Any) -> bytes:
    validate_tree(value, "canonical")
    try:
        payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)
    except (TypeError, ValueError, UnicodeError, RecursionError, OverflowError) as exc:
        raise GateError("not canonical JSON data") from exc
    return (payload + "\n").encode("utf-8")


def sha(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def exact_keys(obj: dict[str, Any], allowed: set[str], label: str) -> None:
    extra = set(obj) - allowed
    if extra:
        raise GateError(f"{label}: unknown keys: {sorted(extra)}")


def integer(value: Any, label: str, *, minimum: int | None = None) -> int:
    if type(value) is not int:
        raise GateError(f"{label}: expected integer")
    if not (-MAX_SAFE_INT <= value <= MAX_SAFE_INT):
        raise GateError(f"{label}: integer exceeds safe range")
    if minimum is not None and value < minimum:
        raise GateError(f"{label}: expected >= {minimum}")
    return value


def parse_time(value: Any, label: str) -> _dt.datetime:
    raw = text(value, label)
    try:
        parsed = _dt.datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except (ValueError, OverflowError):
        raise GateError(f"{label}: invalid ISO-8601 timestamp") from None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise GateError(f"{label}: timezone is required")
    return parsed.astimezone(_dt.timezone.utc)


def digest(value: Any, label: str) -> str:
    raw = text(value, label)
    if _SHA256_RE.fullmatch(raw) is None:
        raise GateError(f"{label}: expected lowercase sha256 hex")
    return raw
