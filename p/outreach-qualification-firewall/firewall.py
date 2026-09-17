#!/usr/bin/env python3
"""Fail-closed pre-send outreach qualification firewall.

This module never sends anything. It deterministically evaluates retained
evidence and separates:
1. qualification for owner review; from
2. authorization to perform one exact outbound action.

All time is caller-supplied. No host clock is consulted.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Mapping, Sequence
from urllib.parse import urlsplit, urlunsplit

SCHEMA = "tjlabs-outreach-qualification/v1"
TERMINAL_BLOCK_RELATIONSHIPS = {"DNR", "BOUNCE", "BLOCKED", "CLOSED"}
OPEN_RELATIONSHIPS = {"OPEN", "WARM", "INBOUND", "REFERRED"}
ELIGIBILITY_PASS = {"PROVEN", "NOT_REQUIRED"}
ROUTE_KINDS = {"EMAIL", "GITHUB_PR", "PORTAL", "FORM", "SLACK_CONNECT", "OTHER"}
COMPENSATION_BASES = {"FIXED_FEE", "HOURLY", "BOUNTY"}
PRIOR_BLOCK_STATES = {"PENDING", "SENT", "DELIVERED", "ACCEPTED", "PAID"}
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
CURRENCY_RE = re.compile(r"^[A-Z]{3}$")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class PacketError(ValueError):
    """Packet violates a structural or trust-boundary contract."""


@dataclass(frozen=True)
class Decision:
    qualified_for_owner_review: bool
    authorized_to_send: bool
    blockers: tuple[str, ...]
    warnings: tuple[str, ...]
    qualification_digest: str
    action_digest: str
    dedupe_key: str
    runway_seconds: int

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema": "tjlabs-outreach-qualification-decision/v1",
            "qualified_for_owner_review": self.qualified_for_owner_review,
            "authorized_to_send": self.authorized_to_send,
            "blockers": list(self.blockers),
            "warnings": list(self.warnings),
            "qualification_digest": self.qualification_digest,
            "action_digest": self.action_digest,
            "dedupe_key": self.dedupe_key,
            "runway_seconds": self.runway_seconds,
        }


def _require_mapping(value: Any, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise PacketError(f"{name} must be an object")
    return value


def _require_list(value: Any, name: str) -> list[Any]:
    if not isinstance(value, list):
        raise PacketError(f"{name} must be a list")
    return value


def _text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise PacketError(f"{name} must be a non-empty string")
    return value.strip()


def _enum(value: Any, name: str, allowed: set[str]) -> str:
    text = _text(value, name)
    if text not in allowed:
        raise PacketError(f"{name} must be one of {sorted(allowed)}")
    return text


def _parse_utc(value: Any, name: str) -> datetime:
    text = _text(value, name)
    if not text.endswith("Z"):
        raise PacketError(f"{name} must use canonical UTC Z form")
    try:
        parsed = datetime.fromisoformat(text[:-1] + "+00:00")
    except ValueError as exc:
        raise PacketError(f"{name} is not a valid timestamp") from exc
    if parsed.tzinfo != timezone.utc:
        parsed = parsed.astimezone(timezone.utc)
    canonical = parsed.isoformat(timespec="seconds").replace("+00:00", "Z")
    if text != canonical:
        raise PacketError(f"{name} must be canonical to whole seconds: {canonical}")
    return parsed


def _canonical_bytes(value: Any) -> bytes:
    try:
        return json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise PacketError("packet must be canonical-JSON encodable without NaN/Infinity") from exc


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _digest(value: Any) -> str:
    return sha256_hex(_canonical_bytes(value))


def _norm_text(value: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", value).strip().casefold().split())


def _norm_route(kind: str, route: str) -> str:
    route = unicodedata.normalize("NFKC", route).strip()
    if kind == "EMAIL":
        lowered = route.casefold()
        if lowered.startswith("mailto:"):
            lowered = lowered[7:].strip()
        if not EMAIL_RE.fullmatch(lowered):
            raise PacketError("action.route must be a syntactically valid email address")
        return lowered
    if kind in {"GITHUB_PR", "PORTAL", "FORM"}:
        parts = urlsplit(route)
        if parts.scheme.casefold() not in {"https", "http"} or not parts.netloc:
            raise PacketError("action.route must be an absolute http(s) URL")
        scheme = parts.scheme.casefold()
        host = parts.netloc.casefold()
        path = re.sub(r"/+", "/", parts.path or "/")
        if path != "/":
            path = path.rstrip("/")
        return urlunsplit((scheme, host, path, parts.query, ""))
    return _norm_text(route)


def _decimal_positive(value: Any, name: str) -> Decimal:
    if isinstance(value, bool):
        raise PacketError(f"{name} must be a positive decimal")
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise PacketError(f"{name} must be a positive decimal") from exc
    if not parsed.is_finite() or parsed <= 0:
        raise PacketError(f"{name} must be finite and > 0")
    return parsed


def _source_binding(packet: Mapping[str, Any], source_bytes: bytes) -> dict[str, Any]:
    source = _require_mapping(packet.get("source"), "source")
    locator = _text(source.get("locator"), "source.locator")
    expected = _text(source.get("sha256"), "source.sha256")
    if not SHA256_RE.fullmatch(expected):
        raise PacketError("source.sha256 must be lowercase sha256")
    actual = sha256_hex(source_bytes)
    if actual != expected:
        raise PacketError(
            f"retained source digest mismatch: expected {expected}, got {actual}"
        )
    if "\x00" in locator:
        raise PacketError("source.locator contains NUL")
    return {"locator": locator, "sha256": expected}


def _qualification_material(
    packet: Mapping[str, Any],
    source_binding: Mapping[str, Any],
    now: datetime,
) -> tuple[dict[str, Any], list[str], list[str], int, str]:
    blockers: list[str] = []
    warnings: list[str] = []

    if packet.get("schema") != SCHEMA:
        raise PacketError(f"schema must be {SCHEMA!r}")

    as_of = _parse_utc(packet.get("as_of_utc"), "as_of_utc")
    if as_of != now:
        raise PacketError(
            "as_of_utc must exactly equal evaluator-supplied --now; mutable-clock replay rejected"
        )

    opportunity = _require_mapping(packet.get("opportunity"), "opportunity")
    opportunity_id = _text(opportunity.get("id"), "opportunity.id")
    deadline = _parse_utc(opportunity.get("deadline_utc"), "opportunity.deadline_utc")
    min_runway_hours = opportunity.get("min_runway_hours")
    if isinstance(min_runway_hours, bool) or not isinstance(min_runway_hours, int) or min_runway_hours < 0:
        raise PacketError("opportunity.min_runway_hours must be an integer >= 0")
    runway_seconds = int((deadline - now).total_seconds())
    required_seconds = min_runway_hours * 3600
    if runway_seconds < required_seconds:
        blockers.append("RUNWAY_BELOW_MINIMUM")
    if runway_seconds < 0:
        blockers.append("DEADLINE_PASSED")

    submission = _require_mapping(packet.get("submission"), "submission")
    route_state = _enum(
        submission.get("route_state"), "submission.route_state",
        {"PROVEN", "UNKNOWN", "FAILED"},
    )
    route_kind = _enum(submission.get("kind"), "submission.kind", ROUTE_KINDS)
    route_locator = _text(submission.get("locator"), "submission.locator")
    registration_required = submission.get("registration_required")
    if not isinstance(registration_required, bool):
        raise PacketError("submission.registration_required must be boolean")
    registration_state = _enum(
        submission.get("registration_state"), "submission.registration_state",
        {"PROVEN", "NOT_REQUIRED", "UNKNOWN", "FAILED"},
    )
    if route_state != "PROVEN":
        blockers.append("SUBMISSION_ROUTE_NOT_PROVEN")
    if registration_required and registration_state != "PROVEN":
        blockers.append("REGISTRATION_NOT_PROVEN")
    if not registration_required and registration_state not in {"NOT_REQUIRED", "PROVEN"}:
        blockers.append("REGISTRATION_STATE_INCONSISTENT")

    eligibility = _require_mapping(packet.get("eligibility"), "eligibility")
    gates = _require_list(eligibility.get("gates"), "eligibility.gates")
    if not gates:
        raise PacketError("eligibility.gates must not be empty")
    normalized_gates: list[dict[str, Any]] = []
    gate_names: set[str] = set()
    for index, raw in enumerate(gates):
        gate = _require_mapping(raw, f"eligibility.gates[{index}]")
        name = _text(gate.get("name"), f"eligibility.gates[{index}].name")
        folded = _norm_text(name)
        if folded in gate_names:
            raise PacketError(f"duplicate eligibility gate name: {name}")
        gate_names.add(folded)
        state = _enum(
            gate.get("state"), f"eligibility.gates[{index}].state",
            {"PROVEN", "NOT_REQUIRED", "UNKNOWN", "FAILED"},
        )
        refs_raw = _require_list(
            gate.get("evidence_refs"), f"eligibility.gates[{index}].evidence_refs"
        )
        refs = [_text(x, f"eligibility.gates[{index}].evidence_refs[]") for x in refs_raw]
        if state == "PROVEN" and not refs:
            raise PacketError(f"PROVEN eligibility gate {name!r} needs evidence_refs")
        if state not in ELIGIBILITY_PASS:
            blockers.append(f"ELIGIBILITY_{state}:{name}")
        normalized_gates.append({"name": name, "state": state, "evidence_refs": refs})

    economics = _require_mapping(packet.get("economics"), "economics")
    basis = _enum(economics.get("basis"), "economics.basis", COMPENSATION_BASES)
    amount = _decimal_positive(economics.get("amount"), "economics.amount")
    currency = _text(economics.get("currency"), "economics.currency")
    if not CURRENCY_RE.fullmatch(currency):
        raise PacketError("economics.currency must be ISO-like uppercase 3-letter code")
    scope = _text(economics.get("bounded_scope"), "economics.bounded_scope")
    payment_path_state = _enum(
        economics.get("payment_path_state"), "economics.payment_path_state",
        {"PROVEN", "UNKNOWN", "FAILED"},
    )
    if payment_path_state != "PROVEN":
        blockers.append("PAYMENT_PATH_NOT_PROVEN")

    target = _require_mapping(packet.get("target"), "target")
    organization = _text(target.get("organization"), "target.organization")
    contact = _text(target.get("contact"), "target.contact")
    relationship_state = _enum(
        target.get("relationship_state"), "target.relationship_state",
        OPEN_RELATIONSHIPS | TERMINAL_BLOCK_RELATIONSHIPS,
    )
    if relationship_state in TERMINAL_BLOCK_RELATIONSHIPS:
        blockers.append(f"RELATIONSHIP_{relationship_state}")

    action = _require_mapping(packet.get("action"), "action")
    action_kind = _enum(action.get("kind"), "action.kind", ROUTE_KINDS)
    action_route = _text(action.get("route"), "action.route")
    normalized_route = _norm_route(action_kind, action_route)
    purpose = _text(action.get("purpose"), "action.purpose")
    content_sha256 = _text(action.get("content_sha256"), "action.content_sha256")
    if not SHA256_RE.fullmatch(content_sha256):
        raise PacketError("action.content_sha256 must be lowercase sha256")

    if action_kind == "EMAIL" and _norm_route("EMAIL", contact) != normalized_route:
        blockers.append("ACTION_ROUTE_CONTACT_MISMATCH")

    dedupe_material = {
        "opportunity_id": _norm_text(opportunity_id),
        "organization": _norm_text(organization),
        "contact": _norm_text(contact),
        "action_kind": action_kind,
        "route": normalized_route,
        "purpose": _norm_text(purpose),
    }
    dedupe_key = _digest(dedupe_material)

    prior_actions = _require_list(packet.get("prior_actions"), "prior_actions")
    for index, raw in enumerate(prior_actions):
        prior = _require_mapping(raw, f"prior_actions[{index}]")
        prior_key = _text(prior.get("dedupe_key"), f"prior_actions[{index}].dedupe_key")
        if not SHA256_RE.fullmatch(prior_key):
            raise PacketError(f"prior_actions[{index}].dedupe_key must be lowercase sha256")
        state = _enum(
            prior.get("state"), f"prior_actions[{index}].state",
            PRIOR_BLOCK_STATES | {"FAILED", "VOID"},
        )
        if prior_key == dedupe_key and state in PRIOR_BLOCK_STATES:
            blockers.append(f"DUPLICATE_PRIOR_ACTION:{state}")

    material = {
        "schema": SCHEMA,
        "source": dict(source_binding),
        "as_of_utc": packet["as_of_utc"],
        "opportunity": {
            "id": opportunity_id,
            "deadline_utc": opportunity["deadline_utc"],
            "min_runway_hours": min_runway_hours,
        },
        "submission": {
            "kind": route_kind,
            "locator": route_locator,
            "route_state": route_state,
            "registration_required": registration_required,
            "registration_state": registration_state,
        },
        "eligibility": {"gates": normalized_gates},
        "economics": {
            "basis": basis,
            "amount": format(amount, "f"),
            "currency": currency,
            "bounded_scope": scope,
            "payment_path_state": payment_path_state,
        },
        "target": {
            "organization": organization,
            "contact": contact,
            "relationship_state": relationship_state,
        },
        "action": {
            "kind": action_kind,
            "route": normalized_route,
            "purpose": purpose,
            "content_sha256": content_sha256,
        },
        "dedupe_key": dedupe_key,
        "prior_actions": [
            {"dedupe_key": p["dedupe_key"], "state": p["state"]}
            for p in prior_actions
        ],
    }
    if runway_seconds == required_seconds:
        warnings.append("RUNWAY_EXACTLY_AT_MINIMUM")
    return material, blockers, warnings, runway_seconds, dedupe_key


def evaluate(
    packet: Mapping[str, Any],
    source_bytes: bytes,
    *,
    now_utc: str,
    writer: str,
) -> Decision:
    """Evaluate one exact packet against retained bytes and explicit time/writer."""
    if not isinstance(packet, Mapping):
        raise PacketError("packet must be an object")
    now = _parse_utc(now_utc, "now_utc")
    writer = _text(writer, "writer")

    source_binding = _source_binding(packet, source_bytes)
    material, blockers, warnings, runway_seconds, dedupe_key = _qualification_material(
        packet, source_binding, now
    )
    qualification_digest = _digest(material)

    action_material = {
        "qualification_digest": qualification_digest,
        "dedupe_key": dedupe_key,
        "action": material["action"],
    }
    action_digest = _digest(action_material)

    qualified = not blockers

    owner_review = packet.get("owner_review")
    owner_ok = False
    if owner_review is None:
        if qualified:
            warnings.append("OWNER_REVIEW_REQUIRED")
    else:
        review = _require_mapping(owner_review, "owner_review")
        status = _enum(
            review.get("status"), "owner_review.status", {"APPROVED", "REJECTED"}
        )
        reviewer = _text(review.get("reviewer"), "owner_review.reviewer")
        _ = reviewer
        reviewed_at = _parse_utc(review.get("reviewed_at_utc"), "owner_review.reviewed_at_utc")
        expires_at = _parse_utc(review.get("expires_at_utc"), "owner_review.expires_at_utc")
        bound = _text(
            review.get("qualification_digest"), "owner_review.qualification_digest"
        )
        if not SHA256_RE.fullmatch(bound):
            raise PacketError("owner_review.qualification_digest must be lowercase sha256")
        if status != "APPROVED":
            blockers.append("OWNER_REVIEW_REJECTED")
        elif bound != qualification_digest:
            blockers.append("OWNER_REVIEW_STALE_OR_FOREIGN")
        elif reviewed_at > now or expires_at < now or expires_at < reviewed_at:
            blockers.append("OWNER_REVIEW_TIME_INVALID")
        elif not qualified:
            blockers.append("OWNER_REVIEW_CANNOT_OVERRIDE_QUALIFICATION_BLOCKER")
        else:
            owner_ok = True

    lease = packet.get("writer_lease")
    lease_ok = False
    if lease is None:
        if qualified:
            warnings.append("WRITER_LEASE_REQUIRED")
    else:
        lease_obj = _require_mapping(lease, "writer_lease")
        status = _enum(
            lease_obj.get("status"), "writer_lease.status",
            {"SELECTED", "HOLD", "COLLISION", "VOID"},
        )
        key = _text(lease_obj.get("key"), "writer_lease.key")
        _ = key
        selected_writer = _text(
            lease_obj.get("selected_writer"), "writer_lease.selected_writer"
        )
        bound_action = _text(
            lease_obj.get("action_digest"), "writer_lease.action_digest"
        )
        if not SHA256_RE.fullmatch(bound_action):
            raise PacketError("writer_lease.action_digest must be lowercase sha256")
        issued_at = _parse_utc(
            lease_obj.get("issued_at_utc"), "writer_lease.issued_at_utc"
        )
        expires_at = _parse_utc(
            lease_obj.get("expires_at_utc"), "writer_lease.expires_at_utc"
        )
        if status != "SELECTED":
            blockers.append(f"WRITER_LEASE_{status}")
        elif selected_writer != writer:
            blockers.append("WRITER_LEASE_FOREIGN_WRITER")
        elif bound_action != action_digest:
            blockers.append("WRITER_LEASE_STALE_OR_FOREIGN_ACTION")
        elif issued_at > now or expires_at < now or expires_at < issued_at:
            blockers.append("WRITER_LEASE_TIME_INVALID")
        else:
            lease_ok = True

    qualification_blockers = [
        b for b in blockers
        if not b.startswith("OWNER_REVIEW_") and not b.startswith("WRITER_LEASE_")
    ]
    qualified = not qualification_blockers
    authorized = qualified and owner_ok and lease_ok and not blockers

    return Decision(
        qualified_for_owner_review=qualified,
        authorized_to_send=authorized,
        blockers=tuple(sorted(set(blockers))),
        warnings=tuple(sorted(set(warnings))),
        qualification_digest=qualification_digest,
        action_digest=action_digest,
        dedupe_key=dedupe_key,
        runway_seconds=runway_seconds,
    )


def _load_json(path: Path) -> Mapping[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    return _require_mapping(value, "packet")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Evaluate a retained outreach qualification packet; never sends anything."
    )
    parser.add_argument("packet", type=Path)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--now", required=True, dest="now_utc")
    parser.add_argument("--writer", required=True)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)

    packet = _load_json(args.packet)
    source_bytes = args.source.read_bytes()
    decision = evaluate(
        packet, source_bytes, now_utc=args.now_utc, writer=args.writer
    )
    payload = json.dumps(decision.as_dict(), sort_keys=True, indent=2) + "\n"
    if args.out:
        args.out.write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")
    return 0 if decision.authorized_to_send else 2


if __name__ == "__main__":
    raise SystemExit(main())
