#!/usr/bin/env python3
"""Safe public wrapper for the reviewed verifier-clock implementation.

The large implementation is retained byte-for-byte in ``current_impl``.
Its deterministic core dependency is rebound to the underscore-private v1
engine before every authority operation. The private core is deliberately not
exported through this module.

Positive authority always reinstalls a process-UTC clock and the private
core before compile/verify. Caller-writable module attributes on this wrapper
or on ``current_impl`` are not the authority time source.
"""
from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any

from . import _guard_core as _legacy_core
from . import current_impl as _impl

# Bind once immediately; every authority wrapper below reasserts the binding.
_impl.guard = _legacy_core

CurrentGuardError = _impl.CurrentGuardError
CURRENT_RECEIPT_SCHEMA = _impl.CURRENT_RECEIPT_SCHEMA
HISTORICAL_RECEIPT_SCHEMA = _impl.HISTORICAL_RECEIPT_SCHEMA
CURRENT_VERIFICATION_SCHEMA = _impl.CURRENT_VERIFICATION_SCHEMA
POLICY_GENERATION = _impl.POLICY_GENERATION
MODE_CURRENT = _impl.MODE_CURRENT
MODE_HISTORICAL = _impl.MODE_HISTORICAL
MAX_EVIDENCE_AGE_SECONDS = _impl.MAX_EVIDENCE_AGE_SECONDS
MAX_REQUEST_AGE_SECONDS = _impl.MAX_REQUEST_AGE_SECONDS
MAX_FUTURE_SKEW_SECONDS = _impl.MAX_FUTURE_SKEW_SECONDS
POSITIVE_RECEIPT_TTL_SECONDS = _impl.POSITIVE_RECEIPT_TTL_SECONDS
MAX_INPUT_BYTES = _impl.MAX_INPUT_BYTES
DECISIONS = _impl.DECISIONS
POSITIVE = _impl.POSITIVE

# Inspectable aliases only. Authority wrappers do not copy these back into
# the implementation; rebinding them cannot select verifier time or core.
_utc_now = _impl._utc_now
_core = _impl._core

# Safe helper compatibility for existing tests/callers. There is intentionally
# no ``evaluate`` or ``main`` attribute here.
guard = SimpleNamespace(
    GuardError=_legacy_core.GuardError,
    canonical_bytes=_legacy_core.canonical_bytes,
    digest_bytes=_legacy_core.digest_bytes,
    digest_object=_legacy_core.digest_object,
    parse_json_bytes=_legacy_core.parse_json_bytes,
    parse_time=_legacy_core.parse_time,
    format_time=_legacy_core.format_time,
    normalize_email=_legacy_core.normalize_email,
)

# Pure helpers that do not emit current authority may remain inspectable.
_snapshot = _impl._snapshot
_parse_bytes = _impl._parse_bytes
_temporal_projection = _impl._temporal_projection
_decision = _impl._decision
_policy = _impl._policy
_source_record = _impl._source_record
_receipt_current = _impl._receipt_current


def _owned_utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _owned_core(
    intent: dict[str, Any], evidence: dict[str, Any], ib: bytes, eb: bytes
) -> dict[str, Any]:
    return _legacy_core.evaluate(
        intent,
        evidence,
        intent_sha256=_legacy_core.digest_bytes(ib),
        evidence_sha256=_legacy_core.digest_bytes(eb),
    )


def _sync_impl(
    _clock=_owned_utc_now,
    _core_fn=_owned_core,
) -> None:
    # Defaults bind the original function objects at definition time.
    _impl.guard = _legacy_core
    _impl._utc_now = _clock
    _impl._core = _core_fn


def _compile_current_owned_clock(
    intent: dict[str, Any],
    evidence: dict[str, Any],
    *,
    ib: bytes,
    eb: bytes,
    source_mode: str,
) -> dict[str, Any]:
    _sync_impl()
    return _impl._compile_current_owned_clock(
        intent, evidence, ib=ib, eb=eb, source_mode=source_mode
    )


def compile_current(
    intent_raw: dict[str, Any], evidence_raw: dict[str, Any]
) -> dict[str, Any]:
    _sync_impl()
    return _impl.compile_current(intent_raw, evidence_raw)


def compile_current_bytes(
    intent_bytes: bytes, evidence_bytes: bytes
) -> dict[str, Any]:
    _sync_impl()
    return _impl.compile_current_bytes(intent_bytes, evidence_bytes)


def compile_historical_at(
    intent_raw: dict[str, Any],
    evidence_raw: dict[str, Any],
    *,
    historical_at: datetime,
) -> dict[str, Any]:
    _sync_impl()
    return _impl.compile_historical_at(
        intent_raw, evidence_raw, historical_at=historical_at
    )


def _verify_current_owned_clock(
    intent: dict[str, Any],
    evidence: dict[str, Any],
    *,
    ib: bytes,
    eb: bytes,
    source_mode: str,
    receipt_raw: dict[str, Any],
) -> dict[str, Any]:
    _sync_impl()
    return _impl._verify_current_owned_clock(
        intent,
        evidence,
        ib=ib,
        eb=eb,
        source_mode=source_mode,
        receipt_raw=receipt_raw,
    )


def verify_current(
    intent_raw: dict[str, Any],
    evidence_raw: dict[str, Any],
    receipt_raw: dict[str, Any],
) -> dict[str, Any]:
    _sync_impl()
    return _impl.verify_current(intent_raw, evidence_raw, receipt_raw)


def verify_current_bytes(
    intent_bytes: bytes,
    evidence_bytes: bytes,
    receipt_bytes: bytes,
) -> dict[str, Any]:
    _sync_impl()
    return _impl.verify_current_bytes(intent_bytes, evidence_bytes, receipt_bytes)


def main(argv: list[str] | None = None) -> int:
    _sync_impl()
    return _impl.main(argv)


def __getattr__(name: str) -> Any:
    if name == "guard":
        return guard
    if name.startswith("__"):
        raise AttributeError(name)
    return getattr(_impl, name)


if __name__ == "__main__":
    raise SystemExit(main())
