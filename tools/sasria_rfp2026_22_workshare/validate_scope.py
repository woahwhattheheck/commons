#!/usr/bin/env python3
"""Fail-closed validator for the Sasria RFP2026/22 TJLabs workshare package."""
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any

SCHEMA = "tjlabs-sasria-rfp2026-22-workshare/v1"
COMMERCIAL_STATE = "PROPOSED_NOT_ACCEPTED"
EXPECTED_RFP = "2026/22"
EXPECTED_TITLE = "Appointment of Service Provider for Artificial Intelligence Training"
EXPECTED_DOCUMENTS = {
    "2026_22-RFP2026.22 Appointment of Service Provider for Artificial Intelligence Training.pdf",
    "2026_22-SBD 6.1 .docx",
    "2026_22-SCM-Bid documents SBD 1.doc",
    "2026_22-Standard Bidding Document (SDB) 4_Annexure A.doc",
}
REQUIRED_PRIME_GATES = {
    "live_bid_intent_confirmed",
    "procurement_documents_owned",
    "compliance_documents_owned",
    "accreditation_and_certification_evidence_owned",
    "facilitators_and_references_owned",
    "platform_access_owned",
    "bid_pricing_owned",
    "signatory_authority_owned",
    "submission_authority_owned",
    "controlling_tender_criteria_supplied",
}
EXPECTED_DELIVERABLES = {
    "responsible_ai_control_evidence_map",
    "six_role_pathway_acceptance_criteria",
    "hands_on_lab_qa_matrix",
    "deterministic_pre_post_assessment_pack",
    "versioned_evidence_exception_pack",
    "governance_evidence_handoff",
}


