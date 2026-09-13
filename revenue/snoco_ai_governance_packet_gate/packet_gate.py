#!/usr/bin/env python3
"""Fail-closed compliance gate for Snohomish County RFP-26-0791BC.

This package does not submit, contact, price, sign, or log into procurement
systems.  It only verifies that requirement claims are backed by allowed
source authority and reports whether the official packet is still required.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

SOURCE_SCHEMA = "snoco-rfp-source-registry/v1"
MATRIX_SCHEMA = "snoco-rfp-compliance-matrix/v1"
RECEIPT_SCHEMA = "snoco-rfp-packet-gate-receipt/v1"
SOLICITATION_ID = "RFP-26-0791BC"

OFFICIAL_AUTHORITIES = {
    "OFFICIAL_PUBLIC_NOTICE",
    "OFFICIAL_COUNTY_GUIDANCE",
    "OFFICIAL_PORTAL",
}
ALLOWED_AUTHORITIES = OFFICIAL_AUTHORITIES | {"THIRD_PARTY_MIRROR"}
ALLOWED_STATES = {"CONFIRMED_OFFICIAL", "PACKET_REQUIRED"}
ALLOWED_CLASSIFICATIONS = {
    "MANDATORY",
    "SUBMISSION",
    "CONTROL",
    "INFORMATIONAL",
    "SCOREABLE",
    "SCOREABLE_OR_MANDATORY",
}
BOUNDARY_KEYS = {
    "portal_login_authorized",
    "vendor_registration_authorized",
    "county_contact_authorized",
    "question_submission_authorized",
    "pricing_commitment_authorized",
    "signature_authorized",
    "proposal_submission_authorized",
    "award_claim_authorized",
    "recognized_revenue",
}

class GateError(ValueError):
    pass

def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")

def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()

def _exact_keys(obj: Any, expected: set[str], label: str) -> None:
    if not isinstance(obj, dict):
        raise GateError(f"{label} must be an object")
    actual = set(obj)
    if actual != expected:
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        raise GateError(f"{label} keys mismatch: missing={missing} extra={extra}")

def _bounded_text(value: Any, label: str, *, maximum: int = 1000) -> str:
    if not isinstance(value, str):
        raise GateError(f"{label} must be text")
    clean = " ".join(value.split())
    if not clean or len(clean) > maximum or any(ord(c) < 32 for c in clean):
        raise GateError(f"{label} must be bounded printable text")
    return clean

def validate_sources(registry: Any) -> dict[str, dict[str, Any]]:
    _exact_keys(
        registry,
        {"schema", "solicitation_id", "title", "retrieved_at", "sources"},
        "source registry",
    )
    if registry["schema"] != SOURCE_SCHEMA or registry["solicitation_id"] != SOLICITATION_ID:
        raise GateError("wrong source registry identity")
    _bounded_text(registry["title"], "title", maximum=200)
    if not isinstance(registry["retrieved_at"], str) or not registry["retrieved_at"].endswith("Z"):
        raise GateError("retrieved_at must be a UTC string")
    if not isinstance(registry["sources"], list) or not registry["sources"]:
        raise GateError("sources must be a non-empty list")

    by_id: dict[str, dict[str, Any]] = {}
    for index, source in enumerate(registry["sources"]):
        _exact_keys(
            source,
            {"id", "authority", "url", "assertable", "raw_bytes_sha256", "raw_hash_status", "facts"},
            f"source[{index}]",
        )
        sid = _bounded_text(source["id"], f"source[{index}].id", maximum=120)
        if sid in by_id:
            raise GateError(f"duplicate source id: {sid}")
        if source["authority"] not in ALLOWED_AUTHORITIES:
            raise GateError(f"unsupported authority: {source['authority']}")
        if not isinstance(source["url"], str) or not source["url"].startswith("https://"):
            raise GateError(f"source {sid} must use https")
        if source["authority"] == "THIRD_PARTY_MIRROR":
            if source["assertable"] is not False:
                raise GateError(f"third-party source {sid} must be non-assertable")
        elif source["assertable"] is not True:
            raise GateError(f"official source {sid} must be assertable")
        digest = source["raw_bytes_sha256"]
        if digest is not None and (not isinstance(digest, str) or len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest)):
            raise GateError(f"source {sid} raw_bytes_sha256 is invalid")
        _bounded_text(source["raw_hash_status"], f"source {sid} hash status", maximum=120)
        if not isinstance(source["facts"], list) or not source["facts"]:
            raise GateError(f"source {sid} needs at least one fact")
        for fact_index, fact in enumerate(source["facts"]):
            _bounded_text(fact, f"source {sid} fact[{fact_index}]", maximum=600)
        by_id[sid] = source
    return by_id

def validate_matrix(matrix: Any, sources: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    _exact_keys(
        matrix,
        {"schema", "solicitation_id", "packet_state", "requirements", "boundaries"},
        "matrix",
    )
    if matrix["schema"] != MATRIX_SCHEMA or matrix["solicitation_id"] != SOLICITATION_ID:
        raise GateError("wrong matrix identity")
    if matrix["packet_state"] != "LOGIN_REQUIRED_NOT_RETRIEVED":
        raise GateError("packet_state must fail closed until the official packet is actually retrieved")
    if not isinstance(matrix["requirements"], list) or not matrix["requirements"]:
        raise GateError("requirements must be a non-empty list")
    ids: set[str] = set()
    normalized: list[dict[str, Any]] = []
    for index, req in enumerate(matrix["requirements"]):
        _exact_keys(req, {"id", "classification", "state", "source_ids", "requirement"}, f"requirement[{index}]")
        rid = _bounded_text(req["id"], f"requirement[{index}].id", maximum=120)
        if rid in ids:
            raise GateError(f"duplicate requirement id: {rid}")
        ids.add(rid)
        if req["classification"] not in ALLOWED_CLASSIFICATIONS:
            raise GateError(f"unsupported classification for {rid}")
        if req["state"] not in ALLOWED_STATES:
            raise GateError(f"unsupported state for {rid}")
        if not isinstance(req["source_ids"], list):
            raise GateError(f"source_ids for {rid} must be a list")
        if len(set(req["source_ids"])) != len(req["source_ids"]):
            raise GateError(f"duplicate source ids for {rid}")
        cited = []
        for sid in req["source_ids"]:
            if sid not in sources:
                raise GateError(f"unknown source {sid} for {rid}")
            cited.append(sources[sid])
        _bounded_text(req["requirement"], f"requirement {rid}", maximum=1200)

        if req["state"] == "CONFIRMED_OFFICIAL":
            if not cited:
                raise GateError(f"confirmed requirement {rid} must cite official evidence")
            if not any(source["authority"] in OFFICIAL_AUTHORITIES and source["assertable"] for source in cited):
                raise GateError(f"confirmed requirement {rid} lacks official authority")
        normalized.append(req)

    _exact_keys(matrix["boundaries"], BOUNDARY_KEYS, "boundaries")
    for key in BOUNDARY_KEYS:
        if matrix["boundaries"][key] is not False:
            raise GateError(f"authority boundary escalated: {key}")
    return normalized

def build_receipt(registry: Any, matrix: Any) -> dict[str, Any]:
    sources = validate_sources(registry)
    requirements = validate_matrix(matrix, sources)
    confirmed = [req["id"] for req in requirements if req["state"] == "CONFIRMED_OFFICIAL"]
    packet_required = [req["id"] for req in requirements if req["state"] == "PACKET_REQUIRED"]
    scoreable_packet_required = [
        req["id"] for req in requirements
        if req["state"] == "PACKET_REQUIRED" and req["classification"] in {"SCOREABLE", "SCOREABLE_OR_MANDATORY"}
    ]
    mandatory_packet_required = [
        req["id"] for req in requirements
        if req["state"] == "PACKET_REQUIRED" and req["classification"] in {"MANDATORY", "SCOREABLE_OR_MANDATORY"}
    ]
    if not packet_required:
        raise GateError("this receipt must not claim packet completeness without official packet ingestion")

    core = {
        "schema": RECEIPT_SCHEMA,
        "solicitation_id": SOLICITATION_ID,
        "source_registry_sha256": _sha256(registry),
        "matrix_sha256": _sha256(matrix),
        "official_source_count": sum(source["authority"] in OFFICIAL_AUTHORITIES for source in sources.values()),
        "mirror_source_count": sum(source["authority"] == "THIRD_PARTY_MIRROR" for source in sources.values()),
        "confirmed_official_ids": confirmed,
        "packet_required_ids": packet_required,
        "mandatory_packet_required_ids": mandatory_packet_required,
        "scoreable_packet_required_ids": scoreable_packet_required,
        "decision": "HOLD_PACKET_REQUIRED",
        "state": "EVIDENCE_MATRIX_READY_PACKET_BLOCKED",
        "authorities": dict(matrix["boundaries"]),
    }
    return {**core, "receipt_sha256": _sha256(core)}

def verify_receipt(receipt: Any, registry: Any, matrix: Any) -> bool:
    try:
        rebuilt = build_receipt(registry, matrix)
    except (GateError, TypeError, ValueError):
        return False
    return receipt == rebuilt

def _load(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sources", type=Path, default=Path(__file__).with_name("sources.json"))
    parser.add_argument("--matrix", type=Path, default=Path(__file__).with_name("matrix.json"))
    parser.add_argument("--receipt", type=Path)
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    registry = _load(args.sources)
    matrix = _load(args.matrix)
    receipt = build_receipt(registry, matrix)
    if args.verify:
        if args.receipt is None:
            raise SystemExit("--verify requires --receipt")
        supplied = _load(args.receipt)
        ok = verify_receipt(supplied, registry, matrix)
        print(json.dumps({"ok": ok}, sort_keys=True))
        return 0 if ok else 1
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
