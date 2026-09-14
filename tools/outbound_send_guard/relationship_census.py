#!/usr/bin/env python3
"""Live relationship-census authority wrapper (v2, fail closed).

The original parser/normalizer/transfer machinery is retained byte-for-byte in the
underscore-private ``_relationship_census_v1`` module.  This public module fixes
three v1 authority defects:

* live time and freshness policy are process-owned, not caller-selected;
* waiting/inbound/closed and other non-reusable relationship states fail closed;
* a supplied-secret HMAC is integrity evidence, not independent provider-origin
  authority.  Therefore v2 never emits non-HOLD live custody by itself.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from . import _relationship_census_v1 as _core

CENSUS_SCHEMA = _core.CENSUS_SCHEMA
AUTHORITY_SCHEMA = _core.AUTHORITY_SCHEMA
TARGET_BINDING_SCHEMA = _core.TARGET_BINDING_SCHEMA
TRANSFER_SCHEMA = _core.TRANSFER_SCHEMA
RECEIPT_SCHEMA = "outbound-provider-relationship-custody-receipt/v2"
LIVE_POLICY_SCHEMA = "outbound-provider-relationship-currentness-policy/v1"
LIVE_POLICY_ID = "process-utc-fixed-900-300-v1"
DEFAULT_MAX_SNAPSHOT_AGE_SECONDS = 900
DEFAULT_MAX_FUTURE_SKEW_SECONDS = 300
MAX_ROUTES = _core.MAX_ROUTES
MAX_BYTES = _core.MAX_BYTES
RELATIONSHIP_STATES = _core.RELATIONSHIP_STATES
OWNER_REQUIRED_STATES = _core.OWNER_REQUIRED_STATES
NON_REUSABLE_STATES = frozenset(
    {
        "WAITING_REPLY",
        "INBOUND_NEEDS_OWNER",
        "UNSUBSCRIBED",
        "DNR",
        "HARD_BOUNCE",
        "TRANSFER_PENDING",
        "CLOSED",
    }
)

CensusError = _core.CensusError
DuplicateKeyError = _core.DuplicateKeyError
canonical_bytes = _core.canonical_bytes
digest_object = _core.digest_object
parse_json_bytes = _core.parse_json_bytes
target_binding_sha256 = _core.target_binding_sha256
route_set_sha256 = _core.route_set_sha256
signing_material = _core.signing_material
compute_signature = _core.compute_signature
_normalize = _core._normalize
_atomic_publish_new = _core._atomic_publish_new
_read_exact_once = _core._read_exact_once
_aliases = _core._aliases


def _authority_valid(normalized: Mapping[str, Any], key: bytes) -> bool:
    return _core._authority_valid(normalized, key)


def _fmt(value: datetime) -> str:
    return _core._fmt(value)


def _semantic_reasons(
    normalized: Mapping[str, Any], *, key: bytes, now: datetime
) -> list[str]:
    """Reuse v1 semantic checks under fixed policy, then close lifecycle gaps."""
    reasons = list(
        _core._semantic_reasons(
            normalized,
            key=key,
            now=now,
            max_snapshot_age_seconds=DEFAULT_MAX_SNAPSHOT_AGE_SECONDS,
            max_future_skew_seconds=DEFAULT_MAX_FUTURE_SKEW_SECONDS,
        )
    )
    census = normalized["census"]
    relationship = census["relationship"]
    state = relationship["state"]
    if state in NON_REUSABLE_STATES:
        reasons.append(f"RELATIONSHIP_STATE_BLOCKED:{state}")
    for row in census["route_observations"]:
        if row["state"] in NON_REUSABLE_STATES:
            reasons.append(
                f"ROUTE_STATE_BLOCKED:{row['route_sha256'][:12]}:{row['state']}"
            )
    return sorted(set(reasons))


def _currentness_policy(clock_source: str) -> dict[str, Any]:
    return {
        "schema_version": LIVE_POLICY_SCHEMA,
        "policy_id": LIVE_POLICY_ID,
        "clock_source": clock_source,
        "max_snapshot_age_seconds": DEFAULT_MAX_SNAPSHOT_AGE_SECONDS,
        "max_future_skew_seconds": DEFAULT_MAX_FUTURE_SKEW_SECONDS,
    }


def _evaluate_at(
    raw: dict[str, Any],
    *,
    provider_hmac_key: bytes,
    now: datetime,
    source_sha256: str | None = None,
    historical_replay: bool = True,
) -> dict[str, Any]:
    """Private deterministic replay.  Its receipt is never current authority."""
    normalized = _normalize(_core._dict(raw, "census input"))
    key = provider_hmac_key
    if type(key) is not bytes or len(key) < 32:
        raise CensusError("integrity HMAC key must contain at least 32 bytes")
    if now.tzinfo is None or now.utcoffset() is None:
        raise CensusError("historical now must include a timezone")
    evaluated_at = now.astimezone(timezone.utc)
    semantic_reasons = _semantic_reasons(normalized, key=key, now=evaluated_at)
    relationship = normalized["census"]["relationship"]
    if semantic_reasons:
        projected_custody = "UNPROVEN"
    elif relationship["state"] == "CLEAR":
        projected_custody = "CUSTODY_CLEAR"
    else:
        projected_custody = "CURRENT_OWNER"

    reasons = list(semantic_reasons)
    reasons.append("PROVIDER_ORIGIN_UNATTESTED")
    if historical_replay:
        reasons.append("HISTORICAL_REPLAY_NOT_LIVE_AUTHORITY")
    reasons = sorted(set(reasons))

    transfer = normalized["census"]["transfer"]
    payload = {
        "schema_version": RECEIPT_SCHEMA,
        "target_scope": normalized["target_scope"],
        "target_route_set_sha256": route_set_sha256(
            normalized["target_scope"], normalized["route_sha256s"]
        ),
        "route_sha256s": normalized["route_sha256s"],
        "provider": normalized["census"]["provider"],
        "workspace_sha256": normalized["census"]["workspace_sha256"],
        "snapshot_id": normalized["census"]["snapshot_id"],
        "snapshot_at": normalized["census"]["snapshot_at"],
        "coverage_started_at": normalized["census"]["coverage_started_at"],
        "evaluated_at": _fmt(evaluated_at),
        "currentness_policy": _currentness_policy(
            "historical_replay_argument" if historical_replay else "process_utc"
        ),
        "current_worker": normalized["current_worker"],
        "claimed_generation": normalized["claimed_generation"],
        "relationship": relationship,
        "decision": "HOLD",
        "projected_custody": projected_custody,
        "reasons": reasons,
        "integrity_hmac_valid": _authority_valid(normalized, key),
        "integrity_key_id": normalized["authority"]["key_id"],
        "authority_scope": "SUPPLIED_SECRET_INTEGRITY_ONLY",
        "provider_origin_attested": False,
        "current_authority": False,
        "provider_census_object_sha256": digest_object(normalized["census"]),
        "authority_material_sha256": digest_object(signing_material(normalized)),
        "source_exact_bytes_sha256": source_sha256,
        "transfer_receipt_sha256": digest_object(transfer) if transfer is not None else None,
        "requires_provider_origin_attestation": True,
        "requires_route_lifecycle_gate": True,
        "requires_outbound_send_guard": True,
        "requires_atomic_send_lease": True,
        "external_send_authorized": False,
        "side_effects_authorized": False,
    }
    return {"payload": payload, "receipt_sha256": digest_object(payload)}


def evaluate(raw: dict[str, Any], *, provider_hmac_key: bytes) -> dict[str, Any]:
    """Live object surface: process UTC, fixed freshness, no exact-byte claim."""
    return _evaluate_at(
        raw,
        provider_hmac_key=provider_hmac_key,
        now=datetime.now(timezone.utc),
        source_sha256=None,
        historical_replay=False,
    )


def evaluate_bytes(raw: bytes, *, provider_hmac_key: bytes) -> dict[str, Any]:
    """Live exact-byte surface; digest is computed by this function, never caller-supplied."""
    parsed = parse_json_bytes(raw)
    return _evaluate_at(
        parsed,
        provider_hmac_key=provider_hmac_key,
        now=datetime.now(timezone.utc),
        source_sha256=hashlib.sha256(raw).hexdigest(),
        historical_replay=False,
    )


def _key_from_env() -> bytes:
    value = os.environ.get("OUTBOUND_RELATIONSHIP_CENSUS_HMAC_KEY_HEX")
    if value is None:
        raise CensusError(
            "OUTBOUND_RELATIONSHIP_CENSUS_HMAC_KEY_HEX is required for integrity checking"
        )
    try:
        key = bytes.fromhex(value)
    except ValueError as exc:
        raise CensusError("OUTBOUND_RELATIONSHIP_CENSUS_HMAC_KEY_HEX must be hex") from exc
    if len(key) < 32:
        raise CensusError(
            "OUTBOUND_RELATIONSHIP_CENSUS_HMAC_KEY_HEX must decode to at least 32 bytes"
        )
    return key


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Fail-closed provider relationship census integrity projection"
    )
    parser.add_argument("--census", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        if _aliases(args.census, args.out):
            raise CensusError("output must not alias census input")
        raw = _read_exact_once(args.census)
        receipt = evaluate_bytes(raw, provider_hmac_key=_key_from_env())
        encoded = (
            json.dumps(receipt, ensure_ascii=False, sort_keys=True, indent=2).encode("utf-8")
            + b"\n"
        )
        _atomic_publish_new(args.out, encoded)
        return 4
    except CensusError as exc:
        print(f"outbound-relationship-census: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