def _need(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def _parse_dt(value: Any, field: str, errors: list[str]) -> datetime | None:
    if not isinstance(value, str):
        errors.append(f"{field}: expected ISO-8601 string")
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        errors.append(f"{field}: invalid ISO-8601 timestamp")
        return None
    if parsed.tzinfo is None:
        errors.append(f"{field}: timezone offset required")
        return None
    return parsed


def validate(payload: dict[str, Any], *, release: bool = False) -> list[str]:
    errors: list[str] = []
    _need(payload.get("schema") == SCHEMA, "schema: unsupported or missing", errors)
    _need(payload.get("commercial_state") == COMMERCIAL_STATE,
          "commercial_state: must remain PROPOSED_NOT_ACCEPTED", errors)
    _need(payload.get("fee") == "TO_BE_AGREED", "fee: must remain TO_BE_AGREED before agreement", errors)

    tender = payload.get("tender")
    _need(isinstance(tender, dict), "tender: object required", errors)
    if isinstance(tender, dict):
        _need(tender.get("issuer") == "Sasria SOC Ltd", "tender.issuer: mismatch", errors)
        _need(tender.get("rfp_number") == EXPECTED_RFP, "tender.rfp_number: mismatch", errors)
        _need(tender.get("title") == EXPECTED_TITLE, "tender.title: mismatch", errors)
        _need(tender.get("portal_status") == "Published", "tender.portal_status: expected Published", errors)
        docs = tender.get("documents")
        _need(isinstance(docs, list) and set(docs) == EXPECTED_DOCUMENTS,
              "tender.documents: controlling filename set drifted", errors)
        published = _parse_dt(tender.get("published_at_portal"), "tender.published_at_portal", errors)
        close = _parse_dt(tender.get("closes_at_portal"), "tender.closes_at_portal", errors)
        queries = _parse_dt(tender.get("queries_deadline_at_portal"), "tender.queries_deadline_at_portal", errors)
        if published and close:
            _need(published < close, "tender dates: published must precede close", errors)
        if queries and close:
            _need(queries < close, "tender dates: query deadline must precede close", errors)
        _need(tender.get("closes_at_portal") == "2026-09-17T10:00:00+02:00",
              "tender.closes_at_portal: provider receipt drift", errors)
        _need(tender.get("queries_deadline_at_portal") == "2026-09-13T22:00:00+02:00",
              "tender.queries_deadline_at_portal: provider receipt drift", errors)

    receipt = payload.get("source_receipt")
    _need(isinstance(receipt, dict), "source_receipt: object required", errors)
    if isinstance(receipt, dict):
        _parse_dt(receipt.get("observed_at"), "source_receipt.observed_at", errors)
        _need(receipt.get("source_kind") == "SASRIA_PUBLIC_ETENDER_DETAIL",
              "source_receipt.source_kind: mismatch", errors)
        _need(type(receipt.get("controlling_documents_read")) is bool,
              "source_receipt.controlling_documents_read: boolean required", errors)

    boundary = payload.get("tjlabs_boundary")
    _need(isinstance(boundary, dict), "tjlabs_boundary: object required", errors)
    if isinstance(boundary, dict):
        for false_field in ("prime_role", "submission_authority", "legal_or_compliance_certification", "production_mutation_authority"):
            _need(boundary.get(false_field) is False, f"tjlabs_boundary.{false_field}: must be false", errors)
        _need(boundary.get("learner_pii") == "OPAQUE_IDENTIFIERS_ONLY",
              "tjlabs_boundary.learner_pii: boundary widened", errors)
        deliverables = boundary.get("deliverables")
        _need(isinstance(deliverables, list) and set(deliverables) == EXPECTED_DELIVERABLES,
              "tjlabs_boundary.deliverables: scope drift", errors)

    pathways = payload.get("role_pathways")
    _need(isinstance(pathways, list) and len(pathways) == 6, "role_pathways: exactly six slots required", errors)
    if isinstance(pathways, list):
        expected_ids = {f"role-{i:02d}" for i in range(1, 7)}
        actual_ids = {item.get("id") for item in pathways if isinstance(item, dict)}
        _need(actual_ids == expected_ids, "role_pathways: identifiers drifted", errors)
        for item in pathways:
            _need(isinstance(item, dict) and isinstance(item.get("acceptance_criteria"), list),
                  "role_pathways: each slot requires acceptance_criteria list", errors)

    gates = payload.get("prime_gates")
    _need(isinstance(gates, dict), "prime_gates: object required", errors)
    if isinstance(gates, dict):
        _need(set(gates) == REQUIRED_PRIME_GATES, "prime_gates: exact gate set required", errors)
        for key, value in gates.items():
            _need(type(value) is bool, f"prime_gates.{key}: boolean required", errors)

    release_block = payload.get("release")
    _need(isinstance(release_block, dict), "release: object required", errors)
    if isinstance(release_block, dict):
        _need(release_block.get("buyer_send_allowed") is False,
              "release.buyer_send_allowed: this artifact never grants outbound authority", errors)
        _need(release_block.get("bid_submission_allowed") is False,
              "release.bid_submission_allowed: this artifact never grants submission authority", errors)

    if release:
        _need(isinstance(gates, dict) and all(gates.get(key) is True for key in REQUIRED_PRIME_GATES),
              "release: every prime gate must be explicitly true", errors)
        _need(isinstance(pathways, list) and all(
            isinstance(item, dict) and len(item.get("acceptance_criteria", [])) > 0 for item in pathways
        ), "release: all six role pathways need at least one acceptance criterion", errors)
        _need(isinstance(receipt, dict) and receipt.get("controlling_documents_read") is True,
              "release: controlling tender document bodies must be read", errors)

    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("scope", type=Path)
    parser.add_argument("--release", action="store_true", help="also test readiness to negotiate/hand off scope")
    args = parser.parse_args()
    payload = json.loads(args.scope.read_text(encoding="utf-8"))
    errors = validate(payload, release=args.release)
    if errors:
        for error in errors:
            print(f"HOLD: {error}")
        return 2
    print("VALID")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
