#!/usr/bin/env python3
"""Fail-closed verifier for the Okaloosa TDD 77-26 / iVvy workshare packet.

The verifier is intentionally offline. It binds the current public-notice facts,
source authority ceilings, proposed commercial state, workshare boundary,
non-inferences, and all-false external/commercial authority to one reviewed
semantic digest. A hosted notice copy is evidence for notice facts only; it is
not promoted into the controlling RFP/addenda.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parent
DEFAULT_LEDGER = ROOT / "source_ledger.json"
SCHEMA_VERSION = 2
COVERED_FIELDS = (
    "opportunity",
    "commercial_hypothesis",
    "sources",
    "workshare_boundary",
    "non_inferences",
    "authority",
)
EXPECTED_SEMANTIC_DIGEST = "c1ed1857aee0ade48a9d13863632a836ff7d962f74fe6b925bf8ce1bb6d02e3d"
EXPECTED_SOURCE_ROLES = {
    "fl_dms_current_opportunity_index_tdd77_26": "GOVERNMENT_CURRENT_OPPORTUNITY_INDEX",
    "okaloosa_public_notice_copy_tdd77_26": "PUBLIC_NOTICE_COPY_NONCONTROLLING_HOST",
    "buyer_discovery_govly_tdd77_26": "DISCOVERY_NONCONTROLLING",
    "buyer_discovery_bidscope_tdd77_26": "DISCOVERY_NONCONTROLLING",
    "ivvy_public_product": "CANDIDATE_PRIME_PUBLIC_FIRST_PARTY",
    "ivvy_public_integrations": "CANDIDATE_PRIME_PUBLIC_FIRST_PARTY",
    "ivvy_public_api_getting_started": "CANDIDATE_PRIME_PUBLIC_FIRST_PARTY",
    "ivvy_public_financial_integration": "CANDIDATE_PRIME_PUBLIC_FIRST_PARTY",
    "ivvy_public_faq_migration": "CANDIDATE_PRIME_PUBLIC_FIRST_PARTY",
}
EXPECTED_AUTHORITY_KEYS = (
    "muse_selected",
    "external_send_authorized",
    "buyer_contact_authorized",
    "prime_contact_authorized",
    "bid_authorized",
    "portal_submission_authorized",
    "signature_authorized",
    "production_access_authorized",
    "production_mutation_authorized",
    "payment_mutation_authorized",
    "proposal_accepted",
    "contract_exists",
    "work_authorized",
    "invoice_exists",
    "receivable_exists",
    "payment_received",
    "booked_revenue",
    "recognized_revenue",
)


class PacketError(ValueError):
    """The retained packet does not satisfy its reviewed truth contract."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise PacketError(message)


