"""Deterministic route and report compiler for DCSA Innovation Call #01."""

from __future__ import annotations

import copy
import datetime as dt
import hmac
from typing import Any, Dict, Mapping

from .contracts import (
    CONCEPT_DEADLINE,
    ESTIMATED_START_DATE,
    GENERAL_SOLICITATION_ID,
    LIVE_QA_AT,
    MAX_SOURCE_OBSERVATION_AGE,
    NOTICE_ID,
    QUESTION_DEADLINE,
    REPORT_SCHEMA,
    REQUIRED_CAPABILITIES,
    _sha256,
    authority_sha256,
    normalize_authority,
    normalize_candidate,
    normalize_floor,
    normalize_source_ledger,
)
from .strict import ValidationError, canonical_json_bytes, format_utc, parse_utc

def _is_verified(row: Mapping[str, Any]) -> bool:
    return row["state"] == "VERIFIED"


def _route_projection(
    candidate: Mapping[str, Any],
    source: Mapping[str, Any],
    authority: Mapping[str, Any] | None,
    floor: Mapping[str, Any] | None,
    now: dt.datetime,
) -> tuple[str, list[str], Dict[str, Any]]:
    blockers: list[str] = []
    evidence_summary: Dict[str, Any] = {
        "source_complete": bool(source["complete"]),
        "authority_loaded": authority is not None,
        "authority_floor_loaded": floor is not None,
        "required_capabilities_declared": set(candidate["declared_capabilities"])
        == set(REQUIRED_CAPABILITIES),
    }
    source_observed = parse_utc(source["observed_at"], field="source observed_at")
    if source_observed > now:
        blockers.append("SOURCE_OBSERVED_IN_FUTURE")
    if now - source_observed > MAX_SOURCE_OBSERVATION_AGE:
        blockers.append("SOURCE_OBSERVATION_STALE")
    if not source["complete"]:
        blockers.append("CONTROLLING_SOURCE_BYTES_INCOMPLETE")
    if now >= CONCEPT_DEADLINE:
        blockers.append("CONCEPT_PAPER_DEADLINE_CLOSED")
    if set(candidate["declared_capabilities"]) != set(REQUIRED_CAPABILITIES):
        blockers.append("REQUIRED_CAPABILITY_DECLARATIONS_INCOMPLETE")
    if authority is None:
        blockers.append("HOST_AUTHORITY_UNAVAILABLE")
    if floor is None:
        blockers.append("HOST_AUTHORITY_FLOOR_UNAVAILABLE")
    if authority is None or floor is None:
        return "HOLD", sorted(set(blockers)), evidence_summary

    auth_digest = authority_sha256(authority)
    evidence_summary.update(
        {
            "authority_generation": authority["generation"],
            "authority_sha256": auth_digest,
            "authority_valid_until": authority["valid_until"],
        }
    )
    if authority["generation"] != floor["generation"]:
        blockers.append("AUTHORITY_GENERATION_NOT_CURRENT")
    if not hmac.compare_digest(auth_digest, floor["authority_sha256"]):
        blockers.append("AUTHORITY_DIGEST_NOT_CURRENT")
    if not hmac.compare_digest(
        authority["source_generation_sha256"], floor["source_generation_sha256"]
    ):
        blockers.append("AUTHORITY_SOURCE_FLOOR_MISMATCH")
    if not hmac.compare_digest(
        source["source_generation_sha256"], authority["source_generation_sha256"]
    ):
        blockers.append("AUTHORITY_SOURCE_GENERATION_MISMATCH")
    if authority["subject_id"] != candidate["subject_id"]:
        blockers.append("AUTHORITY_SUBJECT_MISMATCH")
    issued_at = parse_utc(authority["issued_at"], field="authority issued_at")
    valid_until = parse_utc(authority["valid_until"], field="authority valid_until")
    if issued_at > now:
        blockers.append("AUTHORITY_ISSUED_IN_FUTURE")
    if valid_until <= now:
        blockers.append("AUTHORITY_EXPIRED")

    capability_states = {
        row["capability"]: row["state"] for row in authority["capability_evidence"]
    }
    unverified_caps = sorted(
        capability for capability, state in capability_states.items() if state != "VERIFIED"
    )
    evidence_summary["unverified_capabilities"] = unverified_caps
    if unverified_caps:
        blockers.append("CAPABILITY_EVIDENCE_INCOMPLETE")

    owner = authority["owner_decisions"]
    if candidate["rom_state"] != "OWNER_APPROVED" or not owner["rom_approved"]:
        blockers.append("ROM_OWNER_APPROVAL_REQUIRED")

    direct_rows = [
        authority["direct_clearance"]["active_top_secret_fcl"],
        authority["personnel"]["all_assigned_us_citizens"],
        authority["personnel"]["all_assigned_interim_secret_or_higher"],
        authority["personnel"]["privileged_users_t5_or_ts_start"],
        authority["personnel"]["cac_operability"],
        authority["ota_eligibility"]["direct_path"],
    ]
    direct_ready = all(_is_verified(row) for row in direct_rows)
    team_ready = _is_verified(authority["ota_eligibility"]["teaming_prime_path"])
    evidence_summary["direct_eligibility_verified"] = direct_ready
    evidence_summary["teaming_prime_eligibility_verified"] = team_ready

    common_blockers = {
        "SOURCE_OBSERVED_IN_FUTURE",
        "SOURCE_OBSERVATION_STALE",
        "CONTROLLING_SOURCE_BYTES_INCOMPLETE",
        "CONCEPT_PAPER_DEADLINE_CLOSED",
        "REQUIRED_CAPABILITY_DECLARATIONS_INCOMPLETE",
        "AUTHORITY_GENERATION_NOT_CURRENT",
        "AUTHORITY_DIGEST_NOT_CURRENT",
        "AUTHORITY_SOURCE_FLOOR_MISMATCH",
        "AUTHORITY_SOURCE_GENERATION_MISMATCH",
        "AUTHORITY_SUBJECT_MISMATCH",
        "AUTHORITY_ISSUED_IN_FUTURE",
        "AUTHORITY_EXPIRED",
        "CAPABILITY_EVIDENCE_INCOMPLETE",
        "ROM_OWNER_APPROVAL_REQUIRED",
    }
    if common_blockers.intersection(blockers):
        return "HOLD", sorted(set(blockers)), evidence_summary

    preference = candidate["route_preference"]
    if preference in {"AUTO", "DIRECT"} and direct_ready and owner["direct_route_approved"]:
        return "DIRECT_READY", [], evidence_summary
    if team_ready and owner["teaming_route_approved"]:
        if preference == "DIRECT" and direct_ready and not owner["direct_route_approved"]:
            blockers.append("DIRECT_ROUTE_NOT_OWNER_APPROVED")
        return "TEAMING_REQUIRED", sorted(set(blockers)), evidence_summary

    if not direct_ready:
        blockers.append("DIRECT_CLEARANCE_OR_PERSONNEL_NOT_VERIFIED")
    if not owner["direct_route_approved"]:
        blockers.append("DIRECT_ROUTE_NOT_OWNER_APPROVED")
    if not team_ready:
        blockers.append("TEAMING_PRIME_ELIGIBILITY_NOT_VERIFIED")
    if not owner["teaming_route_approved"]:
        blockers.append("TEAMING_ROUTE_NOT_OWNER_APPROVED")
    return "HOLD", sorted(set(blockers)), evidence_summary


