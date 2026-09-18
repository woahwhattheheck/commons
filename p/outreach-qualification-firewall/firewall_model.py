from __future__ import annotations

import re
from typing import Any

from firewall_codec import (
    SCHEMA, TOP_KEYS, SOURCE_KEYS, QUAL_KEYS, ECON_KEYS, CONTACT_KEYS, IDENTITY_KEYS, LEASE_KEYS,
    MAX_LIST_ROWS, MAX_MINOR_UNITS, MAX_QUANTITY, MAX_RUNWAY_SECONDS, MAX_LEASE_SECONDS,
    MAX_IDENTITY_VALIDITY_SECONDS, MAX_RELATIONSHIP_VALIDITY_SECONDS,
    QUAL_DISPOSITIONS, SUBMISSION_ROUTE_TYPES, REGISTRATION_STATES, COMPENSATION_BASES,
    RELATIONSHIP_STATES, LEASE_STATUSES, FirewallError, canonical_json, sha256_hex,
    _exact_keys, _token, _digest, _exact_int, _exact_bool, _utc, _canonical_https, _canonical_route,
)
from context_authority import verify_context_authority
from writer_authority import verify_writer_lease_authority


def _validate_source(source: Any) -> dict[str, Any]:
    row = _exact_keys(source, SOURCE_KEYS, "source_packet")
    row["opportunity_id"] = _token(row["opportunity_id"], "opportunity_id")
    row["source_uri"] = _canonical_https(row["source_uri"], "source_uri")
    row["source_generation"] = _token(row["source_generation"], "source_generation")
    observed = _utc(row["observed_at"], "observed_at")
    deadline = _utc(row["deadline_at"], "deadline_at")
    if observed > deadline:
        raise FirewallError("source observation is after deadline")
    row["min_runway_seconds"] = _exact_int(row["min_runway_seconds"], "min_runway_seconds", 0, MAX_RUNWAY_SECONDS)
    route_type = row["submission_route_type"]
    if route_type not in SUBMISSION_ROUTE_TYPES:
        raise FirewallError("unsupported submission_route_type")
    row["submission_route"] = _canonical_route(route_type, row["submission_route"], "submission_route")
    required = _exact_bool(row["registration_required"], "registration_required")
    if row["registration_state"] not in REGISTRATION_STATES:
        raise FirewallError("unsupported registration_state")
    if not required and row["registration_state"] != "NOT_REQUIRED":
        raise FirewallError("registration_state must be NOT_REQUIRED when registration is not required")
    if required and row["registration_state"] == "NOT_REQUIRED":
        raise FirewallError("registration required but state says NOT_REQUIRED")
    return row


def _validate_qualifications(value: Any) -> list[dict[str, Any]]:
    if type(value) is not list or not value or len(value) > MAX_LIST_ROWS:
        raise FirewallError("qualifications must be a nonempty bounded list")
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw in value:
        row = _exact_keys(raw, QUAL_KEYS, "qualification")
        row["gate_id"] = _token(row["gate_id"], "gate_id")
        if row["gate_id"] in seen:
            raise FirewallError("duplicate qualification gate_id")
        seen.add(row["gate_id"])
        if row["disposition"] not in QUAL_DISPOSITIONS:
            raise FirewallError("unsupported qualification disposition")
        row["required_for_outreach"] = _exact_bool(row["required_for_outreach"], "required_for_outreach")
        row["evidence_ref"] = _token(row["evidence_ref"], "evidence_ref")
        row["evidence_sha256"] = _digest(row["evidence_sha256"], "evidence_sha256")
        out.append(row)
    return sorted(out, key=lambda r: r["gate_id"])


def _validate_economics(value: Any) -> dict[str, Any]:
    row = _exact_keys(value, ECON_KEYS, "economics")
    row["workshare_ref"] = _token(row["workshare_ref"], "workshare_ref")
    if type(row["currency"]) is not str or not re.fullmatch(r"[A-Z]{3}", row["currency"]):
        raise FirewallError("currency must be three uppercase ASCII letters")
    row["amount_minor"] = _exact_int(row["amount_minor"], "amount_minor", 1, MAX_MINOR_UNITS)
    if row["compensation_basis"] not in COMPENSATION_BASES:
        raise FirewallError("unsupported compensation_basis")
    row["quantity_max"] = _exact_int(row["quantity_max"], "quantity_max", 1, MAX_QUANTITY)
    row["scope_ref"] = _token(row["scope_ref"], "scope_ref")
    return row


