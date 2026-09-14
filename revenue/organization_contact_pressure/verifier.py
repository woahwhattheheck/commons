"""Verify immutable and current organization-pressure receipts."""

from __future__ import annotations

import hmac
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .core import (
    READY, InputError, VerificationError, _canonical_bytes, _expect_object,
    _hmac_hex, _parse_time, _sha256, strict_json_loads,
)
from .receipt_parse import _normalize_receipt
from .records import _load_authority, _load_ledger
from .storage import _authority_root, _load_active_key, _load_key_by_id

def _verify_receipt_integrity_at(receipt_data: bytes, *, root: Path) -> dict[str, Any]:
    try:
        document = _expect_object(strict_json_loads(receipt_data), "receipt")
        body, receipt_hmac, receipt_sha = _normalize_receipt(document)
    except InputError as exc:
        raise VerificationError("receipt is malformed") from exc
    key = _load_key_by_id(root, body["key_id"])
    expected_hmac = _hmac_hex(key, body)
    if not hmac.compare_digest(receipt_hmac, expected_hmac):
        raise VerificationError("receipt HMAC is invalid")
    signed = {**body, "receipt_hmac": receipt_hmac}
    expected_sha = _sha256(_canonical_bytes(signed))
    if not hmac.compare_digest(receipt_sha, expected_sha):
        raise VerificationError("receipt SHA-256 is invalid")
    return {**signed, "receipt_sha256": receipt_sha}


def verify_receipt_integrity(receipt_data: bytes) -> dict[str, Any]:
    """Verify immutable receipt history using a retained verifier key."""
    return _verify_receipt_integrity_at(receipt_data, root=_authority_root())


def _verify_receipt_current_at(receipt_data: bytes, *, root: Path, now: datetime) -> dict[str, Any]:
    receipt = _verify_receipt_integrity_at(receipt_data, root=root)
    if receipt["decision"] != READY:
        return receipt
    now = now.astimezone(timezone.utc).replace(microsecond=0)
    if _parse_time(receipt["valid_until"], "receipt.valid_until") < now:
        raise VerificationError("READY receipt is expired")
    active = _load_active_key(root)
    if receipt["key_id"] != active.key_id or receipt["verifier_id"] != active.verifier_id:
        raise VerificationError("READY receipt verifier generation is no longer active")
    authority = _load_authority(root, active, receipt["organization_scope_sha256"], now)
    ledger = _load_ledger(root, active, authority, now)
    if authority.policy_generation != receipt["authority_policy_generation"]:
        raise VerificationError("READY receipt policy generation moved")
    if authority.digest != receipt["authority_sha256"]:
        raise VerificationError("READY receipt authority generation moved")
    if ledger.generation != receipt["ledger_generation"] or ledger.digest != receipt["ledger_sha256"]:
        raise VerificationError("READY receipt ledger generation moved")
    return receipt


def verify_receipt_current(receipt_data: bytes) -> dict[str, Any]:
    """Verify receipt integrity and reacquire live authority for READY receipts."""
    return _verify_receipt_current_at(
        receipt_data,
        root=_authority_root(),
        now=datetime.now(timezone.utc).replace(microsecond=0),
    )
