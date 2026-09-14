"""Separately retained monotonic ledger-head authority."""

from __future__ import annotations

import hmac
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Mapping

from .core import (
    LEDGER_HEAD_SCHEMA,
    MAX_SAFE_INTEGER,
    ActiveKey,
    AuthorityView,
    InputError,
    VerificationError,
    _canonical_bytes,
    _expect_exact_fields,
    _expect_hex64,
    _expect_int,
    _expect_key_id,
    _expect_object,
    _expect_slug,
    _format_time,
    _hmac_hex,
    _parse_time,
    _sha256,
    strict_json_loads,
)
from .storage import _read_regular_file


def _normalize_ledger_head_document(document: Mapping[str, Any]) -> tuple[dict[str, Any], str]:
    fields = {
        "schema",
        "organization_scope_sha256",
        "policy_generation",
        "ledger_generation",
        "ledger_sha256",
        "ledger_updated_at",
        "key_id",
        "verifier_id",
        "signature",
    }
    _expect_exact_fields(document, fields, "ledger head")
    if document["schema"] != LEDGER_HEAD_SCHEMA:
        raise InputError("unsupported ledger head schema")
    body = {
        "schema": LEDGER_HEAD_SCHEMA,
        "organization_scope_sha256": _expect_hex64(
            document["organization_scope_sha256"], "ledger_head.organization_scope_sha256"
        ),
        "policy_generation": _expect_int(
            document["policy_generation"],
            "ledger_head.policy_generation",
            minimum=1,
            maximum=MAX_SAFE_INTEGER,
        ),
        "ledger_generation": _expect_int(
            document["ledger_generation"],
            "ledger_head.ledger_generation",
            minimum=0,
            maximum=MAX_SAFE_INTEGER,
        ),
        "ledger_sha256": _expect_hex64(document["ledger_sha256"], "ledger_head.ledger_sha256"),
        "ledger_updated_at": _format_time(
            _parse_time(document["ledger_updated_at"], "ledger_head.ledger_updated_at")
        ),
        "key_id": _expect_key_id(document["key_id"], "ledger_head.key_id"),
        "verifier_id": _expect_slug(document["verifier_id"], "ledger_head.verifier_id"),
    }
    signature = _expect_hex64(document["signature"], "ledger_head.signature")
    return body, signature


def _load_ledger_head(
    root: Path,
    active: ActiveKey,
    authority: AuthorityView,
    now: datetime,
) -> tuple[dict[str, Any], str]:
    organization = authority.organization_scope_sha256
    raw = _read_regular_file(root / "heads" / f"{organization}.json", limit=65_536, private=True)
    try:
        document = _expect_object(strict_json_loads(raw), "ledger head")
        body, signature = _normalize_ledger_head_document(document)
    except InputError as exc:
        raise VerificationError("retained ledger head is malformed") from exc
    if body["organization_scope_sha256"] != organization:
        raise VerificationError("ledger head path/scope mismatch")
    if body["policy_generation"] != authority.policy_generation:
        raise VerificationError("ledger head policy generation mismatch")
    if body["key_id"] != active.key_id or body["verifier_id"] != active.verifier_id:
        raise VerificationError("ledger head is not bound to the active verifier generation")
    if not hmac.compare_digest(signature, _hmac_hex(active.key, body)):
        raise VerificationError("ledger head HMAC is invalid")
    updated = _parse_time(body["ledger_updated_at"], "ledger_head.ledger_updated_at")
    skew = timedelta(seconds=authority.max_future_skew_seconds)
    if updated > now + skew:
        raise VerificationError("ledger head is future-updated")
    if updated < authority.issued_at:
        raise VerificationError("ledger head predates its authority generation")
    canonical = {**body, "signature": signature}
    return body, _sha256(_canonical_bytes(canonical))
