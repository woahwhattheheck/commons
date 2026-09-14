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
    raw = Path(path).read_text(encoding="utf-8")
    value = json.loads(raw, object_pairs_hook=_strict_object_pairs)
    if type(value) is not dict:
        raise QualificationError("packet must be a JSON object")
    return value


def _require_dict(value: Any, label: str) -> dict[str, Any]:
    if type(value) is not dict:
        raise QualificationError(f"{label} must be an object")
    return value


def _require_list(value: Any, label: str) -> list[Any]:
    if type(value) is not list:
        raise QualificationError(f"{label} must be an array")
    return value


def _require_bool(value: Any, label: str) -> bool:
    if type(value) is not bool:
        raise QualificationError(f"{label} must be a boolean")
    return value


def _require_str(value: Any, label: str, *, allow_empty: bool = False) -> str:
    if type(value) is not str or (not allow_empty and not value.strip()):
        raise QualificationError(f"{label} must be a non-empty string")
    return value


def _require_int(value: Any, label: str) -> int:
    if type(value) is not int or value < 0:
        raise QualificationError(f"{label} must be a non-negative integer")
    return value


def _parse_utc(value: Any, label: str) -> datetime:
    text = _require_str(value, label)
    if not text.endswith("Z"):
        raise QualificationError(f"{label} must use UTC Z form")
    try:
        parsed = datetime.fromisoformat(text[:-1] + "+00:00")
    except ValueError as exc:
        raise QualificationError(f"{label} invalid UTC timestamp") from exc
    if parsed.microsecond:
        raise QualificationError(f"{label} must be whole-second UTC")
    return parsed.astimezone(timezone.utc)


