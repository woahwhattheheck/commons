from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Optional

from .constants import FINANCIAL_CLASSES, ID_RE, SHA_RE, UTC_RE

class RegistryError(ValueError):
    pass


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise RegistryError(f"DUPLICATE_JSON_KEY:{key}")
        out[key] = value
    return out


def load_json_strict(text: str) -> Any:
    try:
        return json.loads(text, object_pairs_hook=_strict_object)
    except RegistryError:
        raise
    except (json.JSONDecodeError, TypeError) as exc:
        raise RegistryError(f"INVALID_JSON:{exc}") from exc


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_hex(value: Any) -> str:
    raw = value if isinstance(value, (bytes, bytearray)) else canonical_json(value)
    return hashlib.sha256(raw).hexdigest()


def _require_exact_keys(obj: Any, keys: set[str], where: str) -> dict[str, Any]:
    if not isinstance(obj, dict):
        raise RegistryError(f"{where}:EXPECTED_OBJECT")
    actual = set(obj)
    if actual != keys:
        missing = sorted(keys - actual)
        extra = sorted(actual - keys)
        raise RegistryError(f"{where}:KEYS:missing={missing}:extra={extra}")
    return obj


def _require_str(value: Any, where: str, *, nonempty: bool = True) -> str:
    if not isinstance(value, str):
        raise RegistryError(f"{where}:EXPECTED_STRING")
    if nonempty and not value:
        raise RegistryError(f"{where}:EMPTY")
    if len(value) > 512:
        raise RegistryError(f"{where}:TOO_LONG")
    return value


def _require_id(value: Any, where: str, *, nullable: bool = False) -> Optional[str]:
    if value is None and nullable:
        return None
    value = _require_str(value, where)
    if not ID_RE.fullmatch(value):
        raise RegistryError(f"{where}:UNSAFE_ID")
    return value


def _require_sha(value: Any, where: str) -> str:
    value = _require_str(value, where)
    if not SHA_RE.fullmatch(value):
        raise RegistryError(f"{where}:INVALID_SHA256")
    return value


def _parse_utc(value: Any, where: str, *, nullable: bool = False) -> Optional[datetime]:
    if value is None and nullable:
        return None
    value = _require_str(value, where)
    if not UTC_RE.fullmatch(value):
        raise RegistryError(f"{where}:INVALID_UTC_SECONDS")
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError as exc:
        raise RegistryError(f"{where}:INVALID_UTC_SECONDS") from exc


def _require_enum(value: Any, allowed: set[str], where: str) -> str:
    value = _require_str(value, where)
    if value not in allowed:
        raise RegistryError(f"{where}:INVALID_ENUM:{value}")
    return value


def _require_id_list(value: Any, where: str, *, allowed: Optional[set[str]] = None) -> list[str]:
    if not isinstance(value, list):
        raise RegistryError(f"{where}:EXPECTED_LIST")
    out: list[str] = []
    seen: set[str] = set()
    for index, item in enumerate(value):
        if allowed is None:
            item = _require_id(item, f"{where}[{index}]")
            assert item is not None
        else:
            item = _require_enum(item, allowed, f"{where}[{index}]")
        if item in seen:
            raise RegistryError(f"{where}:DUPLICATE:{item}")
        seen.add(item)
        out.append(item)
    return sorted(out)


def _validate_metadata(category: str, metadata: Any, where: str) -> dict[str, Any]:
    if not isinstance(metadata, dict):
        raise RegistryError(f"{where}:EXPECTED_OBJECT")
    if category == "FINANCIAL_STATEMENT":
        if set(metadata) != {"financial_class"}:
            raise RegistryError(f"{where}:FINANCIAL_KEYS")
        return {"financial_class": _require_enum(metadata["financial_class"], FINANCIAL_CLASSES, f"{where}.financial_class")}
    if metadata:
        raise RegistryError(f"{where}:UNEXPECTED_METADATA")
    return {}
