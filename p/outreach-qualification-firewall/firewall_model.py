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

_CURRENCY_RE = re.compile(r"^[A-Z]{3}$")


def _make_validate_source(
    exact, token, canonical_https, canonical_route, utc, exact_int, exact_bool, err,
    source_keys, route_types, registration_states, max_runway,
):
    keys = frozenset(source_keys)
    routes = frozenset(route_types)
    registrations = frozenset(registration_states)

    def validate_source(source: Any) -> dict[str, Any]:
        row = exact(source, keys, "source_packet")
        row["opportunity_id"] = token(row["opportunity_id"], "opportunity_id")
        row["source_uri"] = canonical_https(row["source_uri"], "source_uri")
        row["source_generation"] = token(row["source_generation"], "source_generation")
        observed = utc(row["observed_at"], "observed_at")
        deadline = utc(row["deadline_at"], "deadline_at")
        if observed > deadline:
            raise err("source observation is after deadline")
        row["min_runway_seconds"] = exact_int(
            row["min_runway_seconds"], "min_runway_seconds", 0, max_runway
        )
        route_type = row["submission_route_type"]
        if route_type not in routes:
            raise err("unsupported submission_route_type")
        row["submission_route"] = canonical_route(
            route_type, row["submission_route"], "submission_route"
        )
        required = exact_bool(row["registration_required"], "registration_required")
        if row["registration_state"] not in registrations:
            raise err("unsupported registration_state")
        if not required and row["registration_state"] != "NOT_REQUIRED":
            raise err("registration_state must be NOT_REQUIRED when registration is not required")
        if required and row["registration_state"] == "NOT_REQUIRED":
            raise err("registration required but state says NOT_REQUIRED")
        return row

    return validate_source


_validate_source = _make_validate_source(
    _exact_keys,
    _token,
    _canonical_https,
    _canonical_route,
    _utc,
    _exact_int,
    _exact_bool,
    FirewallError,
    SOURCE_KEYS,
    SUBMISSION_ROUTE_TYPES,
    REGISTRATION_STATES,
    MAX_RUNWAY_SECONDS,
)


def _make_validate_qualifications(
    exact, token, exact_bool, digest, err, qual_keys, dispositions, max_rows,
):
    keys = frozenset(qual_keys)
    allowed = frozenset(dispositions)

    def validate_qualifications(value: Any) -> list[dict[str, Any]]:
        if type(value) is not list or not value or len(value) > max_rows:
            raise err("qualifications must be a nonempty bounded list")
        out: list[dict[str, Any]] = []
        seen: set[str] = set()
        for raw in value:
            row = exact(raw, keys, "qualification")
            row["gate_id"] = token(row["gate_id"], "gate_id")
            if row["gate_id"] in seen:
                raise err("duplicate qualification gate_id")
            seen.add(row["gate_id"])
            if row["disposition"] not in allowed:
                raise err("unsupported qualification disposition")
            row["required_for_outreach"] = exact_bool(
                row["required_for_outreach"], "required_for_outreach"
            )
            row["evidence_ref"] = token(row["evidence_ref"], "evidence_ref")
            row["evidence_sha256"] = digest(row["evidence_sha256"], "evidence_sha256")
            out.append(row)
        return sorted(out, key=lambda row: row["gate_id"])

    return validate_qualifications


_validate_qualifications = _make_validate_qualifications(
    _exact_keys,
    _token,
    _exact_bool,
    _digest,
    FirewallError,
    QUAL_KEYS,
    QUAL_DISPOSITIONS,
    MAX_LIST_ROWS,
)


def _make_validate_economics(
    exact, token, exact_int, currency_re, err, econ_keys, bases, max_minor, max_quantity,
):
    keys = frozenset(econ_keys)
    allowed_bases = frozenset(bases)

    def validate_economics(value: Any) -> dict[str, Any]:
        row = exact(value, keys, "economics")
        row["workshare_ref"] = token(row["workshare_ref"], "workshare_ref")
        if type(row["currency"]) is not str or not currency_re.fullmatch(row["currency"]):
            raise err("currency must be three uppercase ASCII letters")
        row["amount_minor"] = exact_int(row["amount_minor"], "amount_minor", 1, max_minor)
        if row["compensation_basis"] not in allowed_bases:
            raise err("unsupported compensation_basis")
        row["quantity_max"] = exact_int(
            row["quantity_max"], "quantity_max", 1, max_quantity
        )
        row["scope_ref"] = token(row["scope_ref"], "scope_ref")
        return row

    return validate_economics


