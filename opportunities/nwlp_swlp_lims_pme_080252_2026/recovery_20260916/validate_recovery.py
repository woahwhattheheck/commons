#!/usr/bin/env python3
"""Fail-closed validator for the 2026-09-16 C467704 public-recovery/partner packet.

This validator does not authorize portal access, buyer contact, or outbound mail.
It protects the evidence packet from being rewritten into a false READY/SEND state.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

EXPECTED = {
    "operation_id": "NWLP-SWLP-C467704-CONTROLLING-PACK-RECOVERY-20260916",
    "source_operation_id": "NWLP-SWLP-LIMS-PME-080252-ZVHJ7P4-20260913",
    "notice_id": "080252-2026",
    "ocid": "ocds-h6vhtk-06ea51",
    "atamis_contract_reference": "C467704",
    "buyer": "Imperial College Healthcare NHS Trust",
}
EXPECTED_DEADLINE = "2026-10-01T12:00:00+01:00"
EXPECTED_RECOVERY_STATE = "HOLD_PORTAL_ATTACHMENT_AUTH_REQUIRED"
EXPECTED_MUSE_KEY = "NWLP-SWLP-CIRDAN-PAID-WORKSHARE-ZSOL-20260916"
EXPECTED_CIRDAN_ROUTE = "info@cirdan.com"
EXPECTED_CLINISYS_THREAD = "1a09af0c5f357d15"


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


def require_exact_type(obj: dict[str, Any], key: str, typ: type):
    if key not in obj:
        raise PacketError(f"missing key: {key}")
    if type(obj[key]) is not typ:
        raise PacketError(f"{key}: expected exact {typ.__name__}")
    return obj[key]


def require_dict(obj: dict[str, Any], key: str) -> dict[str, Any]:
    return require_exact_type(obj, key, dict)


def require_list(obj: dict[str, Any], key: str) -> list[Any]:
    return require_exact_type(obj, key, list)


def validate_public(packet: dict[str, Any]) -> list[str]:
    if require_exact_type(packet, "schema_version", int) != 1:
        raise PacketError("public recovery: unsupported schema_version")
    for key, expected in EXPECTED.items():
        if require_exact_type(packet, key, str) != expected:
            raise PacketError(f"public recovery: identity mismatch for {key}")

    deadline = require_dict(packet, "response_deadline_authority")
    if require_exact_type(deadline, "deadline", str) != EXPECTED_DEADLINE:
        raise PacketError("public recovery: controlling deadline changed")
    if not require_exact_type(deadline, "controlling_public_text", str):
        raise PacketError("public recovery: deadline authority text empty")
    if not require_exact_type(deadline, "conflict_note", str):
        raise PacketError("public recovery: deadline conflict note empty")

    recovery = require_dict(packet, "public_recovery")
    if require_exact_type(recovery, "opportunity_metadata_publicly_readable", bool) is not True:
        raise PacketError("public recovery: public opportunity readback lost")
    if require_exact_type(recovery, "questionnaire_referenced_as_attached", bool) is not True:
        raise PacketError("public recovery: buyer attachment instruction lost")
    retrieved = require_exact_type(recovery, "questionnaire_bytes_publicly_retrieved", bool)
    public_link = require_exact_type(recovery, "public_attachment_link_found", bool)
    auth_required = require_exact_type(
        recovery, "authenticated_supplier_portal_or_owner_access_required_for_next_recovery_step", bool
    )
    sha = recovery.get("questionnaire_sha256")
    state = require_exact_type(recovery, "state", str)

    if retrieved is not False or public_link is not False:
        raise PacketError("public recovery: current packet must not claim public questionnaire recovery")
    if sha is not None:
        raise PacketError("public recovery: questionnaire digest forbidden without bytes")
    if auth_required is not True:
        raise PacketError("public recovery: owner portal boundary erased")
    if state != EXPECTED_RECOVERY_STATE:
        raise PacketError("public recovery: fail-closed state changed")

    sources = require_list(packet, "sources")
    if len(sources) < 3:
        raise PacketError("public recovery: expected independent public source set")
    kinds = set()
    for idx, item in enumerate(sources):
        if type(item) is not dict:
            raise PacketError(f"public recovery: source[{idx}] must be object")
        kind = require_exact_type(item, "kind", str)
        url = require_exact_type(item, "url", str)
        qbytes = require_exact_type(item, "questionnaire_bytes", str)
        if not url.startswith("https://"):
            raise PacketError(f"public recovery: source[{idx}] must be https")
        if qbytes not in {"NOT_EXPOSED_IN_PUBLIC_PAGE", "NOT_PRESENT"}:
            raise PacketError(f"public recovery: source[{idx}] invents questionnaire bytes")
        kinds.add(kind)
    if "buyer_portal_public_metadata" not in kinds:
        raise PacketError("public recovery: buyer portal evidence missing")

    contact = require_dict(packet, "buyer_contact_public_notice")
    if require_exact_type(contact, "contact_authority", str) != "INFORMATION_ONLY_NO_CONTACT_AUTHORITY":
        raise PacketError("public recovery: contact authority escalated")
    if require_exact_type(contact, "email", str) != "nigel.weatherhead1@nhs.net":
        raise PacketError("public recovery: public contact identity changed")

    authority = require_dict(packet, "authority")
    forbidden_true = (
        "atamis_registration_authorized",
        "atamis_login_authorized",
        "buyer_contact_authorized",
        "questionnaire_submission_authorized",
        "supplier_representation_authorized",
        "commercial_readiness",
    )
    for key in forbidden_true:
        if require_exact_type(authority, key, bool) is not False:
            raise PacketError(f"public recovery: forbidden authority escalation: {key}")
    if require_exact_type(authority, "strongest_state", str) != EXPECTED_RECOVERY_STATE:
        raise PacketError("public recovery: strongest state changed")

    return [
        "PUBLIC_METADATA_CURRENT",
        "QUESTIONNAIRE_BYTES_NOT_PUBLICLY_RECOVERED",
        EXPECTED_RECOVERY_STATE,
    ]


def validate_partner(packet: dict[str, Any]) -> list[str]:
    if require_exact_type(packet, "schema_version", int) != 1:
        raise PacketError("partner ledger: unsupported schema_version")
    if require_exact_type(packet, "opportunity", str) != "NWLP/SWLP LIMS C467704":
        raise PacketError("partner ledger: opportunity mismatch")
    if not require_exact_type(packet, "single_prime_outbound_rule", str):
        raise PacketError("partner ledger: single-prime rule missing")

    routes = require_list(packet, "routes")
    by_partner = {}
    for idx, route in enumerate(routes):
        if type(route) is not dict:
            raise PacketError(f"partner ledger: route[{idx}] must be object")
        partner = require_exact_type(route, "partner", str)
        if partner in by_partner:
            raise PacketError(f"partner ledger: duplicate partner: {partner}")
        by_partner[partner] = route

    clinisys = by_partner.get("Clinisys UK")
    if type(clinisys) is not dict:
        raise PacketError("partner ledger: Clinisys prior-send row missing")
    if require_exact_type(clinisys, "state", str) != "HARD_DNR_PROVIDER_SENT":
        raise PacketError("partner ledger: Clinisys DNR erased")
    evidence = require_dict(clinisys, "evidence")
    if require_exact_type(evidence, "gmail_message_thread", str) != EXPECTED_CLINISYS_THREAD:
        raise PacketError("partner ledger: Clinisys provider receipt changed")
    if require_exact_type(clinisys, "allowed_next_action", str) != "NONE_ABSENT_GENUINE_REPLY_OR_PROVIDER_EVENT":
        raise PacketError("partner ledger: Clinisys follow-up gate loosened")

    cirdan = by_partner.get("Cirdan")
    if type(cirdan) is not dict:
        raise PacketError("partner ledger: Cirdan row missing")
    if require_exact_type(cirdan, "route", str) != EXPECTED_CIRDAN_ROUTE:
        raise PacketError("partner ledger: Cirdan route mismatch")
    if require_exact_type(cirdan, "commercial_key", str) != EXPECTED_MUSE_KEY:
        raise PacketError("partner ledger: Muse key mismatch")
    if require_exact_type(cirdan, "state", str) not in {
        "MUSE_ARBITRATION_PENDING",
        "MUSE_CLEAR_PROVIDER_SEND_PENDING",
        "HARD_DNR_PROVIDER_SENT",
        "HOLD_COLLISION",
    }:
        raise PacketError("partner ledger: unsupported Cirdan lifecycle state")
    if require_exact_type(cirdan, "send_authorized", bool) is not False:
        raise PacketError("partner ledger: repository packet can never authorize send")

    census = require_dict(cirdan, "collision_census")
    for key in (
        "slack_exact_org_domain_route_before_take",
        "gmail_all_history_exact_org_domain_route_before_take",
    ):
        value = require_exact_type(census, key, int)
        if value != 0:
            raise PacketError(f"partner ledger: original collision-clean fact changed: {key}")

    if len(require_list(cirdan, "scope")) < 4:
        raise PacketError("partner ledger: paid workshare scope collapsed")
    if len(require_list(cirdan, "retained_by_prime")) < 5:
        raise PacketError("partner ledger: prime authority exclusions collapsed")
    sources = require_list(cirdan, "first_party_sources")
    if len(sources) < 3 or any(type(x) is not str or not x.startswith("https://cirdan.com/") for x in sources):
        raise PacketError("partner ledger: first-party Cirdan evidence incomplete")

    return [
        "CLINISYS_HARD_DNR_PRESERVED",
        "CIRDAN_SINGLE_WRITER_PACKET_VALID",
        "REPOSITORY_SEND_AUTHORITY_FALSE",
    ]


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--public", default="public_recovery_20260916.json", help="public recovery packet")
    parser.add_argument("--partners", default="partner_route_ledger_20260916.json", help="partner route ledger")
    args = parser.parse_args(argv)
    try:
        public = load_json(Path(args.public))
        partners = load_json(Path(args.partners))
        checks = validate_public(public) + validate_partner(partners)
    except PacketError as exc:
        print(json.dumps({"valid": False, "error": str(exc)}, sort_keys=True))
        return 2
    print(json.dumps({
        "valid": True,
        "commercial_readiness": False,
        "buyer_contact_authorized": False,
        "send_authorized": False,
        "checks": checks,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
