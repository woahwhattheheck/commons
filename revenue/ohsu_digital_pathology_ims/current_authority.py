# SPDX-License-Identifier: Apache-2.0
"""Current verifier authority for the OHSU qualification evidence pack.

`qualification.evaluate` is a deterministic candidate compiler used for replay and
historical tests. Current positive authority lives here instead: the verifier
owns both wall-clock time and a completeness-attestation trust root retained
outside the candidate bundle.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from qualification import QualificationError, digest, evaluate as evaluate_candidate

TRUSTED_ROOT_PATH = Path(__file__).with_name("trusted_completeness.sha256")
CURRENT_AUTHORITY_MODE = "VERIFIER_RETAINED_COMPLETENESS_V1"


def _is_sha256(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(
        c in "0123456789abcdef" for c in value
    )


def _utc_now_string() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _candidate_attestation_sha256(payload: dict[str, Any]) -> str | None:
    manifest = payload.get("requirements_manifest")
    if not isinstance(manifest, dict):
        return None
    attestation = manifest.get("completeness_attestation")
    if not isinstance(attestation, dict):
        return None
    value = attestation.get("sha256")
    return value if _is_sha256(value) else None


def _load_trusted_completeness_root() -> str | None:
    """Read the verifier-retained root from a fixed, non-candidate path."""
    try:
        value = TRUSTED_ROOT_PATH.read_text(encoding="utf-8").strip()
    except (OSError, UnicodeError):
        return None
    return value if _is_sha256(value) else None


def _evaluate_with_verifier_root(
    payload: dict[str, Any],
    *,
    evaluated_at: str,
    trusted_completeness_sha256: str | None,
) -> dict[str, Any]:
    """Deterministic verifier seam used by tests and historical reconstruction.

    The trust root is a separate verifier input. It must never be sourced from
    `payload` at this boundary.
    """
    core = evaluate_candidate(payload, evaluated_at=evaluated_at)
    receipt = dict(core)
    receipt.pop("receipt_digest", None)

    holds = set(receipt.get("holds") or [])
    candidate_root = _candidate_attestation_sha256(payload)
    trusted_root_valid = _is_sha256(trusted_completeness_sha256)

    if not trusted_root_valid:
        holds.add("TRUSTED_COMPLETENESS_ROOT_MISSING_OR_INVALID")
    elif candidate_root != trusted_completeness_sha256:
        holds.add("TRUSTED_COMPLETENESS_ROOT_MISMATCH")

    if holds:
        receipt["decision"] = "HOLD"
    receipt["holds"] = sorted(holds)
    receipt["candidate_completeness_attestation_sha256"] = candidate_root
    receipt["trusted_completeness_root_sha256"] = (
        trusted_completeness_sha256 if trusted_root_valid else None
    )
    receipt["current_authority_mode"] = CURRENT_AUTHORITY_MODE
    receipt["current_authority"] = receipt["decision"] == "READY_FOR_INTERNAL_BID_REVIEW"
    receipt["receipt_digest"] = digest(receipt)
    return receipt


def evaluate_current(payload: dict[str, Any]) -> dict[str, Any]:
    """Evaluate current authority with verifier-owned clock and retained root.

    There is deliberately no caller-supplied clock or trust-root parameter on
    this public path. Until `trusted_completeness.sha256` has been provisioned by
    an independent review, even a self-consistent candidate bundle remains HOLD.
    """
    return _evaluate_with_verifier_root(
        payload,
        evaluated_at=_utc_now_string(),
        trusted_completeness_sha256=_load_trusted_completeness_root(),
    )
