#!/usr/bin/env python3
"""Fail-closed readiness gate for the 2026 RCAP CRM assessment opportunity."""
from __future__ import annotations

import argparse
from datetime import date, timedelta
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

SCHEMA = "RCAP_CRM_ASSESSMENT_QUALIFICATION_V1"
OFFICIAL_URL = "https://www.rcap.org/careers/rfp-assessment-strategic-planning-services/"
RELEASE_DATE = date(2026, 9, 4)
QUESTIONS_DUE = date(2026, 9, 13)
PROPOSALS_DUE = date(2026, 10, 4)
MAX_SOURCE_AGE_DAYS = 3
EVALUATION_WEIGHTS = {
    "comparable_assessment": 30,
    "approach_methodology": 25,
    "nonprofit_or_similar": 20,
    "delivery_model": 15,
    "cost_value": 10,
}
DESIRED_QUALIFICATIONS = {
    "crm_or_enterprise_assessment",
    "nonprofit_or_network_experience",
    "stakeholder_discovery",
    "modernization_integration_data_security_governance",
    "vendor_neutral_recommendations",
}


class FactsError(ValueError):
    pass


def _pairs_no_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise FactsError(f"duplicate JSON key: {key}")
        out[key] = value
    return out


def _reject_constant(value: str) -> None:
    raise FactsError(f"non-finite JSON value: {value}")


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_pairs_no_duplicates,
            parse_constant=_reject_constant,
        )
    except (OSError, UnicodeError, json.JSONDecodeError, FactsError) as exc:
        raise FactsError(f"invalid facts file: {exc}") from exc
    if type(value) is not dict:
        raise FactsError("facts root must be an object")
    return value


def _obj(parent: dict[str, Any], key: str) -> dict[str, Any]:
    value = parent.get(key)
    if type(value) is not dict:
        raise FactsError(f"{key} must be an object")
    return value


def _text(parent: dict[str, Any], key: str, *, allow_empty: bool = False) -> str:
    value = parent.get(key)
    if type(value) is not str:
        raise FactsError(f"{key} must be a string")
    if not allow_empty and not value.strip():
        raise FactsError(f"{key} must be non-empty")
    return value


def _bool(parent: dict[str, Any], key: str) -> bool:
    value = parent.get(key)
    if type(value) is not bool:
        raise FactsError(f"{key} must be a boolean")
    return value


def _date(value: Any, field: str) -> date:
    if type(value) is not str:
        raise FactsError(f"{field} must be an ISO date string")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise FactsError(f"{field} must be an ISO date string") from exc
    if value != parsed.isoformat():
        raise FactsError(f"{field} must use canonical YYYY-MM-DD format")
    return parsed