def _validate_contact(value: Any) -> dict[str, Any]:
    row = _exact_keys(value, CONTACT_KEYS, "contact")
    for field in (
        "org_ref", "contact_ref", "relationship_evidence_ref", "relationship_generation", "purpose_ref"
    ):
        row[field] = _token(row[field], field)
    if row["route_type"] not in {"EMAIL", "FORM"}:
        raise FirewallError("unsupported outreach route_type")
    row["route"] = _canonical_route("EMAIL" if row["route_type"] == "EMAIL" else "FORM", row["route"], "contact.route")
    if row["relationship_state"] not in RELATIONSHIP_STATES:
        raise FirewallError("unsupported relationship_state")
    row["relationship_evidence_sha256"] = _digest(row["relationship_evidence_sha256"], "relationship_evidence_sha256")
    row["relationship_head_sha256"] = _digest(row["relationship_head_sha256"], "relationship_head_sha256")
    row["relationship_authority_tag_hex"] = _digest(row["relationship_authority_tag_hex"], "relationship_authority_tag_hex")
    observed = _utc(row["relationship_observed_at"], "relationship_observed_at")
    valid_until = _utc(row["relationship_valid_until"], "relationship_valid_until")
    if valid_until <= observed:
        raise FirewallError("relationship validity must end after observation")
    if (valid_until - observed).total_seconds() > MAX_RELATIONSHIP_VALIDITY_SECONDS:
        raise FirewallError("relationship snapshot validity exceeds bounded ceiling")
    return row


def _validate_identity_binding(
    value: Any,
    *,
    source: dict[str, Any],
    source_digest: str,
    contact: dict[str, Any],
    _verify=verify_context_authority,
) -> dict[str, Any]:
    row = _exact_keys(value, IDENTITY_KEYS, "identity_binding")
    for field in ("binding_id", "opportunity_id", "org_ref", "purpose_ref", "canonical_org_id", "canonical_purpose_id"):
        row[field] = _token(row[field], field)
    row["source_packet_sha256"] = _digest(row["source_packet_sha256"], "identity source_packet_sha256")
    row["auth_tag_hex"] = _digest(row["auth_tag_hex"], "identity auth_tag_hex")
    observed = _utc(row["observed_at"], "identity observed_at")
    valid_until = _utc(row["valid_until"], "identity valid_until")
    if valid_until <= observed:
        raise FirewallError("identity validity must end after observation")
    if (valid_until - observed).total_seconds() > MAX_IDENTITY_VALIDITY_SECONDS:
        raise FirewallError("identity binding validity exceeds bounded ceiling")
    if row["source_packet_sha256"] != source_digest or row["opportunity_id"] != source["opportunity_id"]:
        raise FirewallError("identity binding source/opportunity mismatch")
    if row["org_ref"] != contact["org_ref"] or row["purpose_ref"] != contact["purpose_ref"]:
        raise FirewallError("identity binding aliases do not match contact")
    unsigned = {k: v for k, v in row.items() if k != "auth_tag_hex"}
    row["authority_authenticated"] = _verify("IDENTITY", unsigned, row["auth_tag_hex"])
    return row


def _relationship_authority_payload(
    source: dict[str, Any],
    source_digest: str,
    contact: dict[str, Any],
    identity: dict[str, Any],
) -> dict[str, Any]:
    return {
        "source_packet_sha256": source_digest,
        "opportunity_id": source["opportunity_id"],
        "canonical_org_id": identity["canonical_org_id"],
        "canonical_purpose_id": identity["canonical_purpose_id"],
        "contact_ref": contact["contact_ref"],
        "route_type": contact["route_type"],
        "route": contact["route"],
        "relationship_state": contact["relationship_state"],
        "relationship_evidence_ref": contact["relationship_evidence_ref"],
        "relationship_evidence_sha256": contact["relationship_evidence_sha256"],
        "relationship_generation": contact["relationship_generation"],
        "relationship_head_sha256": contact["relationship_head_sha256"],
        "relationship_observed_at": contact["relationship_observed_at"],
        "relationship_valid_until": contact["relationship_valid_until"],
    }


