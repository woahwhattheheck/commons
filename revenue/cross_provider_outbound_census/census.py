"""Deterministic PII-free cross-provider outbound census gate.

This module is deliberately not send authority.  It answers whether all registered
provider/fallback routes for one opaque logical outbound opportunity have fresh,
complete collision-history coverage.  Any incomplete provider census, prior touch,
suppression, or route-failure evidence holds before the existing Commons lease and
send-authority gates are consulted.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from revenue.outbound_connector_lease.key import (
    LeaseKeyError,
    SUPPORTED_REPLY_PROVIDERS,
    compile_document as compile_lease_document,
)

INPUT_SCHEMA = "commons-cross-provider-outbound-census/input-v1"
PACKET_SCHEMA = "commons-cross-provider-outbound-census/packet-v1"
MAX_SAFE_INTEGER = (1 << 53) - 1
MAX_ROWS = 100_000
MAX_SNAPSHOT_AGE_SECONDS = 300
MAX_INTENT_AGE_SECONDS = 300
SCOPE_RE = re.compile(r"^[a-z0-9][a-z0-9._:/#-]{2,160}$")
SHA_RE = re.compile(r"^[0-9a-f]{64}$")
UTC_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
SNAPSHOT_STATES = {"COMPLETE", "THROTTLED", "UNAVAILABLE", "AMBIGUOUS"}
EVENTS = {
    "PROVIDER_SENT",
    "HUMAN_REPLY",
    "AUTO_REPLY",
    "HARD_BOUNCE",
    "SOFT_BOUNCE",
    "PROVIDER_REJECTED",
    "UNSUBSCRIBE",
    "DNR",
    "AMBIGUOUS_EFFECT",
}


class CensusError(ValueError):
    pass


def _walk(value: Any, depth: int = 0) -> None:
    if depth > 40:
        raise CensusError("JSON graph exceeds maximum nesting depth")
    t = type(value)
    if value is None or t in (str, bool):
        return
    if t is int:
        if abs(value) > MAX_SAFE_INTEGER:
            raise CensusError("integer exceeds safe interoperability range")
        return
    if t is float:
        if not math.isfinite(value):
            raise CensusError("non-finite number forbidden")
        return
    if t is list:
        if len(value) > MAX_ROWS:
            raise CensusError("array exceeds row limit")
        for item in value:
            _walk(item, depth + 1)
        return
    if t is dict:
        if len(value) > MAX_ROWS:
            raise CensusError("object exceeds member limit")
        for key, item in value.items():
            if type(key) is not str:
                raise CensusError("object key must be built-in string")
            _walk(item, depth + 1)
        return
    raise CensusError("input must be an inert built-in JSON graph")


def _canonical_bytes(value: Any) -> bytes:
    _walk(value)
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                          allow_nan=False).encode("utf-8")
    except (TypeError, ValueError, OverflowError) as exc:
        raise CensusError("value is not canonical JSON") from exc


def _snapshot(value: Any) -> Any:
    return json.loads(_canonical_bytes(value).decode("utf-8"))


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _exact_keys(value: Any, expected: set[str], where: str) -> None:
    if type(value) is not dict:
        raise CensusError(f"{where} must be an object")
    actual = set(value)
    if actual != expected:
        raise CensusError(
            f"{where} fields differ: missing={sorted(expected-actual)} extra={sorted(actual-expected)}"
        )


def _scope(value: Any, where: str) -> str:
    if type(value) is not str or not SCOPE_RE.fullmatch(value):
        raise CensusError(f"{where} must be a lower-case opaque scope id")
    return value


def _sha(value: Any, where: str) -> str:
    if type(value) is not str or not SHA_RE.fullmatch(value):
        raise CensusError(f"{where} must be lowercase sha256")
    return value


def _utc(value: Any, where: str) -> datetime:
    if type(value) is not str or not UTC_RE.fullmatch(value):
        raise CensusError(f"{where} must be canonical whole-second UTC ending Z")
    try:
        dt = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise CensusError(f"{where} is not a real UTC instant") from exc
    if dt.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ") != value:
        raise CensusError(f"{where} must be canonical whole-second UTC")
    return dt


def _provider(value: Any, where: str) -> str:
    if type(value) is not str or value not in SUPPORTED_REPLY_PROVIDERS:
        raise CensusError(f"{where} unsupported provider")
    return value


def _epoch(dt: datetime) -> int:
    delta = dt.astimezone(UTC) - datetime(1970, 1, 1, tzinfo=UTC)
    return delta.days * 86400 + delta.seconds


def _normalize(raw: Any) -> dict[str, Any]:
    value = _snapshot(raw)
    _exact_keys(
        value,
        {"schema", "lease_input", "intent", "aliases", "snapshots"},
        "input",
    )
    if value["schema"] != INPUT_SCHEMA:
        raise CensusError("unsupported input schema")
    lease_input = value["lease_input"]
    try:
        lease_key = compile_lease_document(lease_input)
    except LeaseKeyError as exc:
        raise CensusError(f"invalid canonical outbound lease input: {exc}") from exc
    lease_input = {
        "schema": lease_key["schema"],
        "buyer_scope": lease_key["buyer_scope"],
        "opportunity": lease_key["opportunity"],
    }

    intent = value["intent"]
    _exact_keys(intent, {"provider", "route_sha256", "claimant_scope", "claim_scope", "requested_at"}, "intent")
    intent = {
        "provider": _provider(intent["provider"], "intent.provider"),
        "route_sha256": _sha(intent["route_sha256"], "intent.route_sha256"),
        "claimant_scope": _scope(intent["claimant_scope"], "intent.claimant_scope"),
        "claim_scope": _scope(intent["claim_scope"], "intent.claim_scope"),
        "requested_at": intent["requested_at"],
    }
    _utc(intent["requested_at"], "intent.requested_at")

    aliases_raw = value["aliases"]
    if type(aliases_raw) is not list or not aliases_raw:
        raise CensusError("aliases must be a non-empty array")
    aliases: list[dict[str, str]] = []
    alias_keys: set[tuple[str, str]] = set()
    for idx, alias in enumerate(aliases_raw):
        where = f"aliases[{idx}]"
        _exact_keys(alias, {"provider", "route_sha256"}, where)
        normalized = {
            "provider": _provider(alias["provider"], f"{where}.provider"),
            "route_sha256": _sha(alias["route_sha256"], f"{where}.route_sha256"),
        }
        key = (normalized["provider"], normalized["route_sha256"])
        if key in alias_keys:
            raise CensusError("duplicate provider route alias")
        alias_keys.add(key)
        aliases.append(normalized)
    aliases.sort(key=lambda row: (row["provider"], row["route_sha256"]))

    required_providers = {provider for provider, _ in alias_keys}

    snapshots_raw = value["snapshots"]
    if type(snapshots_raw) is not list:
        raise CensusError("snapshots must be an array")
    snapshots: list[dict[str, Any]] = []
    seen_providers: set[str] = set()
    for idx, snap in enumerate(snapshots_raw):
        where = f"snapshots[{idx}]"
        _exact_keys(snap, {"provider", "status", "observed_at", "query_sha256", "covered_routes", "events"}, where)
        provider = _provider(snap["provider"], f"{where}.provider")
        if provider in seen_providers:
            raise CensusError("duplicate provider snapshot")
        if provider not in required_providers:
            raise CensusError("provider snapshot has no registered fallback alias")
        seen_providers.add(provider)
        status = snap["status"]
        if type(status) is not str or status not in SNAPSHOT_STATES:
            raise CensusError(f"{where}.status invalid")
        _utc(snap["observed_at"], f"{where}.observed_at")
        query_sha = _sha(snap["query_sha256"], f"{where}.query_sha256")
        covered_raw = snap["covered_routes"]
        if type(covered_raw) is not list:
            raise CensusError(f"{where}.covered_routes must be array")
        covered: list[str] = []
        for cidx, route in enumerate(covered_raw):
            covered.append(_sha(route, f"{where}.covered_routes[{cidx}]"))
        if len(set(covered)) != len(covered):
            raise CensusError("duplicate covered route")
        covered.sort()

        events_raw = snap["events"]
        if type(events_raw) is not list:
            raise CensusError(f"{where}.events must be array")
        events: list[dict[str, str]] = []
        event_ids: set[str] = set()
        snap_dt = _utc(snap["observed_at"], f"{where}.observed_at")
        for eidx, event in enumerate(events_raw):
            ewhere = f"{where}.events[{eidx}]"
            _exact_keys(event, {"route_sha256", "event", "event_at", "evidence_sha256"}, ewhere)
            route = _sha(event["route_sha256"], f"{ewhere}.route_sha256")
            kind = event["event"]
            if type(kind) is not str or kind not in EVENTS:
                raise CensusError(f"{ewhere}.event invalid")
            event_dt = _utc(event["event_at"], f"{ewhere}.event_at")
            if event_dt > snap_dt:
                raise CensusError("provider event cannot occur after snapshot observation")
            evidence = _sha(event["evidence_sha256"], f"{ewhere}.evidence_sha256")
            if evidence in event_ids:
                raise CensusError("duplicate evidence event")
            event_ids.add(evidence)
            if (provider, route) not in alias_keys:
                raise CensusError("provider event route is not a registered fallback alias")
            events.append({
                "route_sha256": route,
                "event": kind,
                "event_at": event["event_at"],
                "evidence_sha256": evidence,
            })
        events.sort(key=lambda row: (row["event_at"], row["route_sha256"], row["event"], row["evidence_sha256"]))
        snapshots.append({
            "provider": provider,
            "status": status,
            "observed_at": snap["observed_at"],
            "query_sha256": query_sha,
            "covered_routes": covered,
            "events": events,
        })
    snapshots.sort(key=lambda row: row["provider"])
    return {
        "schema": INPUT_SCHEMA,
        "lease_input": lease_input,
        "intent": intent,
        "aliases": aliases,
        "snapshots": snapshots,
    }


def compile_census(raw: Any, *, trusted_now: str) -> dict[str, Any]:
    data = _normalize(raw)
    now = _utc(trusted_now, "trusted_now")
    now_epoch = _epoch(now)
    reasons: list[str] = []
    evidence: list[dict[str, str]] = []

    intent = data["intent"]
    intent_key = (intent["provider"], intent["route_sha256"])
    alias_keys = {(row["provider"], row["route_sha256"]) for row in data["aliases"]}
    if intent_key not in alias_keys:
        reasons.append("INTENT_ROUTE_UNMAPPED")
    requested = _utc(intent["requested_at"], "intent.requested_at")
    if requested > now:
        reasons.append("INTENT_REQUESTED_IN_FUTURE")
    elif now_epoch - _epoch(requested) > MAX_INTENT_AGE_SECONDS:
        reasons.append("INTENT_STALE")

    snapshots = {row["provider"]: row for row in data["snapshots"]}
    aliases_by_provider: dict[str, set[str]] = {}
    for alias in data["aliases"]:
        aliases_by_provider.setdefault(alias["provider"], set()).add(alias["route_sha256"])

    all_events: list[tuple[str, dict[str, str]]] = []
    provider_census: list[dict[str, Any]] = []
    clear_expiry_epochs: list[int] = [_epoch(requested) + MAX_INTENT_AGE_SECONDS]
    for provider in sorted(aliases_by_provider):
        snap = snapshots.get(provider)
        if snap is None:
            reasons.append(f"PROVIDER_CENSUS_MISSING:{provider}")
            provider_census.append({
                "provider": provider,
                "status": "MISSING",
                "observed_at": None,
                "query_sha256": None,
                "registered_routes": len(aliases_by_provider[provider]),
                "covered_routes": 0,
                "history_events": 0,
            })
            continue

        # Even an incomplete provider census may contain concrete prior-touch
        # evidence. Preserve that evidence in the packet while still HOLDing on
        # the incomplete census state; never turn a throttle into a false clean.
        for event in snap["events"]:
            all_events.append((provider, event))
        provider_census.append({
            "provider": provider,
            "status": snap["status"],
            "observed_at": snap["observed_at"],
            "query_sha256": snap["query_sha256"],
            "registered_routes": len(aliases_by_provider[provider]),
            "covered_routes": len(snap["covered_routes"]),
            "history_events": len(snap["events"]),
        })

        if snap["status"] != "COMPLETE":
            reasons.append(f"PROVIDER_CENSUS_{snap['status']}:{provider}")
            continue
        observed = _utc(snap["observed_at"], f"snapshot.{provider}.observed_at")
        observed_epoch = _epoch(observed)
        clear_expiry_epochs.append(observed_epoch + MAX_SNAPSHOT_AGE_SECONDS)
        if observed > now:
            reasons.append(f"PROVIDER_CENSUS_FUTURE:{provider}")
        elif observed < requested:
            reasons.append(f"PROVIDER_CENSUS_BEFORE_INTENT:{provider}")
        elif now_epoch - observed_epoch > MAX_SNAPSHOT_AGE_SECONDS:
            reasons.append(f"PROVIDER_CENSUS_STALE:{provider}")
        missing = aliases_by_provider[provider] - set(snap["covered_routes"])
        extra = set(snap["covered_routes"]) - aliases_by_provider[provider]
        if missing:
            reasons.append(f"PROVIDER_ROUTE_COVERAGE_MISSING:{provider}")
        if extra:
            reasons.append(f"PROVIDER_ROUTE_COVERAGE_UNKNOWN:{provider}")

    suppress = {"UNSUBSCRIBE", "DNR"}
    existing = {"PROVIDER_SENT", "HUMAN_REPLY", "AUTO_REPLY"}
    route_repair = {"HARD_BOUNCE", "SOFT_BOUNCE", "PROVIDER_REJECTED"}
    ambiguous = {"AMBIGUOUS_EFFECT"}
    if any(event["event"] in suppress for _, event in all_events):
        reasons.append("SUPPRESSION_HISTORY_PRESENT")
    if any(event["event"] in existing for _, event in all_events):
        reasons.append("PRIOR_PROVIDER_TOUCH_PRESENT")
    if any(event["event"] in route_repair for _, event in all_events):
        reasons.append("ROUTE_REPAIR_REQUIRED")
    if any(event["event"] in ambiguous for _, event in all_events):
        reasons.append("AMBIGUOUS_PROVIDER_EFFECT_PRESENT")

    for provider, event in all_events:
        evidence.append({
            "provider": provider,
            "route_sha256": event["route_sha256"],
            "event": event["event"],
            "event_at": event["event_at"],
            "evidence_sha256": event["evidence_sha256"],
        })
    evidence.sort(key=lambda row: (row["event_at"], row["provider"], row["route_sha256"], row["event"], row["evidence_sha256"]))
    reasons = sorted(set(reasons))

    lease_key = compile_lease_document(data["lease_input"])
    logical_seam = lease_key["seam_sha256"]
    decision = "CLEAR_FOR_DOWNSTREAM_GATES" if not reasons else "HOLD"
    clear_until = None
    if decision == "CLEAR_FOR_DOWNSTREAM_GATES":
        clear_until = datetime.fromtimestamp(min(clear_expiry_epochs), UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    packet: dict[str, Any] = {
        "schema": PACKET_SCHEMA,
        "trusted_now": trusted_now,
        "downstream_lease_seam_sha256": logical_seam,
        "downstream_lease_branch": lease_key["branch"],
        "decision": decision,
        "clear_until": clear_until,
        "reasons": reasons,
        "provider_census": provider_census,
        "summary": {
            "registered_aliases": len(data["aliases"]),
            "required_providers": sorted(aliases_by_provider),
            "provider_snapshots": len(data["snapshots"]),
            "history_events": len(evidence),
        },
        "evidence": evidence,
        "authority": {
            "kind": "PREFLIGHT_COLLISION_CENSUS_ONLY",
            "external_send_authorized": False,
            "lease_authorized": False,
            "provider_mutation_authorized": False,
        },
        "input_sha256": _digest(data),
    }
    packet["receipt_sha256"] = _digest(packet)
    return packet


def verify_census(packet_raw: Any, input_raw: Any, *, trusted_now: str) -> dict[str, Any]:
    packet = _snapshot(packet_raw)
    if type(packet) is not dict:
        raise CensusError("packet must be object")
    receipt = packet.get("receipt_sha256")
    _sha(receipt, "packet.receipt_sha256")
    unsigned = dict(packet)
    unsigned.pop("receipt_sha256", None)
    if _digest(unsigned) != receipt:
        raise CensusError("packet receipt mismatch")
    expected = compile_census(input_raw, trusted_now=trusted_now)
    if _canonical_bytes(packet) != _canonical_bytes(expected):
        raise CensusError("packet does not match exact input generation and trusted_now")
    return {"ok": True, "decision": packet["decision"], "receipt_sha256": receipt}


def _strict_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise CensusError(f"duplicate JSON key: {key}")
        out[key] = value
    return out


def _reject_constant(value: str) -> Any:
    raise CensusError(f"non-finite JSON constant forbidden: {value}")


def load_json(path: Path) -> Any:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise CensusError(f"unable to read {path}") from exc
    try:
        return json.loads(text, object_pairs_hook=_strict_pairs, parse_constant=_reject_constant)
    except CensusError:
        raise
    except json.JSONDecodeError as exc:
        raise CensusError(f"invalid JSON in {path}") from exc


def write_exclusive(path: Path, value: Any) -> None:
    raw = _canonical_bytes(value) + b"\n"
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        fd = os.open(path, flags, 0o600)
    except OSError as exc:
        raise CensusError(f"refusing to overwrite/follow output path: {path}") from exc
    with os.fdopen(fd, "wb", closefd=True) as handle:
        handle.write(raw)
        handle.flush()
        os.fsync(handle.fileno())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    compile_p = sub.add_parser("compile")
    compile_p.add_argument("--input", type=Path, required=True)
    compile_p.add_argument("--trusted-now", required=True)
    compile_p.add_argument("--out", type=Path, required=True)
    verify_p = sub.add_parser("verify")
    verify_p.add_argument("--input", type=Path, required=True)
    verify_p.add_argument("--trusted-now", required=True)
    verify_p.add_argument("--packet", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        source = load_json(args.input)
        if args.command == "compile":
            packet = compile_census(source, trusted_now=args.trusted_now)
            write_exclusive(args.out, packet)
            print(json.dumps({"decision": packet["decision"], "receipt_sha256": packet["receipt_sha256"]}, sort_keys=True))
        else:
            print(json.dumps(verify_census(load_json(args.packet), source, trusted_now=args.trusted_now), sort_keys=True))
    except CensusError as exc:
        print(f"REFUSED: {exc}", file=os.sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
