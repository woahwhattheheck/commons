#!/usr/bin/env python3
"""Legacy Jersey DN827803 compatibility gate backed by repo-pinned pursuit authority.

The original v1 qualifier accepted caller-owned time, route, partner confirmation,
and evidence declarations and could therefore self-mint READY after a future
pack acquisition. Current readiness authority lives in the shared
``revenue.pursuit_evidence_bridge`` binding. This module keeps the historical
CLI/library surface usable for HOLD diagnostics, but it can never emit READY.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from revenue.pursuit_evidence_bridge.bridge import (  # noqa: E402
    BridgeError,
    compile_bridge as _bridge_compile,
)

BINDING_ID = "jersey-dn827803-main-v1"
NOTICE_ID = "DN827803"
SCHEMA_VERSION = 2

# Retained for compatibility with consumers that import the historical names.
# These are advisory route vocabularies only; they no longer carry READY authority.
AUTHORITY_FLAGS = {
    "portal_registration",
    "buyer_contact",
    "clarification_question",
    "tender_submission",
    "pricing_commitment",
    "staffing_commitment",
    "clinical_certification_claim",
    "contract_acceptance",
    "spend",
    "revenue_claim",
}
ROUTES: dict[str, tuple[str, ...]] = {
    "PRIME_CDR": (
        "openehr_platform_product",
        "clinical_cdr_delivery",
        "real_time_clinical_data",
        "healthcare_interoperability",
        "clinical_identity_terminology",
        "security_privacy",
        "clinical_safety",
        "migration_at_scale",
        "service_operations",
        "commercial_delivery_capacity",
    ),
    "TEAMING_INTEROPERABILITY_SPECIALIST": (
        "healthcare_interoperability",
        "data_migration_reconciliation",
        "interface_conformance",
        "replay_idempotency",
        "observability_lineage",
        "security_data_governance",
    ),
    "TEAMING_ACCEPTANCE_EVIDENCE": (
        "interface_conformance",
        "data_migration_reconciliation",
        "observability_lineage",
        "replay_idempotency",
        "human_release_controls",
    ),
}
TEAMING_ROUTES = {"TEAMING_INTEROPERABILITY_SPECIALIST", "TEAMING_ACCEPTANCE_EVIDENCE"}


class QualificationError(ValueError):
    """Malformed, stale, unbound, or self-authenticating legacy input."""


def _unique_object(pairs: Iterable[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise QualificationError(f"DUPLICATE_JSON_KEY:{key}")
        out[key] = value
    return out


def load_json_bytes(raw: bytes, label: str) -> dict[str, Any]:
    if not isinstance(raw, (bytes, bytearray)):
        raise QualificationError(f"{label}:BYTES_REQUIRED")
    try:
        value = json.loads(bytes(raw).decode("utf-8", "strict"), object_pairs_hook=_unique_object)
    except QualificationError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise QualificationError(f"{label}:INVALID_JSON_OR_UTF8") from exc
    if type(value) is not dict:
        raise QualificationError(f"{label}:ROOT_MUST_BE_OBJECT")
    return value


@dataclass(frozen=True)
class Evaluation:
    state: str
    exit_code: int
    payload: dict[str, Any]

    def bytes(self) -> bytes:
        return (json.dumps(self.payload, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def _legacy_state(bridge_result: dict[str, Any]) -> str:
    if type(bridge_result) is not dict:
        raise QualificationError("BRIDGE_RESULT:MUST_BE_OBJECT")
    status = bridge_result.get("status")
    reasons = bridge_result.get("reason_codes")
    if status not in {"HOLD", "OPPORTUNITY_EVIDENCE_READY"}:
        raise QualificationError("BRIDGE_RESULT:UNKNOWN_STATUS")
    if type(reasons) is not list or any(type(item) is not str for item in reasons):
        raise QualificationError("BRIDGE_RESULT:INVALID_REASON_CODES")
    if bridge_result.get("external_submission_authorized") is not False:
        raise QualificationError("BRIDGE_RESULT:EXTERNAL_AUTHORITY_ESCALATION")
    action_authority = bridge_result.get("authority")
    if type(action_authority) is not dict or any(value is not False for value in action_authority.values()):
        raise QualificationError("BRIDGE_RESULT:ACTION_AUTHORITY_ESCALATION")

    # Even a future evidence-ready bridge generation cannot resurrect this
    # historical route/partner READY surface. A separate reviewed route decision
    # must consume the evidence-ready result.
    if status == "OPPORTUNITY_EVIDENCE_READY":
        return "HOLD_LEGACY_QUALIFIER_RETIRED"
    if "PROPOSAL_DEADLINE_EXPIRED" in reasons:
        return "HOLD_DEADLINE_EXPIRED"
    if any("TENDER_PACK" in reason for reason in reasons):
        return "HOLD_TENDER_PACK_REQUIRED"
    return "HOLD_EVIDENCE_AUTHORITY_REQUIRED"


def _bind_current_evaluate(bridge_compile: Any):
    """Capture the reviewed bridge capability instead of a mutable module alias."""
    def current_evaluate(
        manifest: dict[str, Any],
        source: dict[str, Any],
        source_raw: bytes,
        *,
        tender_pack_bytes: bytes | None = None,
    ) -> Evaluation:
        if type(manifest) is not dict or type(source) is not dict:
            raise QualificationError("manifest/source:MUST_BE_OBJECT")
        if tender_pack_bytes is not None:
            raise QualificationError(
                "LEGACY_TENDER_PACK_BYTES_NOT_AUTHORITY:rotate the repo-pinned pursuit binding instead"
            )

        parsed_raw = load_json_bytes(source_raw, "source_raw")
        if parsed_raw != source:
            raise QualificationError("SOURCE_RAW_OBJECT_MISMATCH")

        try:
            bridge_result = bridge_compile(BINDING_ID, source, manifest, None)
        except BridgeError as exc:
            raise QualificationError(f"BRIDGE_AUTHORITY_REJECTED:{exc}") from exc

        state = _legacy_state(bridge_result)
        payload = {
            "schema_version": SCHEMA_VERSION,
            "notice_id": NOTICE_ID,
            "state": state,
            "binding_id": bridge_result["binding_id"],
            "binding_registry_sha256": bridge_result["binding_registry_sha256"],
            "bridge_status": bridge_result["status"],
            "bridge_reason_codes": list(bridge_result["reason_codes"]),
            "deadline_utc": bridge_result["deadline_utc"],
            "evaluated_at": bridge_result["evaluated_at"],
            "legacy_manifest_route_advisory": manifest.get("route"),
            "legacy_partner_prime_confirmed_advisory": manifest.get("partner_prime_confirmed"),
            "authority": "INTERNAL_QUALIFICATION_ONLY",
            "action_authority": dict(bridge_result["authority"]),
            "tender_submission_authorized": False,
            "external_submission_authorized": False,
            "legacy_ready_authority_retired": True,
        }
        # Compatibility gate is intentionally HOLD-only. Current evidence
        # authority belongs to the shared bridge; route/commercial approval is a
        # separate reviewed decision.
        return Evaluation(state, 3, payload)

    return current_evaluate


evaluate = _bind_current_evaluate(_bridge_compile)
del _bind_current_evaluate


def _write_exclusive(path: Path, data: bytes) -> None:
    """Create a diagnostic receipt without following/replacing a final symlink."""
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(path, flags, 0o600)
    try:
        with os.fdopen(fd, "wb", closefd=False) as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
    finally:
        os.close(fd)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--source-ledger", type=Path, default=Path(__file__).with_name("sources.json"))
    parser.add_argument(
        "--tender-pack",
        type=Path,
        default=None,
        help="legacy compatibility option; supplying bytes now fails closed",
    )
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args(argv)

    try:
        source_raw = args.source_ledger.read_bytes()
        source = load_json_bytes(source_raw, "source")
        manifest = load_json_bytes(args.manifest.read_bytes(), "manifest")
        pack_bytes = args.tender_pack.read_bytes() if args.tender_pack else None
        result = evaluate(manifest, source, source_raw, tender_pack_bytes=pack_bytes)
        encoded = result.bytes()
        if args.output is None:
            sys.stdout.buffer.write(encoded)
        else:
            _write_exclusive(args.output, encoded)
        return result.exit_code
    except (OSError, QualificationError) as exc:
        payload = {
            "state": "INVALID_INPUT",
            "error": str(exc),
            "tender_submission_authorized": False,
            "external_submission_authorized": False,
        }
        sys.stderr.write(json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