def _bind_relationship_authority(
    source: dict[str, Any],
    source_digest: str,
    contact: dict[str, Any],
    identity: dict[str, Any],
    _verify=verify_context_authority,
) -> dict[str, Any]:
    payload = _relationship_authority_payload(source, source_digest, contact, identity)
    contact["relationship_authority_authenticated"] = _verify(
        "RELATIONSHIP", payload, contact["relationship_authority_tag_hex"]
    )
    contact["canonical_org_id"] = identity["canonical_org_id"]
    contact["canonical_purpose_id"] = identity["canonical_purpose_id"]
    return contact


def compute_dedupe_key(source: dict[str, Any], contact: dict[str, Any]) -> str:
    try:
        canonical_org_id = contact["canonical_org_id"]
        canonical_purpose_id = contact["canonical_purpose_id"]
    except KeyError as exc:
        raise FirewallError("canonical identity binding required before dedupe") from exc
    return sha256_hex(canonical_json({
        "opportunity_id": source["opportunity_id"],
        "canonical_org_id": canonical_org_id,
        "canonical_purpose_id": canonical_purpose_id,
    }))


def _validate_lease(value: Any, _verify_writer_authority=verify_writer_lease_authority) -> dict[str, Any]:
    if type(value) is not dict:
        raise FirewallError("writer_lease must be an object")
    if set(value) != set(LEASE_KEYS) | {"authority_tag_hex"}:
        raise FirewallError("writer_lease schema mismatch")
    row = dict(value)
    for field in ("lease_id", "seat", "session_nonce"):
        row[field] = _token(row[field], field)
    row["collision_key"] = _digest(row["collision_key"], "collision_key")
    row["authority_tag_hex"] = _digest(row["authority_tag_hex"], "authority_tag_hex")
    issued = _utc(row["issued_at"], "lease.issued_at")
    expires = _utc(row["expires_at"], "lease.expires_at")
    if expires <= issued:
        raise FirewallError("lease expires_at must be after issued_at")
    if (expires - issued).total_seconds() > MAX_LEASE_SECONDS:
        raise FirewallError("lease duration exceeds one-hour ceiling")
    if row["status"] not in LEASE_STATUSES:
        raise FirewallError("unsupported lease status")
    row["authority_authenticated"] = _verify_writer_authority(row)
    return row


def normalize_packet(payload: Any, _validate_lease_fn=_validate_lease) -> dict[str, Any]:
    row = _exact_keys(payload, TOP_KEYS, "packet")
    if row["schema"] != SCHEMA:
        raise FirewallError("wrong packet schema")
    source = _validate_source(row["source_packet"])
    expected_source_digest = _digest(row["source_packet_sha256"], "source_packet_sha256")
    if sha256_hex(canonical_json(source)) != expected_source_digest:
        raise FirewallError("source_packet digest mismatch")
    qualifications = _validate_qualifications(row["qualifications"])
    economics = _validate_economics(row["economics"])
    contact = _validate_contact(row["contact"])
    identity = _validate_identity_binding(
        row["identity_binding"], source=source, source_digest=expected_source_digest, contact=contact
    )
    contact = _bind_relationship_authority(source, expected_source_digest, contact, identity)
    requesting_seat = _token(row["requesting_seat"], "requesting_seat")
    session_nonce = _token(row["session_nonce"], "session_nonce")
    lease = None if row["writer_lease"] is None else _validate_lease_fn(row["writer_lease"])
    return {
        "schema": SCHEMA,
        "source_packet": source,
        "source_packet_sha256": expected_source_digest,
        "qualifications": qualifications,
        "economics": economics,
        "contact": contact,
        "identity_binding": identity,
        "requesting_seat": requesting_seat,
        "session_nonce": session_nonce,
        "writer_lease": lease,
    }
