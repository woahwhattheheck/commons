from __future__ import annotations

from types import MappingProxyType
from typing import Any

from .common import digest_object

# Repository-owned policy. Current compilation has no caller-selectable policy path.
_POLICY: dict[str, Any] = {
    "schema": "teaming-conversion-policy/v2",
    "policy_id": "commons-teaming-conversion-control",
    "policy_version": "2026-09-15",
    "max_future_skew_seconds": 300,
    "max_reply_age_seconds": 7 * 24 * 60 * 60,
    "max_source_age_seconds": 14 * 24 * 60 * 60,
    "max_current_receipt_age_seconds": 5 * 60,
    "required_clear_gate_ids": [],
    "required_commitment_ids": [],
}

POLICY = MappingProxyType(_POLICY)
POLICY_SHA256 = digest_object(_POLICY)


def policy_dict() -> dict[str, Any]:
    """Return a detached copy suitable for receipts and deterministic evaluation."""
    return {
        "schema": _POLICY["schema"],
        "policy_id": _POLICY["policy_id"],
        "policy_version": _POLICY["policy_version"],
        "max_future_skew_seconds": _POLICY["max_future_skew_seconds"],
        "max_reply_age_seconds": _POLICY["max_reply_age_seconds"],
        "max_source_age_seconds": _POLICY["max_source_age_seconds"],
        "max_current_receipt_age_seconds": _POLICY["max_current_receipt_age_seconds"],
        "required_clear_gate_ids": list(_POLICY["required_clear_gate_ids"]),
        "required_commitment_ids": list(_POLICY["required_commitment_ids"]),
    }
