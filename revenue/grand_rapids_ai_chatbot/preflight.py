#!/usr/bin/env python3
"""Fail-closed proposal readiness preflight for Grand Rapids RFP 920-45-269.

This module never submits a bid, contacts the buyer, or mutates a portal.  It only
turns a source/evidence state document into a deterministic HOLD/READY receipt.
READY means every named gate has explicit PASS evidence and the owner has
released the package for submission; it is not an award, acceptance, or payment.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "grand-rapids-920-45-269-preflight/v1"
ALLOWED_STATUS = {"PASS", "HOLD"}
REQUIRED_GATES = (
    "controlling_packet_acquired",
    "packet_sha256_verified",
    "question_channel_resolved",
    "addenda_reconciled",
    "bidder_eligibility_resolved",
    "vss_registration_resolved",
    "ebo_requirements_resolved",
    "certifications_resolved",
    "references_resolved",
    "mandatory_forms_complete",
    "technical_narrative_complete",
    "integration_scope_resolved",
    "security_requirements_resolved",
    "acceptance_plan_complete",
    "pricing_form_complete",
    "owner_release_to_submit",
)


def _canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _nonempty_strings(value: Any) -> bool:
    return isinstance(value, list) and bool(value) and all(isinstance(v, str) and v.strip() for v in value)


def evaluate(state: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    blockers: list[dict[str, str]] = []

    if state.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"schema_version must be {SCHEMA_VERSION!r}")

    if state.get("solicitation_id") != "920-45-269":
        errors.append("solicitation_id must be exactly '920-45-269'")

    gates = state.get("gates")
    if not isinstance(gates, dict):
        errors.append("gates must be an object")
        gates = {}

    unknown = sorted(set(gates) - set(REQUIRED_GATES))
    if unknown:
        errors.append("unknown gates: " + ", ".join(unknown))

    for gate in REQUIRED_GATES:
        entry = gates.get(gate)
        if not isinstance(entry, dict):
            errors.append(f"gate {gate!r} must be an object")
            continue
        status = entry.get("status")
        if status not in ALLOWED_STATUS:
            errors.append(f"gate {gate!r} status must be PASS or HOLD")
            continue
        evidence = entry.get("evidence")
        reason = entry.get("reason")
        if not isinstance(reason, str) or not reason.strip():
            errors.append(f"gate {gate!r} requires a non-empty reason")
        if status == "PASS":
            if not _nonempty_strings(evidence):
                errors.append(f"gate {gate!r} PASS requires non-empty evidence strings")
            elif any(v.startswith("placeholder:") or v.startswith("unknown:") for v in evidence):
                errors.append(f"gate {gate!r} PASS cannot rely on placeholder/unknown evidence")
        else:
            blockers.append({"gate": gate, "reason": reason.strip() if isinstance(reason, str) else "missing reason"})

    for hard_gate in ("controlling_packet_acquired", "packet_sha256_verified", "owner_release_to_submit"):
        if not isinstance(gates.get(hard_gate), dict) or gates[hard_gate].get("status") != "PASS":
            if not any(b["gate"] == hard_gate for b in blockers):
                blockers.append({"gate": hard_gate, "reason": "hard fail-closed submission gate"})

    status = "INVALID" if errors else ("HOLD" if blockers else "READY")
    material = {
        "schema_version": state.get("schema_version"),
        "solicitation_id": state.get("solicitation_id"),
        "gates": gates,
    }
    digest = hashlib.sha256(_canonical_json(material)).hexdigest()
    return {
        "schema_version": SCHEMA_VERSION,
        "solicitation_id": "920-45-269",
        "status": status,
        "state_sha256": digest,
        "blockers": blockers,
        "errors": errors,
        "authority": "readiness-evidence-only; no portal mutation, signature, submission, award, or payment authority",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("state", type=Path)
    parser.add_argument("--write-receipt", type=Path)
    args = parser.parse_args()
    state = json.loads(args.state.read_text(encoding="utf-8"))
    receipt = evaluate(state)
    rendered = json.dumps(receipt, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    if args.write_receipt:
        args.write_receipt.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if receipt["status"] in {"HOLD", "READY"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
