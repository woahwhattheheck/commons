from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .core import ProofCutError, canonical_json

REQUIRED_EXTERNAL = (
    "application_submitted",
    "acceptance_confirmed",
    "in_person_attendance_confirmed",
    "participant_credits_issued",
    "event_submission_completed",
)

def compile_readiness(source: dict[str, Any], witness: dict[str, Any] | None = None) -> dict[str, Any]:
    if source.get("schema") != "proofcut.readiness-source.v1":
        raise ProofCutError("bad readiness source schema")
    if witness is not None and witness.get("schema") != "proofcut.external-witness.v1":
        raise ProofCutError("bad witness schema")
    witness = witness or {"schema": "proofcut.external-witness.v1"}
    status: dict[str, bool] = {}
    for key in REQUIRED_EXTERNAL:
        status[key] = witness.get(key) is True
    source_ok = all(source.get(k) is True for k in (
        "prototype_tests_pass",
        "application_copy_ready",
        "shipped_link_ready",
        "idea_within_280_chars",
        "no_committed_secret",
    ))
    # Acceptance, credits and submission can never be minted from source facts.
    application_ready = source_ok
    event_submission_ready = source_ok and all(status.values())
    core = {
        "schema": "proofcut.readiness.v1",
        "source_ok": source_ok,
        "external": status,
        "application_packet_status": "READY" if application_ready else "HOLD",
        "competition_status": "SUBMITTED" if event_submission_ready else "HOLD_EXTERNAL",
    }
    return {**core, "sha256": hashlib.sha256(canonical_json(core)).hexdigest()}
