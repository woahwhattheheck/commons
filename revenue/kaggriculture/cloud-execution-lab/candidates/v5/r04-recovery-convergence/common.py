# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations
import hashlib, json, math, re
from pathlib import PurePosixPath
from typing import Any

HEX64 = re.compile(r"^[0-9a-f]{64}$")
HEX40 = re.compile(r"^[0-9a-f]{40}$")
V5C = re.compile(r"^v5c:[0-9a-f]{64}$")
MAX_INT = (1 << 63) - 1


class GateError(ValueError):
    pass


def _reject_constant(token: str) -> None:
    raise GateError(f"non-finite JSON constant is forbidden: {token}")


def _strict_object(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise GateError(f"duplicate JSON object key: {key}")
        out[key] = value
    return out


def loads_raw(raw: Any, field: str):
    if type(raw) is not str:
        raise GateError(f"{field} must be a raw UTF-8 JSON string")
    encoded = raw.encode("utf-8")
    try:
        value = json.loads(raw, object_pairs_hook=_strict_object, parse_constant=_reject_constant)
    except GateError:
        raise
    except json.JSONDecodeError as exc:
        raise GateError(f"{field} is invalid JSON") from exc
    return value, encoded, hashlib.sha256(encoded).hexdigest()


def canonical(value: Any) -> bytes:
    try:
        return json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise GateError("value is not canonical JSON") from exc


def canonical_sha(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def exact_bool(value: Any, field: str) -> bool:
    if type(value) is not bool:
        raise GateError(f"{field} must be an exact JSON boolean")
    return value


def text(value: Any, field: str) -> str:
    if type(value) is not str or not value:
        raise GateError(f"{field} must be a non-empty string")
    return value


def hex_value(value: Any, field: str, regex) -> str:
    value = text(value, field)
    if regex.fullmatch(value) is None:
        raise GateError(f"{field} has invalid lowercase-hex shape")
    return value


def v5c(value: Any, field: str) -> str:
    value = text(value, field)
    if V5C.fullmatch(value) is None:
        raise GateError(f"{field} must be v5c:<64 lowercase hex>")
    return value


def plain_int(value: Any, field: str, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum or value > MAX_INT:
        raise GateError(f"{field} must be a plain int in [{minimum}, {MAX_INT}]")
    return value


def number(value: Any, field: str) -> float:
    if type(value) not in (int, float) or isinstance(value, bool):
        raise GateError(f"{field} must be a finite number")
    value = float(value)
    if not math.isfinite(value):
        raise GateError(f"{field} must be finite")
    return value


def safe_path(value: Any, field: str, forbidden_suffixes=()) -> str:
    value = text(value, field)
    if "\\" in value:
        raise GateError(f"{field} must be a canonical POSIX path")
    path = PurePosixPath(value)
    if path.is_absolute() or path.as_posix() != value or any(
        part in ("", ".", "..") for part in path.parts
    ):
        raise GateError(f"{field} must be a canonical relative POSIX path")
    normalized = "/" + value.lstrip("/")
    if normalized.endswith(tuple(forbidden_suffixes)):
        raise GateError(f"{field} attempts forbidden whole-router/tape transplant")
    return value


def git_blob_sha1(raw: bytes) -> str:
    return hashlib.sha1(f"blob {len(raw)}\0".encode("ascii") + raw).hexdigest()
