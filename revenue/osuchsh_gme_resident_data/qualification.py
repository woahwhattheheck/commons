"""Fail-closed static qualification gate for the OSU-CHS pursuit.

Deadline authority belongs in the shared pursuit_evidence_bridge. This module only
answers whether the retained opportunity/bidder evidence is sufficient to claim a
prime-ready package. It deliberately has no caller-supplied `as_of` parameter.
"""

from __future__ import annotations

import re
from typing import Any, Mapping

from .core import DataError, digest

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_EXPECTED_OPPORTUNITY = "OSUTUL-RFP-001864-2027"


def _sha(value: Any, name: str) -> str:
    if not isinstance(value, str) or not _SHA256_RE.fullmatch(value):
        raise DataError(f"{name} must be lowercase SHA-256")
    return value


def qualify_manifest(manifest: Mapping[str, Any]) -> dict[str, Any]:
    expected_keys = {
        "opportunity_id",
        "controlling_packet_sha256",
        "similar_reference_receipts",
        "non_collusion_owner_confirmed",
        "portal_registration_confirmed",
        "pricing_owner_confirmed",
    }
    if not isinstance(manifest, Mapping) or set(manifest) != expected_keys:
        raise DataError("qualification manifest shape invalid")
    if manifest["opportunity_id"] != _EXPECTED_OPPORTUNITY:
        raise DataError("opportunity_id mismatch")

    packet = manifest["controlling_packet_sha256"]
    refs = manifest["similar_reference_receipts"]
    if packet is not None:
        packet = _sha(packet, "controlling_packet_sha256")
    if not isinstance(refs, list):
        raise DataError("similar_reference_receipts must be a list")

    normalized_refs = []
    seen_orgs: set[str] = set()
    for item in refs:
        if not isinstance(item, Mapping) or set(item) != {"organization", "scope", "evidence_sha256"}:
            raise DataError("reference receipt shape invalid")
        organization = item["organization"]
        scope = item["scope"]
        if not isinstance(organization, str) or not organization.strip():
            raise DataError("reference organization invalid")
        if not isinstance(scope, str) or not scope.strip():
            raise DataError("reference scope invalid")
        org_key = organization.strip().casefold()
        if org_key in seen_orgs:
            raise DataError("duplicate reference organization")
        seen_orgs.add(org_key)
        normalized_refs.append(
            {
                "organization": organization.strip(),
                "scope": scope.strip(),
                "evidence_sha256": _sha(item["evidence_sha256"], "reference evidence_sha256"),
            }
        )

    for flag in ("non_collusion_owner_confirmed", "portal_registration_confirmed", "pricing_owner_confirmed"):
        if type(manifest[flag]) is not bool:
            raise DataError(f"{flag} must be boolean")

    holds: list[str] = []
    if packet is None:
        holds.append("CONTROLLING_PACKET_NOT_RETAINED")
    if len(normalized_refs) < 3:
        holds.append("THREE_SIMILAR_REFERENCES_NOT_EVIDENCED")
    if not manifest["non_collusion_owner_confirmed"]:
        holds.append("NON_COLLUSION_OWNER_CONFIRMATION_MISSING")
    if not manifest["portal_registration_confirmed"]:
        holds.append("PORTAL_REGISTRATION_NOT_CONFIRMED")
    if not manifest["pricing_owner_confirmed"]:
        holds.append("PRICING_OWNER_CONFIRMATION_MISSING")

    if not holds:
        status = "PRIME_EVIDENCE_READY"
    elif len(normalized_refs) < 3:
        status = "TEAMING_REQUIRED"
    else:
        status = "HOLD"

    evidence = {
        "opportunity_id": _EXPECTED_OPPORTUNITY,
        "controlling_packet_sha256": packet,
        "reference_receipts": normalized_refs,
        "owner_flags": {
            "non_collusion_owner_confirmed": manifest["non_collusion_owner_confirmed"],
            "portal_registration_confirmed": manifest["portal_registration_confirmed"],
            "pricing_owner_confirmed": manifest["pricing_owner_confirmed"],
        },
    }
    return {
        "schema": "osuchsh-gme-qualification-v1",
        "status": status,
        "holds": holds,
        "evidence_digest": digest(evidence),
        "submission_authorized": False,
        "buyer_contact_authorized": False,
        "award_or_payment_claimed": False,
    }
