#!/usr/bin/env python3
"""Fail-closed gate for the Kentucky AI Workforce Readiness response kit.

Exit codes:
  0 READY   all mandatory gates are explicitly RESOLVED with evidence
  1 INVALID manifest contract is malformed or contradictory
  2 HOLD    manifest is valid but one or more mandatory gates are OPEN/DRAFTED

This validator does not authorize submission. It only validates the internal gate ledger.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ALLOWED_STATES = {"OPEN", "DRAFTED", "RESOLVED"}
PLACEHOLDER_TOKENS = ("[OPEN]", "TBD", "TODO", "PLACEHOLDER")
REQUIRED_GATE_IDS = {
    "source_freshness",
    "both_services_and_five_pathways",
    "partner_legal_role_and_consent",
    "minimum_three_year_experience_attribution",
    "three_comparable_references",
    "named_instructor_roster",
    "live_remote_and_kentucky_in_person_capacity",
    "prime_admin_financial_and_federal_funds_capacity",
    "accessibility_plan",
    "privacy_security_and_participant_data_plan",
    "attendance_completion_reporting_and_audit",
    "ip_licensing_and_reviewable_materials",
    "commercial_model_and_approved_prices",
    "subcontractor_disclosure_and_role_matrix",
    "legal_registration_insurance_and_certifications",
    "authorized_signatory_and_submission_owner",
    "final_current_instruction_check",
    "final_package_hash_and_submission_authorization",
}


class DuplicateKeyError(ValueError):
    pass


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise DuplicateKeyError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


@dataclass(frozen=True)
class GateResult:
    gate_id: str
    state: str
    evidence: str


@dataclass(frozen=True)
class Evaluation:
    status: str
    gates: tuple[GateResult, ...]

    @property
    def ready(self) -> bool:
        return self.status == "READY"


def load_manifest_text(text: str) -> dict[str, Any]:
    payload = json.loads(text, object_pairs_hook=_unique_object)
    if not isinstance(payload, dict):
        raise ValueError("manifest root must be an object")
    return payload


def evaluate_manifest(payload: dict[str, Any]) -> Evaluation:
    if payload.get("schema_version") != 1:
        raise ValueError("schema_version must be exactly 1")

    gates = payload.get("gates")
    if not isinstance(gates, list):
        raise ValueError("gates must be a list")

    seen: set[str] = set()
    evaluated: list[GateResult] = []
    for index, raw in enumerate(gates):
        if not isinstance(raw, dict):
            raise ValueError(f"gate[{index}] must be an object")

        gate_id = raw.get("id")
        state = raw.get("state")
        evidence = raw.get("evidence")
        mandatory = raw.get("mandatory")

        if not isinstance(gate_id, str) or not gate_id.strip():
            raise ValueError(f"gate[{index}] id must be a non-empty string")
        if gate_id in seen:
            raise ValueError(f"duplicate gate id: {gate_id}")
        seen.add(gate_id)

        if mandatory is not True:
            raise ValueError(f"gate {gate_id} must be mandatory=true")
        if state not in ALLOWED_STATES:
            raise ValueError(f"gate {gate_id} has invalid state: {state!r}")
        if not isinstance(evidence, str):
            raise ValueError(f"gate {gate_id} evidence must be a string")

        clean_evidence = evidence.strip()
        if state in {"DRAFTED", "RESOLVED"} and not clean_evidence:
            raise ValueError(f"gate {gate_id} state {state} requires evidence")
        if state == "RESOLVED" and any(token in clean_evidence.upper() for token in PLACEHOLDER_TOKENS):
            raise ValueError(f"gate {gate_id} RESOLVED evidence contains a placeholder token")
        if state == "OPEN" and clean_evidence:
            raise ValueError(f"gate {gate_id} OPEN must not carry pseudo-evidence")

        evaluated.append(GateResult(gate_id=gate_id, state=state, evidence=clean_evidence))

    missing = REQUIRED_GATE_IDS - seen
    extra = seen - REQUIRED_GATE_IDS
    if missing:
        raise ValueError(f"missing required gate(s): {', '.join(sorted(missing))}")
    if extra:
        raise ValueError(f"unexpected gate(s): {', '.join(sorted(extra))}")

    status = "READY" if all(g.state == "RESOLVED" for g in evaluated) else "HOLD"
    return Evaluation(status=status, gates=tuple(evaluated))


def _print_human(evaluation: Evaluation, path: Path) -> None:
    blockers = [gate for gate in evaluation.gates if gate.state != "RESOLVED"]
    print(f"KY AI Workforce response kit: {evaluation.status} — {path}")
    print(f"  gates: {len(evaluation.gates)} total / {len(blockers)} unresolved")
    for gate in blockers:
        print(f"  - {gate.gate_id}: {gate.state}")


def main(argv: list[str] | None = None) -> int:
    default_path = Path(__file__).with_name("readiness_manifest.json")
    parser = argparse.ArgumentParser(description="Fail closed on unresolved SCWDB response gates.")
    parser.add_argument("path", nargs="?", type=Path, default=default_path)
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args(argv)

    try:
        text = args.path.read_text(encoding="utf-8")
        evaluation = evaluate_manifest(load_manifest_text(text))
    except (OSError, UnicodeError, json.JSONDecodeError, DuplicateKeyError, ValueError) as exc:
        if args.as_json:
            print(json.dumps({"status": "INVALID", "path": str(args.path), "error": str(exc)}, sort_keys=True))
        else:
            print(f"KY AI Workforce response kit: INVALID — {exc}", file=sys.stderr)
        return 1

    if args.as_json:
        print(
            json.dumps(
                {
                    "status": evaluation.status,
                    "path": str(args.path),
                    "gate_count": len(evaluation.gates),
                    "unresolved": [
                        {"id": gate.gate_id, "state": gate.state}
                        for gate in evaluation.gates
                        if gate.state != "RESOLVED"
                    ],
                },
                sort_keys=True,
            )
        )
    else:
        _print_human(evaluation, args.path)

    return 0 if evaluation.ready else 2


if __name__ == "__main__":
    raise SystemExit(main())