def _no_duplicate_object(pairs: Iterable[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise PacketError(f"duplicate JSON key: {key}")
        out[key] = value
    return out


def load_packet(path: Path = DEFAULT_LEDGER) -> dict[str, Any]:
    try:
        text = path.read_text(encoding="utf-8")
        value = json.loads(text, object_pairs_hook=_no_duplicate_object)
    except PacketError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise PacketError(f"could not load ledger: {exc}") from exc
    _require(isinstance(value, dict), "ledger root must be an object")
    return value


def semantic_payload(packet: dict[str, Any]) -> dict[str, Any]:
    missing = [field for field in COVERED_FIELDS if field not in packet]
    _require(not missing, "semantic fields missing: " + ", ".join(missing))
    return {field: packet[field] for field in COVERED_FIELDS}


def semantic_digest(packet: dict[str, Any]) -> str:
    canonical = json.dumps(
        semantic_payload(packet),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _source_map(packet: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows = packet.get("sources")
    _require(isinstance(rows, list), "sources must be a list")
    out: dict[str, dict[str, Any]] = {}
    for index, row in enumerate(rows):
        _require(isinstance(row, dict), f"sources[{index}] must be an object")
        source_id = row.get("id")
        _require(isinstance(source_id, str) and source_id, f"sources[{index}].id is invalid")
        _require(source_id not in out, f"duplicate source id: {source_id}")
        out[source_id] = row
    return out


def validate_packet(packet: dict[str, Any]) -> dict[str, Any]:
    _require(type(packet.get("schema_version")) is int, "schema_version must be an integer")
    _require(packet["schema_version"] == SCHEMA_VERSION, "unsupported schema_version")

    opportunity = packet.get("opportunity")
    _require(isinstance(opportunity, dict), "opportunity must be an object")
    expected_opportunity = {
        "buyer": "Okaloosa County Board of County Commissioners / Tourism Department",
        "solicitation_id": "TDD 77-26",
        "working_title": "Venue & Event Management Software",
        "literal_response_deadline_from_notice": "September 25, 2026 @ 3:00 PM (CST)",
        "submission_method_from_notice": "OpenGov only",
        "submission_portal_from_notice": "https://procurement.opengov.com/portal/myokaloosa",
        "notice_document_identity": "NOTICE TO RESPONDENTS / RFP TDD 77-26 / VENUE & EVENT MANAGEMENT SOFTWARE",
        "notice_copy_url": "https://bqohpheioaljycjpwbjd.supabase.co/storage/v1/object/public/documents/documents/unique/0b4b2067f4270c13e6311fa1e779aca7ded6d5a0ce3f2717d9fefa5680895781?download=RFP+TDD+77-26.NTR.pdf",
        "notice_copy_retained_in_repository": False,
        "buyer_controlled_full_rfp_and_addenda_retained": False,
        "qualification_state": "CURRENT_NOTICE_FACTS_BOUND_FULL_SCOPE_REQUIRES_CONTROLLING_PACKET",
    }
    _require(opportunity == expected_opportunity, "opportunity / notice binding changed")

    commercial = packet.get("commercial_hypothesis")
    _require(
        commercial
        == {
            "counterparty": "iVvy",
            "currency": "USD",
            "fixed_fee_minor_units": 3500000,
            "delivery_target_business_days": 15,
            "state": "PROPOSED_NOT_ACCEPTED",
        },
        "commercial hypothesis changed",
    )

    sources = _source_map(packet)
    _require(set(sources) == set(EXPECTED_SOURCE_ROLES), "source inventory changed")
    for source_id, expected_role in EXPECTED_SOURCE_ROLES.items():
        _require(
            sources[source_id].get("source_role") == expected_role,
            f"source role changed: {source_id}",
        )

    _require(
        sources["fl_dms_current_opportunity_index_tdd77_26"].get("authority_ceiling")
        == "CURRENT_IDENTITY_AND_TITLE_ONLY",
        "government index authority ceiling changed",
    )
    _require(
        sources["okaloosa_public_notice_copy_tdd77_26"].get("authority_ceiling")
        == "CURRENT_NOTICE_FACTS_ONLY",
        "notice-copy authority ceiling changed",
    )
    _require(
        sources["buyer_discovery_govly_tdd77_26"].get("authority_ceiling")
        == "SCOPE_DISCOVERY_ONLY",
        "Govly authority ceiling changed",
    )
    _require(
        sources["buyer_discovery_bidscope_tdd77_26"].get("authority_ceiling")
        == "INDEX_AND_ROUTE_DISCOVERY_ONLY",
        "Bidscope authority ceiling changed",
    )
    conflict_rows = sources["buyer_discovery_bidscope_tdd77_26"].get("known_conflicts")
    _require(
        conflict_rows
        == [
            "Bidscope UI displays Sep 25, 2026 12:00 PM; do not use that displayed time as the deadline. The notice copy says September 25, 2026 @ 3:00 PM (CST)."
        ],
        "Bidscope deadline conflict guard changed",
    )
    for source_id in (
        "ivvy_public_product",
        "ivvy_public_integrations",
        "ivvy_public_api_getting_started",
        "ivvy_public_financial_integration",
        "ivvy_public_faq_migration",
    ):
        _require(
            sources[source_id].get("authority_ceiling") == "VENDOR_SELF_DESCRIPTION_ONLY",
            f"iVvy source authority ceiling changed: {source_id}",
        )

    authority = packet.get("authority")
    _require(isinstance(authority, dict), "authority must be an object")
    _require(tuple(authority.keys()) == EXPECTED_AUTHORITY_KEYS, "authority key set or order changed")
    for key in EXPECTED_AUTHORITY_KEYS:
        _require(authority[key] is False, f"authority must remain false: {key}")

    receipt = packet.get("semantic_receipt")
    _require(
        receipt
        == {
            "algorithm": "sha256-canonical-json-v1",
            "covers": list(COVERED_FIELDS),
            "digest": EXPECTED_SEMANTIC_DIGEST,
        },
        "semantic receipt changed",
    )
    observed_digest = semantic_digest(packet)
    _require(
        observed_digest == EXPECTED_SEMANTIC_DIGEST,
        "semantic digest mismatch",
    )

    return {
        "status": "OK",
        "schema_version": SCHEMA_VERSION,
        "semantic_digest": observed_digest,
        "source_count": len(sources),
        "authority_false_count": len(EXPECTED_AUTHORITY_KEYS),
        "commercial_state": commercial["state"],
        "notice_deadline": opportunity["literal_response_deadline_from_notice"],
        "full_rfp_retained": opportunity["buyer_controlled_full_rfp_and_addenda_retained"],
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ledger", type=Path, default=DEFAULT_LEDGER)
    parser.add_argument("--verify", action="store_true", help="verify and emit one JSON receipt")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        packet = load_packet(args.ledger)
        result = validate_packet(packet)
    except PacketError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    if args.verify:
        print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    else:
        print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