def _base_report(
    candidate: Mapping[str, Any],
    source: Mapping[str, Any],
    *,
    now: dt.datetime,
    mode: str,
    authority: Mapping[str, Any] | None,
    floor: Mapping[str, Any] | None,
) -> Dict[str, Any]:
    projected_state, blockers, evidence_summary = _route_projection(
        candidate, source, authority, floor, now
    )
    current = mode == "CURRENT"
    state = projected_state if current else "HOLD"
    report: Dict[str, Any] = {
        "schema": REPORT_SCHEMA,
        "mode": mode,
        "evaluated_at": format_utc(now),
        "notice_id": NOTICE_ID,
        "general_solicitation_id": GENERAL_SOLICITATION_ID,
        "subject_id": candidate["subject_id"],
        "operation_id": candidate["operation_id"],
        "concept_title": candidate["concept_title"],
        "state": state,
        "historical_route_projection": None if current else projected_state,
        "blockers": blockers,
        "question_window": "OPEN" if now < QUESTION_DEADLINE else "CLOSED",
        "question_deadline": format_utc(QUESTION_DEADLINE),
        "live_qa_at": format_utc(LIVE_QA_AT),
        "concept_deadline": format_utc(CONCEPT_DEADLINE),
        "estimated_start_date": ESTIMATED_START_DATE,
        "source_generation_sha256": source["source_generation_sha256"],
        "evidence_summary": evidence_summary,
        "external_contact_authorized": False,
        "external_submission_authorized": False,
        "signature_authorized": False,
        "pricing_commitment_authorized": False,
        "clearance_claim_authorized": False,
        "award_or_revenue_claimed": False,
        "current_work_authorized": False,
        "receipt_sha256": "",
    }
    report["current_work_authorized"] = current and state in {
        "DIRECT_READY",
        "TEAMING_REQUIRED",
    }
    report["receipt_sha256"] = _sha256(
        canonical_json_bytes({**report, "receipt_sha256": ""})
    )
    return report


def _compile_at(
    candidate_value: Any,
    source_value: Any,
    authority_value: Any | None,
    floor_value: Any | None,
    *,
    now: dt.datetime,
    mode: str,
) -> Dict[str, Any]:
    if not isinstance(now, dt.datetime) or now.tzinfo is None:
        raise ValidationError("evaluation time must be timezone-aware")
    now = now.astimezone(dt.timezone.utc).replace(microsecond=0)
    candidate = normalize_candidate(candidate_value)
    source = normalize_source_ledger(source_value)
    authority = None if authority_value is None else normalize_authority(authority_value)
    floor = None if floor_value is None else normalize_floor(floor_value)
    if mode not in {"CURRENT", "HISTORICAL_INTEGRITY_ONLY"}:
        raise ValidationError("unsupported evaluation mode")
    return _base_report(
        candidate,
        source,
        now=now,
        mode=mode,
        authority=authority,
        floor=floor,
    )

