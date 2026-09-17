from __future__ import annotations

import json
from typing import Any

from . import engine as _engine

ContractError = _engine.ContractError
MAX_JSON_BYTES = _engine.MAX_JSON_BYTES
MAX_SAFE_INT = 9_007_199_254_740_991


def _require_utf8_scalar(text: str, error: str) -> None:
    try:
        text.encode("utf-8", "strict")
    except UnicodeEncodeError as exc:
        raise ContractError(error) from exc


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if type(key) is not str:
            raise ContractError("json_object_key_text_required")
        _require_utf8_scalar(key, "json_object_key_unicode_scalar")
        if key in out:
            # Never reflect attacker-authored key text into a CLI diagnostic.
            raise ContractError("duplicate_json_key")
        out[key] = value
    return out


def _parse_int(token: str) -> int:
    digits = token[1:] if token.startswith("-") else token
    # Safe JSON integers are at most 16 decimal digits. Fence lexically before
    # calling int() so CPython's interpreter-global digit limit is irrelevant.
    if not digits or len(digits) > 16:
        raise ContractError("unsafe_integer")
    try:
        value = int(token, 10)
    except ValueError as exc:
        raise ContractError("invalid_integer") from exc
    if not (-MAX_SAFE_INT <= value <= MAX_SAFE_INT):
        raise ContractError("unsafe_integer")
    return value


def _reject_constant(_: str) -> None:
    raise ContractError("nonfinite_number")


def _reject_float(_: str) -> None:
    raise ContractError("float_not_allowed")


def _reject_invalid_unicode_scalars(value: Any) -> None:
    # json.loads accepts escaped lone surrogates. Walk iteratively so the
    # validation boundary itself cannot recurse out of bounds.
    stack = [value]
    while stack:
        current = stack.pop()
        if type(current) is str:
            _require_utf8_scalar(current, "json_text_unicode_scalar")
        elif type(current) is list:
            stack.extend(current)
        elif type(current) is dict:
            for key, item in current.items():
                if type(key) is not str:
                    raise ContractError("json_object_key_text_required")
                _require_utf8_scalar(key, "json_object_key_unicode_scalar")
                stack.append(item)


def strict_json_loads(raw: bytes) -> Any:
    if type(raw) is not bytes:
        raise ContractError("json_bytes_required")
    if len(raw) > MAX_JSON_BYTES:
        raise ContractError("input_too_large")
    try:
        text = raw.decode("utf-8", "strict")
    except UnicodeDecodeError as exc:
        raise ContractError("utf8_required") from exc
    try:
        value = json.loads(
            text,
            object_pairs_hook=_pairs,
            parse_int=_parse_int,
            parse_constant=_reject_constant,
            parse_float=_reject_float,
        )
    except ContractError:
        raise
    except (json.JSONDecodeError, RecursionError, ValueError, UnicodeError, OverflowError) as exc:
        raise ContractError("invalid_json") from exc
    try:
        _reject_invalid_unicode_scalars(value)
    except ContractError:
        raise
    except (RecursionError, UnicodeError) as exc:
        raise ContractError("invalid_json") from exc
    return value
