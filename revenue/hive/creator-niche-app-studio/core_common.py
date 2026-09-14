from __future__ import annotations

import datetime as dt
import hashlib
import json
import re
from typing import Any

SCHEMA_VERSION = "creator-niche-app-studio/v1"
MAX_JSON_BYTES = 1_000_000
MAX_TEXT = 240
MAX_SUPPORT_TEXT = 2_000
CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
HEX_COLOR_RE = re.compile(r"^#[0-9a-fA-F]{6}$")
ID_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._-]{0,63}$")

TIERS: dict[str, dict[str, int]] = {
    "starter": {"max_active_plans": 3, "max_expected_attendees": 60, "max_items": 40},
    "studio": {"max_active_plans": 25, "max_expected_attendees": 500, "max_items": 250},
}


class StudioError(Exception):
    code = "STUDIO_ERROR"
    status = 400

    def __init__(self, message: str, *, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def as_dict(self) -> dict[str, Any]:
        return {"error": self.code, "message": self.message, "details": self.details}


class ValidationError(StudioError):
    code = "VALIDATION_ERROR"
    status = 422


class ConflictError(StudioError):
    code = "CONFLICT"
    status = 409


class NotFoundError(StudioError):
    code = "NOT_FOUND"
    status = 404


class LimitError(StudioError):
    code = "PLAN_LIMIT"
    status = 409


def _reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise ValidationError(f"duplicate JSON key: {key}")
        out[key] = value
    return out


def loads_strict(raw: bytes | str) -> Any:
    if isinstance(raw, str):
        raw_bytes = raw.encode("utf-8")
        text = raw
    else:
        raw_bytes = raw
        try:
            text = raw.decode("utf-8", errors="strict")
        except UnicodeDecodeError as exc:
            raise ValidationError("JSON must be UTF-8") from exc
    if len(raw_bytes) > MAX_JSON_BYTES:
        raise ValidationError("JSON body exceeds 1,000,000 bytes")
    try:
        return json.loads(
            text,
            object_pairs_hook=_reject_duplicates,
            parse_constant=lambda value: (_ for _ in ()).throw(ValidationError(f"non-finite JSON number: {value}")),
        )
    except StudioError:
        raise
    except (json.JSONDecodeError, TypeError, ValueError) as exc:
        raise ValidationError("invalid JSON") from exc


def canonical_bytes(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ValidationError("value is not canonical JSON") from exc


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_sha(value: Any) -> str:
    return sha256_bytes(canonical_bytes(value))


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _text(value: Any, field: str, *, max_len: int = MAX_TEXT, allow_empty: bool = False) -> str:
    if not isinstance(value, str):
        raise ValidationError(f"{field} must be a string")
    value = value.strip()
    if not value and not allow_empty:
        raise ValidationError(f"{field} cannot be empty")
    if len(value) > max_len:
        raise ValidationError(f"{field} exceeds {max_len} characters")
    if CONTROL_RE.search(value):
        raise ValidationError(f"{field} contains control characters")
    return value


def _identifier(value: Any, field: str) -> str:
    value = _text(value, field, max_len=64)
    if not ID_RE.fullmatch(value):
        raise ValidationError(f"{field} must match {ID_RE.pattern}")
    return value


def _integer(value: Any, field: str, *, minimum: int = 0, maximum: int = 1_000_000) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValidationError(f"{field} must be an integer")
    if not minimum <= value <= maximum:
        raise ValidationError(f"{field} must be between {minimum} and {maximum}")
    return value


def _exact_keys(value: Any, field: str, allowed: set[str], required: set[str]) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValidationError(f"{field} must be an object")
    unknown = sorted(set(value) - allowed)
    missing = sorted(required - set(value))
    if unknown:
        raise ValidationError(f"{field} has unknown fields", details={"fields": unknown})
    if missing:
        raise ValidationError(f"{field} is missing fields", details={"fields": missing})
    return value
