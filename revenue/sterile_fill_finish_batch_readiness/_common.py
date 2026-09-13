from __future__ import annotations

import copy
import hashlib
import json
import re
from datetime import datetime, timezone
from typing import Any

SCHEMA_VERSION = "tj.sterile-fill-finish-batch-readiness/v1"
READY_STATUS = "READY_FOR_OWNER_BATCH_REVIEW"
HOLD_STATUS = "HOLD_FOR_OWNER_REVIEW"
_ALLOWED_EVENT_KINDS = {
    "BATCH_PLAN", "MATERIAL_RELEASE", "EQUIPMENT_STATUS", "ENVIRONMENT_STATUS",
    "FILL_INSPECTION", "PACKAGING_STATUS", "DEVIATION_STATUS",
}
_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,79}$")
_REF_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/#-]{1,159}$")
_EMAIL_RE = re.compile(r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b")
_SECRET_VALUE_RE = re.compile(r"(?i)(?:\bBearer\s+[A-Za-z0-9._~+/=-]{8,}|\b(?:sk|rk|pk)-(?:live|test|proj)?[-_A-Za-z0-9]{8,}|\bAKIA[A-Z0-9]{12,})")
_FORBIDDEN_KEY_RE = re.compile(r"(?i)(?:password|passwd|secret|api[_-]?key|access[_-]?token|refresh[_-]?token|authorization|patient[_-]?name|patient[_-]?email)")


class ReadinessError(ValueError):
    def __init__(self, code: str, detail: str | None = None):
        self.code = code
        self.detail = detail
        super().__init__(code if detail is None else f"{code}: {detail}")


def _fail(code: str, detail: str | None = None) -> None:
    raise ReadinessError(code, detail)


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _object(value: Any, code: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        _fail(code)
    return value


def _list(value: Any, code: str) -> list[Any]:
    if not isinstance(value, list):
        _fail(code)
    return value


def _exact_keys(value: dict[str, Any], expected: set[str], code: str) -> None:
    if set(value) != expected:
        _fail(code, f"missing={sorted(expected - set(value))};extra={sorted(set(value) - expected)}")


def _safe_int(value: Any, name: str, minimum: int, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        _fail("INTEGER_REQUIRED", name)
    if value < minimum or value > maximum:
        _fail("INTEGER_OUT_OF_RANGE", name)
    return value


def _text(value: Any, name: str, max_len: int = 160) -> str:
    if not isinstance(value, str):
        _fail("TEXT_REQUIRED", name)
    if not value or value != value.strip() or len(value) > max_len:
        _fail("TEXT_INVALID", name)
    if any(ord(ch) < 32 or ord(ch) == 127 for ch in value):
        _fail("TEXT_INVALID", name)
    if _EMAIL_RE.search(value):
        _fail("PII_SHAPED_TEXT", name)
    if _SECRET_VALUE_RE.search(value):
        _fail("SECRET_SHAPED_TEXT", name)
    return value


def _identifier(value: Any, name: str) -> str:
    value = _text(value, name, 80)
    if not _ID_RE.fullmatch(value):
        _fail("IDENTIFIER_INVALID", name)
    return value


def _evidence_ref(value: Any, name: str) -> str:
    value = _text(value, name, 160)
    if not _REF_RE.fullmatch(value):
        _fail("EVIDENCE_REF_INVALID", name)
    return value


def _timestamp(value: Any, name: str) -> tuple[str, datetime]:
    value = _text(value, name, 40)
    if not value.endswith("Z"):
        _fail("TIMESTAMP_UTC_REQUIRED", name)
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError:
        _fail("TIMESTAMP_INVALID", name)
    parsed = parsed.astimezone(timezone.utc)
    canonical = parsed.isoformat(timespec="seconds").replace("+00:00", "Z")
    if canonical != value:
        _fail("TIMESTAMP_CANONICAL_REQUIRED", name)
    return canonical, parsed


def _assert_public_safe(value: Any, path: str = "$") -> None:
    if isinstance(value, dict):
        for key, nested in value.items():
            if not isinstance(key, str):
                _fail("NON_STRING_KEY", path)
            if _FORBIDDEN_KEY_RE.search(key):
                _fail("SECRET_OR_PII_KEY", f"{path}.{key}")
            _assert_public_safe(nested, f"{path}.{key}")
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            _assert_public_safe(nested, f"{path}[{index}]")
    elif isinstance(value, str):
        if _EMAIL_RE.search(value):
            _fail("PII_SHAPED_TEXT", path)
        if _SECRET_VALUE_RE.search(value):
            _fail("SECRET_SHAPED_TEXT", path)


def _normalize_string_map(value: Any, name: str) -> dict[str, str]:
    obj = _object(value, "STRING_MAP_REQUIRED")
    out: dict[str, str] = {}
    for raw_key, raw_value in obj.items():
        key = _identifier(raw_key, f"{name}.key")
        out[key] = _identifier(raw_value, f"{name}.{key}")
    if not out:
        _fail("NONEMPTY_MAP_REQUIRED", name)
    return dict(sorted(out.items()))


def _normalize_id_list(value: Any, name: str) -> list[str]:
    rows = _list(value, "ID_LIST_REQUIRED")
    out = [_identifier(row, f"{name}[]") for row in rows]
    if not out:
        _fail("NONEMPTY_LIST_REQUIRED", name)
    if len(set(out)) != len(out):
        _fail("DUPLICATE_LIST_VALUE", name)
    return sorted(out)


