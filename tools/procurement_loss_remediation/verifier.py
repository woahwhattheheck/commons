"""Semantic verifier for procurement loss/debrief remediation receipts."""
from __future__ import annotations

from typing import Any

from .compiler import (
    RECEIPT_SCHEMA,
    RemediationError,
    canonical_bytes,
    compile_record,
    digest,
)


def verify_receipt(raw: Any, receipt: Any) -> dict[str, Any]:
    if type(receipt) is not dict:
        raise RemediationError("receipt must be an object")
    if receipt.get("schema") != RECEIPT_SCHEMA:
        raise RemediationError(f"receipt.schema must be {RECEIPT_SCHEMA}")
    supplied_hash = receipt.get("receipt_sha256")
    if type(supplied_hash) is not str:
        raise RemediationError("receipt.receipt_sha256 must be a string")
    unhashed = dict(receipt)
    unhashed.pop("receipt_sha256", None)
    if digest(unhashed) != supplied_hash:
        raise RemediationError("receipt.receipt_sha256 does not match receipt content")

    expected = compile_record(raw)
    if canonical_bytes(receipt) != canonical_bytes(expected):
        raise RemediationError("receipt does not semantically match source input")
    return {
        "verified": True,
        "opportunity_id": expected["opportunity_id"],
        "backlog_state": expected["backlog_state"],
        "receipt_sha256": expected["receipt_sha256"],
    }
