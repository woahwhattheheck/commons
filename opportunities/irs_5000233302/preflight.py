#!/usr/bin/env python3
"""Fail-closed internal preflight for IRS 5000233302 partner-first capture.

This program performs no network call, outreach, form submission, buyer response,
signature, spend, contract, payment, receivable, or revenue action.
"""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

SOURCE_SCHEMA = "irs.5000233302.source/v1"
OWNER_SCHEMA = "irs.5000233302.owner_inputs/v1"
PARTNER_SCHEMA = "irs.5000233302.partner_shortlist/v1"

HOLD = "HOLD"
PARTNER_PACKET_READY = "PARTNER_PACKET_READY"
DIRECT_IRS_HOLD = "DIRECT_IRS_HOLD"

MAX_SOURCE_AGE = timedelta(days=4)
UTC_RE = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z")
PLACEHOLDER_RE = re.compile(r"(?:OWNER_INPUT_REQUIRED|\bUNKNOWN\b|\bTBD\b|\bTODO\b)", re.I)
URL_RE = re.compile(r"https://[^\s]+")

AUTHORITY_FALSE_KEYS = {
    "respond_to_irs_authorized",
    "represent_prime_eligibility_authorized",
    "represent_contract_vehicle_authorized",
    "represent_past_performance_authorized",
    "contact_partner_authorized",
    "award_or_revenue_claim_authorized",
}

EXPECTED_TASKS = [
    "Transition-In",
    "Program Intake and Platform Migration Port/Test",
    "Source System Analysis and Data Acquisition",
    "Databricks Pipeline Development and Transformation",
    "Data Product Design and BI Consumption",
    "Metadata, Governance, Security, and Data Quality",
    "Self-Service Analytics and Natural-Language Query Enablement",
    "AI-Assisted Legacy Modernization Support",
    "DevSecOps, Automation, and Deployment",
    "Testing, Performance, and Production Readiness",
    "Operations, Maintenance, and Production Support",
    "Transition-Out",
]


class PreflightError(ValueError):
    pass


def _pairs(pairs):
    out = {}
    for k, v in pairs:
        if k in out:
            raise PreflightError(f"duplicate JSON key: {k}")
        out[k] = v
    return out


def _bad_constant(value: str):
    raise PreflightError(f"non-finite JSON value: {value}")


def load(path: Path) -> dict:
    raw = path.read_bytes()
    if len(raw) > 2_000_000:
        raise PreflightError(f"{path}: input too large")
    try:
        value = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_pairs,
            parse_constant=_bad_constant,
        )
    except UnicodeDecodeError as exc:
        raise PreflightError(f"{path}: not UTF-8") from exc
    except json.JSONDecodeError as exc:
        raise PreflightError(f"{path}: invalid JSON") from exc
    if not isinstance(value, dict):
        raise PreflightError(f"{path}: root must be object")
    return value


def parse_utc(value: Any, label: str) -> datetime:
    if not isinstance(value, str) or not UTC_RE.fullmatch(value):
        raise PreflightError(f"{label}: canonical UTC required")
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=timezone.utc
        )
    except ValueError as exc:
        raise PreflightError(f"{label}: invalid UTC") from exc


