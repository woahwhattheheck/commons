from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA = "tjlabs.usac-it-26-139-qualification/v1"
DEADLINE = datetime(2026, 9, 30, 15, 0, 0, tzinfo=timezone.utc)
PAST_PERFORMANCE_CUTOFF = datetime(2023, 8, 31, tzinfo=timezone.utc)
PAGE_LIMITS = {
    "volume_1_corporate": 4,
    "volume_2_technical": 12,
    "volume_3_past_performance": 5,
    "volume_4_price": 4,
}


class QualificationError(ValueError):
    pass


def _strict_object_pairs(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise QualificationError(f"duplicate JSON key: {key}")
        out[key] = value
    return out


def load_json(path: str | Path) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"), object_pairs_hook=_strict_object_pairs)
    if type(value) is not dict:
        raise QualificationError("packet must be a JSON object")
    return value


def _dict(value: Any, label: str) -> dict[str, Any]:
    if type(value) is not dict:
        raise QualificationError(f"{label} must be an object")
    return value


def _list(value: Any, label: str) -> list[Any]:
    if type(value) is not list:
        raise QualificationError(f"{label} must be an array")
    return value


def _bool(value: Any, label: str) -> bool:
    if type(value) is not bool:
        raise QualificationError(f"{label} must be a boolean")
    return value


def _str(value: Any, label: str, *, allow_empty: bool = False) -> str:
    if type(value) is not str or (not allow_empty and not value.strip()):
        raise QualificationError(f"{label} must be a string")
    return value


def _int(value: Any, label: str) -> int:
    if type(value) is not int or value < 0:
        raise QualificationError(f"{label} must be a non-negative integer")
    return value


def _utc(value: Any, label: str) -> datetime:
    text = _str(value, label)
    if not text.endswith("Z"):
        raise QualificationError(f"{label} must use UTC Z form")
    try:
        parsed = datetime.fromisoformat(text[:-1] + "+00:00")
    except ValueError as exc:
        raise QualificationError(f"{label} invalid UTC timestamp") from exc
    if parsed.microsecond:
        raise QualificationError(f"{label} must be whole-second UTC")
    return parsed.astimezone(timezone.utc)


def _date(value: Any, label: str) -> datetime:
    text = _str(value, label)
    try:
        return datetime.strptime(text, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError as exc:
        raise QualificationError(f"{label} must be YYYY-MM-DD") from exc


def _keys(obj: dict[str, Any], expected: set[str], label: str) -> None:
    if set(obj) != expected:
        raise QualificationError(f"{label} keys invalid")


def evaluate(packet: dict[str, Any]) -> dict[str, Any]:
    packet = _dict(packet, "packet")
    _keys(packet, {
        "schema", "as_of", "source_generation", "organization",
        "key_personnel", "past_performance", "proposal", "route",
    }, "packet")
    if packet["schema"] != SCHEMA:
        raise QualificationError("unsupported schema")

    as_of = _utc(packet["as_of"], "as_of")
    route = _str(packet["route"], "route")
    if route not in {"PRIME", "TEAM"}:
        raise QualificationError("route must be PRIME or TEAM")
    if as_of >= DEADLINE:
        return {
            "schema": SCHEMA,
            "decision": "NO_BID",
            "reason_codes": ["PROPOSAL_DEADLINE_EXPIRED"],
            "external_submission_authorized": False,
        }

    reasons: list[str] = []

    source = _dict(packet["source_generation"], "source_generation")
    _keys(source, {
        "buyer_page_checked_at",
        "complete_package_observed",
        "controlling_rfp_bytes_retained",
        "bid_sheet_bytes_retained",
        "confidentiality_agreement_bytes_retained",
        "q_and_a_bytes_retained",
    }, "source_generation")
    checked = _utc(source["buyer_page_checked_at"], "source_generation.buyer_page_checked_at")
    if checked > as_of:
        reasons.append("SOURCE_OBSERVATION_FROM_FUTURE")
    for key, reason in (
        ("complete_package_observed", "CONTROLLING_PACKAGE_INCOMPLETE"),
        ("controlling_rfp_bytes_retained", "CONTROLLING_RFP_BYTES_MISSING"),
        ("bid_sheet_bytes_retained", "BID_SHEET_BYTES_MISSING"),
        ("confidentiality_agreement_bytes_retained", "CONFIDENTIALITY_AGREEMENT_BYTES_MISSING"),
        ("q_and_a_bytes_retained", "Q_AND_A_BYTES_MISSING"),
    ):
        if not _bool(source[key], f"source_generation.{key}"):
            reasons.append(reason)

    org = _dict(packet["organization"], "organization")
    _keys(org, {
        "uei", "sam_active", "authorized_signer_available",
        "terms_reviewed_by_counsel", "confidentiality_agreement_executable",
        "insurance_evidence_available", "conflict_review_complete",
    }, "organization")
    if not _str(org["uei"], "organization.uei", allow_empty=True).strip():
        reasons.append("UEI_MISSING")
    for key, reason in (
        ("sam_active", "SAM_REGISTRATION_NOT_ACTIVE"),
        ("authorized_signer_available", "AUTHORIZED_SIGNER_MISSING"),
        ("terms_reviewed_by_counsel", "TERMS_COUNSEL_REVIEW_MISSING"),
        ("confidentiality_agreement_executable", "CONFIDENTIALITY_AGREEMENT_NOT_READY"),
        ("insurance_evidence_available", "INSURANCE_EVIDENCE_MISSING"),
        ("conflict_review_complete", "CONFLICT_REVIEW_INCOMPLETE"),
    ):
        if not _bool(org[key], f"organization.{key}"):
            reasons.append(reason)

    people = _list(packet["key_personnel"], "key_personnel")
    ai_sme = additional = team_personnel = 0
    for raw in people:
        row = _dict(raw, "key_personnel row")
        _keys(row, {"person_id", "role", "employer_type", "employed_at_submission"}, "key_personnel row")
        _str(row["person_id"], "key_personnel.person_id")
        role = _str(row["role"], "key_personnel.role")
        employer = _str(row["employer_type"], "key_personnel.employer_type")
        if role not in {"AI_SME", "ADDITIONAL_KEY"}:
            raise QualificationError("key_personnel.role invalid")
        if employer not in {"PRIME", "TEAMING_PARTNER", "SUBCONTRACTOR"}:
            raise QualificationError("key_personnel.employer_type invalid")
        if not _bool(row["employed_at_submission"], "key_personnel.employed_at_submission"):
            reasons.append("KEY_PERSON_NOT_EMPLOYED_AT_SUBMISSION")
        ai_sme += role == "AI_SME"
        additional += role == "ADDITIONAL_KEY"
        team_personnel += employer != "PRIME"
    if ai_sme != 1:
        reasons.append("EXACTLY_ONE_AI_SME_REQUIRED")
    if additional < 1 or additional > 3:
        reasons.append("ADDITIONAL_KEY_PERSONNEL_COUNT_INVALID")
    if len(people) > 4:
        reasons.append("KEY_PERSONNEL_MAX_FOUR_EXCEEDED")

    refs = _list(packet["past_performance"], "past_performance")
    valid_refs: list[str] = []
    prime_refs = team_refs = 0
    ids: set[str] = set()
    for raw in refs:
        row = _dict(raw, "past_performance row")
        _keys(row, {
            "engagement_id", "entity_type", "similar_scope", "reference_reachable",
            "currently_performing", "completed_on",
        }, "past_performance row")
        engagement_id = _str(row["engagement_id"], "past_performance.engagement_id")
        if engagement_id in ids:
            reasons.append("DUPLICATE_PAST_PERFORMANCE_ID")
        ids.add(engagement_id)
        entity = _str(row["entity_type"], "past_performance.entity_type")
        if entity not in {"PRIME", "TEAMING_PARTNER", "SUBCONTRACTOR", "AFFILIATE"}:
            raise QualificationError("past_performance.entity_type invalid")
        similar = _bool(row["similar_scope"], "past_performance.similar_scope")
        reachable = _bool(row["reference_reachable"], "past_performance.reference_reachable")
        current = _bool(row["currently_performing"], "past_performance.currently_performing")
        recent = current or _date(row["completed_on"], "past_performance.completed_on") >= PAST_PERFORMANCE_CUTOFF
        if similar and reachable and recent:
            valid_refs.append(engagement_id)
            if entity == "PRIME":
                prime_refs += 1
            else:
                team_refs += 1
    if len(valid_refs) < 2 or len(valid_refs) > 3:
        reasons.append("TWO_TO_THREE_VALID_REFERENCES_REQUIRED")

    proposal = _dict(packet["proposal"], "proposal")
    _keys(proposal, {
        "page_counts", "with_ai_bid_sheet", "without_ai_bid_sheet",
        "confidentiality_agreement_signed", "legal_review_statement_included",
        "cover_requirements_complete", "final_price_present",
        "price_owner_approved", "no_unsupported_claims",
    }, "proposal")
    counts = _dict(proposal["page_counts"], "proposal.page_counts")
    _keys(counts, set(PAGE_LIMITS), "proposal.page_counts")
    for volume, limit in PAGE_LIMITS.items():
        if _int(counts[volume], f"proposal.page_counts.{volume}") > limit:
            reasons.append(f"{volume.upper()}_PAGE_LIMIT_EXCEEDED")
    for key, reason in (
        ("with_ai_bid_sheet", "WITH_AI_BID_SHEET_MISSING"),
        ("without_ai_bid_sheet", "WITHOUT_AI_BID_SHEET_MISSING"),
        ("confidentiality_agreement_signed", "SIGNED_CONFIDENTIALITY_AGREEMENT_MISSING"),
        ("legal_review_statement_included", "LEGAL_REVIEW_STATEMENT_MISSING"),
        ("cover_requirements_complete", "COVER_REQUIREMENTS_INCOMPLETE"),
        ("final_price_present", "FINAL_PRICE_MISSING"),
        ("price_owner_approved", "FINAL_PRICE_NOT_OWNER_APPROVED"),
        ("no_unsupported_claims", "UNSUPPORTED_CLAIM_PRESENT"),
    ):
        if not _bool(proposal[key], f"proposal.{key}"):
            reasons.append(reason)

    if route == "PRIME":
        if prime_refs < 2:
            reasons.append("PRIME_LACKS_TWO_VALID_REFERENCES")
        if team_personnel:
            reasons.append("PRIME_ROUTE_DEPENDS_ON_TEAM_PERSONNEL")
    elif team_refs == 0 and team_personnel == 0:
        reasons.append("TEAM_ROUTE_HAS_NO_TEAM_EVIDENCE")

    return {
        "schema": SCHEMA,
        "decision": "HOLD" if reasons else ("PRIME_READY" if route == "PRIME" else "TEAMING_READY"),
        "reason_codes": sorted(set(reasons)),
        "valid_reference_count": len(valid_refs),
        "prime_reference_count": prime_refs,
        "team_reference_count": team_refs,
        "external_submission_authorized": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="USAC IT-26-139 offline qualification gate")
    parser.add_argument("packet")
    args = parser.parse_args(argv)
    result = evaluate(load_json(args.packet))
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0 if result["decision"] in {"PRIME_READY", "TEAMING_READY"} else 3


if __name__ == "__main__":
    raise SystemExit(main())
