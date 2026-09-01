"""Tamper-evident local audit receipt chain."""

import hashlib
import json
from typing import Iterable

from .cases import AuditReceipt, CaseRecord, utc_now


GENESIS_HASH = "0" * 64


def _receipt_digest(
    sequence: int,
    event: str,
    detail: str,
    created_at: str,
    previous_hash: str,
) -> str:
    canonical = json.dumps(
        {
            "sequence": sequence,
            "event": event,
            "detail": detail,
            "created_at": created_at,
            "previous_hash": previous_hash,
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def append_receipt(case: CaseRecord, event: str, detail: str) -> AuditReceipt:
    previous_hash = (
        case.receipts[-1].receipt_hash if case.receipts else GENESIS_HASH
    )
    sequence = len(case.receipts) + 1
    created_at = utc_now()
    receipt = AuditReceipt(
        sequence=sequence,
        event=event,
        detail=detail,
        created_at=created_at,
        previous_hash=previous_hash,
        receipt_hash=_receipt_digest(
            sequence, event, detail, created_at, previous_hash
        ),
    )
    case.receipts.append(receipt)
    case.updated_at = created_at
    return receipt


def verify_receipts(receipts: Iterable[AuditReceipt]) -> bool:
    previous_hash = GENESIS_HASH
    expected_sequence = 1
    for receipt in receipts:
        if (
            receipt.sequence != expected_sequence
            or receipt.previous_hash != previous_hash
            or receipt.receipt_hash
            != _receipt_digest(
                receipt.sequence,
                receipt.event,
                receipt.detail,
                receipt.created_at,
                receipt.previous_hash,
            )
        ):
            return False
        previous_hash = receipt.receipt_hash
        expected_sequence += 1
    return True
