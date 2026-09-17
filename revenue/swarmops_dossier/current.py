from __future__ import annotations

from datetime import datetime, timezone
import math
from typing import Any, Callable

from .engine import DossierError, canonical_bytes, compile_dossier, digest

OUTPUT_SCHEMA = "commons.swarmops-dossier-output/v4"
CURRENT_MODE = "CURRENT_SEMANTIC_SNAPSHOT"
HISTORICAL_MODE = "HISTORICAL_INTEGRITY_ONLY"


def _parse_utc(
    value: Any,
    name: str,
    _datetime: type[datetime] = datetime,
    _error: type[Exception] = DossierError,
) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise _error(f"{name}: UTC Z time required")
    try:
        parsed = _datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise _error(f"{name}: invalid timestamp") from exc
    if parsed.microsecond:
        raise _error(f"{name}: whole seconds required")
    return parsed


def _wrap_core(
    core: dict[str, Any],
    mode: str,
    _digest: Callable[[Any], str] = digest,
    _schema: str = OUTPUT_SCHEMA,
    _current_mode: str = CURRENT_MODE,
    _historical_mode: str = HISTORICAL_MODE,
    _error: type[Exception] = DossierError,
) -> dict[str, Any]:
    if mode not in {_current_mode, _historical_mode}:
        raise _error("unsupported evaluation mode")
    wrapped = dict(core)
    core_receipt = wrapped.pop("receipt_sha256")
    wrapped["schema"] = _schema
    wrapped["evaluation_mode"] = mode
    wrapped["core_v3_receipt_sha256"] = core_receipt
    if mode == _historical_mode:
        wrapped["historical_status"] = wrapped["status"]
        wrapped["status"] = "NON_CURRENT"
    wrapped["receipt_sha256"] = _digest(wrapped)
    return wrapped


def compile_historical_dossier(
    packet: Any,
    policy: Any,
    as_of: str,
    trusted_commercial_receipts: Any = None,
) -> dict[str, Any]:
    """Deterministic replay only; the result can never claim current readiness."""
    _parse_utc(as_of, "as_of")
    core = compile_dossier(packet, policy, as_of, trusted_commercial_receipts)
    return _wrap_core(core, HISTORICAL_MODE)


def verify_historical_dossier(
    packet: Any,
    policy: Any,
    as_of: str,
    candidate: Any,
    trusted_commercial_receipts: Any = None,
) -> bool:
    if type(candidate) is not dict:
        return False
    try:
        expected = compile_historical_dossier(
            packet, policy, as_of, trusted_commercial_receipts
        )
        return canonical_bytes(expected) == canonical_bytes(candidate)
    except (DossierError, TypeError, ValueError, OverflowError):
        return False


def _current_semantics(
    value: dict[str, Any],
    _canonical: Callable[[Any], bytes] = canonical_bytes,
) -> bytes:
    """Remove only evaluation/receipt-time fields; keep all readiness semantics."""
    projected = dict(value)
    projected.pop("as_of", None)
    projected.pop("receipt_sha256", None)
    projected.pop("core_v3_receipt_sha256", None)
    return _canonical(projected)


def _freeze_plain_json(
    value: Any,
    path: str = "candidate",
    _error: type[Exception] = DossierError,
    _finite: Callable[[float], bool] = math.isfinite,
) -> Any:
    """Copy only exact built-in JSON values before any semantic access."""
    if value is None or type(value) in {str, int, bool}:
        return value
    if type(value) is float:
        if not _finite(value):
            raise _error(f"{path}: non-finite number")
        return value
    if type(value) is list:
        return [
            _freeze_plain_json(item, f"{path}[{idx}]", _error, _finite)
            for idx, item in enumerate(value)
        ]
    if type(value) is dict:
        out: dict[str, Any] = {}
        for key, item in value.items():
            if type(key) is not str:
                raise _error(f"{path}: non-string object key")
            out[key] = _freeze_plain_json(item, f"{path}.{key}", _error, _finite)
        return out
    raise _error(f"{path}: exact plain JSON value required")


def _clock_text(
    _now: Callable[..., datetime] = datetime.now,
    _utc: timezone = timezone.utc,
) -> str:
    """UTC clock callable captured at module initialization."""
    return _now(_utc).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")


def _build_current_api(
    clock: Callable[[], str],
    *,
    _compile: Callable[..., dict[str, Any]] = compile_dossier,
    _wrap: Callable[[dict[str, Any], str], dict[str, Any]] = _wrap_core,
    _canonical: Callable[[Any], bytes] = canonical_bytes,
    _parse: Callable[[Any, str], datetime] = _parse_utc,
    _semantics: Callable[[dict[str, Any]], bytes] = _current_semantics,
    _freeze: Callable[[Any], Any] = _freeze_plain_json,
    _schema: str = OUTPUT_SCHEMA,
    _mode: str = CURRENT_MODE,
    _error: type[Exception] = DossierError,
):
    """Build one current API generation with sealed semantic dependencies.

    The returned functions capture the clock plus compiler/serializer/parser/
    projection helpers used for authority decisions. Rebinding those module names
    after initialization cannot change the exported current API generation.

    This is not same-process hostile-code attestation. A caller that mutates the
    Python interpreter or dependency modules before module initialization/reload
    is outside the currentness trust boundary. The receipt therefore claims only
    semantic currentness, never provenance of its recorded ``as_of`` timestamp.
    """
    verification_errors = (_error, TypeError, ValueError, OverflowError)

    def compile_current_dossier(
        packet: Any,
        policy: Any,
        trusted_commercial_receipts: Any = None,
    ) -> dict[str, Any]:
        now = clock()
        core = _compile(packet, policy, now, trusted_commercial_receipts)
        return _wrap(core, _mode)

    def verify_current_dossier(
        packet: Any,
        policy: Any,
        candidate: Any,
        trusted_commercial_receipts: Any = None,
    ) -> bool:
        if type(candidate) is not dict:
            return False
        try:
            frozen = _freeze(candidate)
            if frozen.get("schema") != _schema:
                return False
            if frozen.get("evaluation_mode") != _mode:
                return False

            candidate_as_of = frozen.get("as_of")
            candidate_time = _parse(candidate_as_of, "candidate.as_of")

            # Authenticate the exact candidate first. Current time is sampled
            # only after this potentially non-trivial work completes so a
            # freshness boundary crossed during authentication cannot reuse an
            # earlier clock sample.
            original_core = _compile(
                packet, policy, candidate_as_of, trusted_commercial_receipts
            )
            expected_candidate = _wrap(original_core, _mode)
            if _canonical(expected_candidate) != _canonical(frozen):
                return False

            now_text = clock()
            now = _parse(now_text, "process_now")
            if candidate_time > now:
                return False

            fresh_core = _compile(
                packet, policy, now_text, trusted_commercial_receipts
            )
            fresh = _wrap(fresh_core, _mode)
            return _semantics(expected_candidate) == _semantics(fresh)
        except verification_errors:
            return False

    return compile_current_dossier, verify_current_dossier


compile_current_dossier, verify_current_dossier = _build_current_api(_clock_text)

# Retain a private construction seam for deterministic predecessor tests. It
# creates separate callables and cannot alter the already-exported generation
# without an explicit direct replacement of that public API (outside boundary).
_build_current_api_for_test = _build_current_api

# Remove replaceable source clock/factory names from the normal module surface.
del _build_current_api
del _clock_text
globals().pop("_process_utc_now_text", None)
