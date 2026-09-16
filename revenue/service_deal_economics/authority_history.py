"""Historical reconstruction for Service Deal Economics receipts.

Kept in a separate module from the current verifier so retained-time
replay cannot be confused with process-current authority. This module
never emits CURRENT_VERIFIED and is not a current-state API.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from .engine import DealEconomicsError, canonical_json, compile_report


def historical_valid(packet: Any, report: Any) -> bool:
    from .authority import (
        CURRENT_SCHEMA,
        AuthorityError,
        _assemble,
        _authority_status,
        _unauth,
        _utc,
        _utc_text,
        digest,
    )

    if (
        type(report) is not dict
        or report.get("schema") != CURRENT_SCHEMA
        or report.get("receipt_sha256") != digest({k: v for k, v in report.items() if k != "receipt_sha256"})
    ):
        return False
    try:
        evaluated = _utc(report["evaluated_at"], "evaluated_at")
        embedded = report.get("authority_registry")
        if embedded is None:
            expected = _assemble(compile_report(packet, _utc_text(evaluated)), evaluated, _unauth())
        else:
            expected = replay_historical_at(
                packet,
                evaluated,
                embedded,
                report["input_authority"]["registry_sha256"],
            )
        return canonical_json(expected) == canonical_json(report)
    except (AuthorityError, DealEconomicsError, OSError, KeyError, TypeError, ValueError):
        return False


def replay_historical_at(
    packet: Any,
    instant: datetime,
    registry: dict[str, Any],
    registry_sha256: str,
) -> dict[str, Any]:
    """Reconstruct a historical report from its embedded signed registry; never a current-state API."""
    from .authority import _assemble, _authority_status, _utc_text

    candidate = compile_report(packet, _utc_text(instant))
    auth = _authority_status(packet, instant, registry=registry, registry_sha256=registry_sha256)
    return _assemble(candidate, instant, auth)
