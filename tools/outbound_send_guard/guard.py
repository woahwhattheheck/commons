"""Backward-compatible fail-closed facade for the outbound send guard.

The deterministic v1 engine remains available as helper/parsing machinery, but
embedded evaluation can never mint positive CURRENT authority. Positive CURRENT
is supported only by the direct isolated CLI process.
"""
from __future__ import annotations

import sys
from copy import deepcopy
from datetime import datetime
from typing import Any

from . import _guard_core as _legacy_core

for _name in dir(_legacy_core):
    if not _name.startswith("__") and _name not in {"evaluate", "main"}:
        globals()[_name] = getattr(_legacy_core, _name)

_EMBEDDED_REASON = (
    "embedded CURRENT authority is unavailable; use direct isolated startup: "
    "python -I -S tools/outbound_send_guard/cli.py ..."
)


def evaluate(
    intent_raw: dict[str, Any],
    evidence_raw: dict[str, Any],
    *,
    intent_sha256: str | None = None,
    evidence_sha256: str | None = None,
) -> dict[str, Any]:
    """Return the legacy-compatible shape with no positive embedded authority."""
    receipt = _legacy_core.evaluate(intent_raw, evidence_raw)
    payload = deepcopy(receipt["payload"])
    historical = payload["decision"]
    if intent_sha256 is not None:
        payload["evidence"]["intent_sha256"] = intent_sha256
    if evidence_sha256 is not None:
        payload["evidence"]["evidence_sha256"] = evidence_sha256
    if historical in {"ALLOW_NEW", "REPLY_ONLY"}:
        payload["decision"] = "HOLD"
        payload["reasons"] = list(
            dict.fromkeys([*payload.get("reasons", []), _EMBEDDED_REASON])
        )
    payload["historical_decision"] = historical
    payload["current_preflight_clear"] = False
    payload["net_new_send_preflight_clear"] = False
    payload["reply_preflight_clear"] = False
    payload["side_effects_authorized"] = False
    return {"payload": payload, "receipt_sha256": _legacy_core.digest_object(payload)}


def evaluate_bytes(intent_bytes: bytes, evidence_bytes: bytes) -> dict[str, Any]:
    intent = _legacy_core.parse_json_bytes(intent_bytes, "intent")
    evidence = _legacy_core.parse_json_bytes(evidence_bytes, "evidence")
    return evaluate(
        intent,
        evidence,
        intent_sha256=_legacy_core.digest_bytes(intent_bytes),
        evidence_sha256=_legacy_core.digest_bytes(evidence_bytes),
    )


def evaluate_historical_at(
    intent_raw: dict[str, Any],
    evidence_raw: dict[str, Any],
    *,
    historical_at: datetime,
) -> dict[str, Any]:
    from .current import compile_historical_at

    return compile_historical_at(
        intent_raw, evidence_raw, historical_at=historical_at
    )


def main(argv: list[str] | None = None) -> int:
    del argv
    print(
        "embedded guard CLI is non-authorizing; use direct isolated startup: "
        "python -I -S tools/outbound_send_guard/cli.py ...",
        file=sys.stderr,
    )
    return 4


if __name__ == "__main__":
    raise SystemExit(main())
