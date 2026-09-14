"""Current-only TTUHSC 739-SL3821039 evidence gate.

The original PR #14310 caller-assertion qualifier was independently source-RED because
one runtime packet could assert both facts and the values that supposedly authorized
PRIME/TEAM readiness, including a caller-selected clock. This replacement exposes no
caller clock and no PRIME/TEAM self-certification path. Current evidence is evaluated
only through the repo-pinned Pursuit Evidence Bridge binding.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from revenue.pursuit_evidence_bridge.bridge import (  # noqa: E402
    BridgeError,
    compile_bridge,
    load_json as bridge_load_json,
)

BINDING_ID = "ttuhsc-739-sl3821039-main-v1"
SCHEMA = "tjlabs.ttuhsc-739-sl3821039-current-gate/v2"


class QualificationError(ValueError):
    """Malformed current-gate input."""


def _exact_keys(value: Any, expected: set[str], label: str) -> dict[str, Any]:
    if type(value) is not dict:
        raise QualificationError(f"{label} must be an object")
    if set(value) != expected:
        missing = sorted(expected - set(value))
        extra = sorted(set(value) - expected)
        raise QualificationError(f"{label} keys invalid missing={missing} extra={extra}")
    return value


def load_json(path: str | Path) -> dict[str, Any]:
    try:
        return bridge_load_json(Path(path).read_bytes(), str(path))
    except (OSError, BridgeError) as exc:
        raise QualificationError(str(exc)) from exc


def evaluate_current(envelope: dict[str, Any]) -> dict[str, Any]:
    """Evaluate repo-pinned opportunity evidence at the bridge's process-owned UTC.

    The envelope intentionally has no as_of, deadline, route, expected hash, owner
    approval, signature, reference, staffing, security, or pricing authority fields.
    Those values can affect readiness only after independently retained evidence is
    pinned by ordinary repository review.
    """
    envelope = _exact_keys(envelope, {"source_ledger", "submission_manifest", "vault"}, "envelope")
    try:
        bridge_result = compile_bridge(
            BINDING_ID,
            envelope["source_ledger"],
            envelope["submission_manifest"],
            envelope["vault"],
        )
    except BridgeError as exc:
        raise QualificationError(str(exc)) from exc

    # Keep the shared bridge vocabulary. OPPORTUNITY_EVIDENCE_READY is deliberately
    # not translated into PRIME_READY / TEAMING_READY: route choice and proposal action
    # remain separate authority decisions. The current production binding is HOLD.
    return {
        "schema": SCHEMA,
        "binding_id": BINDING_ID,
        "status": bridge_result["status"],
        "reason_codes": list(bridge_result["reason_codes"]),
        "evaluated_at": bridge_result["evaluated_at"],
        "deadline_utc": bridge_result["deadline_utc"],
        "source_ledger": bridge_result["source_ledger"],
        "submission_manifest": bridge_result["submission_manifest"],
        "vault": bridge_result["vault"],
        "authority": dict(bridge_result["authority"]),
        "external_submission_authorized": False,
        "semantic_boundary": (
            "This gate reports repo-pinned opportunity evidence only. It never emits PRIME_READY "
            "or TEAMING_READY and never authorizes buyer/reference contact, TechBid/portal mutation, "
            "submission, signature, certification/compliance claims, pricing/staffing commitments, "
            "contract acceptance, spend, award, payment, or revenue recognition."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="TTUHSC 739-SL3821039 current repo-pinned evidence gate")
    parser.add_argument("envelope", help="JSON with exactly source_ledger, submission_manifest, vault")
    args = parser.parse_args(argv)
    try:
        result = evaluate_current(load_json(args.envelope))
    except QualificationError as exc:
        raise SystemExit(f"HOLD: {exc}") from exc
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0 if result["status"] == "OPPORTUNITY_EVIDENCE_READY" else 2


if __name__ == "__main__":
    raise SystemExit(main())
