#!/usr/bin/env python3
"""Fail-closed validator for the TARC 20262046 public-recovery/workshare packet.

The repository records evidence only. It cannot authorize Bonfire actions,
buyer contact, bid submission, partner outbound, acceptance, award or revenue.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

OP = "TARC-20262046-CHERRYROAD-PAID-WORKSHARE-ZNP-20260917"
SOLICITATION = "20262046"
BUYER = "Transit Authority of River City (TARC)"
TITLE = "Human Capital Management (HCM) System Solutions and Implementation Services"
PORTAL_URL = "https://tarc.bonfirehub.com/opportunities/251030"
PORTAL_ID = "251030"
INTENT_DUE = "2026-10-06T12:00:00-04:00"
PROPOSAL_DUE = "2026-10-15T12:00:00-04:00"
ROUTE = "sales@cherryroad.com"
PARTNER = "CherryRoad Technologies"
STATE = "PUBLIC_METADATA_RECOVERED_PACK_NOT_IN_CUSTODY"

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

def _all_nonempty_strings(items: list[Any], *, minimum: int, label: str) -> None:
    if len(items) < minimum or any(type(x) is not str or not x.strip() for x in items):
        raise PacketError(f"{label}: incomplete")

def validate_public(packet: dict[str, Any]) -> list[str]:
    if exact(packet, "schema_version", int) != 1:
        raise PacketError("public packet: unsupported schema_version")
    expected = {
        "operation_id": OP,
        "solicitation_id": SOLICITATION,
        "buyer": BUYER,
        "title": TITLE,
    }
    for key, wanted in expected.items():
        if exact(packet, key, str) != wanted:
            raise PacketError(f"public packet: identity mismatch for {key}")

    portal = obj(packet, "official_portal")
    if exact(portal, "provider", str) != "Bonfire":
        raise PacketError("public packet: portal provider drift")
    if exact(portal, "opportunity_id", str) != PORTAL_ID:
        raise PacketError("public packet: portal opportunity drift")
    if exact(portal, "url", str) != PORTAL_URL:
        raise PacketError("public packet: portal URL drift")
    if exact(portal, "participation_route", str) != "REGISTER_WITH_OWNER_PORTAL":
        raise PacketError("public packet: participation route drift")
    for key in (
        "portal_registration_performed",
        "intent_to_bid_performed",
        "solicitation_pack_acquired",
        "solicitation_pack_reviewed",
    ):
        if exact(portal, key, bool) is not False:
            raise PacketError(f"public packet: unsupported performed/custody claim: {key}")
    if portal.get("solicitation_pack_sha256") is not None:
        raise PacketError("public packet: solicitation digest forbidden without pack custody")

    gates = obj(packet, "public_time_gates")
    if exact(gates, "intent_to_bid_due", str) != INTENT_DUE:
        raise PacketError("public packet: intent deadline drift")
    if exact(gates, "proposal_due", str) != PROPOSAL_DUE:
        raise PacketError("public packet: proposal deadline drift")
    if exact(gates, "questions_due", str) != "2026-09-15T17:00:00-04:00":
        raise PacketError("public packet: question deadline drift")
    if exact(gates, "preproposal", str) != "2026-09-10T13:00:00-04:00":
        raise PacketError("public packet: preproposal time drift")

    _all_nonempty_strings(arr(packet, "public_scope"), minimum=12, label="public scope")
    sources = arr(packet, "sources")
    if len(sources) < 4:
        raise PacketError("public packet: source hierarchy collapsed")
    tiers = []
    urls = set()
    for i, source in enumerate(sources):
        if type(source) is not dict:
            raise PacketError(f"public packet: source[{i}] must be object")
        tier = exact(source, "tier", str)
        url = exact(source, "url", str)
        claim_scope = exact(source, "claim_scope", str)
        if not claim_scope.strip() or not url.startswith("https://"):
            raise PacketError("public packet: malformed source evidence")
        tiers.append(tier)
        if url in urls:
            raise PacketError("public packet: duplicate source URL")
        urls.add(url)
    if "OWNER_PORTAL_ROUTE" not in tiers or "PUBLIC_BID_MIRROR" not in tiers:
        raise PacketError("public packet: required source tiers missing")
    if PORTAL_URL not in urls:
        raise PacketError("public packet: owner portal source missing")

    authority = obj(packet, "authority")
    for key in (
        "buyer_contact_authorized",
        "portal_registration_authorized",
        "intent_to_bid_authorized",
        "solicitation_pack_custody",
        "prime_status",
        "partnership_exists",
        "bid_submission_authorized",
        "accepted_offer",
        "award",
        "payment",
        "receivable",
        "booked_revenue",
        "recognized_revenue",
    ):
        if exact(authority, key, bool) is not False:
            raise PacketError(f"public packet: forbidden authority escalation: {key}")
    if exact(packet, "strongest_state", str) != STATE:
        raise PacketError("public packet: strongest state drift")

    return [
        "TARC_20262046_IDENTITY_BOUND",
        "BONFIRE_ROUTE_BOUND_WITHOUT_PACK_CUSTODY",
        "OCT06_INTENT_GATE_BOUND",
        "OCT15_PROPOSAL_GATE_BOUND",
        STATE,
    ]

def validate_partner(packet: dict[str, Any]) -> list[str]:
    if exact(packet, "schema_version", int) != 1:
        raise PacketError("partner ledger: unsupported schema_version")
    if exact(packet, "opportunity", str) != "TARC RFP 20262046":
        raise PacketError("partner ledger: opportunity drift")
    if "One prime candidate at a time" not in exact(packet, "single_partner_rule", str):
        raise PacketError("partner ledger: single-partner rule missing")

    routes = arr(packet, "routes")
    if len(routes) != 1:
        raise PacketError("partner ledger: exactly one active candidate is required")
    route = routes[0]
    if type(route) is not dict:
        raise PacketError("partner ledger: route must be object")
    if exact(route, "partner", str) != PARTNER:
        raise PacketError("partner ledger: candidate drift")
    if exact(route, "domain", str) != "cherryroad.com":
        raise PacketError("partner ledger: domain drift")
    if exact(route, "route", str) != ROUTE:
        raise PacketError("partner ledger: contact route drift")
    if "Business Inquiries" not in exact(route, "route_evidence", str):
        raise PacketError("partner ledger: route evidence weakened")
    if exact(route, "commercial_key", str) != OP:
        raise PacketError("partner ledger: commercial/Muse key drift")

    commercial = obj(route, "commercial_hypothesis")
    if exact(commercial, "amount_minor", int) != 3_500_000:
        raise PacketError("partner ledger: amount drift")
    if exact(commercial, "currency", str) != "USD":
        raise PacketError("partner ledger: currency drift")
    if exact(commercial, "display", str) != "$35,000 fixed":
        raise PacketError("partner ledger: display price drift")
    if exact(commercial, "offer_state", str) != "PROPOSED_NOT_ACCEPTED":
        raise PacketError("partner ledger: unsupported acceptance claim")

    _all_nonempty_strings(arr(route, "scope"), minimum=6, label="partner scope")
    _all_nonempty_strings(arr(route, "retained_by_prime"), minimum=10, label="prime-retained authority")
    _all_nonempty_strings(arr(route, "fit_facts"), minimum=4, label="fit facts")
    sources = arr(route, "first_party_sources")
    _all_nonempty_strings(sources, minimum=3, label="first-party sources")
    if any("cherryroad.com" not in x for x in sources):
        raise PacketError("partner ledger: non-CherryRoad source in first-party set")

    census = obj(route, "collision_census")
    for key in (
        "slack_material_prior_contact_before_take",
        "gmail_all_history_material_prior_contact_before_take",
        "owned_github_material_carrier_before_take",
    ):
        if exact(census, key, int) != 0:
            raise PacketError(f"partner ledger: original clean collision census changed: {key}")

    muse = obj(route, "muse_arbitration")
    reqs = arr(muse, "request_ts")
    if not reqs or any(type(x) is not str or not x for x in reqs):
        raise PacketError("partner ledger: Muse request evidence missing")
    cleared = exact(muse, "explicit_clearance_observed", bool)
    clearance_ts = muse.get("clearance_ts")
    if cleared:
        if type(clearance_ts) is not str or not clearance_ts:
            raise PacketError("partner ledger: Muse clearance lacks receipt TS")
    elif clearance_ts is not None:
        raise PacketError("partner ledger: clearance TS without explicit clearance")
    if exact(muse, "terminal_without_clearance", str) != "WAITING_ON_MUSE_NO_SEND":
        raise PacketError("partner ledger: fail-closed Muse terminal drift")

    allowed_states = {
        "MUSE_ARBITRATION_PENDING",
        "MUSE_CLEAR_PROVIDER_SEND_PENDING",
        "HARD_DNR_PROVIDER_SENT",
        "HOLD_COLLISION",
    }
    lifecycle = exact(route, "state", str)
    if lifecycle not in allowed_states:
        raise PacketError("partner ledger: unsupported lifecycle state")
    if lifecycle == "MUSE_CLEAR_PROVIDER_SEND_PENDING" and not cleared:
        raise PacketError("partner ledger: clear state without explicit Muse clearance")
    if lifecycle == "HOLD_COLLISION" and cleared:
        raise PacketError("partner ledger: collision and clearance conflict")

    provider = obj(route, "provider_send")
    performed = exact(provider, "performed", bool)
    if performed:
        if lifecycle != "HARD_DNR_PROVIDER_SENT":
            raise PacketError("partner ledger: provider send must be hard DNR")
        for key in ("message_id", "thread_id", "sent_at"):
            if type(provider.get(key)) is not str or not provider[key]:
                raise PacketError(f"partner ledger: provider send missing {key}")
        if not cleared:
            raise PacketError("partner ledger: provider send without Muse clearance")
    else:
        for key in ("message_id", "thread_id", "sent_at"):
            if provider.get(key) is not None:
                raise PacketError(f"partner ledger: provider receipt without send: {key}")
        if lifecycle == "HARD_DNR_PROVIDER_SENT":
            raise PacketError("partner ledger: hard DNR without provider send")

    if exact(route, "send_authorized", bool) is not False:
        raise PacketError("partner ledger: repository can never authorize send")
    for key in ("accepted_workshare", "award", "payment", "receivable", "revenue"):
        if exact(route, key, bool) is not False:
            raise PacketError(f"partner ledger: unsupported commercial truth escalation: {key}")

    return [
        "CHERRYROAD_SINGLE_PARTNER_BOUND",
        "USD_35000_PROPOSED_NOT_ACCEPTED_BOUND",
        "MUSE_EVIDENCE_FAIL_CLOSED",
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
        "portal_registration_authorized": False,
        "bid_submission_authorized": False,
        "send_authorized": False,
        "accepted_workshare": False,
        "payment": False,
        "revenue": False,
        "checks": checks,
    }, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
