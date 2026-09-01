"""Terms, package, recipient, and deletion contracts. Offline only."""

from __future__ import annotations

import hashlib
from typing import Any

REQUIRED_TERM_INSTRUMENTS = (
    "terms_of_service",
    "privacy_and_data_use",
    "authority_attestation",
    "peer_ai_disclosure",
    "retention_export_deletion",
    "recipient_transfer_authorization",
    "affiliate_compensation_disclosure",
)

TERM_STATES = {
    "NOT_ACCEPTED",
    "ACCEPTED_v1",
    "REACCEPT_REQUIRED",
    "AUTHORITY_HOLD",
    "TRANSFER_NOT_AUTHORIZED",
    "TRANSFER_AUTHORIZED",
}

PACKAGE_PARTS = (
    "reviewed_pdf",
    "chronology",
    "lead_tables",
    "weak_lead_appendix",
    "source_manifest",
    "citation_index",
    "structured_json",
    "grounding_versions",
    "release_manifest",
    "package_hash",
    "recipient",
    "release_version",
)

TOMBSTONE_FIELDS = (
    "case_id",
    "deleted_at",
    "actor_role",
    "receipt_hash",
    "keys_destroyed",
    "case_bytes_remaining",
)


def default_terms_state(*, accepted: bool = False) -> dict[str, Any]:
    return {
        "instruments": {name: {"version": "v1", "digest": f"syn-{name}"} for name in REQUIRED_TERM_INSTRUMENTS},
        "analysis_held_before_acceptance": True,
        "prechecked_boxes": False,
        "transfer_default": "off",
        "legal_button_on_every_screen": True,
        "terms_state": "ACCEPTED_v1" if accepted else "NOT_ACCEPTED",
    }


def terms_report(state: dict[str, Any]) -> dict[str, Any]:
    missing = [name for name in REQUIRED_TERM_INSTRUMENTS if name not in state.get("instruments", {})]
    return {
        "missing_instruments": missing,
        "pass": (
            not missing
            and bool(state.get("analysis_held_before_acceptance"))
            and not bool(state.get("prechecked_boxes"))
            and state.get("transfer_default") == "off"
            and bool(state.get("legal_button_on_every_screen"))
            and state.get("terms_state") in TERM_STATES
        ),
    }


def default_package() -> dict[str, Any]:
    payload = b"SYN-CTPKG-GOLDEN"
    return {
        "reviewed_pdf": "synthetic",
        "chronology": "synthetic",
        "lead_tables": "synthetic",
        "weak_lead_appendix": "synthetic",
        "source_manifest": "synthetic",
        "citation_index": "synthetic",
        "structured_json": "synthetic",
        "grounding_versions": "charttrace.grounding.v1.1",
        "release_manifest": "synthetic",
        "package_hash": hashlib.sha256(payload).hexdigest(),
        "recipient": {"name": "SYN Counsel Reviewer", "authorized": True, "authorization_id": "SYN-XFER-0001"},
        "release_version": 1,
        "payload": payload,
    }


def package_report(package: dict[str, Any], mutated: bytes | None = None) -> dict[str, Any]:
    missing = [name for name in PACKAGE_PARTS if name not in package]
    locked = package.get("package_hash")
    byte_mismatch = False
    if mutated is not None and locked:
        byte_mismatch = hashlib.sha256(mutated).hexdigest() != locked
    return {
        "missing": missing,
        "byte_change_fails_closed": byte_mismatch if mutated is not None else True,
        "pass": not missing and (mutated is None or byte_mismatch),
    }


def recipient_report(recipient: dict[str, Any], *, bytes_locked: bool = True) -> dict[str, Any]:
    authorized = bool(
        recipient.get("authorized")
        and recipient.get("authorization_id")
        and recipient.get("name")
    )
    return {"authorized": authorized, "pass": authorized and bytes_locked}


def default_deletion_receipt() -> dict[str, Any]:
    return {
        "case_id": "syn-case-01",
        "deleted_at": "2026-09-01T00:00:00Z",
        "actor_role": "operator",
        "receipt_hash": "syn-tombstone-v1",
        "keys_destroyed": True,
        "case_bytes_remaining": 0,
    }


def deletion_report(receipt: dict[str, Any]) -> dict[str, Any]:
    missing = [field for field in TOMBSTONE_FIELDS if field not in receipt]
    return {
        "missing": missing,
        "pass": not missing and bool(receipt.get("keys_destroyed")) and receipt.get("case_bytes_remaining") == 0,
    }


def peer_input_isolation(payload: dict[str, Any]) -> dict[str, Any]:
    banned = ("order_total", "destination_office", "affiliate_id", "recovery_share")
    leaks = [key for key in banned if payload.get(key) not in {None, "", False}]
    return {"leaks": leaks, "pass": not leaks}