def _canonical_digest(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def evaluate(facts: dict[str, Any], *, today: date | None = None) -> dict[str, Any]:
    today = today or date.today()
    if facts.get("schema") != SCHEMA:
        raise FactsError(f"schema must be {SCHEMA}")

    opportunity = _obj(facts, "opportunity")
    if _text(opportunity, "official_url") != OFFICIAL_URL:
        raise FactsError("official_url does not match the first-party RCAP source")
    if _date(opportunity.get("release_date"), "release_date") != RELEASE_DATE:
        raise FactsError("release_date does not match the first-party RFP")
    if _date(opportunity.get("questions_due"), "questions_due") != QUESTIONS_DUE:
        raise FactsError("questions_due does not match the first-party RFP")
    if _date(opportunity.get("proposals_due"), "proposals_due") != PROPOSALS_DUE:
        raise FactsError("proposals_due does not match the first-party RFP")
    revalidated = _date(opportunity.get("revalidated_date"), "revalidated_date")
    if revalidated > today:
        raise FactsError("revalidated_date cannot be in the future")

    evaluation = _obj(facts, "evaluation")
    if evaluation != EVALUATION_WEIGHTS:
        raise FactsError("evaluation weights do not match the first-party RFP")

    qualification = _obj(facts, "qualification")
    observed_desired = _obj(qualification, "desired_experience")
    if set(observed_desired) != DESIRED_QUALIFICATIONS:
        raise FactsError("desired_experience must enumerate the five RFP qualification dimensions")
    for name, value in observed_desired.items():
        if value not in ("EVIDENCED", "UNKNOWN", "NOT_EVIDENCED"):
            raise FactsError(f"desired_experience.{name} has unsupported state")

    organization = _obj(facts, "organization")
    primary_country = organization.get("primary_place_of_business_country")
    if primary_country is not None and type(primary_country) is not str:
        raise FactsError("primary_place_of_business_country must be a string or null")
    insurance = organization.get("professional_indemnity_coi")
    if insurance not in ("AVAILABLE", "WILL_OBTAIN_BEFORE_AWARD", "UNKNOWN"):
        raise FactsError("professional_indemnity_coi has unsupported state")

    proposal = _obj(facts, "proposal")
    discovery_meetings = proposal.get("discovery_meetings_included")
    if discovery_meetings is not None and (type(discovery_meetings) is not int or discovery_meetings <= 0):
        raise FactsError("discovery_meetings_included must be a positive integer or null")
    fixed_fee = proposal.get("fixed_fee_usd")
    if fixed_fee is not None and (type(fixed_fee) is not int or fixed_fee <= 0):
        raise FactsError("fixed_fee_usd must be a positive whole-dollar integer or null")
    for field in (
        "firm_overview_ready",
        "approach_ready",
        "deliverable_description_ready",
        "schedule_ready",
        "delivery_model_ready",
        "optional_services_separated",
        "deadline_time_revalidated",
        "owner_submission_authorized",
    ):
        _bool(proposal, field)

    blockers: list[str] = []
    warnings: list[str] = []

    if today > PROPOSALS_DUE:
        blockers.append("proposal_deadline_passed")
    if today - revalidated > timedelta(days=MAX_SOURCE_AGE_DAYS):
        blockers.append("official_source_stale")

    if primary_country is None:
        blockers.append("us_primary_place_of_business_unverified")
    elif primary_country != "US":
        blockers.append("us_primary_place_of_business_required")

    if insurance == "UNKNOWN":
        blockers.append("professional_indemnity_coi_plan_unverified")

    required_ready_fields = {
        "firm_overview_ready": "firm_overview_missing",
        "approach_ready": "approach_missing",
        "deliverable_description_ready": "deliverable_description_missing",
        "schedule_ready": "schedule_missing",
        "delivery_model_ready": "delivery_model_missing",
        "optional_services_separated": "optional_services_not_separated",
    }
    for field, blocker in required_ready_fields.items():
        if not proposal[field]:
            blockers.append(blocker)

    if discovery_meetings is None:
        blockers.append("discovery_meeting_count_unset")
    if fixed_fee is None:
        blockers.append("fixed_fee_unset")
    if not proposal["deadline_time_revalidated"]:
        blockers.append("exact_submission_deadline_time_unverified")
    if not proposal["owner_submission_authorized"]:
        blockers.append("owner_submission_authorization_missing")

    unknown_desired = sorted(k for k, v in observed_desired.items() if v != "EVIDENCED")
    if unknown_desired:
        warnings.append("desired_experience_is_not_pass_fail:" + ",".join(unknown_desired))

    references = qualification.get("comparable_examples_or_references")
    if type(references) is not list:
        raise FactsError("comparable_examples_or_references must be a list")
    for index, ref in enumerate(references):
        if type(ref) is not dict:
            raise FactsError(f"reference {index} must be an object")
        _text(ref, "description")
    if not references:
        warnings.append("no_comparable_examples_or_references_supplied_if_available")

    status = "READY_TO_SUBMIT" if not blockers else "HOLD"
    return {
        "schema": SCHEMA,
        "status": status,
        "as_of": today.isoformat(),
        "blockers": blockers,
        "warnings": warnings,
        "questions_window": "OPEN_OR_DATE_UNRESOLVED" if today == QUESTIONS_DUE else ("OPEN" if today < QUESTIONS_DUE else "CLOSED"),
        "days_until_proposal_date": (PROPOSALS_DUE - today).days,
        "source_digest": _canonical_digest({
            "official_url": OFFICIAL_URL,
            "release_date": RELEASE_DATE.isoformat(),
            "questions_due": QUESTIONS_DUE.isoformat(),
            "proposals_due": PROPOSALS_DUE.isoformat(),
            "evaluation": EVALUATION_WEIGHTS,
        }),
        "evaluation_weights": EVALUATION_WEIGHTS,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--facts", default=str(Path(__file__).with_name("qualification.json")))
    parser.add_argument("--today", help="override current date for deterministic validation")
    parser.add_argument("--expect-hold", action="store_true")
    args = parser.parse_args(argv)
    try:
        facts = load_json(Path(args.facts))
        today = _date(args.today, "today") if args.today else date.today()
        result = evaluate(facts, today=today)
    except FactsError as exc:
        print(json.dumps({"status": "INVALID", "error": str(exc)}, sort_keys=True))
        return 2
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    if args.expect_hold:
        return 0 if result["status"] == "HOLD" else 3
    return 0 if result["status"] == "READY_TO_SUBMIT" else 4


if __name__ == "__main__":
    raise SystemExit(main())
