"""Strict bounded JSON codec for source-bound evidence authority."""
from __future__ import annotations

import json
from typing import Any

MAX_DOCUMENT_BYTES = 131_072
MAX_SAFE_INTEGER = 9_007_199_254_740_991


class DomainError(ValueError):
    """Fail-closed domain error safe for CLI rendering."""


def _build_codec():
    # All trust-bearing parser helpers live in this initialization closure so
    # ordinary module-global rebinding cannot widen an already imported kernel.
    _json = json
    _DomainError = DomainError
    _max_document = MAX_DOCUMENT_BYTES
    _max_integer = MAX_SAFE_INTEGER

    def _reject_constant(token: str) -> None:
        raise _DomainError(f"non-finite JSON number is forbidden: {token}")

    def _parse_int(token: str) -> int:
        digits = token[1:] if token.startswith("-") else token
        if len(digits) > 16:
            raise _DomainError("integer token exceeds exact safe bound")
        value = int(token, 10)
        if abs(value) > _max_integer:
            raise _DomainError("integer exceeds exact safe bound")
        return value

    def _parse_float(token: str) -> None:
        raise _DomainError("floating-point JSON numbers are forbidden")

    def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for key, value in pairs:
            if key in out:
                raise _DomainError(f"duplicate JSON key: {key!r}")
            out[key] = value
        return out

    def _valid_string(value: str) -> bool:
        return all(not (0xD800 <= ord(ch) <= 0xDFFF) for ch in value)

    def validate_json_tree(value: Any, *, depth: int = 0) -> None:
        if depth > 24:
            raise _DomainError("JSON nesting exceeds bound")
        if value is None or isinstance(value, bool):
            return
        if isinstance(value, int):
            if abs(value) > _max_integer:
                raise _DomainError("integer exceeds exact safe bound")
            return
        if isinstance(value, float):
            raise _DomainError("floating-point JSON numbers are forbidden")
        if isinstance(value, str):
            if not _valid_string(value):
                raise _DomainError("lone surrogate / unsafe Unicode is forbidden")
            if len(value.encode("utf-8")) > 16_384:
                raise _DomainError("string exceeds bound")
            return
        if isinstance(value, list):
            if len(value) > 1024:
                raise _DomainError("array exceeds bound")
            for item in value:
                validate_json_tree(item, depth=depth + 1)
            return
        if isinstance(value, dict):
            if len(value) > 1024:
                raise _DomainError("object exceeds bound")
            for key, item in value.items():
                if not isinstance(key, str):
                    raise _DomainError("JSON object key must be a string")
                if not _valid_string(key):
                    raise _DomainError("unsafe Unicode in object key")
                validate_json_tree(item, depth=depth + 1)
            return
        raise _DomainError(f"non-JSON value type: {type(value).__name__}")

    def canonical_bytes(value: Any) -> bytes:
        validate_json_tree(value)
        try:
            return _json.dumps(
                value,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            ).encode("utf-8")
        except (TypeError, ValueError, UnicodeError) as exc:
            raise _DomainError("value cannot be encoded as canonical UTF-8 JSON") from exc

    def strict_loads(
        raw: bytes | str,
        *,
        max_bytes: int = _max_document,
        require_canonical: bool = False,
    ) -> Any:
        if isinstance(max_bytes, bool) or not isinstance(max_bytes, int):
            raise _DomainError("max_bytes must be an integer")
        if max_bytes < 1 or max_bytes > 8 * _max_document:
            raise _DomainError("max_bytes outside bounded range")
        if isinstance(raw, str):
            try:
                encoded = raw.encode("utf-8")
            except UnicodeError as exc:
                raise _DomainError("input is not valid UTF-8") from exc
        elif isinstance(raw, bytes):
            encoded = raw
        else:
            raise _DomainError("JSON input must be bytes or text")
        if len(encoded) > max_bytes:
            raise _DomainError("JSON document exceeds byte bound")
        try:
            text = encoded.decode("utf-8", errors="strict")
        except UnicodeDecodeError as exc:
            raise _DomainError("input is not valid UTF-8") from exc
        try:
            value = _json.loads(
                text,
                object_pairs_hook=_pairs,
                parse_int=_parse_int,
                parse_float=_parse_float,
                parse_constant=_reject_constant,
            )
        except _DomainError:
            raise
        except (_json.JSONDecodeError, UnicodeError, ValueError) as exc:
            raise _DomainError("invalid JSON") from exc
        validate_json_tree(value)
        if require_canonical and encoded != canonical_bytes(value):
            raise _DomainError("authority JSON bytes are not canonical")
        return value

    return canonical_bytes, strict_loads, validate_json_tree


canonical_bytes, strict_loads, validate_json_tree = _build_codec()
del _build_codec
