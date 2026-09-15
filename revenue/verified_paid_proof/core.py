#!/usr/bin/env python3
"""Deterministic, fail-closed compiler for permission-safe paid-work proof.

This module intentionally has no network, email, Slack, publishing, or provider side effects.
It accepts one strict JSON evidence record and emits a canonical proof model, a sales-safe
Markdown projection, and a SHA-256 receipt.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any

POLICY_VERSION = "verified-paid-proof/v1"
STATUSES = {"HOLD", "PRIVATE_VERIFIED", "PUBLIC_ANONYMOUS", "PUBLIC_NAMED"}
PAYMENT_STATES = {"NONE", "PENDING", "SETTLED", "REFUNDED"}
DELIVERY_STATES = {"NOT_DELIVERED", "DELIVERED", "ACCEPTED"}
PERMISSION_SCOPES = {
    "public_proof",
    "payment_fact",
    "customer_identity",
    "logo",
    "exact_amount",
    "delivery_acceptance",
    "quote",
}
ENGAGEMENT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{2,127}$")
CURRENCY_RE = re.compile(r"^[A-Z]{3}$")


class ProofError(ValueError):
    """Input failed a truth, type, or permission validation rule."""


def _reject_constant(value: str) -> None:
    raise ProofError(f"non-finite JSON number is forbidden: {value}")


def _pairs_no_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise ProofError(f"duplicate JSON key: {key}")
        out[key] = value
    return out


def strict_json_loads(text: str) -> dict[str, Any]:
    try:
        value = json.loads(
            text,
            object_pairs_hook=_pairs_no_duplicates,
            parse_constant=_reject_constant,
        )
    except ProofError:
        raise
    except json.JSONDecodeError as exc:
        raise ProofError(f"invalid JSON: {exc.msg}") from exc
    if not isinstance(value, dict):
        raise ProofError("top-level JSON value must be an object")
    _reject_floats(value, path="$")
    return value


def _reject_floats(value: Any, path: str) -> None:
    if isinstance(value, float):
        raise ProofError(f"floating-point values are forbidden; use integer minor units: {path}")
    if isinstance(value, dict):
        for key, child in value.items():
            _reject_floats(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _reject_floats(child, f"{path}[{index}]")


def _exact_keys(obj: dict[str, Any], expected: set[str], path: str) -> None:
    actual = set(obj)
    missing = sorted(expected - actual)
    extra = sorted(actual - expected)
    if missing or extra:
        raise ProofError(f"{path} keys mismatch; missing={missing}, extra={extra}")


def _dict(value: Any, path: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ProofError(f"{path} must be an object")
    return value


def _list(value: Any, path: str) -> list[Any]:
    if not isinstance(value, list):
        raise ProofError(f"{path} must be an array")
    return value


def _bool(value: Any, path: str) -> bool:
    if type(value) is not bool:
        raise ProofError(f"{path} must be a JSON boolean")
    return value


def _int(value: Any, path: str, *, minimum: int | None = None, maximum: int | None = None) -> int:
    if type(value) is not int:
        raise ProofError(f"{path} must be a JSON integer")
    if minimum is not None and value < minimum:
        raise ProofError(f"{path} must be >= {minimum}")
    if maximum is not None and value > maximum:
        raise ProofError(f"{path} must be <= {maximum}")
    return value


def _str(value: Any, path: str, *, min_len: int = 1, max_len: int = 2048) -> str:
    if not isinstance(value, str):
        raise ProofError(f"{path} must be a string")
    normalized = value.strip()
    if len(normalized) < min_len or len(normalized) > max_len:
        raise ProofError(f"{path} length must be {min_len}..{max_len}")
    if "\x00" in normalized:
        raise ProofError(f"{path} contains NUL")
    return normalized


def _nullable_str(value: Any, path: str, *, max_len: int = 2048) -> str | None:
    if value is None:
        return None
    return _str(value, path, max_len=max_len)


def _source_ref(value: Any, path: str) -> str:
    ref = _str(value, path, max_len=512)
    if "\n" in ref or "\r" in ref:
        raise ProofError(f"{path} must be single-line")
    return ref


def _source_refs(value: Any, path: str, *, required: bool = False) -> list[str]:
    refs = [_source_ref(item, f"{path}[{index}]") for index, item in enumerate(_list(value, path))]
    refs = sorted(set(refs))
    if required and not refs:
        raise ProofError(f"{path} requires at least one evidence reference")
    return refs


def _timestamp(value: Any, path: str) -> str:
    text = _str(value, path, max_len=80)
    candidate = text[:-1] + "+00:00" if text.endswith("Z") else text
    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError as exc:
        raise ProofError(f"{path} must be RFC3339/ISO-8601") from exc
    if parsed.tzinfo is None:
        raise ProofError(f"{path} must include a timezone")
    return text


def _nullable_timestamp(value: Any, path: str) -> str | None:
    if value is None:
        return None
    return _timestamp(value, path)


def _permission(value: Any, path: str) -> dict[str, Any]:
    obj = _dict(value, path)
    _exact_keys(obj, {"granted", "evidence_refs"}, path)
    granted = _bool(obj["granted"], f"{path}.granted")
    refs = _source_refs(obj["evidence_refs"], f"{path}.evidence_refs", required=granted)
    return {"granted": granted, "evidence_refs": refs}


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def _money(amount_minor: int, currency: str, decimals: int) -> str:
    if decimals == 0:
        return f"{currency} {amount_minor}"
    scale = 10**decimals
    major, minor = divmod(amount_minor, scale)
    return f"{currency} {major}.{minor:0{decimals}d}"


def _public_proof_id(engagement_id: str) -> str:
    digest = hashlib.sha256(("proof:" + engagement_id).encode("utf-8")).hexdigest()[:16]
    return f"proof-{digest}"


def _redacted_customer_id(engagement_id: str) -> str:
    digest = hashlib.sha256(("customer:" + engagement_id).encode("utf-8")).hexdigest()[:10]
    return f"anonymous-customer-{digest}"


@dataclass(frozen=True)
class CompiledProof:
    proof: dict[str, Any]
    markdown: str
    receipt_sha256: str

    def proof_json(self) -> str:
        return json.dumps(self.proof, sort_keys=True, ensure_ascii=False, indent=2) + "\n"