def _nonempty_text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _source(source: dict, now: datetime, blockers: list[str]) -> None:
    if source.get("schema") != SOURCE_SCHEMA:
        raise PreflightError("source schema mismatch")
    if source.get("notice_number") != "5000233302":
        raise PreflightError("notice number mismatch")
    if source.get("buyer") != "Internal Revenue Service":
        raise PreflightError("buyer mismatch")
    if source.get("notice_type") != "SOURCES_SOUGHT":
        raise PreflightError("notice type must remain SOURCES_SOUGHT")
    if source.get("market_research_only") is not True:
        raise PreflightError("market-research truth drift")
    if source.get("response_is_proposal") is not False:
        raise PreflightError("Sources Sought response must not become proposal")
    if source.get("government_commitment_to_award") is not False:
        raise PreflightError("award commitment must remain false")
    if source.get("naics") != "541512" or source.get("psc") != "DA01":
        raise PreflightError("NAICS/PSC drift")
    value = source.get("anticipated_value_usd")
    if value != {"min": 15000000, "max": 20000000}:
        raise PreflightError("market-research value range drift")
    if source.get("task_areas") != EXPECTED_TASKS:
        raise PreflightError("task-area inventory drift")
    questions = source.get("questions")
    if (
        not isinstance(questions, list)
        or len(questions) != 9
        or not all(_nonempty_text(x) for x in questions)
    ):
        raise PreflightError("nine market-research questions required")
    sources = source.get("sources")
    if not isinstance(sources, list) or len(sources) < 4:
        raise PreflightError("source inventory incomplete")
    for i, row in enumerate(sources):
        if not isinstance(row, dict) or set(row) != {"class", "url", "label"}:
            raise PreflightError(f"source row {i} malformed")
        if (
            not _nonempty_text(row["class"])
            or not _nonempty_text(row["label"])
            or not isinstance(row["url"], str)
            or not URL_RE.fullmatch(row["url"])
        ):
            raise PreflightError(f"source row {i} invalid")
    authority = source.get("authority")
    if (
        not isinstance(authority, dict)
        or set(authority) != AUTHORITY_FALSE_KEYS
        or any(authority.values())
    ):
        raise PreflightError("source authority ceiling drift")
    checked = parse_utc(source.get("checked_at"), "source.checked_at")
    deadline = parse_utc(source.get("response_due_at"), "source.response_due_at")
    if checked > now + timedelta(minutes=5):
        raise PreflightError("source snapshot is from the future")
    if now - checked > MAX_SOURCE_AGE:
        blockers.append("SOURCE_SNAPSHOT_STALE")
    if now >= deadline:
        blockers.append("SOURCES_SOUGHT_DEADLINE_PASSED")


def _owner(owner: dict, blockers: list[str], warnings: list[str]) -> None:
    if owner.get("schema") != OWNER_SCHEMA:
        raise PreflightError("owner schema mismatch")
    org = owner.get("organization")
    fed = owner.get("federal")
    delivery = owner.get("delivery")
    commercial = owner.get("commercial")
    if not all(isinstance(x, dict) for x in (org, fed, delivery, commercial)):
        raise PreflightError("owner sections malformed")
    if org.get("working_name") != "Token Junkie Labs":
        raise PreflightError("working-name drift")
    for key in (
        "legal_name",
        "address",
        "website",
        "point_of_contact",
        "telephone",
        "email",
        "uei",
    ):
        if not _nonempty_text(org.get(key)):
            raise PreflightError(f"organization.{key} missing")
        if PLACEHOLDER_RE.search(org[key]):
            warnings.append(f"OWNER_FACT_UNVERIFIED:{key}")
    if org.get("naics_541512_size") not in {
        "UNKNOWN",
        "SMALL",
        "OTHER_THAN_SMALL",
    }:
        raise PreflightError("invalid NAICS size state")
    if not isinstance(org.get("socioeconomic_status"), list):
        raise PreflightError("socioeconomic status must be list")
    for key in (
        "contract_vehicles",
        "federal_past_performance",
        "clearance_or_security_claims",
        "insurance_or_bonding_claims",
    ):
        if not isinstance(fed.get(key), list):
            raise PreflightError(f"federal.{key} must be list")
    for key in (
        "named_key_personnel",
        "recruiting_retention_evidence",
        "comparable_data_modernization_evidence",
        "databricks_aws_evidence",
        "mainframe_legacy_modernization_evidence",
        "production_support_evidence",
    ):
        if not isinstance(delivery.get(key), list):
            raise PreflightError(f"delivery.{key} must be list")
    if commercial.get("offer_state") != "PROPOSED_NOT_ACCEPTED":
        blockers.append("WORKSHARE_MUST_REMAIN_PROPOSED_NOT_ACCEPTED")
    price = commercial.get("partner_workshare_price_usd")
    if type(price) is not int or price <= 0:
        raise PreflightError("positive integer workshare price required")
    if (
        commercial.get("workshare_name")
        != "Legacy-to-Databricks Pipeline Acceptance & Migration Evidence Desk"
    ):
        raise PreflightError("workshare name drift")
    if not isinstance(owner.get("claims"), list):
        raise PreflightError("claims must be list")
    warnings.append(
        "DIRECT_IRS_RESPONSE_REQUIRES_SEPARATE_VERIFIED_PRIME_AUTHORITY"
    )


