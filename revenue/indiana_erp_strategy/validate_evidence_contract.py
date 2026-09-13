#!/usr/bin/env python3
"""Fail-closed validator for the Indiana ERP evidence/traceability packet."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
DEFAULT_CONTRACT = HERE / "evidence_contract.json"

MANDATORY_FORBIDDEN = {
    "indiana_endorsement_or_engagement",
    "verified_public_sector_erp_past_performance_without_evidence",
    "direct_submission_authority_without_owner_approval",
    "unknown_current_state_fact_as_observation",
    "cost_estimate_without_basis",
    "recommendation_without_traceability",
    "product_selection_by_bounded_workstream",
}
MANDATORY_RULES = {
    "observations_require_source_ids": True,
    "unknowns_may_be_promoted_to_observations": False,
    "assumptions_require_owner_and_status": True,
    "dependencies_require_source_ids": True,
    "options_require_evidence_or_assumption_refs": True,
    "risks_require_basis_and_owner": True,
    "cost_ranges_require_basis_currency_exclusions": True,
    "recommendations_require_evidence_and_assumption_refs": True,
    "source_changes_require_impact_recalculation": True,
}
MANDATORY_RECORD_FIELDS = {
    "source": {"id", "kind", "title", "date", "owner", "provenance"},
    "observation": {"id", "statement", "source_ids"},
    "assumption": {"id", "statement", "owner", "status", "confidence"},
    "dependency": {"id", "from", "to", "kind", "source_ids"},
    "option": {"id", "statement", "criteria", "evidence_refs", "assumption_refs"},
    "risk": {"id", "statement", "trigger", "impact", "mitigation", "owner", "basis_refs"},
    "cost_range": {"id", "minimum", "maximum", "currency", "basis_refs", "assumption_refs", "exclusions"},
    "recommendation": {"id", "statement", "evidence_refs", "assumption_refs", "decision_owner"},
}


class ContractError(ValueError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ContractError(message)


def validate_contract(contract: dict[str, Any]) -> None:
    require(contract.get("schema_version") == 1, "schema_version must be 1")
    require(contract.get("opportunity") == "27-87809", "opportunity must remain 27-87809")
    require(contract.get("event_id") == "000610000087809", "event_id mismatch")
    require(contract.get("procurement_state") == "market_research_rfi", "procurement state must remain market_research_rfi")
    require(contract.get("direct_state_submission_authorized") is False, "direct State submission must remain unauthorized")
    require(contract.get("customer_prime_decision_authority_retained") is True, "customer/prime decision authority must be retained")
    require(contract.get("erp_product_selection_in_scope") is False, "ERP product selection must remain out of scope")

    qualifications = contract.get("qualification_evidence")
    require(isinstance(qualifications, dict), "qualification_evidence must be an object")
    for field in (
        "indiana_customer_relationship_verified",
        "public_sector_erp_past_performance_verified",
        "prime_bidder_authority_verified",
    ):
        require(qualifications.get(field) is False, f"{field} cannot be promoted inside this packet")

    rules = contract.get("evidence_rules")
    require(isinstance(rules, dict), "evidence_rules must be an object")
    for rule, value in MANDATORY_RULES.items():
        require(rules.get(rule) is value, f"evidence rule weakened: {rule}")

    forbidden = contract.get("forbidden_claims")
    require(isinstance(forbidden, list), "forbidden_claims must be a list")
    require(MANDATORY_FORBIDDEN.issubset(set(forbidden)), "mandatory forbidden claim missing")

    records = contract.get("required_record_types")
    require(isinstance(records, list) and records, "required_record_types must be non-empty")
    seen: set[str] = set()
    for record in records:
        require(isinstance(record, dict), "record type entry must be an object")
        kind = record.get("type")
        require(kind in MANDATORY_RECORD_FIELDS, f"unknown or missing record type: {kind}")
        require(kind not in seen, f"duplicate record type: {kind}")
        seen.add(kind)
        fields = record.get("required_fields")
        require(isinstance(fields, list), f"{kind}.required_fields must be a list")
        require(MANDATORY_RECORD_FIELDS[kind].issubset(set(fields)), f"{kind} is missing mandatory fields")
    require(seen == set(MANDATORY_RECORD_FIELDS), "one or more mandatory record types are missing")


def load_contract(path: Path = DEFAULT_CONTRACT) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ContractError(f"cannot load contract: {exc}") from exc
    require(isinstance(data, dict), "contract root must be an object")
    return data


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) > 1:
        print("usage: validate_evidence_contract.py [evidence_contract.json]", file=sys.stderr)
        return 2
    path = Path(args[0]) if args else DEFAULT_CONTRACT
    try:
        validate_contract(load_contract(path))
    except ContractError as exc:
        print(f"INVALID: {exc}", file=sys.stderr)
        return 1
    print(f"VALID: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