_validate_economics = _make_validate_economics(
    _exact_keys,
    _token,
    _exact_int,
    _CURRENCY_RE,
    FirewallError,
    ECON_KEYS,
    COMPENSATION_BASES,
    MAX_MINOR_UNITS,
    MAX_QUANTITY,
)


def _make_validate_contact(
    exact, token, route, digest, utc, err, contact_keys, relationship_states,
    max_relationship_validity,
):
    keys = frozenset(contact_keys)
    allowed_states = frozenset(relationship_states)

    def validate_contact(value: Any) -> dict[str, Any]:
        row = exact(value, keys, "contact")
        for field in (
            "org_ref",
            "contact_ref",
            "relationship_evidence_ref",
            "relationship_generation",
            "purpose_ref",
        ):
            row[field] = token(row[field], field)
        if row["route_type"] not in {"EMAIL", "FORM"}:
            raise err("unsupported outreach route_type")
        row["route"] = route(
            "EMAIL" if row["route_type"] == "EMAIL" else "FORM",
            row["route"],
            "contact.route",
        )
        if row["relationship_state"] not in allowed_states:
            raise err("unsupported relationship_state")
        row["relationship_evidence_sha256"] = digest(
            row["relationship_evidence_sha256"], "relationship_evidence_sha256"
        )
        row["relationship_head_sha256"] = digest(
            row["relationship_head_sha256"], "relationship_head_sha256"
        )
        row["relationship_authority_tag_hex"] = digest(
            row["relationship_authority_tag_hex"], "relationship_authority_tag_hex"
        )
        observed = utc(row["relationship_observed_at"], "relationship_observed_at")
        valid_until = utc(row["relationship_valid_until"], "relationship_valid_until")
        if valid_until <= observed:
            raise err("relationship validity must end after observation")
        if (valid_until - observed).total_seconds() > max_relationship_validity:
            raise err("relationship snapshot validity exceeds bounded ceiling")
        return row

    return validate_contact


_validate_contact = _make_validate_contact(
    _exact_keys,
    _token,
    _canonical_route,
    _digest,
    _utc,
    FirewallError,
    CONTACT_KEYS,
    RELATIONSHIP_STATES,
    MAX_RELATIONSHIP_VALIDITY_SECONDS,
)


def _make_validate_identity_binding(
    exact, token, digest, utc, verify, err, identity_keys, max_identity_validity,
):
    keys = frozenset(identity_keys)

    def validate_identity_binding(
        value: Any,
        *,
        source: dict[str, Any],
        source_digest: str,
        contact: dict[str, Any],
    ) -> dict[str, Any]:
        row = exact(value, keys, "identity_binding")
        for field in (
            "binding_id",
            "opportunity_id",
            "org_ref",
            "purpose_ref",
            "canonical_org_id",
            "canonical_purpose_id",
        ):
            row[field] = token(row[field], field)
        row["source_packet_sha256"] = digest(
            row["source_packet_sha256"], "identity source_packet_sha256"
        )
        row["auth_tag_hex"] = digest(row["auth_tag_hex"], "identity auth_tag_hex")
        observed = utc(row["observed_at"], "identity observed_at")
        valid_until = utc(row["valid_until"], "identity valid_until")
        if valid_until <= observed:
            raise err("identity validity must end after observation")
        if (valid_until - observed).total_seconds() > max_identity_validity:
            raise err("identity binding validity exceeds bounded ceiling")
        if (
            row["source_packet_sha256"] != source_digest
            or row["opportunity_id"] != source["opportunity_id"]
        ):
            raise err("identity binding source/opportunity mismatch")
        if row["org_ref"] != contact["org_ref"] or row["purpose_ref"] != contact["purpose_ref"]:
            raise err("identity binding aliases do not match contact")
        unsigned = {key: item for key, item in row.items() if key != "auth_tag_hex"}
        row["authority_authenticated"] = verify(
            "IDENTITY", unsigned, row["auth_tag_hex"]
        )
        return row

    return validate_identity_binding


_validate_identity_binding = _make_validate_identity_binding(
    _exact_keys,
    _token,
    _digest,
    _utc,
    verify_context_authority,
    FirewallError,
    IDENTITY_KEYS,
    MAX_IDENTITY_VALIDITY_SECONDS,
)


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


def _make_bind_relationship_authority(verify, payload_fn):
    def bind_relationship_authority(
        source: dict[str, Any],
        source_digest: str,
        contact: dict[str, Any],
        identity: dict[str, Any],
    ) -> dict[str, Any]:
        payload = payload_fn(source, source_digest, contact, identity)
        contact["relationship_authority_authenticated"] = verify(
            "RELATIONSHIP", payload, contact["relationship_authority_tag_hex"]
        )
        contact["canonical_org_id"] = identity["canonical_org_id"]
        contact["canonical_purpose_id"] = identity["canonical_purpose_id"]
        return contact

    return bind_relationship_authority


