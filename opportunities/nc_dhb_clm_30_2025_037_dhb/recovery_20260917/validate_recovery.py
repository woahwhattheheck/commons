#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

OP = "NC-DHB-CLM-30-2025-037-DHB-MITRATECH-PAID-WORKSHARE-ZNP-20260917"
SOLICITATION = "30-2025-037-DHB"
BUYER = "North Carolina Department of Health and Human Services, Division of Health Benefits"
TITLE = "Contract Lifecycle Management System"
PORTAL = "https://evp.nc.gov/solicitations/details/?id=5d9802e7-e99b-f111-8077-001dd80bcb64"
PROPOSAL_DUE = "2026-10-23T14:00:00-04:00"
PARTNER = "Mitratech"
ROUTE = "info@mitratech.com"
STATE = "OPEN_PUBLIC_RFP_PARTNER_PATH_RESEARCHED"

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
    expected = {"operation_id": OP, "solicitation_id": SOLICITATION, "buyer": BUYER, "title": TITLE}
    for key, wanted in expected.items():
        if exact(packet, key, str) != wanted:
            raise PacketError(f"public: identity mismatch for {key}")

    portal = obj(packet, "owner_portal")
    if exact(portal, "provider", str) != "North Carolina eVP":
        raise PacketError("public: owner portal provider drift")
    if exact(portal, "url", str) != PORTAL:
        raise PacketError("public: owner portal URL drift")
    if exact(portal, "status", str) != "OPEN":
        raise PacketError("public: open-status drift")
    for key in ("vendor_registration_performed", "proposal_submission_performed"):
        if exact(portal, key, bool) is not False:
            raise PacketError(f"public: unsupported performed action: {key}")

    gates = obj(packet, "public_time_gates")
    expected_gates = {"posted":"2026-08-19","preproposal":"2026-08-24","written_questions_due":"2026-08-31","proposal_due":PROPOSAL_DUE}
    for key, wanted in expected_gates.items():
        if exact(gates, key, str) != wanted:
            raise PacketError(f"public: time-gate drift: {key}")

    scale = obj(packet, "public_scale")
    if exact(scale, "active_medicaid_contracts_min", int) != 250:
        raise PacketError("public: contract-scale drift")
    if exact(scale, "authorized_users_approx", int) != 410:
        raise PacketError("public: user-scale drift")

    strings(arr(packet, "public_scope"), minimum=15, label="public scope")
    sources = arr(packet, "sources")
    if len(sources) < 2:
        raise PacketError("public: source hierarchy collapsed")
    tiers=set(); urls=set()
    for i, source in enumerate(sources):
        if type(source) is not dict:
            raise PacketError(f"public: source[{i}] must be object")
        tier=exact(source,"tier",str); url=exact(source,"url",str); scope=exact(source,"claim_scope",str)
        if not url.startswith("https://") or not scope.strip():
            raise PacketError("public: malformed source evidence")
        if url in urls:
            raise PacketError("public: duplicate source URL")
        tiers.add(tier); urls.add(url)
    if "BUYER_OWNER_PORTAL" not in tiers or "PUBLIC_RFP_COPY" not in tiers or PORTAL not in urls:
        raise PacketError("public: required source tiers missing")
    caution=exact(packet,"source_caution",str)
    if "addenda control" not in caution or "excluded" not in caution:
        raise PacketError("public: source caution weakened")

    authority=obj(packet,"authority")
    for key in ("buyer_contact_authorized","vendor_registration_authorized","prime_status","partnership_exists","proposal_submission_authorized","award","payment","receivable","booked_revenue","recognized_revenue"):
        if exact(authority,key,bool) is not False:
            raise PacketError(f"public: forbidden authority escalation: {key}")
    if exact(packet,"strongest_state",str)!=STATE:
        raise PacketError("public: strongest state drift")
    return ["NC_DHB_CLM_IDENTITY_BOUND","OWNER_EVP_ROUTE_BOUND","OCT23_1400_ET_BOUND",STATE]

