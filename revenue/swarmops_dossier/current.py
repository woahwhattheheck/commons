from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable

from .engine import DossierError, canonical_bytes, compile_dossier, digest

OUTPUT_SCHEMA = "commons.swarmops-dossier-output/v4"
CURRENT_MODE = "CURRENT_PROCESS_UTC"
HISTORICAL_MODE = "HISTORICAL_INTEGRITY_ONLY"


def _parse_utc(value: Any, name: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise DossierError(f"{name}: UTC Z time required")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise DossierError(f"{name}: invalid timestamp") from exc
    if parsed.microsecond:
        raise DossierError(f"{name}: whole seconds required")
    return parsed


def _wrap_core(core: dict[str, Any], mode: str) -> dict[str, Any]:
    if mode not in {CURRENT_MODE, HISTORICAL_MODE}:
        raise DossierError("unsupported evaluation mode")
    wrapped = dict(core)
    core_receipt = wrapped.pop("receipt_sha256")
    wrapped["schema"] = OUTPUT_SCHEMA
    wrapped["evaluation_mode"] = mode
    wrapped["core_v3_receipt_sha256"] = core_receipt
    if mode == HISTORICAL_MODE:
        wrapped["historical_status"] = wrapped["status"]
        wrapped["status"] = "NON_CURRENT"
    wrapped["receipt_sha256"] = digest(wrapped)
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
    if not isinstance(candidate, dict):
        return False
    try:
        expected = compile_historical_dossier(
            packet, policy, as_of, trusted_commercial_receipts
        )
    except DossierError:
        return False
    return canonical_bytes(expected) == canonical_bytes(candidate)


def _current_semantics(value: dict[str, Any]) -> bytes:
    """Remove only evaluation/receipt-time fields; keep all readiness semantics."""
    projected = dict(value)
    projected.pop("as_of", None)
    projected.pop("receipt_sha256", None)
    projected.pop("core_v3_receipt_sha256", None)
    return canonical_bytes(projected)


def _clock_text(
    _now: Callable[..., datetime] = datetime.now,
    _utc: timezone = timezone.utc,
) -> str:
    """Clock generation captured from stdlib objects at definition time."""
    return _now(_utc).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")


def _build_current_api(clock: Callable[[], str]):
    """Bind current authority to one captured clock generation.

    The returned public functions never look up a clock through the module
    namespace. The factory and source clock name are deleted after construction,
    so ordinary module/global reassignment cannot substitute historical time.
    """

    def compile_current_dossier(
        packet: Any,
        policy: Any,
        trusted_commercial_receipts: Any = None,
    ) -> dict[str, Any]:
        now = clock()
        core = compile_dossier(packet, policy, now, trusted_commercial_receipts)
        return _wrap_core(core, CURRENT_MODE)

    def verify_current_dossier(
        packet: Any,
        policy: Any,
        candidate: Any,
        trusted_commercial_receipts: Any = None,
    ) -> bool:
        if not isinstance(candidate, dict):
            return False
        if candidate.get("schema") != OUTPUT_SCHEMA:
            return False
        if candidate.get("evaluation_mode") != CURRENT_MODE:
            return False
        candidate_as_of = candidate.get("as_of")
        try:
            candidate_time = _parse_utc(candidate_as_of, "candidate.as_of")
            now_text = clock()
            now = _parse_utc(now_text, "process_now")
            if candidate_time > now:
                return False

            original_core = compile_dossier(
                packet, policy, candidate_as_of, trusted_commercial_receipts
            )
            expected_candidate = _wrap_core(original_core, CURRENT_MODE)
            if canonical_bytes(expected_candidate) != canonical_bytes(candidate):
                return False

            fresh_core = compile_dossier(
                packet, policy, now_text, trusted_commercial_receipts
            )
            fresh = _wrap_core(fresh_core, CURRENT_MODE)
        except DossierError:
            return False

        return _current_semantics(expected_candidate) == _current_semantics(fresh)

    return compile_current_dossier, verify_current_dossier


compile_current_dossier, verify_current_dossier = _build_current_api(_clock_text)

# Do not leave a replaceable clock/factory authority in the public module
# namespace. importlib.reload() executes in the existing module dictionary, so
# also remove the predecessor seam if a caller inserted it before reload.
del _build_current_api
del _clock_text
globals().pop("_process_utc_now_text", None)
