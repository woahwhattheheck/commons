from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_ID = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._:-]{0,127}$")


class BidVeilError(ValueError):
    pass


def _reject_float(raw: str) -> None:
    raise BidVeilError(f"floating point numbers are not allowed: {raw}")


def _pairs_no_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise BidVeilError(f"duplicate JSON key: {key}")
        out[key] = value
    return out


def load_json_strict(path: str | Path) -> Any:
    text = Path(path).read_text(encoding="utf-8")
    try:
        return json.loads(
            text,
            object_pairs_hook=_pairs_no_duplicates,
            parse_float=_reject_float,
            parse_constant=lambda raw: (_ for _ in ()).throw(BidVeilError(f"invalid JSON number: {raw}")),
        )
    except BidVeilError:
        raise
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise BidVeilError(f"invalid JSON: {exc}") from exc


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def sha256_hex(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def digest_json(value: Any) -> str:
    return sha256_hex(canonical_bytes(value))


def domain_hash(domain: str, *parts: str) -> str:
    h = hashlib.sha256()
    h.update(domain.encode("ascii"))
    h.update(b"\x00")
    for part in parts:
        h.update(part.encode("ascii"))
        h.update(b"\x00")
    return h.hexdigest()


def require_object(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise BidVeilError(f"{name} must be an object")
    return value


def require_list(value: Any, name: str) -> list[Any]:
    if not isinstance(value, list):
        raise BidVeilError(f"{name} must be an array")
    return value


def require_str(value: Any, name: str, *, nonempty: bool = True) -> str:
    if not isinstance(value, str):
        raise BidVeilError(f"{name} must be a string")
    if nonempty and not value:
        raise BidVeilError(f"{name} must not be empty")
    return value


def require_id(value: Any, name: str) -> str:
    value = require_str(value, name)
    if not _ID.fullmatch(value):
        raise BidVeilError(f"{name} has invalid characters or length")
    return value


def require_int(value: Any, name: str, *, minimum: int | None = None) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise BidVeilError(f"{name} must be an integer")
    if minimum is not None and value < minimum:
        raise BidVeilError(f"{name} must be >= {minimum}")
    return value


def require_bool(value: Any, name: str) -> bool:
    if not isinstance(value, bool):
        raise BidVeilError(f"{name} must be a boolean")
    return value


def require_hex64(value: Any, name: str) -> str:
    value = require_str(value, name)
    if not _HEX64.fullmatch(value):
        raise BidVeilError(f"{name} must be 64 lowercase hex characters")
    return value


def parse_time(value: Any, name: str) -> datetime:
    raw = require_str(value, name)
    if not raw.endswith("Z"):
        raise BidVeilError(f"{name} must be canonical UTC ending in Z")
    try:
        dt = datetime.fromisoformat(raw[:-1] + "+00:00")
    except ValueError as exc:
        raise BidVeilError(f"{name} is not a valid timestamp") from exc
    if dt.tzinfo is None or dt.utcoffset() != timezone.utc.utcoffset(dt):
        raise BidVeilError(f"{name} must be UTC")
    rendered = dt.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    if rendered != raw:
        raise BidVeilError(f"{name} must use second-precision canonical UTC")
    return dt


def canonical_time(dt: datetime) -> str:
    if dt.tzinfo is None:
        raise BidVeilError("timestamp must be timezone-aware")
    return dt.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
