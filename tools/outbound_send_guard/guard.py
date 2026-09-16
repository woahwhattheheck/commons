"""Compatibility facade for the outbound send guard.

Supported evaluation is verifier-clock current. The public compatibility
receipt preserves the v1 payload contract used by composed guards while binding
its decision and digest to current verifier time. The deterministic v1 engine
remains underscore-private for reconstruction and internal composition only.
"""
from __future__ import annotations

import sys
from copy import deepcopy
from datetime import datetime
from typing import Any

from . import _guard_core as _legacy_core

# Preserve parsing/canonicalization/helper compatibility, but do not re-export
# the historical positive evaluator or its CLI.
for _name in dir(_legacy_core):
    if not _name.startswith("__") and _name not in {"evaluate", "main"}:
        globals()[_name] = getattr(_legacy_core, _name)


def evaluate(
    intent_raw: dict[str, Any],
    evidence_raw: dict[str, Any],
    *,
    intent_sha256: str | None = None,
    evidence_sha256: str | None = None,
) -> dict[str, Any]:
    """Evaluate at verifier-owned current time with a v1-compatible payload.

    Existing composed guards consume the historical v1 payload keys (intent,
    evidence, authority, latest_*). Those keys remain stable, but the outward
    decision is the current verifier decision and the receipt digest also binds
    current-clock metadata. Exact caller-supplied source digests remain attached
    when a byte-custody caller provides them.
    """
    from .current import compile_current

    current_receipt = compile_current(intent_raw, evidence_raw)
    rich = current_receipt["payload"]
    payload = deepcopy(rich["core"])

    # Preserve exact-byte custody supplied by existing composed callers.
    if intent_sha256 is not None:
        payload["evidence"]["intent_sha256"] = intent_sha256
    if evidence_sha256 is not None:
        payload["evidence"]["evidence_sha256"] = evidence_sha256

    core_reasons = list(payload.get("reasons", []))
    temporal_reasons = list(rich.get("temporal_reasons", []))
    payload["decision"] = rich["decision"]
    payload["reasons"] = list(dict.fromkeys([*core_reasons, *temporal_reasons]))
    payload["side_effects_authorized"] = False

    # Additive current-clock proof. Legacy consumers ignore these keys, while
    # the receipt digest prevents a historical positive receipt from being
    # replay-identical to a current one.
    payload["verified_at"] = rich["verified_at"]
    payload["valid_until"] = rich["valid_until"]
    payload["policy_generation"] = rich["policy_generation"]
    payload["historical_decision"] = rich["historical_decision"]
    payload["temporal_reasons"] = temporal_reasons
    payload["current_preflight_clear"] = rich["current_preflight_clear"]
    payload["net_new_send_preflight_clear"] = rich["net_new_send_preflight_clear"]
    payload["reply_preflight_clear"] = rich["reply_preflight_clear"]

    return {"payload": payload, "receipt_sha256": _legacy_core.digest_object(payload)}


def evaluate_bytes(intent_bytes: bytes, evidence_bytes: bytes) -> dict[str, Any]:
    """Evaluate exact consumed bytes at verifier-owned current time."""
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
    """Explicit historical replay; outward result is permanently HOLD."""
    from .current import compile_historical_at

    return compile_historical_at(
        intent_raw,
        evidence_raw,
        historical_at=historical_at,
    )


def main(argv: list[str] | None = None) -> int:
    """Route old and new CLI syntax through the current verifier-clock boundary."""
    from .current import main as current_main

    args = list(sys.argv[1:] if argv is None else argv)
    if args and args[0] in {"compile", "verify"}:
        return current_main(args)
    return current_main(["compile", *args])


if __name__ == "__main__":
    raise SystemExit(main())