def _parse_date(value: Any, label: str) -> datetime:
    text = _require_str(value, label)
    try:
        parsed = datetime.strptime(text, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError as exc:
        raise QualificationError(f"{label} must be YYYY-MM-DD") from exc
    return parsed


def _valid_reference(row: dict[str, Any]) -> tuple[bool, str]:
    entity_type = _require_str(row.get("entity_type"), "past_performance.entity_type")
    if entity_type not in {"PRIME", "TEAMING_PARTNER", "SUBCONTRACTOR", "AFFILIATE"}:
        raise QualificationError("past_performance.entity_type invalid")
    similar = _require_bool(row.get("similar_scope"), "past_performance.similar_scope")
    reachable = _require_bool(row.get("reference_reachable"), "past_performance.reference_reachable")
    current = _require_bool(row.get("currently_performing"), "past_performance.currently_performing")
    _require_str(row.get("engagement_id"), "past_performance.engagement_id")
    if current:
        recent = True
    else:
        recent = _parse_date(row.get("completed_on"), "past_performance.completed_on") >= PAST_PERFORMANCE_CUTOFF
    return similar and reachable and recent, entity_type


def evaluate(packet: dict[str, Any]) -> dict[str, Any]:
    packet = _require_dict(packet, "packet")
    if set(packet) != {
        "schema",
        "as_of",
        "source_generation",
        "organization",
        "key_personnel",
        "past_performance",
        "proposal",
        "route",
    }:
        raise QualificationError("packet keys must match schema exactly")
    if packet["schema"] != SCHEMA:
        raise QualificationError("unsupported schema")

    as_of = _parse_utc(packet["as_of"], "as_of")
    route = _require_str(packet["route"], "route")
    if route not in {"PRIME", "TEAM"}:
        raise QualificationError("route must be PRIME or TEAM")

    reasons: list[str] = []
    if as_of >= DEADLINE:
        return {
            "schema": SCHEMA,
            "decision": "NO_BID",
            "reason_codes": ["PROPOSAL_DEADLINE_EXPIRED"],
            "external_submission_authorized": False,
        }

    source = _require_dict(packet["source_generation"], "source_generation")
    if set(source) != {"buyer_page_checked_at", "complete_package_observed"}:
        raise QualificationError("source_generation keys invalid")
    checked = _parse_utc(source["buyer_page_checked_at"], "buyer_page_checked_at")
    if checked > as_of:
        reasons.append("SOURCE_OBSERVATION_FROM_FUTURE")
    if not _require_bool(source["complete_package_observed"], "complete_package_observed"):
        reasons.append("CONTROLLING_PACKAGE_INCOMPLETE")

    org = _require_dict(packet["organization"], "organization")
    required_org = {
        "uei",
        "sam_active",
        "authorized_signer_available",
        "terms_reviewed_by_counsel",
        "confidentiality_agreement_executable",
        "insurance_evidence_available",
        "conflict_review_complete",
    }
    if set(org) != required_org:
        raise QualificationError("organization keys invalid")
    if not _require_str(org["uei"], "organization.uei", allow_empty=True).strip():
        reasons.append("UEI_MISSING")
    for key, reason in (
        ("sam_active", "SAM_REGISTRATION_NOT_ACTIVE"),
        ("authorized_signer_available", "AUTHORIZED_SIGNER_MISSING"),
        ("terms_reviewed_by_counsel", "TERMS_COUNSEL_REVIEW_MISSING"),
        ("confidentiality_agreement_executable", "CONFIDENTIALITY_AGREEMENT_NOT_READY"),
        ("insurance_evidence_available", "INSURANCE_EVIDENCE_MISSING"),
        ("conflict_review_complete", "CONFLICT_REVIEW_INCOMPLETE"),
    ):
        if not _require_bool(org[key], f"organization.{key}"):
            reasons.append(reason)

    people = _require_list(packet["key_personnel"], "key_personnel")
    ai_sme = 0
    additional = 0
    team_personnel = 0
    for raw in people:
        row = _require_dict(raw, "key_personnel row")
        if set(row) != {"person_id", "role", "employer_type", "employed_at_submission"}:
            raise QualificationError("key_personnel row keys invalid")
        _require_str(row["person_id"], "key_personnel.person_id")
        role = _require_str(row["role"], "key_personnel.role")
        employer = _require_str(row["employer_type"], "key_personnel.employer_type")
        if role not in {"AI_SME", "ADDITIONAL_KEY"}:
            raise QualificationError("key_personnel.role invalid")
        if employer not in {"PRIME", "TEAMING_PARTNER", "SUBCONTRACTOR"}:
            raise QualificationError("key_personnel.employer_type invalid")
        if not _require_bool(row["employed_at_submission"], "key_personnel.employed_at_submission"):
            reasons.append("KEY_PERSON_NOT_EMPLOYED_AT_SUBMISSION")
        if role == "AI_SME":
            ai_sme += 1
        else:
            additional += 1
        if employer != "PRIME":
            team_personnel += 1
    if ai_sme != 1:
        reasons.append("EXACTLY_ONE_AI_SME_REQUIRED")
    if additional < 1 or additional > 3:
        reasons.append("ADDITIONAL_KEY_PERSONNEL_COUNT_INVALID")
    if len(people) > 4:
        reasons.append("KEY_PERSONNEL_MAX_FOUR_EXCEEDED")

    refs = _require_list(packet["past_performance"], "past_performance")
    valid_refs = []
    prime_refs = 0
    team_refs = 0
    ids = set()
    for raw in refs:
        row = _require_dict(raw, "past_performance row")
        expected = {
            "engagement_id",
            "entity_type",
            "similar_scope",
            "reference_reachable",
            "currently_performing",
            "completed_on",
        }
        if set(row) != expected:
            raise QualificationError("past_performance row keys invalid")
        engagement_id = _require_str(row["engagement_id"], "past_performance.engagement_id")
        if engagement_id in ids:
            reasons.append("DUPLICATE_PAST_PERFORMANCE_ID")
        ids.add(engagement_id)
        ok, entity = _valid_reference(row)
        if ok:
            valid_refs.append(engagement_id)
            if entity == "PRIME":
                prime_refs += 1
            else:
                team_refs += 1
    if len(valid_refs) < 2 or len(valid_refs) > 3:
        reasons.append("TWO_TO_THREE_VALID_REFERENCES_REQUIRED")

    proposal = _require_dict(packet["proposal"], "proposal")
    required_prop = {
        "page_counts",
        "with_ai_bid_sheet",
        "without_ai_bid_sheet",
        "confidentiality_agreement_signed",
        "legal_review_statement_included",
        "cover_requirements_complete",
        "final_price_present",
        "price_owner_approved",
        "no_unsupported_claims",
    }
    if set(proposal) != required_prop:
        raise QualificationError("proposal keys invalid")
    counts = _require_dict(proposal["page_counts"], "proposal.page_counts")
    if set(counts) != set(PAGE_LIMITS):
        raise QualificationError("page_counts keys invalid")
    for volume, limit in PAGE_LIMITS.items():
        if _require_int(counts[volume], f"page_counts.{volume}") > limit:
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
        if not _require_bool(proposal[key], f"proposal.{key}"):
            reasons.append(reason)

    if route == "PRIME":
        if prime_refs < 2:
            reasons.append("PRIME_LACKS_TWO_VALID_REFERENCES")
        if team_personnel:
            reasons.append("PRIME_ROUTE_DEPENDS_ON_TEAM_PERSONNEL")
    else:
        if team_refs == 0 and team_personnel == 0:
            reasons.append("TEAM_ROUTE_HAS_NO_TEAM_EVIDENCE")

    decision = "HOLD" if reasons else ("PRIME_READY" if route == "PRIME" else "TEAMING_READY")
    return {
        "schema": SCHEMA,
        "decision": decision,
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
