#!/usr/bin/env python3
"""Fail-closed validator for the Snohomish County AI-governance evidence map.

This tool is deliberately offline.  It does not fetch the procurement portal,
contact the County, qualify a bidder, price work, or authorize a submission.
Its job is narrower: prevent a public/secondary scope signal or a local code
capability from silently becoming an unsupported proposal claim.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import PurePosixPath
from typing import Any

SCHEMA = "snoco-ai-gov-capability-map/v1"
RECEIPT_SCHEMA = "snoco-ai-gov-capability-map-verification/v1"
SOLICITATION_ID = "RFP-26-0791BC"
RECOMMENDATION = "TEAMING_WEDGE_ONLY_PENDING_PACKET"
ALLOWED_CLASSIFICATIONS = {
    "SUPPORTED_WEDGE",
    "PARTNER_REQUIRED",
    "CANNOT_CLAIM",
    "PACKET_REQUIRED",
}
ALLOWED_AUTHORITIES = {
    "published_legal_notice",
    "county_procurement_portal",
    "county_purchasing_guidance",
    "secondary_scope_signal",
    "packet_required",
}
REQUIRED_FALSE_BOUNDARIES = {
    "county_packet_retrieved",
    "tjlabs_is_prime",
    "m365_gcc_implementation_claim",
    "purview_implementation_claim",
    "entra_implementation_claim",
    "wa_pra_legal_compliance_claim",
    "proposal_submission_authorized",
    "county_contact_authorized_by_this_artifact",
    "pricing_authorized_by_this_artifact",
}
PINNED_REPO_EVIDENCE = {
    "mcp-conformance-receipts": {
        "path": "host/mcp_conformance.py",
        "blob": "4db5e56f93fe609d0539ab270d088d5b1c23e6b0",
    },
    "exact-change-review-receipts": {
        "path": "host/swarm_review.py",
        "blob": "2f76e23572133de43bfae02a9c14c3c60f070a12",
    },
}
CLASSIFICATION_FLOOR = {
    "m365-gcc-purview-implementation": "CANNOT_CLAIM",
    "entra-rbac-conditional-access": "CANNOT_CLAIM",
    "wa-public-records-legal-compliance": "CANNOT_CLAIM",
    "shadow-ai-enterprise-discovery": "PARTNER_REQUIRED",
    "enterprise-ai-vendor-risk-program": "PARTNER_REQUIRED",
    "enterprise-spend-roi-attribution": "PARTNER_REQUIRED",
    "county-training-change-management": "PARTNER_REQUIRED",
    "public-records-export-redaction-implementation": "PARTNER_REQUIRED",
    "contract-term-scoring-certifications": "PACKET_REQUIRED",
}
HEX40 = re.compile(r"^[0-9a-f]{40}$")
HTTPS = re.compile(r"^https://[^\s]+$")


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _safe_repo_path(value: Any) -> bool:
    if not isinstance(value, str) or not value or value.startswith(("/", "-")) or "\\" in value:
        return False
    parts = PurePosixPath(value).parts
    return bool(parts) and all(part not in ("", ".", "..") for part in parts)


def _nonempty_strings(value: Any) -> bool:
    return isinstance(value, list) and bool(value) and all(isinstance(x, str) and x.strip() for x in value)


def validate(value: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(value, dict):
        return ["matrix_must_be_object"]
    if value.get("schema") != SCHEMA:
        errors.append("schema_mismatch")

    solicitation = value.get("solicitation")
    if not isinstance(solicitation, dict):
        errors.append("solicitation_missing")
        solicitation = {}
    if solicitation.get("id") != SOLICITATION_ID:
        errors.append("solicitation_id_mismatch")
    if solicitation.get("recommendation") != RECOMMENDATION:
        errors.append("recommendation_must_remain_teaming_wedge_pending_packet")
    if solicitation.get("full_packet_authority") != "PACKET_REQUIRED":
        errors.append("full_packet_authority_must_be_packet_required")

    boundary = value.get("boundary")
    if not isinstance(boundary, dict):
        errors.append("boundary_missing")
        boundary = {}
    for field in sorted(REQUIRED_FALSE_BOUNDARIES):
        if boundary.get(field) is not False:
            errors.append("boundary_must_be_false:" + field)

    sources = value.get("sources")
    if not isinstance(sources, list) or len(sources) < 3:
        errors.append("sources_incomplete")
        sources = []
    source_ids: set[str] = set()
    has_notice = False
    has_portal = False
    has_secondary = False
    has_county_guidance = False
    for source in sources:
        if not isinstance(source, dict):
            errors.append("source_not_object")
            continue
        sid = source.get("id")
        if not isinstance(sid, str) or not sid:
            errors.append("source_id_invalid")
            continue
        if sid in source_ids:
            errors.append("duplicate_source_id:" + sid)
        source_ids.add(sid)
        authority = source.get("authority")
        if authority not in ALLOWED_AUTHORITIES:
            errors.append("source_authority_invalid:" + sid)
        url = source.get("url")
        if not isinstance(url, str) or not HTTPS.fullmatch(url):
            errors.append("source_url_invalid:" + sid)
        if authority == "published_legal_notice":
            has_notice = True
        elif authority == "county_procurement_portal":
            has_portal = True
            if source.get("packet_retrieved") is not False:
                errors.append("portal_packet_must_remain_unretrieved")
        elif authority == "county_purchasing_guidance":
            has_county_guidance = True
        elif authority == "secondary_scope_signal":
            has_secondary = True
    if not has_notice:
        errors.append("published_legal_notice_missing")
    if not has_portal:
        errors.append("county_procurement_portal_missing")
    if not has_county_guidance:
        errors.append("county_purchasing_guidance_missing")
    if not has_secondary:
        errors.append("secondary_scope_signal_missing")

    catalog = value.get("repository_evidence_catalog")
    if not isinstance(catalog, list):
        errors.append("repository_evidence_catalog_missing")
        catalog = []
    catalog_by_id: dict[str, dict[str, Any]] = {}
    for item in catalog:
        if not isinstance(item, dict):
            errors.append("repository_evidence_not_object")
            continue
        eid = item.get("id")
        if not isinstance(eid, str) or eid not in PINNED_REPO_EVIDENCE:
            errors.append("repository_evidence_id_unpinned:" + str(eid))
            continue
        if eid in catalog_by_id:
            errors.append("duplicate_repository_evidence_id:" + eid)
        expected = PINNED_REPO_EVIDENCE[eid]
        if item.get("path") != expected["path"] or item.get("blob") != expected["blob"]:
            errors.append("repository_evidence_pin_mismatch:" + eid)
        if not _safe_repo_path(item.get("path")) or not HEX40.fullmatch(str(item.get("blob") or "")):
            errors.append("repository_evidence_identity_invalid:" + eid)
        if not _nonempty_strings(item.get("capabilities")):
            errors.append("repository_evidence_capabilities_missing:" + eid)
        if not _nonempty_strings(item.get("limitations")):
            errors.append("repository_evidence_limitations_missing:" + eid)
        catalog_by_id[eid] = item
    if set(catalog_by_id) != set(PINNED_REPO_EVIDENCE):
        errors.append("repository_evidence_catalog_not_exact")

    rows = value.get("rows")
    if not isinstance(rows, list) or not rows:
        errors.append("rows_missing")
        rows = []
    seen: set[str] = set()
    counts = {name: 0 for name in ALLOWED_CLASSIFICATIONS}
    for row in rows:
        if not isinstance(row, dict):
            errors.append("row_not_object")
            continue
        rid = row.get("id")
        if not isinstance(rid, str) or not rid:
            errors.append("row_id_invalid")
            continue
        if rid in seen:
            errors.append("duplicate_row_id:" + rid)
        seen.add(rid)
        classification = row.get("classification")
        if classification not in ALLOWED_CLASSIFICATIONS:
            errors.append("classification_invalid:" + rid)
            continue
        counts[classification] += 1
        floor = CLASSIFICATION_FLOOR.get(rid)
        if floor is not None and classification != floor:
            errors.append("classification_boundary_violated:" + rid)

        authority = row.get("requirement_authority")
        if authority not in ALLOWED_AUTHORITIES:
            errors.append("requirement_authority_invalid:" + rid)
        if authority == "county_procurement_portal" and boundary.get("county_packet_retrieved") is not True:
            errors.append("unretrieved_packet_used_as_authority:" + rid)
        if classification == "PACKET_REQUIRED" and authority != "packet_required":
            errors.append("packet_required_row_must_use_packet_authority:" + rid)

        if not isinstance(row.get("claim"), str) or not row["claim"].strip():
            errors.append("claim_missing:" + rid)
        if not _nonempty_strings(row.get("limitations")):
            errors.append("limitations_missing:" + rid)

        evidence = row.get("repository_evidence")
        if not isinstance(evidence, list):
            errors.append("repository_evidence_refs_invalid:" + rid)
            evidence = []
        if classification == "SUPPORTED_WEDGE":
            if not evidence:
                errors.append("supported_wedge_without_repository_evidence:" + rid)
            if not _nonempty_strings(row.get("bounded_deliverables")):
                errors.append("supported_wedge_without_bounded_deliverables:" + rid)
            if not _nonempty_strings(row.get("does_not_establish")):
                errors.append("supported_wedge_without_nonclaim_boundary:" + rid)
        elif evidence:
            errors.append("non_supported_row_must_not_use_positive_repo_evidence:" + rid)
        for eid in evidence:
            if eid not in catalog_by_id:
                errors.append("row_references_unpinned_evidence:" + rid + ":" + str(eid))

    missing_floor = sorted(set(CLASSIFICATION_FLOOR) - seen)
    for rid in missing_floor:
        errors.append("required_boundary_row_missing:" + rid)
    if counts["SUPPORTED_WEDGE"] < 2:
        errors.append("insufficient_supported_wedge_rows")
    if counts["CANNOT_CLAIM"] < 3:
        errors.append("insufficient_explicit_nonclaim_rows")
    if counts["PACKET_REQUIRED"] < 1:
        errors.append("packet_required_boundary_missing")
    return errors


def verification_receipt(raw: bytes) -> dict[str, Any]:
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        return {
            "schema": RECEIPT_SCHEMA,
            "ok": False,
            "raw_sha256": sha256_bytes(raw),
            "semantic_sha256": None,
            "errors": ["invalid_json:" + exc.__class__.__name__],
            "classification_counts": {},
            "recommendation": None,
            "packet_retrieved": False,
        }
    errors = validate(value)
    rows = value.get("rows") if isinstance(value, dict) else []
    counts = {name: 0 for name in sorted(ALLOWED_CLASSIFICATIONS)}
    if isinstance(rows, list):
        for row in rows:
            if isinstance(row, dict) and row.get("classification") in counts:
                counts[row["classification"]] += 1
    solicitation = value.get("solicitation") if isinstance(value, dict) else {}
    boundary = value.get("boundary") if isinstance(value, dict) else {}
    return {
        "schema": RECEIPT_SCHEMA,
        "ok": not errors,
        "raw_sha256": sha256_bytes(raw),
        "semantic_sha256": sha256_bytes(canonical_json(value).encode("utf-8")),
        "errors": errors,
        "classification_counts": counts,
        "recommendation": solicitation.get("recommendation") if isinstance(solicitation, dict) else None,
        "packet_retrieved": bool(boundary.get("county_packet_retrieved")) if isinstance(boundary, dict) else False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("matrix")
    args = parser.parse_args(argv)
    with open(args.matrix, "rb") as handle:
        receipt = verification_receipt(handle.read())
    print(canonical_json(receipt))
    return 0 if receipt["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
