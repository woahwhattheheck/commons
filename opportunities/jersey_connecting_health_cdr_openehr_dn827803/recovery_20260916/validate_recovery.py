#!/usr/bin/env python3
"""Fail-closed validator for the 2026-09-16 DN827803 recovery/workshare packet.

The repository packet records evidence only. It cannot authorize portal actions,
buyer contact, tender submission, or partner outbound.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

EXPECTED = {
    "operation_id": "JERSEY-DN827803-TENDER-PACK-RECOVERY-20260916-ZSOL",
    "source_operation_id": "JERSEY-CDR-OPENEHR-DN827803-ZVHJ7P4-20260913",
    "notice_id": "DN827803",
    "buyer": "States of Jersey",
    "programme": "Connecting Health - Clinical Data Repository (CDR) and openEHR",
}
EXPECTED_ADVERT = "https://procontract.due-north.com/Advert?advertId=1a0b26fb-d4a2-f111-813c-005056b64545"
EXPECTED_DEADLINE = "2026-09-29T23:30:00+01:00"
EXPECTED_CONTRACT_START = "2027-01-13"
EXPECTED_CONTRACT_END = "2032-01-12"
EXPECTED_STATE = "HOLD_TENDER_PACK_REQUIRED"
EXPECTED_BOUNDARY = "HOLD_PORTAL_LOGIN_OR_REGISTRATION_REQUIRED"
EXPECTED_BETTER_THREAD = "1a09af22dc174a2c"
EXPECTED_VITA_KEY = "JERSEY-DN827803-VITAGROUP-PAID-WORKSHARE-ZSOL-20260916"
EXPECTED_VITA_ROUTE = "info@vitagroup.ag"


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


def obj(obj_: dict[str, Any], key: str) -> dict[str, Any]:
    return exact(obj_, key, dict)


def arr(obj_: dict[str, Any], key: str) -> list[Any]:
    return exact(obj_, key, list)


def validate_public(packet: dict[str, Any]) -> list[str]:
    if exact(packet, "schema_version", int) != 1:
        raise PacketError("public packet: unsupported schema_version")
    for key, expected in EXPECTED.items():
        if exact(packet, key, str) != expected:
            raise PacketError(f"public packet: identity mismatch for {key}")

    advert = obj(packet, "official_public_advert")
    if exact(advert, "url", str) != EXPECTED_ADVERT:
        raise PacketError("public packet: official advert changed")
    if exact(advert, "expression_end", str) != EXPECTED_DEADLINE:
        raise PacketError("public packet: deadline changed")
    if exact(advert, "contract_start", str) != EXPECTED_CONTRACT_START:
        raise PacketError("public packet: contract start changed")
    if exact(advert, "contract_end", str) != EXPECTED_CONTRACT_END:
        raise PacketError("public packet: contract end changed")
    if exact(advert, "attachments_public_page", str) != "NO_ATTACHMENTS":
        raise PacketError("public packet: unauthenticated attachment state changed")
    if exact(advert, "next_portal_action", str) != "LOGIN_AND_REGISTER_INTEREST":
        raise PacketError("public packet: next portal action changed")
    categories = arr(advert, "categories")
    if len(categories) < 3 or any(type(x) is not str or not x for x in categories):
        raise PacketError("public packet: category evidence incomplete")
    scope = arr(advert, "public_scope")
    if len(scope) < 8 or any(type(x) is not str or not x for x in scope):
        raise PacketError("public packet: public scope evidence incomplete")
    if "joint bids" not in exact(advert, "commercial_structure", str).lower():
        raise PacketError("public packet: partnership structure missing")

    tender = obj(packet, "tender_pack")
    if exact(tender, "acquired", bool) is not False:
        raise PacketError("public packet: cannot claim tender pack acquired")
    if exact(tender, "reviewed", bool) is not False:
        raise PacketError("public packet: cannot claim tender pack reviewed")
    if tender.get("sha256") is not None:
        raise PacketError("public packet: digest forbidden without controlling pack bytes")
    if exact(tender, "public_attachment_link_found", bool) is not False:
        raise PacketError("public packet: cannot invent public attachment link")
    if exact(tender, "state", str) != EXPECTED_STATE:
        raise PacketError("public packet: fail-closed tender state changed")
    if exact(tender, "boundary", str) != EXPECTED_BOUNDARY:
        raise PacketError("public packet: portal boundary changed")

    contact = obj(packet, "buyer_contact_public_notice")
    if exact(contact, "email", str) != "R.Turnbull@gov.je":
        raise PacketError("public packet: buyer contact identity changed")
    if exact(contact, "contact_authority", str) != "INFORMATION_ONLY_NO_CONTACT_AUTHORITY":
        raise PacketError("public packet: buyer contact authority escalated")

    authority = obj(packet, "authority")
    for key in (
        "portal_registration_authorized",
        "portal_login_authorized",
        "register_interest_authorized",
        "buyer_contact_authorized",
        "tender_submission_authorized",
        "supplier_representation_authorized",
        "commercial_readiness",
    ):
        if exact(authority, key, bool) is not False:
            raise PacketError(f"public packet: forbidden authority escalation: {key}")
    if exact(authority, "strongest_state", str) != EXPECTED_STATE:
        raise PacketError("public packet: strongest state changed")

    return [
        "OFFICIAL_PUBLIC_ADVERT_BOUND",
        "PUBLIC_PAGE_NO_ATTACHMENTS_BOUND",
        EXPECTED_BOUNDARY,
        EXPECTED_STATE,
    ]


def validate_partners(packet: dict[str, Any]) -> list[str]:
    if exact(packet, "schema_version", int) != 1:
        raise PacketError("partner ledger: unsupported schema_version")
    if exact(packet, "opportunity", str) != "States of Jersey DN827803":
        raise PacketError("partner ledger: opportunity mismatch")
    if not exact(packet, "single_prime_rule", str):
        raise PacketError("partner ledger: single-prime rule missing")

    routes = arr(packet, "routes")
    by_partner: dict[str, dict[str, Any]] = {}
    for idx, route in enumerate(routes):
        if type(route) is not dict:
            raise PacketError(f"partner ledger: route[{idx}] must be object")
        name = exact(route, "partner", str)
        if name in by_partner:
            raise PacketError(f"partner ledger: duplicate partner: {name}")
        by_partner[name] = route

    better = by_partner.get("Better Ltd")
    if type(better) is not dict:
        raise PacketError("partner ledger: Better prior-send row missing")
    if exact(better, "state", str) != "HARD_DNR_PROVIDER_SENT":
        raise PacketError("partner ledger: Better DNR erased")
    evidence = obj(better, "evidence")
    if exact(evidence, "gmail_message_thread", str) != EXPECTED_BETTER_THREAD:
        raise PacketError("partner ledger: Better provider receipt changed")
    if exact(evidence, "reply_observed_after_send", bool) is not False:
        raise PacketError("partner ledger: unsupported Better reply claim")
    if exact(better, "allowed_next_action", str) != "NONE_ABSENT_GENUINE_REPLY_OR_PROVIDER_EVENT":
        raise PacketError("partner ledger: Better follow-up gate loosened")

    vita = by_partner.get("vitagroup HIP")
    if type(vita) is not dict:
        raise PacketError("partner ledger: vitagroup row missing")
    if exact(vita, "domain", str) != "vitagroup.ag":
        raise PacketError("partner ledger: vitagroup domain mismatch")
    if exact(vita, "route", str) != EXPECTED_VITA_ROUTE:
        raise PacketError("partner ledger: vitagroup route mismatch")
    if exact(vita, "commercial_key", str) != EXPECTED_VITA_KEY:
        raise PacketError("partner ledger: Muse key mismatch")
    if exact(vita, "state", str) not in {
        "MUSE_ARBITRATION_PENDING",
        "MUSE_CLEAR_PROVIDER_SEND_PENDING",
        "HARD_DNR_PROVIDER_SENT",
        "HOLD_COLLISION",
    }:
        raise PacketError("partner ledger: unsupported vitagroup lifecycle state")
    if exact(vita, "send_authorized", bool) is not False:
        raise PacketError("partner ledger: repository packet can never authorize send")

    census = obj(vita, "collision_census")
    for key in (
        "slack_exact_org_domain_before_take",
        "gmail_all_history_exact_org_domain_route_before_take",
    ):
        if exact(census, key, int) != 0:
            raise PacketError(f"partner ledger: original clean census changed: {key}")
    if len(arr(vita, "scope")) < 5:
        raise PacketError("partner ledger: paid workshare scope collapsed")
    if len(arr(vita, "retained_by_prime")) < 7:
        raise PacketError("partner ledger: retained prime authority collapsed")
    sources = arr(vita, "first_party_sources")
    if len(sources) < 4 or any(type(x) is not str or "vitagroup" not in x for x in sources):
        raise PacketError("partner ledger: first-party vitagroup evidence incomplete")
    if len(arr(vita, "fit_facts")) < 4:
        raise PacketError("partner ledger: vitagroup fit evidence collapsed")

    return [
        "BETTER_HARD_DNR_PRESERVED",
        "VITAGROUP_SINGLE_WRITER_PACKET_VALID",
        "REPOSITORY_SEND_AUTHORITY_FALSE",
    ]


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--public", default="public_recovery_20260916.json")
    parser.add_argument("--partners", default="partner_route_ledger_20260916.json")
    args = parser.parse_args(argv)
    try:
        checks = validate_public(load_json(Path(args.public)))
        checks += validate_partners(load_json(Path(args.partners)))
    except PacketError as exc:
        print(json.dumps({"valid": False, "error": str(exc)}, sort_keys=True))
        return 2
    print(json.dumps({
        "valid": True,
        "commercial_readiness": False,
        "buyer_contact_authorized": False,
        "tender_submission_authorized": False,
        "send_authorized": False,
        "checks": checks,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