def validate_partner(packet: dict[str, Any]) -> list[str]:
    if exact(packet,"schema_version",int)!=1:
        raise PacketError("partner: unsupported schema_version")
    if exact(packet,"opportunity",str)!="NC DHHS DHB RFP 30-2025-037-DHB":
        raise PacketError("partner: opportunity drift")
    if "One prime candidate at a time" not in exact(packet,"single_partner_rule",str):
        raise PacketError("partner: single-partner rule missing")
    routes=arr(packet,"routes")
    if len(routes)!=1:
        raise PacketError("partner: exactly one candidate required")
    route=routes[0]
    if type(route) is not dict:
        raise PacketError("partner: route must be object")
    if exact(route,"partner",str)!=PARTNER or exact(route,"domain",str)!="mitratech.com":
        raise PacketError("partner: candidate/domain drift")
    if exact(route,"route",str)!=ROUTE:
        raise PacketError("partner: contact route drift")
    if ROUTE not in exact(route,"route_evidence",str):
        raise PacketError("partner: route evidence weakened")
    if exact(route,"commercial_key",str)!=OP:
        raise PacketError("partner: commercial key drift")
    if SOLICITATION not in exact(route,"qualification_gate",str) or "No participation" not in route["qualification_gate"]:
        raise PacketError("partner: qualification gate weakened")

    commercial=obj(route,"commercial_hypothesis")
    if exact(commercial,"amount_minor",int)!=4_500_000:
        raise PacketError("partner: amount drift")
    if exact(commercial,"currency",str)!="USD" or exact(commercial,"display",str)!="$45,000 fixed":
        raise PacketError("partner: currency/display drift")
    if exact(commercial,"offer_state",str)!="PROPOSED_NOT_ACCEPTED":
        raise PacketError("partner: false acceptance")

    strings(arr(route,"scope"),minimum=6,label="partner scope")
    strings(arr(route,"retained_by_prime"),minimum=12,label="retained authority")
    strings(arr(route,"fit_facts"),minimum=4,label="fit facts")
    sources=arr(route,"first_party_sources"); strings(sources,minimum=3,label="first-party sources")
    if any("mitratech.com" not in x for x in sources):
        raise PacketError("partner: non-Mitratech first-party URL")

    census=obj(route,"collision_census")
    for key in ("slack_material_prior_contact_before_take","gmail_all_history_material_prior_contact_before_take"):
        if exact(census,key,int)!=0:
            raise PacketError(f"partner: original clean census changed: {key}")
    if "Agiloft" not in exact(census,"rejected_candidate_due_prior_contact",str):
        raise PacketError("partner: rejected-candidate collision evidence missing")

    muse=obj(route,"muse_arbitration"); reqs=arr(muse,"request_ts")
    if any(type(x) is not str or not x for x in reqs):
        raise PacketError("partner: malformed Muse request evidence")
    cleared=exact(muse,"explicit_clearance_observed",bool); clearance_ts=muse.get("clearance_ts")
    if cleared:
        if not reqs or type(clearance_ts) is not str or not clearance_ts:
            raise PacketError("partner: clearance lacks request/receipt evidence")
    elif clearance_ts is not None:
        raise PacketError("partner: clearance timestamp without clearance")
    if exact(muse,"terminal_without_clearance",str)!="WAITING_ON_MUSE_NO_SEND":
        raise PacketError("partner: fail-closed Muse terminal drift")

    allowed={"MUSE_ARBITRATION_NOT_REQUESTED","MUSE_ARBITRATION_PENDING","MUSE_CLEAR_PROVIDER_SEND_PENDING","HARD_DNR_PROVIDER_SENT","HOLD_COLLISION"}
    lifecycle=exact(route,"state",str)
    if lifecycle not in allowed:
        raise PacketError("partner: unsupported lifecycle")
    if lifecycle=="MUSE_ARBITRATION_NOT_REQUESTED" and reqs:
        raise PacketError("partner: request exists but lifecycle says not requested")
    if lifecycle=="MUSE_ARBITRATION_PENDING" and not reqs:
        raise PacketError("partner: pending without request")
    if lifecycle=="MUSE_CLEAR_PROVIDER_SEND_PENDING" and not cleared:
        raise PacketError("partner: clear state without clearance")
    if lifecycle=="HOLD_COLLISION" and cleared:
        raise PacketError("partner: collision and clearance conflict")

    provider=obj(route,"provider_send"); performed=exact(provider,"performed",bool)
    if performed:
        if lifecycle!="HARD_DNR_PROVIDER_SENT" or not cleared:
            raise PacketError("partner: provider send requires clearance + hard DNR")
        for key in ("message_id","thread_id","sent_at"):
            if type(provider.get(key)) is not str or not provider[key]:
                raise PacketError(f"partner: provider send missing {key}")
    else:
        for key in ("message_id","thread_id","sent_at"):
            if provider.get(key) is not None:
                raise PacketError(f"partner: provider receipt without send: {key}")
        if lifecycle=="HARD_DNR_PROVIDER_SENT":
            raise PacketError("partner: hard DNR without provider send")

    if exact(route,"candidate_confirmed_evaluating",bool) is not False:
        raise PacketError("partner: unsupported participation claim")
    if exact(route,"send_authorized",bool) is not False:
        raise PacketError("partner: repository cannot authorize send")
    for key in ("accepted_workshare","award","payment","receivable","revenue"):
        if exact(route,key,bool) is not False:
            raise PacketError(f"partner: unsupported commercial escalation: {key}")
    return ["MITRATECH_SINGLE_PARTNER_BOUND","USD_45000_PROPOSED_NOT_ACCEPTED_BOUND","REPOSITORY_SEND_AUTHORITY_FALSE",lifecycle]

def main(argv=None) -> int:
    parser=argparse.ArgumentParser(); parser.add_argument("--public",default="public_opportunity_20260917.json"); parser.add_argument("--partners",default="partner_route_ledger_20260917.json"); args=parser.parse_args(argv)
    try: checks=validate_public(load_json(Path(args.public)))+validate_partner(load_json(Path(args.partners)))
    except PacketError as exc: print(json.dumps({"valid":False,"error":str(exc)},sort_keys=True)); return 2
    print(json.dumps({"valid":True,"buyer_contact_authorized":False,"vendor_registration_authorized":False,"proposal_submission_authorized":False,"candidate_confirmed_evaluating":False,"send_authorized":False,"accepted_workshare":False,"payment":False,"revenue":False,"checks":checks},sort_keys=True)); return 0

if __name__=="__main__": raise SystemExit(main())