_bind_relationship_authority = _make_bind_relationship_authority(
    verify_context_authority,
    _relationship_authority_payload,
)


def _make_compute_dedupe_key(sha, canonical, err):
    def compute_dedupe_key(source: dict[str, Any], contact: dict[str, Any]) -> str:
        try:
            canonical_org_id = contact["canonical_org_id"]
            canonical_purpose_id = contact["canonical_purpose_id"]
        except KeyError as exc:
            raise err("canonical identity binding required before dedupe") from exc
        return sha(canonical({
            "opportunity_id": source["opportunity_id"],
            "canonical_org_id": canonical_org_id,
            "canonical_purpose_id": canonical_purpose_id,
        }))

    return compute_dedupe_key


compute_dedupe_key = _make_compute_dedupe_key(
    sha256_hex,
    canonical_json,
    FirewallError,
)


def _make_validate_lease(
    token, digest, utc, verify, err, lease_keys, statuses, max_lease_seconds,
):
    keys = frozenset(lease_keys) | frozenset({"authority_tag_hex"})
    allowed_statuses = frozenset(statuses)

    def validate_lease(value: Any) -> dict[str, Any]:
        if type(value) is not dict:
            raise err("writer_lease must be an object")
        if set(value) != keys:
            raise err("writer_lease schema mismatch")
        row = dict(value)
        for field in ("lease_id", "seat", "session_nonce"):
            row[field] = token(row[field], field)
        row["collision_key"] = digest(row["collision_key"], "collision_key")
        row["authority_tag_hex"] = digest(row["authority_tag_hex"], "authority_tag_hex")
        issued = utc(row["issued_at"], "lease.issued_at")
        expires = utc(row["expires_at"], "lease.expires_at")
        if expires <= issued:
            raise err("lease expires_at must be after issued_at")
        if (expires - issued).total_seconds() > max_lease_seconds:
            raise err("lease duration exceeds one-hour ceiling")
        if row["status"] not in allowed_statuses:
            raise err("unsupported lease status")
        row["authority_authenticated"] = verify(row)
        return row

    return validate_lease


_validate_lease = _make_validate_lease(
    _token,
    _digest,
    _utc,
    verify_writer_lease_authority,
    FirewallError,
    LEASE_KEYS,
    LEASE_STATUSES,
    MAX_LEASE_SECONDS,
)


def _make_normalize_packet(
    validate_lease,
    exact,
    validate_source,
    digest,
    sha,
    canonical,
    validate_qualifications,
    validate_economics,
    validate_contact,
    validate_identity,
    bind_relationship,
    token,
    schema,
    top_keys,
    err,
):
    keys = frozenset(top_keys)

    def normalize_packet(payload: Any) -> dict[str, Any]:
        row = exact(payload, keys, "packet")
        if row["schema"] != schema:
            raise err("wrong packet schema")
        source = validate_source(row["source_packet"])
        expected_source_digest = digest(
            row["source_packet_sha256"], "source_packet_sha256"
        )
        if sha(canonical(source)) != expected_source_digest:
            raise err("source_packet digest mismatch")
        qualifications = validate_qualifications(row["qualifications"])
        economics = validate_economics(row["economics"])
        contact = validate_contact(row["contact"])
        identity = validate_identity(
            row["identity_binding"],
            source=source,
            source_digest=expected_source_digest,
            contact=contact,
        )
        contact = bind_relationship(
            source, expected_source_digest, contact, identity
        )
        requesting_seat = token(row["requesting_seat"], "requesting_seat")
        session_nonce = token(row["session_nonce"], "session_nonce")
        lease = (
            None
            if row["writer_lease"] is None
            else validate_lease(row["writer_lease"])
        )
        return {
            "schema": schema,
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

    return normalize_packet


normalize_packet = _make_normalize_packet(
    _validate_lease,
    _exact_keys,
    _validate_source,
    _digest,
    sha256_hex,
    canonical_json,
    _validate_qualifications,
    _validate_economics,
    _validate_contact,
    _validate_identity_binding,
    _bind_relationship_authority,
    _token,
    SCHEMA,
    TOP_KEYS,
    FirewallError,
)

del (
    _make_validate_source,
    _make_validate_qualifications,
    _make_validate_economics,
    _make_validate_contact,
    _make_validate_identity_binding,
    _make_bind_relationship_authority,
    _make_compute_dedupe_key,
    _make_validate_lease,
    _make_normalize_packet,
)
