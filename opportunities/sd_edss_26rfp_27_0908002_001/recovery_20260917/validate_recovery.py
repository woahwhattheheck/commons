#!/usr/bin/env python3
"""Fail-closed validator for South Dakota EDSS public-recovery/workshare state."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

OP = "SD-EDSS-26RFP270908002001-INDUCTIVE-PAID-WORKSHARE-ZNP-20260917"
SOLICITATION = "26RFP-27-0908002-001"
DOC_RFP = "27-0908002-001"
BUYER = "State of South Dakota Department of Health / Bureau of Information and Technology"
TITLE = "Electronic Disease Surveillance System (EDSS)"
PARTNER = "InductiveHealth"
ROUTE = "solutions@inductivehealth.com"
STATE = "INVITATION_ONLY_LOI_DEADLINE_PASSED_PARTNER_PATH_ONLY"

class PacketError(ValueError):
    pass

def _no_duplicates(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise PacketError(f"duplicate JSON key: {key}")
        out[key] = value
    return out

def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_no_duplicates)
    except PacketError:
        raise
    except Exception as exc:
        raise PacketError(f"{path.name}: invalid JSON: {exc}") from exc
    if type(value) is not dict:
        raise PacketError(f"{path.name}: top level must be object")
    return value

def exact(obj: dict[str, Any], key: str, typ: type):
    if key not in obj:
        raise PacketError(f"missing key: {key}")
    value = obj[key]
    if type(value) is not typ:
        raise PacketError(f"{key}: expected exact {typ.__name__}")
    return value

def obj(value: dict[str, Any], key: str) -> dict[str, Any]:
    return exact(value, key, dict)

def arr(value: dict[str, Any], key: str) -> list[Any]:
    return exact(value, key, list)

def strings(items: list[Any], *, minimum: int, label: str) -> None:
    if len(items) < minimum or any(type(x) is not str or not x.strip() for x in items):
        raise PacketError(f"{label}: incomplete")

def validate_public(packet: dict[str, Any]) -> list[str]:
    if exact(packet, "schema_version", int) != 1:
        raise PacketError("public: unsupported schema_version")
    expected = {
        "operation_id": OP,
        "solicitation_id": SOLICITATION,
        "document_rfp_id": DOC_RFP,
        "buyer": BUYER,
        "title": TITLE,
        "procurement_mode": "INVITATION_ONLY",
    }
    for key, wanted in expected.items():
        if exact(packet, key, str) != wanted:
            raise PacketError(f"public: identity mismatch for {key}")

    gates = obj(packet, "public_time_gates")
    exact_gates = {
        "letter_of_intent_due": "2026-09-08T23:59:00-05:00",
        "written_questions_due": "2026-09-14T23:59:00-05:00",
        "responses_to_questions_expected": "2026-09-28",
        "sftp_folder_request_due": "2026-10-05",
        "proposal_due": "2026-10-19T23:59:00-05:00",
        "anticipated_award_negotiation": "2026-12-31",
    }
    for key, wanted in exact_gates.items():
        if exact(gates, key, str) != wanted:
            raise PacketError(f"public: deadline drift for {key}")

    strings(arr(packet, "public_scope"), minimum=14, label="public scope")
    sources = arr(packet, "sources")
    if len(sources) < 3:
        raise PacketError("public: source hierarchy collapsed")
    tiers = set()
    urls = set()
    for i, source in enumerate(sources):
        if type(source) is not dict:
            raise PacketError(f"public: source[{i}] must be object")
        tier = exact(source, "tier", str)
        url = exact(source, "url", str)
        claim_scope = exact(source, "claim_scope", str)
        if not claim_scope.strip() or not url.startswith("https://"):
            raise PacketError("public: malformed source")
        if url in urls:
            raise PacketError("public: duplicate source URL")
        tiers.add(tier)
        urls.add(url)
    if "PUBLIC_RFP_COPY" not in tiers or "PUBLIC_OPPORTUNITY_MIRROR" not in tiers:
        raise PacketError("public: required source tiers missing")

    authority = obj(packet, "authority")
    for key in (
        "buyer_contact_authorized", "invited_offeror", "letter_of_intent_submitted",
        "sftp_submission_access", "prime_status", "partnership_exists",
        "bid_submission_authorized", "accepted_offer", "award", "payment",
        "receivable", "booked_revenue", "recognized_revenue",
    ):
        if exact(authority, key, bool) is not False:
            raise PacketError(f"public: forbidden authority escalation: {key}")
    if exact(packet, "strongest_state", str) != STATE:
        raise PacketError("public: strongest-state drift")
    return [
        "SD_EDSS_IDENTITY_BOUND",
        "INVITATION_ONLY_BOUND",
        "LOI_DEADLINE_PASSED_BOUND",
        "OCT19_2359_CT_PROPOSAL_GATE_BOUND",
        STATE,
    ]

def validate_partner(packet: dict[str, Any]) -> list[str]:
    if exact(packet, "schema_version", int) != 1:
        raise PacketError("partner: unsupported schema_version")
    if exact(packet, "opportunity", str) != "South Dakota EDSS RFP 26RFP-27-0908002-001":
        raise PacketError("partner: opportunity drift")
    rule = exact(packet, "single_partner_rule", str)
    if "One prime candidate at a time" not in rule or "already invited" not in rule:
        raise PacketError("partner: qualification rule weakened")

    routes = arr(packet, "routes")
    if len(routes) != 1:
        raise PacketError("partner: exactly one candidate required")
    route = routes[0]
    if type(route) is not dict:
        raise PacketError("partner: route must be object")
    if exact(route, "partner", str) != PARTNER:
        raise PacketError("partner: candidate drift")
    if exact(route, "domain", str) != "inductivehealth.com":
        raise PacketError("partner: domain drift")
    if exact(route, "route", str) != ROUTE:
        raise PacketError("partner: route drift")
    if ROUTE not in exact(route, "route_evidence", str):
        raise PacketError("partner: route evidence weakened")
    if exact(route, "commercial_key", str) != OP:
        raise PacketError("partner: commercial key drift")
    if "already invited" not in exact(route, "qualification_gate", str):
        raise PacketError("partner: invitation qualification gate missing")

    commercial = obj(route, "commercial_hypothesis")
    if exact(commercial, "amount_minor", int) != 4_000_000:
        raise PacketError("partner: amount drift")
    if exact(commercial, "currency", str) != "USD":
        raise PacketError("partner: currency drift")
    if exact(commercial, "display", str) != "$40,000 fixed":
        raise PacketError("partner: display price drift")
    if exact(commercial, "offer_state", str) != "PROPOSED_NOT_ACCEPTED":
        raise PacketError("partner: false acceptance")

    strings(arr(route, "scope"), minimum=6, label="partner scope")
    strings(arr(route, "retained_by_prime"), minimum=12, label="prime retained authority")
    strings(arr(route, "fit_facts"), minimum=5, label="fit facts")
    sources = arr(route, "first_party_sources")
    strings(sources, minimum=5, label="first-party sources")
    if any("inductivehealth.com" not in x for x in sources):
        raise PacketError("partner: non-InductiveHealth URL in first-party set")

    census = obj(route, "collision_census")
    for key in ("slack_material_prior_contact_before_take", "gmail_all_history_material_prior_contact_before_take"):
        if exact(census, key, int) != 0:
            raise PacketError(f"partner: original collision census changed: {key}")

    muse = obj(route, "muse_arbitration")
    reqs = arr(muse, "request_ts")
    if any(type(x) is not str or not x for x in reqs):
        raise PacketError("partner: malformed Muse request evidence")
    cleared = exact(muse, "explicit_clearance_observed", bool)
    clearance_ts = muse.get("clearance_ts")
    if cleared:
        if not reqs or type(clearance_ts) is not str or not clearance_ts:
            raise PacketError("partner: clearance missing request/receipt evidence")
    elif clearance_ts is not None:
        raise PacketError("partner: clearance TS without explicit clearance")
    if exact(muse, "terminal_without_clearance", str) != "WAITING_ON_MUSE_NO_SEND":
        raise PacketError("partner: fail-closed terminal drift")

    allowed = {
        "MUSE_ARBITRATION_NOT_REQUESTED",
        "MUSE_ARBITRATION_PENDING",
        "MUSE_CLEAR_PROVIDER_SEND_PENDING",
        "HARD_DNR_PROVIDER_SENT",
        "HOLD_COLLISION",
    }
    lifecycle = exact(route, "state", str)
    if lifecycle not in allowed:
        raise PacketError("partner: unsupported lifecycle")
    if lifecycle == "MUSE_ARBITRATION_NOT_REQUESTED" and reqs:
        raise PacketError("partner: request exists but lifecycle says not requested")
    if lifecycle == "MUSE_ARBITRATION_PENDING" and not reqs:
        raise PacketError("partner: pending without request")
    if lifecycle == "MUSE_CLEAR_PROVIDER_SEND_PENDING" and not cleared:
        raise PacketError("partner: clear state without explicit clearance")
    if lifecycle == "HOLD_COLLISION" and cleared:
        raise PacketError("partner: collision and clearance conflict")

    provider = obj(route, "provider_send")
    performed = exact(provider, "performed", bool)
    if performed:
        if lifecycle != "HARD_DNR_PROVIDER_SENT" or not cleared:
            raise PacketError("partner: send requires clear + hard DNR")
        for key in ("message_id", "thread_id", "sent_at"):
            if type(provider.get(key)) is not str or not provider[key]:
                raise PacketError(f"partner: provider send missing {key}")
    else:
        for key in ("message_id", "thread_id", "sent_at"):
            if provider.get(key) is not None:
                raise PacketError(f"partner: provider receipt without send: {key}")
        if lifecycle == "HARD_DNR_PROVIDER_SENT":
            raise PacketError("partner: hard DNR without provider send")

    if exact(route, "candidate_confirmed_invited_participating", bool) is not False:
        raise PacketError("partner: unsupported invitation/participation claim")
    if exact(route, "send_authorized", bool) is not False:
        raise PacketError("partner: repository cannot authorize send")
    for key in ("accepted_workshare", "award", "payment", "receivable", "revenue"):
        if exact(route, key, bool) is not False:
            raise PacketError(f"partner: unsupported commercial escalation: {key}")

    return [
        "INDUCTIVE_SINGLE_PARTNER_BOUND",
        "INVITATION_QUALIFICATION_FIRST_BOUND",
        "USD_40000_PROPOSED_NOT_ACCEPTED_BOUND",
        "REPOSITORY_SEND_AUTHORITY_FALSE",
        lifecycle,
    ]

def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--public", default="public_opportunity_20260917.json")
    parser.add_argument("--partners", default="partner_route_ledger_20260917.json")
    args = parser.parse_args(argv)
    try:
        checks = validate_public(load_json(Path(args.public)))
        checks += validate_partner(load_json(Path(args.partners)))
    except PacketError as exc:
        print(json.dumps({"valid": False, "error": str(exc)}, sort_keys=True))
        return 2
    print(json.dumps({
        "valid": True,
        "buyer_contact_authorized": False,
        "invited_offeror": False,
        "letter_of_intent_submitted": False,
        "bid_submission_authorized": False,
        "candidate_confirmed_invited_participating": False,
        "send_authorized": False,
        "accepted_workshare": False,
        "payment": False,
        "revenue": False,
        "checks": checks,
    }, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
