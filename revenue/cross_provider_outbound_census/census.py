"""Cross-provider outbound census with a host-owned authority boundary.

Operational readiness is intentionally impossible to derive from claimant JSON
alone.  The candidate supplies only the canonical outbound lease seam and current
intent.  A host-owned :class:`RetainedAuthoritySource` supplies the retained
fallback registry and per-provider census generations, while process UTC supplies
current time.  The strongest result remains preflight-only and never authorizes an
external send or provider mutation.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
from abc import ABC, abstractmethod
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from revenue.outbound_connector_lease.key import (
    LeaseKeyError,
    SUPPORTED_REPLY_PROVIDERS,
    compile_document as compile_lease_document,
)

INPUT_SCHEMA = "commons-cross-provider-outbound-census/intent-v2"
PACKET_SCHEMA = "commons-cross-provider-outbound-census/packet-v2"
REGISTRY_SCHEMA = "commons-cross-provider-outbound-census/alias-registry-v1"
PROVIDER_SCHEMA = "commons-cross-provider-outbound-census/provider-census-v1"
AUDIT_SCHEMA = "commons-cross-provider-outbound-census/audit-v1"
MAX_SAFE_INTEGER = (1 << 53) - 1
MAX_ROWS = 100_000
MAX_SNAPSHOT_AGE_SECONDS = 300
MAX_INTENT_AGE_SECONDS = 300
MAX_PACKET_VERIFY_AGE_SECONDS = 30
SCOPE_RE = re.compile(r"^[a-z0-9][a-z0-9._:/#-]{2,160}$")
AUTHORITY_ID_RE = re.compile(r"^[a-z0-9][a-z0-9._:/#-]{2,160}$")
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


class RetainedAuthoritySource(ABC):
    """Host capability for authority records retained outside claimant input.

    The operational API deliberately accepts this capability object rather than
    paths, JSON authority fields, provider snapshots, or a caller-selected clock.
    Concrete deployments must source these records from their authenticated,
    retained connector/registry state.  Candidate JSON has no mechanism to mint,
    omit, replace, or redirect this capability.
    """

    @property
    @abstractmethod
    def authority_id(self) -> str:
        """Opaque identifier for the retained authority generation/source."""

    @abstractmethod
    def load_alias_registry(self, seam_sha256: str) -> Any:
        """Return the retained alias registry for exactly ``seam_sha256``."""

    @abstractmethod
    def load_provider_census(
        self, seam_sha256: str, provider: str, registry_generation: int
    ) -> Any | None:
        """Return retained provider census or ``None`` when unavailable."""


def _process_utc_now() -> datetime:
    """Operational clock.  Not selectable through candidate data or CLI args."""
    return datetime.now(UTC).replace(microsecond=0)


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
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError, OverflowError) as exc:
        raise CensusError("value is not canonical JSON") from exc


def _snapshot(value: Any) -> Any:
    return json.loads(_canonical_bytes(value).decode("utf-8"))


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _digest_without_receipt(value: dict[str, Any]) -> str:
    unsigned = dict(value)
    unsigned.pop("receipt_sha256", None)
    return _digest(unsigned)


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


def _authority_id(value: Any, where: str) -> str:
    if type(value) is not str or not AUTHORITY_ID_RE.fullmatch(value):
        raise CensusError(f"{where} must be a lower-case opaque authority id")
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


def _fmt(dt: datetime) -> str:
    return dt.astimezone(UTC).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")


def _provider(value: Any, where: str) -> str:
    if type(value) is not str or value not in SUPPORTED_REPLY_PROVIDERS:
        raise CensusError(f"{where} unsupported provider")
    return value


def _positive_int(value: Any, where: str) -> int:
    if type(value) is not int or value <= 0 or value > MAX_SAFE_INTEGER:
        raise CensusError(f"{where} must be a positive safe integer")
    return value


def _epoch(dt: datetime) -> int:
    delta = dt.astimezone(UTC) - datetime(1970, 1, 1, tzinfo=UTC)
    return delta.days * 86400 + delta.seconds


def _normalize_intent(raw: Any) -> tuple[dict[str, Any], dict[str, Any]]:
    value = _snapshot(raw)
    _exact_keys(value, {"schema", "lease_input", "intent"}, "input")
    if value["schema"] != INPUT_SCHEMA:
        raise CensusError("unsupported input schema")
    try:
        lease_key = compile_lease_document(value["lease_input"])
    except LeaseKeyError as exc:
        raise CensusError(f"invalid canonical outbound lease input: {exc}") from exc
    lease_input = {
        "schema": lease_key["schema"],
        "buyer_scope": lease_key["buyer_scope"],
        "opportunity": lease_key["opportunity"],
    }
    intent = value["intent"]
    _exact_keys(
        intent,
        {"provider", "route_sha256", "claimant_scope", "claim_scope", "requested_at"},
        "intent",
    )
    normalized_intent = {
        "provider": _provider(intent["provider"], "intent.provider"),
        "route_sha256": _sha(intent["route_sha256"], "intent.route_sha256"),
        "claimant_scope": _scope(intent["claimant_scope"], "intent.claimant_scope"),
        "claim_scope": _scope(intent["claim_scope"], "intent.claim_scope"),
        "requested_at": intent["requested_at"],
    }
    _utc(normalized_intent["requested_at"], "intent.requested_at")
    return {
        "schema": INPUT_SCHEMA,
        "lease_input": lease_input,
        "intent": normalized_intent,
    }, lease_key


def _normalize_aliases(raw: Any, seam_sha256: str, authority_id: str) -> dict[str, Any]:
    value = _snapshot(raw)
    _exact_keys(
        value,
        {
            "schema",
            "authority_id",
            "seam_sha256",
            "generation",
            "generated_at",
            "aliases",
            "receipt_sha256",
        },
        "alias_registry",
    )
    if value["schema"] != REGISTRY_SCHEMA:
        raise CensusError("alias_registry schema unsupported")
    if _authority_id(value["authority_id"], "alias_registry.authority_id") != authority_id:
        raise CensusError("alias_registry authority_id mismatch")
    if _sha(value["seam_sha256"], "alias_registry.seam_sha256") != seam_sha256:
        raise CensusError("alias_registry seam mismatch")
    generation = _positive_int(value["generation"], "alias_registry.generation")
    _utc(value["generated_at"], "alias_registry.generated_at")
    receipt = _sha(value["receipt_sha256"], "alias_registry.receipt_sha256")
    if _digest_without_receipt(value) != receipt:
        raise CensusError("alias_registry receipt mismatch")
    rows = value["aliases"]
    if type(rows) is not list or not rows:
        raise CensusError("alias_registry.aliases must be a non-empty array")
    aliases: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for idx, row in enumerate(rows):
        where = f"alias_registry.aliases[{idx}]"
        _exact_keys(row, {"provider", "route_sha256"}, where)
        normalized = {
            "provider": _provider(row["provider"], f"{where}.provider"),
            "route_sha256": _sha(row["route_sha256"], f"{where}.route_sha256"),
        }
        key = (normalized["provider"], normalized["route_sha256"])
        if key in seen:
            raise CensusError("alias_registry contains duplicate route")
        seen.add(key)
        aliases.append(normalized)
    aliases.sort(key=lambda row: (row["provider"], row["route_sha256"]))
    return {
        "schema": REGISTRY_SCHEMA,
        "authority_id": authority_id,
        "seam_sha256": seam_sha256,
        "generation": generation,
        "generated_at": value["generated_at"],
        "aliases": aliases,
        "receipt_sha256": receipt,
    }


def _normalize_provider_receipt(
    raw: Any,
    *,
    seam_sha256: str,
    authority_id: str,
    provider: str,
    registry_generation: int,
    registry_receipt_sha256: str,
    registered_routes: set[str],
) -> dict[str, Any]:
    value = _snapshot(raw)
    _exact_keys(
        value,
        {
            "schema",
            "authority_id",
            "seam_sha256",
            "provider",
            "registry_generation",
            "registry_receipt_sha256",
            "generation",
            "query_generation",
            "status",
            "observed_at",
            "query_sha256",
            "covered_routes",
            "events",
            "receipt_sha256",
        },
        f"provider_census.{provider}",
    )
    where = f"provider_census.{provider}"
    if value["schema"] != PROVIDER_SCHEMA:
        raise CensusError(f"{where} schema unsupported")
    if _authority_id(value["authority_id"], f"{where}.authority_id") != authority_id:
        raise CensusError(f"{where} authority_id mismatch")
    if _sha(value["seam_sha256"], f"{where}.seam_sha256") != seam_sha256:
        raise CensusError(f"{where} seam mismatch")
    if _provider(value["provider"], f"{where}.provider") != provider:
        raise CensusError(f"{where} provider mismatch")
    if _positive_int(value["registry_generation"], f"{where}.registry_generation") != registry_generation:
        raise CensusError(f"{where} registry generation mismatch")
    if _sha(value["registry_receipt_sha256"], f"{where}.registry_receipt_sha256") != registry_receipt_sha256:
        raise CensusError(f"{where} registry receipt mismatch")
    generation = _positive_int(value["generation"], f"{where}.generation")
    query_generation = _positive_int(value["query_generation"], f"{where}.query_generation")
    status = value["status"]
    if type(status) is not str or status not in SNAPSHOT_STATES:
        raise CensusError(f"{where}.status invalid")
    _utc(value["observed_at"], f"{where}.observed_at")
    _sha(value["query_sha256"], f"{where}.query_sha256")
    receipt = _sha(value["receipt_sha256"], f"{where}.receipt_sha256")
    if _digest_without_receipt(value) != receipt:
        raise CensusError(f"{where} receipt mismatch")

    covered_raw = value["covered_routes"]
    if type(covered_raw) is not list:
        raise CensusError(f"{where}.covered_routes must be an array")
    covered = [_sha(route, f"{where}.covered_routes") for route in covered_raw]
    if len(covered) != len(set(covered)):
        raise CensusError(f"{where} duplicate covered route")
    covered.sort()

    events_raw = value["events"]
    if type(events_raw) is not list:
        raise CensusError(f"{where}.events must be an array")
    observed = _utc(value["observed_at"], f"{where}.observed_at")
    events: list[dict[str, str]] = []
    evidence_ids: set[str] = set()
    for idx, event in enumerate(events_raw):
        ewhere = f"{where}.events[{idx}]"
        _exact_keys(event, {"route_sha256", "event", "event_at", "evidence_sha256"}, ewhere)
        route = _sha(event["route_sha256"], f"{ewhere}.route_sha256")
        if route not in registered_routes:
            raise CensusError(f"{ewhere} route is not in retained registry")
        kind = event["event"]
        if type(kind) is not str or kind not in EVENTS:
            raise CensusError(f"{ewhere}.event invalid")
        event_at = _utc(event["event_at"], f"{ewhere}.event_at")
        if event_at > observed:
            raise CensusError(f"{ewhere} occurs after census observation")
        evidence = _sha(event["evidence_sha256"], f"{ewhere}.evidence_sha256")
        if evidence in evidence_ids:
            raise CensusError(f"{where} duplicate evidence event")
        evidence_ids.add(evidence)
        events.append(
            {
                "route_sha256": route,
                "event": kind,
                "event_at": event["event_at"],
                "evidence_sha256": evidence,
            }
        )
    events.sort(
        key=lambda row: (
            row["event_at"],
            row["route_sha256"],
            row["event"],
            row["evidence_sha256"],
        )
    )
    return {
        "schema": PROVIDER_SCHEMA,
        "authority_id": authority_id,
        "seam_sha256": seam_sha256,
        "provider": provider,
        "registry_generation": registry_generation,
        "registry_receipt_sha256": registry_receipt_sha256,
        "generation": generation,
        "query_generation": query_generation,
        "status": status,
        "observed_at": value["observed_at"],
        "query_sha256": value["query_sha256"],
        "covered_routes": covered,
        "events": events,
        "receipt_sha256": receipt,
    }


def _load_authority(
    authority: RetainedAuthoritySource,
    seam_sha256: str,
) -> tuple[dict[str, Any], list[dict[str, Any] | None]]:
    if not isinstance(authority, RetainedAuthoritySource):
        raise CensusError("operational compile requires a RetainedAuthoritySource host capability")
    authority_id = _authority_id(authority.authority_id, "authority.authority_id")
    registry = _normalize_aliases(
        authority.load_alias_registry(seam_sha256), seam_sha256, authority_id
    )
    aliases_by_provider: dict[str, set[str]] = {}
    for alias in registry["aliases"]:
        aliases_by_provider.setdefault(alias["provider"], set()).add(alias["route_sha256"])
    receipts: list[dict[str, Any] | None] = []
    for provider in sorted(aliases_by_provider):
        raw = authority.load_provider_census(
            seam_sha256, provider, registry["generation"]
        )
        if raw is None:
            receipts.append(None)
            continue
        receipts.append(
            _normalize_provider_receipt(
                raw,
                seam_sha256=seam_sha256,
                authority_id=authority_id,
                provider=provider,
                registry_generation=registry["generation"],
                registry_receipt_sha256=registry["receipt_sha256"],
                registered_routes=aliases_by_provider[provider],
            )
        )
    return registry, receipts


def _compile_at(
    raw: Any,
    authority: RetainedAuthoritySource,
    now: datetime,
    *,
    audit_only: bool = False,
) -> dict[str, Any]:
    if not isinstance(now, datetime) or now.tzinfo is None or now.utcoffset() is None:
        raise CensusError("host time must be timezone-aware datetime")
    now = now.astimezone(UTC).replace(microsecond=0)
    data, lease_key = _normalize_intent(raw)
    seam_sha256 = lease_key["seam_sha256"]
    registry, provider_rows = _load_authority(authority, seam_sha256)

    aliases_by_provider: dict[str, set[str]] = {}
    for alias in registry["aliases"]:
        aliases_by_provider.setdefault(alias["provider"], set()).add(alias["route_sha256"])
    alias_keys = {
        (alias["provider"], alias["route_sha256"]) for alias in registry["aliases"]
    }
    intent = data["intent"]
    intent_key = (intent["provider"], intent["route_sha256"])
    reasons: list[str] = []
    registry_generated = _utc(registry["generated_at"], "alias_registry.generated_at")
    if registry_generated > now:
        reasons.append("ALIAS_REGISTRY_GENERATED_IN_FUTURE")
    if intent_key not in alias_keys:
        reasons.append("INTENT_ROUTE_UNMAPPED_BY_RETAINED_REGISTRY")
    requested = _utc(intent["requested_at"], "intent.requested_at")
    now_epoch = _epoch(now)
    if requested > now:
        reasons.append("INTENT_REQUESTED_IN_FUTURE")
    elif now_epoch - _epoch(requested) > MAX_INTENT_AGE_SECONDS:
        reasons.append("INTENT_STALE")

    receipts = {row["provider"]: row for row in provider_rows if row is not None}
    provider_census: list[dict[str, Any]] = []
    all_events: list[tuple[str, dict[str, str]]] = []
    clear_expiries = [_epoch(requested) + MAX_INTENT_AGE_SECONDS]
    for provider in sorted(aliases_by_provider):
        receipt = receipts.get(provider)
        if receipt is None:
            reasons.append(f"PROVIDER_CENSUS_MISSING:{provider}")
            provider_census.append(
                {
                    "provider": provider,
                    "status": "MISSING",
                    "registry_generation": registry["generation"],
                    "provider_generation": None,
                    "query_generation": None,
                    "observed_at": None,
                    "query_sha256": None,
                    "registered_routes": len(aliases_by_provider[provider]),
                    "covered_routes": 0,
                    "history_events": 0,
                    "authority_receipt_sha256": None,
                }
            )
            continue
        for event in receipt["events"]:
            all_events.append((provider, event))
        provider_census.append(
            {
                "provider": provider,
                "status": receipt["status"],
                "registry_generation": registry["generation"],
                "provider_generation": receipt["generation"],
                "query_generation": receipt["query_generation"],
                "observed_at": receipt["observed_at"],
                "query_sha256": receipt["query_sha256"],
                "registered_routes": len(aliases_by_provider[provider]),
                "covered_routes": len(receipt["covered_routes"]),
                "history_events": len(receipt["events"]),
                "authority_receipt_sha256": receipt["receipt_sha256"],
            }
        )
        if receipt["status"] != "COMPLETE":
            reasons.append(f"PROVIDER_CENSUS_{receipt['status']}:{provider}")
            continue
        observed = _utc(receipt["observed_at"], f"provider_census.{provider}.observed_at")
        observed_epoch = _epoch(observed)
        clear_expiries.append(observed_epoch + MAX_SNAPSHOT_AGE_SECONDS)
        if observed > now:
            reasons.append(f"PROVIDER_CENSUS_FUTURE:{provider}")
        elif observed < registry_generated:
            reasons.append(f"PROVIDER_CENSUS_BEFORE_REGISTRY:{provider}")
        elif observed < requested:
            reasons.append(f"PROVIDER_CENSUS_BEFORE_INTENT:{provider}")
        elif now_epoch - observed_epoch > MAX_SNAPSHOT_AGE_SECONDS:
            reasons.append(f"PROVIDER_CENSUS_STALE:{provider}")
        missing = aliases_by_provider[provider] - set(receipt["covered_routes"])
        extra = set(receipt["covered_routes"]) - aliases_by_provider[provider]
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

    evidence = [
        {
            "provider": provider,
            "route_sha256": event["route_sha256"],
            "event": event["event"],
            "event_at": event["event_at"],
            "evidence_sha256": event["evidence_sha256"],
        }
        for provider, event in all_events
    ]
    evidence.sort(
        key=lambda row: (
            row["event_at"],
            row["provider"],
            row["route_sha256"],
            row["event"],
            row["evidence_sha256"],
        )
    )
    reasons = sorted(set(reasons))
    ready = not reasons
    if audit_only:
        decision = "AUDIT_ONLY_CLEAR" if ready else "AUDIT_ONLY_HOLD"
        clear_until = None
    else:
        decision = "CLEAR_FOR_DOWNSTREAM_GATES" if ready else "HOLD"
        clear_until = (
            _fmt(datetime.fromtimestamp(min(clear_expiries), UTC)) if ready else None
        )
    packet = {
        "schema": AUDIT_SCHEMA if audit_only else PACKET_SCHEMA,
        "evaluated_at": _fmt(now),
        "downstream_lease_seam_sha256": seam_sha256,
        "downstream_lease_branch": lease_key["branch"],
        "decision": decision,
        "clear_until": clear_until,
        "reasons": reasons,
        "authority": {
            "authority_id": registry["authority_id"],
            "registry_generation": registry["generation"],
            "registry_receipt_sha256": registry["receipt_sha256"],
            "external_send_authorized": False,
            "lease_authorized": False,
            "provider_mutation_authorized": False,
            "historical_audit_only": bool(audit_only),
        },
        "provider_census": provider_census,
        "summary": {
            "registered_aliases": len(registry["aliases"]),
            "required_providers": sorted(aliases_by_provider),
            "provider_receipts": len(receipts),
            "history_events": len(evidence),
        },
        "evidence": evidence,
        "input_sha256": _digest(data),
    }
    packet["receipt_sha256"] = _digest(packet)
    return packet


def compile_current(raw: Any, authority: RetainedAuthoritySource) -> dict[str, Any]:
    """Compile operational preflight using process UTC and retained authority."""
    return _compile_at(raw, authority, _process_utc_now(), audit_only=False)


def audit_census(
    raw: Any, authority: RetainedAuthoritySource, *, historical_as_of: str
) -> dict[str, Any]:
    """Deterministic historical inspection; never emits consumable CLEAR authority."""
    return _compile_at(
        raw,
        authority,
        _utc(historical_as_of, "historical_as_of"),
        audit_only=True,
    )


def verify_current(
    packet_raw: Any, input_raw: Any, authority: RetainedAuthoritySource
) -> dict[str, Any]:
    """Verify a current packet against process UTC and freshly read authority state."""
    packet = _snapshot(packet_raw)
    if type(packet) is not dict:
        raise CensusError("packet must be object")
    if packet.get("schema") != PACKET_SCHEMA:
        raise CensusError("only current packet schema is operationally verifiable")
    receipt = _sha(packet.get("receipt_sha256"), "packet.receipt_sha256")
    if _digest_without_receipt(packet) != receipt:
        raise CensusError("packet receipt mismatch")
    now = _process_utc_now()
    evaluated = _utc(packet.get("evaluated_at"), "packet.evaluated_at")
    if evaluated > now:
        raise CensusError("packet evaluated_at is in the future")
    if _epoch(now) - _epoch(evaluated) > MAX_PACKET_VERIFY_AGE_SECONDS:
        raise CensusError("packet is too old for current verification")
    clear_until = packet.get("clear_until")
    if packet.get("decision") == "CLEAR_FOR_DOWNSTREAM_GATES":
        if clear_until is None:
            raise CensusError("clear packet missing clear_until")
        if now > _utc(clear_until, "packet.clear_until"):
            raise CensusError("clear packet has expired")
    expected = _compile_at(input_raw, authority, evaluated, audit_only=False)
    if _canonical_bytes(packet) != _canonical_bytes(expected):
        raise CensusError("packet does not match exact input + retained authority generation")
    return {
        "ok": True,
        "decision": packet["decision"],
        "receipt_sha256": receipt,
        "verified_at": _fmt(now),
    }


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
        return json.loads(
            text, object_pairs_hook=_strict_pairs, parse_constant=_reject_constant
        )
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