def _partners(
    partners: dict, blockers: list[str], warnings: list[str]
) -> None:
    if partners.get("schema") != PARTNER_SCHEMA:
        raise PreflightError("partner schema mismatch")
    if partners.get("opportunity") != "5000233302":
        raise PreflightError("partner opportunity mismatch")
    rows = partners.get("partners")
    if not isinstance(rows, list) or len(rows) < 2:
        raise PreflightError("partner shortlist incomplete")
    ranks = [row.get("rank") for row in rows if isinstance(row, dict)]
    if ranks != list(range(1, len(rows) + 1)):
        raise PreflightError("partner ranks must be contiguous and ordered")
    first = rows[0]
    if first.get("name") != "Maximus Federal Services":
        raise PreflightError("primary target drift")
    if first.get("participation_in_5000233302") != "UNKNOWN":
        blockers.append(
            "PUBLIC_RESEARCH_MUST_NOT_SELF_ASSERT_PARTNER_PARTICIPATION"
        )
    route = first.get("route")
    if (
        not isinstance(route, dict)
        or route.get("type") != "FIRST_PARTY_PARTNERSHIP_OFFICE"
    ):
        raise PreflightError("Maximus route class drift")
    if route.get("state") != "PUBLIC_ROUTE_VERIFIED_NOT_AUTHORIZED":
        blockers.append("PARTNER_ROUTE_MUST_NOT_SELF_AUTHORIZE")
    if (
        not isinstance(route.get("url"), str)
        or not route["url"].startswith("https://maximus.com/")
    ):
        raise PreflightError("Maximus route must stay on first-party origin")
    for row in rows:
        if row.get("participation_in_5000233302") != "UNKNOWN":
            blockers.append(
                f"PARTNER_PARTICIPATION_MUST_BE_UNKNOWN:{row.get('name', '?')}"
            )
        evidence = row.get("evidence")
        if not isinstance(evidence, list) or not evidence:
            raise PreflightError("each partner requires evidence inventory")
    warnings.append(
        "MUSE_AND_FRESH_RELATIONSHIP_CENSUS_REQUIRED_BEFORE_ANY_CONTACT"
    )


def evaluate(
    source: dict, owner: dict, partners: dict, *, now: datetime
) -> dict:
    if (
        not isinstance(now, datetime)
        or now.tzinfo is None
        or now.utcoffset() is None
    ):
        raise PreflightError("now must be timezone-aware")
    now = now.astimezone(timezone.utc).replace(microsecond=0)
    blockers: list[str] = []
    warnings: list[str] = []
    _source(source, now, blockers)
    _owner(owner, blockers, warnings)
    _partners(partners, blockers, warnings)
    state = HOLD if blockers else PARTNER_PACKET_READY
    return {
        "schema": "irs.5000233302.preflight_receipt/v1",
        "state": state,
        "direct_irs_state": DIRECT_IRS_HOLD,
        "blockers": sorted(set(blockers)),
        "warnings": sorted(set(warnings)),
        "authority": {
            "partner_contact_authorized": False,
            "irs_contact_authorized": False,
            "submission_authorized": False,
            "prime_representation_authorized": False,
            "contract_vehicle_representation_authorized": False,
            "award_or_revenue_claim_authorized": False,
        },
    }


def main(argv: list[str]) -> int:
    if len(argv) != 4:
        print(
            "usage: preflight.py SOURCE OWNER PARTNER_SHORTLIST",
            file=sys.stderr,
        )
        return 2
    now = datetime.now(timezone.utc)
    try:
        receipt = evaluate(
            load(Path(argv[1])),
            load(Path(argv[2])),
            load(Path(argv[3])),
            now=now,
        )
    except (OSError, PreflightError) as exc:
        print(
            json.dumps({"state": "ERROR", "error": str(exc)}, sort_keys=True)
        )
        return 2
    print(json.dumps(receipt, sort_keys=True, indent=2))
    return 0 if receipt["state"] == PARTNER_PACKET_READY else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
