"""Fail-closed historical relationship custody census.

This module never authorizes an external send.  It verifies an authority-signed,
target-bound provider-history census and projects whether the current worker is
clear/holds the relationship custody generation.  Downstream outbound dedupe,
content, route, DNR and atomic lease gates remain mandatory.
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import math
import os
import re
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

REQUEST_SCHEMA = "relationship-census-request/v1"
CENSUS_SCHEMA = "relationship-census/v1"
TRANSFER_SCHEMA = "relationship-transfer/v1"
RECEIPT_SCHEMA = "relationship-census-receipt/v1"

STATES = frozenset({
    "UNSEEN", "ACTIVE_OWNER", "WAITING_REPLY", "INBOUND_NEEDS_OWNER",
    "DNR", "HARD_BOUNCE", "TRANSFER_PENDING", "TRANSFERRED", "CLOSED",
})
EVENT_KINDS = frozenset({"NONE", "SENT", "RECEIVED", "AUTO_REPLY", "HARD_BOUNCE", "UNSUBSCRIBE"})
_MACHINE_RE = re.compile(r"^[a-z0-9][a-z0-9._:@/+\-]{2,191}$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class CensusError(ValueError):
    pass


def _pairs_no_dupes(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise CensusError(f"duplicate JSON key: {key}")
        out[key] = value
    return out


def _reject_constant(value: str) -> None:
    raise CensusError(f"non-finite JSON number forbidden: {value}")


def strict_loads(raw: bytes) -> Any:
    if not isinstance(raw, bytes):
        raise CensusError("strict_loads requires bytes")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise CensusError("input must be UTF-8") from exc
    try:
        return json.loads(text, object_pairs_hook=_pairs_no_dupes, parse_constant=_reject_constant)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise CensusError("invalid JSON") from exc


def _canon(value: Any) -> bytes:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("ascii")
    except (TypeError, ValueError) as exc:
        raise CensusError("value is not canonical-JSON serializable") from exc


def _sha(value: Any) -> str:
    return hashlib.sha256(_canon(value)).hexdigest()


def _raw_sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _exact_fields(raw: Mapping[str, Any], expected: set[str], field: str) -> None:
    if not isinstance(raw, Mapping) or set(raw) != expected:
        raise CensusError(f"{field}: exact fields required")


def _machine(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.isascii() or value != value.casefold() or _MACHINE_RE.fullmatch(value) is None:
        raise CensusError(f"{field}: lowercase ASCII machine token required")
    return value


def _display(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.isascii() or not (3 <= len(value) <= 192):
        raise CensusError(f"{field}: 3..192 ASCII chars required")
    if any(ord(ch) < 0x20 or ch == "\x7f" for ch in value):
        raise CensusError(f"{field}: control characters forbidden")
    return value


def _sha256(value: Any, field: str) -> str:
    if not isinstance(value, str) or _SHA256_RE.fullmatch(value) is None:
        raise CensusError(f"{field}: 64 lowercase hex chars required")
    return value


def _timestamp(value: Any, field: str) -> tuple[str, datetime]:
    if not isinstance(value, str) or not value:
        raise CensusError(f"{field}: RFC3339 timestamp required")
    raw = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        dt = datetime.fromisoformat(raw)
    except ValueError as exc:
        raise CensusError(f"{field}: invalid RFC3339 timestamp") from exc
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise CensusError(f"{field}: timezone required")
    utc = dt.astimezone(timezone.utc)
    return utc.isoformat().replace("+00:00", "Z"), utc


def _positive_int(value: Any, field: str, *, minimum: int = 1) -> int:
    if type(value) is not int or value < minimum:
        raise CensusError(f"{field}: integer >= {minimum} required")
    return value


def _optional_owner(value: Any, field: str) -> str | None:
    return None if value is None else _display(value, field)


def _secret(key: Any) -> bytes:
    if not isinstance(key, (bytes, bytearray)):
        raise CensusError("authority key must be bytes")
    out = bytes(key)
    if len(out) < 32:
        raise CensusError("authority key must contain at least 32 bytes")
    return out


def _owner_hash(owner: str | None) -> str | None:
    return None if owner is None else hashlib.sha256(owner.encode("ascii")).hexdigest()


def _parse_request(raw: Mapping[str, Any]) -> dict[str, Any]:
    expected = {"schema", "target_scope", "current_worker", "as_of", "max_snapshot_age_seconds", "coverage_required_from", "expected_provider", "expected_key_id", "route_sha256"}
    _exact_fields(raw, expected, "request")
    if raw["schema"] != REQUEST_SCHEMA:
        raise CensusError("request: unsupported schema")
    target_scope = _machine(raw["target_scope"], "request.target_scope")
    worker = _display(raw["current_worker"], "request.current_worker")
    as_of_s, as_of = _timestamp(raw["as_of"], "request.as_of")
    max_age = _positive_int(raw["max_snapshot_age_seconds"], "request.max_snapshot_age_seconds")
    coverage_s, coverage = _timestamp(raw["coverage_required_from"], "request.coverage_required_from")
    provider = _machine(raw["expected_provider"], "request.expected_provider")
    key_id = _machine(raw["expected_key_id"], "request.expected_key_id")
    routes_raw = raw["route_sha256"]
    if not isinstance(routes_raw, list) or not routes_raw:
        raise CensusError("request.route_sha256: non-empty list required")
    routes = [_sha256(item, "request.route_sha256[]") for item in routes_raw]
    if len(routes) != len(set(routes)):
        raise CensusError("request.route_sha256: duplicates forbidden")
    if coverage > as_of:
        raise CensusError("request: coverage_required_from after as_of")
    return {"schema": REQUEST_SCHEMA, "target_scope": target_scope, "current_worker": worker, "as_of": as_of_s, "as_of_dt": as_of, "max_age": max_age, "coverage_required_from": coverage_s, "coverage_dt": coverage, "provider": provider, "key_id": key_id, "routes": tuple(sorted(routes))}


def _parse_transfer(raw: Any) -> dict[str, Any] | None:
    if raw is None:
        return None
    expected = {"schema", "target_scope", "transfer_id", "from_owner", "to_owner", "from_generation", "to_generation", "release_actor", "release_role", "released_at", "accepted_by", "accepted_at"}
    _exact_fields(raw, expected, "transfer")
    if raw["schema"] != TRANSFER_SCHEMA:
        raise CensusError("transfer: unsupported schema")
    role = raw["release_role"]
    if role not in {"owner", "admin"}:
        raise CensusError("transfer.release_role: owner|admin required")
    released_s, released = _timestamp(raw["released_at"], "transfer.released_at")
    accepted_s, accepted = _timestamp(raw["accepted_at"], "transfer.accepted_at")
    result = {
        "schema": TRANSFER_SCHEMA,
        "target_scope": _machine(raw["target_scope"], "transfer.target_scope"),
        "transfer_id": _machine(raw["transfer_id"], "transfer.transfer_id"),
        "from_owner": _display(raw["from_owner"], "transfer.from_owner"),
        "to_owner": _display(raw["to_owner"], "transfer.to_owner"),
        "from_generation": _positive_int(raw["from_generation"], "transfer.from_generation"),
        "to_generation": _positive_int(raw["to_generation"], "transfer.to_generation"),
        "release_actor": _display(raw["release_actor"], "transfer.release_actor"),
        "release_role": role,
        "released_at": released_s,
        "released_dt": released,
        "accepted_by": _display(raw["accepted_by"], "transfer.accepted_by"),
        "accepted_at": accepted_s,
        "accepted_dt": accepted,
    }
    return result


def _parse_census(raw: Mapping[str, Any]) -> dict[str, Any]:
    expected = {"schema", "target_scope", "provider", "snapshot_id", "snapshot_at", "coverage_started_at", "complete", "relationship", "routes", "transfer", "attestation"}
    _exact_fields(raw, expected, "census")
    if raw["schema"] != CENSUS_SCHEMA:
        raise CensusError("census: unsupported schema")
    snapshot_s, snapshot = _timestamp(raw["snapshot_at"], "census.snapshot_at")
    coverage_s, coverage = _timestamp(raw["coverage_started_at"], "census.coverage_started_at")
    if type(raw["complete"]) is not bool:
        raise CensusError("census.complete: bool required")

    relationship = raw["relationship"]
    _exact_fields(relationship, {"state", "owner", "generation"}, "census.relationship")
    state = relationship["state"]
    if state not in STATES:
        raise CensusError("census.relationship.state: unsupported")
    owner = _optional_owner(relationship["owner"], "census.relationship.owner")
    generation = raw_generation = relationship["generation"]
    if type(raw_generation) is not int or raw_generation < 0:
        raise CensusError("census.relationship.generation: integer >= 0 required")
    if state == "UNSEEN" and (owner is not None or generation != 0):
        raise CensusError("UNSEEN requires null owner and generation 0")
    if state != "UNSEEN" and state not in {"DNR", "HARD_BOUNCE", "CLOSED"} and owner is None:
        raise CensusError(f"{state} requires owner")

    routes_raw = raw["routes"]
    if not isinstance(routes_raw, list) or not routes_raw:
        raise CensusError("census.routes: non-empty list required")
    routes: list[dict[str, Any]] = []
    seen_routes: set[str] = set()
    for index, item in enumerate(routes_raw):
        _exact_fields(item, {"target_scope", "route_sha256", "event_kind", "event_at", "provider_record_sha256", "owner", "owner_generation"}, f"census.routes[{index}]")
        route = _sha256(item["route_sha256"], f"census.routes[{index}].route_sha256")
        if route in seen_routes:
            raise CensusError("census.routes: duplicate route")
        seen_routes.add(route)
        kind = item["event_kind"]
        if kind not in EVENT_KINDS:
            raise CensusError(f"census.routes[{index}].event_kind: unsupported")
        if kind == "NONE":
            if item["event_at"] is not None or item["provider_record_sha256"] is not None or item["owner"] is not None or item["owner_generation"] != 0:
                raise CensusError("NONE route must not carry historical event/owner fields")
            event_s = None
            event_dt = None
            record = None
            route_owner = None
            route_generation = 0
        else:
            event_s, event_dt = _timestamp(item["event_at"], f"census.routes[{index}].event_at")
            record = _sha256(item["provider_record_sha256"], f"census.routes[{index}].provider_record_sha256")
            route_owner = _optional_owner(item["owner"], f"census.routes[{index}].owner")
            if type(item["owner_generation"]) is not int or item["owner_generation"] < 0:
                raise CensusError(f"census.routes[{index}].owner_generation: integer >= 0 required")
            route_generation = item["owner_generation"]
        routes.append({"target_scope": _machine(item["target_scope"], f"census.routes[{index}].target_scope"), "route_sha256": route, "event_kind": kind, "event_at": event_s, "event_dt": event_dt, "provider_record_sha256": record, "owner": route_owner, "owner_generation": route_generation})

    transfer = _parse_transfer(raw["transfer"])
    att = raw["attestation"]
    _exact_fields(att, {"key_id", "hmac_sha256"}, "census.attestation")

    return {
        "schema": CENSUS_SCHEMA,
        "target_scope": _machine(raw["target_scope"], "census.target_scope"),
        "provider": _machine(raw["provider"], "census.provider"),
        "snapshot_id": _machine(raw["snapshot_id"], "census.snapshot_id"),
        "snapshot_at": snapshot_s,
        "snapshot_dt": snapshot,
        "coverage_started_at": coverage_s,
        "coverage_dt": coverage,
        "complete": raw["complete"],
        "relationship": {"state": state, "owner": owner, "generation": generation},
        "routes": routes,
        "transfer": transfer,
        "attestation": {"key_id": _machine(att["key_id"], "census.attestation.key_id"), "hmac_sha256": _sha256(att["hmac_sha256"], "census.attestation.hmac_sha256")},
    }


def _census_signed_core(raw: Mapping[str, Any]) -> dict[str, Any]:
    core = dict(raw)
    core.pop("attestation", None)
    return core


def sign_census(census_without_attestation: Mapping[str, Any], key: bytes, key_id: str) -> dict[str, Any]:
    """Test/export-boundary helper: return a copy with an HMAC authority attestation."""
    secret = _secret(key)
    kid = _machine(key_id, "key_id")
    if "attestation" in census_without_attestation:
        raise CensusError("sign_census expects census without attestation")
    candidate = dict(census_without_attestation)
    candidate["attestation"] = {"key_id": kid, "hmac_sha256": "0" * 64}
    _parse_census(candidate)
    signature = hmac.new(secret, _canon(census_without_attestation), hashlib.sha256).hexdigest()
    candidate["attestation"] = {"key_id": kid, "hmac_sha256": signature}
    return candidate


def _validate_transfer(transfer: dict[str, Any] | None, *, census_target: str, relationship: dict[str, Any], snapshot_dt: datetime) -> tuple[bool, str]:
    if relationship["state"] == "TRANSFERRED":
        if transfer is None:
            return False, "TRANSFER_PROOF_MISSING"
        if transfer["target_scope"] != census_target:
            return False, "TRANSFER_TARGET_MISMATCH"
        if transfer["from_owner"] == transfer["to_owner"]:
            return False, "TRANSFER_OWNER_NOT_CHANGED"
        if transfer["to_generation"] != transfer["from_generation"] + 1:
            return False, "TRANSFER_GENERATION_NOT_INCREMENTED"
        if transfer["to_owner"] != relationship["owner"] or transfer["to_generation"] != relationship["generation"]:
            return False, "TRANSFER_CURRENT_RELATIONSHIP_MISMATCH"
        if transfer["release_role"] == "owner" and transfer["release_actor"] != transfer["from_owner"]:
            return False, "TRANSFER_RELEASE_NOT_PRIOR_OWNER"
        if transfer["accepted_by"] != transfer["to_owner"]:
            return False, "TRANSFER_ACCEPTANCE_NOT_NEW_OWNER"
        if transfer["released_dt"] > transfer["accepted_dt"] or transfer["accepted_dt"] > snapshot_dt:
            return False, "TRANSFER_CHRONOLOGY_INVALID"
        return True, "TRANSFER_VALID"
    if transfer is not None:
        return False, "UNEXPECTED_TRANSFER_PROOF"
    return True, "NO_TRANSFER_REQUIRED"


def evaluate(request_raw: Mapping[str, Any], census_raw: Mapping[str, Any], authority_key: bytes, *, byte_custody: Mapping[str, str] | None = None) -> dict[str, Any]:
    request = _parse_request(request_raw)
    census = _parse_census(census_raw)
    secret = _secret(authority_key)

    decision = "HOLD"
    reason = "UNSET"
    attestation_valid = False

    if census["attestation"]["key_id"] != request["key_id"]:
        reason = "ATTESTATION_KEY_ID_MISMATCH"
    else:
        expected_hmac = hmac.new(secret, _canon(_census_signed_core(census_raw)), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected_hmac, census["attestation"]["hmac_sha256"]):
            reason = "ATTESTATION_INVALID"
        else:
            attestation_valid = True
            if census["provider"] != request["provider"]:
                reason = "PROVIDER_MISMATCH"
            elif census["target_scope"] != request["target_scope"]:
                reason = "TARGET_SCOPE_MISMATCH"
            elif any(row["target_scope"] != request["target_scope"] for row in census["routes"]):
                reason = "CROSS_TARGET_ROUTE_TRANSPLANT"
            elif not census["complete"]:
                reason = "CENSUS_INCOMPLETE"
            elif census["snapshot_dt"] > request["as_of_dt"]:
                reason = "CENSUS_FROM_FUTURE"
            elif (request["as_of_dt"] - census["snapshot_dt"]).total_seconds() > request["max_age"]:
                reason = "CENSUS_STALE"
            elif census["coverage_dt"] > request["coverage_dt"]:
                reason = "COVERAGE_TOO_SHALLOW"
            elif census["coverage_dt"] > census["snapshot_dt"]:
                reason = "COVERAGE_AFTER_SNAPSHOT"
            elif any(row["event_dt"] is not None and row["event_dt"] > census["snapshot_dt"] for row in census["routes"]):
                reason = "ROUTE_EVENT_AFTER_SNAPSHOT"
            else:
                observed_routes = {row["route_sha256"] for row in census["routes"]}
                if not set(request["routes"]).issubset(observed_routes):
                    reason = "REQUESTED_ROUTE_NOT_COVERED"
                else:
                    transfer_ok, transfer_reason = _validate_transfer(census["transfer"], census_target=census["target_scope"], relationship=census["relationship"], snapshot_dt=census["snapshot_dt"])
                    if not transfer_ok:
                        reason = transfer_reason
                    else:
                        state = census["relationship"]["state"]
                        owner = census["relationship"]["owner"]
                        if state == "UNSEEN":
                            if any(row["event_kind"] != "NONE" for row in census["routes"]):
                                reason = "UNSEEN_CONTRADICTS_HISTORY"
                            else:
                                decision = "CUSTODY_CLEAR"
                                reason = "NO_PRIOR_RELATIONSHIP"
                        elif state in {"DNR", "HARD_BOUNCE"}:
                            reason = state
                        elif state in {"TRANSFER_PENDING", "CLOSED"}:
                            reason = state
                        elif owner != request["current_worker"]:
                            reason = "OWNED_BY_OTHER"
                        elif state in {"ACTIVE_OWNER", "WAITING_REPLY", "INBOUND_NEEDS_OWNER", "TRANSFERRED"}:
                            if census["relationship"]["generation"] < 1:
                                reason = "OWNER_GENERATION_INVALID"
                            elif any(row["owner"] not in {None, owner} for row in census["routes"]):
                                reason = "ROUTE_OWNER_CONFLICT"
                            elif any(row["owner_generation"] > census["relationship"]["generation"] for row in census["routes"]):
                                reason = "ROUTE_GENERATION_AHEAD"
                            else:
                                decision = "CUSTODY_HELD"
                                reason = transfer_reason if state == "TRANSFERRED" else "CURRENT_OWNER_MATCH"
                        else:
                            reason = "STATE_FAIL_CLOSED"

    receipt: dict[str, Any] = {
        "schema": RECEIPT_SCHEMA,
        "target_scope": request["target_scope"],
        "provider": request["provider"],
        "snapshot_id_sha256": hashlib.sha256(census["snapshot_id"].encode("ascii")).hexdigest(),
        "snapshot_at": census["snapshot_at"],
        "request_object_sha256": _sha(request_raw),
        "census_object_sha256": _sha(census_raw),
        "covered_route_sha256": list(request["routes"]),
        "relationship_state": census["relationship"]["state"],
        "relationship_generation": census["relationship"]["generation"],
        "relationship_owner_sha256": _owner_hash(census["relationship"]["owner"]),
        "current_worker_sha256": _owner_hash(request["current_worker"]),
        "authority_key_id": request["key_id"],
        "attestation_valid": attestation_valid,
        "decision": decision,
        "reason": reason,
        "external_send_authorized": False,
        "byte_custody": dict(byte_custody) if byte_custody is not None else None,
    }
    receipt["receipt_sha256"] = _sha(receipt)
    return receipt


def evaluate_bytes(request_bytes: bytes, census_bytes: bytes, authority_key: bytes) -> dict[str, Any]:
    request = strict_loads(request_bytes)
    census = strict_loads(census_bytes)
    if not isinstance(request, Mapping) or not isinstance(census, Mapping):
        raise CensusError("request and census must be JSON objects")
    return evaluate(request, census, authority_key, byte_custody={"request_sha256": _raw_sha(request_bytes), "census_sha256": _raw_sha(census_bytes)})


def verify_receipt(raw: Mapping[str, Any]) -> bool:
    expected = {"schema", "target_scope", "provider", "snapshot_id_sha256", "snapshot_at", "request_object_sha256", "census_object_sha256", "covered_route_sha256", "relationship_state", "relationship_generation", "relationship_owner_sha256", "current_worker_sha256", "authority_key_id", "attestation_valid", "decision", "reason", "external_send_authorized", "byte_custody", "receipt_sha256"}
    _exact_fields(raw, expected, "receipt")
    if raw["schema"] != RECEIPT_SCHEMA:
        raise CensusError("receipt: unsupported schema")
    _machine(raw["target_scope"], "receipt.target_scope")
    _machine(raw["provider"], "receipt.provider")
    _sha256(raw["snapshot_id_sha256"], "receipt.snapshot_id_sha256")
    _timestamp(raw["snapshot_at"], "receipt.snapshot_at")
    _sha256(raw["request_object_sha256"], "receipt.request_object_sha256")
    _sha256(raw["census_object_sha256"], "receipt.census_object_sha256")
    if not isinstance(raw["covered_route_sha256"], list) or not raw["covered_route_sha256"]:
        raise CensusError("receipt.covered_route_sha256: non-empty list required")
    routes = [_sha256(v, "receipt.covered_route_sha256[]") for v in raw["covered_route_sha256"]]
    if routes != sorted(routes) or len(routes) != len(set(routes)):
        raise CensusError("receipt.covered_route_sha256: unique sorted list required")
    if raw["relationship_state"] not in STATES:
        raise CensusError("receipt.relationship_state: unsupported")
    if type(raw["relationship_generation"]) is not int or raw["relationship_generation"] < 0:
        raise CensusError("receipt.relationship_generation: integer >= 0 required")
    for field in ("relationship_owner_sha256", "current_worker_sha256"):
        if raw[field] is not None:
            _sha256(raw[field], f"receipt.{field}")
    _machine(raw["authority_key_id"], "receipt.authority_key_id")
    if type(raw["attestation_valid"]) is not bool:
        raise CensusError("receipt.attestation_valid: bool required")
    if raw["decision"] not in {"CUSTODY_CLEAR", "CUSTODY_HELD", "HOLD"}:
        raise CensusError("receipt.decision: unsupported")
    if not isinstance(raw["reason"], str) or not raw["reason"]:
        raise CensusError("receipt.reason required")
    if raw["external_send_authorized"] is not False:
        raise CensusError("receipt may never authorize an external send")
    custody = raw["byte_custody"]
    if custody is not None:
        _exact_fields(custody, {"request_sha256", "census_sha256"}, "receipt.byte_custody")
        _sha256(custody["request_sha256"], "receipt.byte_custody.request_sha256")
        _sha256(custody["census_sha256"], "receipt.byte_custody.census_sha256")
    digest = _sha256(raw["receipt_sha256"], "receipt.receipt_sha256")
    material = dict(raw)
    del material["receipt_sha256"]
    if _sha(material) != digest:
        raise CensusError("receipt: digest mismatch")
    if raw["decision"] != "HOLD" and not raw["attestation_valid"]:
        raise CensusError("receipt: non-HOLD decision requires valid attestation")
    return True


def _atomic_write(path: Path, payload: bytes) -> None:
    parent = path.parent
    parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(parent))
    try:
        with os.fdopen(fd, "wb", closefd=True) as fh:
            fh.write(payload)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp_name, path)
        if os.name == "posix":
            dfd = os.open(parent, os.O_RDONLY)
            try:
                os.fsync(dfd)
            finally:
                os.close(dfd)
    except Exception:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Evaluate target-bound provider relationship custody")
    parser.add_argument("--request", required=True)
    parser.add_argument("--census", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--key-env", default="RELATIONSHIP_CENSUS_KEY")
    args = parser.parse_args(argv)
    paths = [Path(args.request).resolve(), Path(args.census).resolve(), Path(args.out).resolve()]
    try:
        if len(set(paths)) != 3:
            raise CensusError("request, census and output paths must be distinct")
        request_bytes = Path(args.request).read_bytes()
        census_bytes = Path(args.census).read_bytes()
        key_text = os.environ.get(args.key_env, "")
        if not key_text:
            raise CensusError(f"authority key environment variable {args.key_env} is required")
        key = key_text.encode("utf-8")
        receipt = evaluate_bytes(request_bytes, census_bytes, key)
        verify_receipt(receipt)
        _atomic_write(Path(args.out), _canon(receipt) + b"\n")
    except (OSError, CensusError) as exc:
        print(f"HOLD: {exc}", file=sys.stderr)
        return 2
    print(receipt["decision"])
    return 0 if receipt["decision"] in {"CUSTODY_CLEAR", "CUSTODY_HELD"} else 4


if __name__ == "__main__":
    raise SystemExit(main())
