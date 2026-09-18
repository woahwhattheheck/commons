from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
from pathlib import Path
from typing import Any

STATUSES = {
    "CURRENT_FOR_OWNER_USE",
    "EXPIRED_REQUOTE_REQUIRED",
    "SUPERSEDED",
    "HOLD_NO_VALIDITY_BASIS",
    "HOLD_SOURCE_DRIFT",
}
EVENT_KINDS = {"AMENDMENT", "REDLINE", "CHANGE_ORDER"}
_ALLOWED_OFFER_KEYS = {
    "schema_version", "offer_id", "source_generation", "pricing_revision", "currency",
    "scope", "economics", "issued_on", "validity", "buyer_deadline", "payment_rail",
}
_ALLOWED_CURRENT_KEYS = {
    "schema_version", "offer_id", "source_generation", "pricing_revision", "currency",
    "scope", "economics", "superseding_events",
}
_ALLOWED_VALIDITY_KEYS = {"mode", "valid_until", "valid_for_seconds"}
_ALLOWED_EVENT_KEYS = {"kind", "event_id", "observed_at", "applies_to_offer_id", "source_generation"}


class GateError(ValueError):
    pass


def _strict_object_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise GateError(f"duplicate JSON key: {key}")
        out[key] = value
    return out


def strict_json_loads(text: str) -> Any:
    def reject_constant(token: str) -> None:
        raise GateError(f"non-finite JSON number: {token}")

    try:
        return json.loads(text, object_pairs_hook=_strict_object_pairs, parse_constant=reject_constant)
    except GateError:
        raise
    except (json.JSONDecodeError, UnicodeError) as exc:
        raise GateError(f"invalid JSON: {exc}") from None


def _canonical(value: Any) -> bytes:
    try:
        text = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise GateError(f"not canonical JSON data: {exc}") from None
    return (text + "\n").encode("utf-8")


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _exact_keys(obj: dict[str, Any], allowed: set[str], label: str) -> None:
    extra = set(obj) - allowed
    if extra:
        raise GateError(f"{label}: unknown keys: {sorted(extra)}")


def _text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise GateError(f"{label}: expected non-empty text")
    if any(ord(ch) < 32 for ch in value):
        raise GateError(f"{label}: control characters are not allowed")
    return value


def _integer(value: Any, label: str, *, minimum: int | None = None) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise GateError(f"{label}: expected integer")
    if minimum is not None and value < minimum:
        raise GateError(f"{label}: expected >= {minimum}")
    return value


def _parse_time(value: Any, label: str) -> _dt.datetime:
    text = _text(value, label)
    try:
        parsed = _dt.datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        raise GateError(f"{label}: invalid ISO-8601 timestamp") from None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise GateError(f"{label}: timezone is required")
    return parsed.astimezone(_dt.timezone.utc)


def _utc_now() -> _dt.datetime:
    return _dt.datetime.now(_dt.timezone.utc)


def _validate_json_tree(value: Any, label: str) -> None:
    if value is None or isinstance(value, (str, bool)):
        return
    if isinstance(value, int):
        return
    if isinstance(value, float):
        raise GateError(f"{label}: floats are not allowed")
    if isinstance(value, list):
        for idx, item in enumerate(value):
            _validate_json_tree(item, f"{label}[{idx}]")
        return
    if isinstance(value, dict):
        for key, item in value.items():
            _text(key, f"{label} key")
            _validate_json_tree(item, f"{label}.{key}")
        return
    raise GateError(f"{label}: unsupported value type")


def _currency(value: Any) -> str:
    text = _text(value, "currency")
    if len(text) != 3 or not text.isascii() or not text.isalpha() or text.upper() != text:
        raise GateError("currency: expected uppercase ISO-like three-letter code")
    return text


def _validate_economics(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or not value:
        raise GateError(f"{label}: expected non-empty object")
    _validate_json_tree(value, label)
    for key, item in value.items():
        if key.endswith("_minor_units"):
            _integer(item, f"{label}.{key}", minimum=0)
    return value


def _validate_scope(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or not value:
        raise GateError(f"{label}: expected non-empty object")
    _validate_json_tree(value, label)
    return value


def _validate_offer(offer: Any) -> dict[str, Any]:
    if not isinstance(offer, dict):
        raise GateError("issued_offer: expected object")
    _exact_keys(offer, _ALLOWED_OFFER_KEYS, "issued_offer")
    if offer.get("schema_version") != 1:
        raise GateError("issued_offer.schema_version: expected 1")
    _text(offer.get("offer_id"), "issued_offer.offer_id")
    _text(offer.get("source_generation"), "issued_offer.source_generation")
    _text(offer.get("pricing_revision"), "issued_offer.pricing_revision")
    _currency(offer.get("currency"))
    _validate_scope(offer.get("scope"), "issued_offer.scope")
    _validate_economics(offer.get("economics"), "issued_offer.economics")
    _parse_time(offer.get("issued_on"), "issued_offer.issued_on")

    validity = offer.get("validity")
    if not isinstance(validity, dict):
        raise GateError("issued_offer.validity: expected object")
    _exact_keys(validity, _ALLOWED_VALIDITY_KEYS, "issued_offer.validity")
    mode = _text(validity.get("mode"), "issued_offer.validity.mode")
    if mode not in {"VALID_UNTIL", "VALID_FOR_SECONDS", "NO_EXPIRY_STATED"}:
        raise GateError("issued_offer.validity.mode: unsupported mode")
    if mode == "VALID_UNTIL":
        if set(validity) != {"mode", "valid_until"}:
            raise GateError("VALID_UNTIL requires exactly mode + valid_until")
    elif mode == "VALID_FOR_SECONDS":
        if set(validity) != {"mode", "valid_for_seconds"}:
            raise GateError("VALID_FOR_SECONDS requires exactly mode + valid_for_seconds")
        _integer(validity.get("valid_for_seconds"), "issued_offer.validity.valid_for_seconds", minimum=1)
    else:
        if set(validity) != {"mode"}:
            raise GateError("NO_EXPIRY_STATED accepts only mode")

    if offer.get("buyer_deadline") is not None:
        _parse_time(offer["buyer_deadline"], "issued_offer.buyer_deadline")
    if offer.get("payment_rail") is not None:
        _validate_json_tree(offer["payment_rail"], "issued_offer.payment_rail")
    return offer


def _validate_current(current: Any) -> dict[str, Any]:
    if not isinstance(current, dict):
        raise GateError("current_offer: expected object")
    _exact_keys(current, _ALLOWED_CURRENT_KEYS, "current_offer")
    if current.get("schema_version") != 1:
        raise GateError("current_offer.schema_version: expected 1")
    _text(current.get("offer_id"), "current_offer.offer_id")
    _text(current.get("source_generation"), "current_offer.source_generation")
    _text(current.get("pricing_revision"), "current_offer.pricing_revision")
    _currency(current.get("currency"))
    _validate_scope(current.get("scope"), "current_offer.scope")
    _validate_economics(current.get("economics"), "current_offer.economics")
    events = current.get("superseding_events")
    if not isinstance(events, list):
        raise GateError("current_offer.superseding_events: expected list")
    seen: set[str] = set()
    for idx, event in enumerate(events):
        if not isinstance(event, dict):
            raise GateError(f"current_offer.superseding_events[{idx}]: expected object")
        _exact_keys(event, _ALLOWED_EVENT_KEYS, f"current_offer.superseding_events[{idx}]")
        kind = _text(event.get("kind"), f"event[{idx}].kind")
        if kind not in EVENT_KINDS:
            raise GateError(f"event[{idx}].kind: unsupported kind")
        event_id = _text(event.get("event_id"), f"event[{idx}].event_id")
        if event_id in seen:
            raise GateError(f"duplicate superseding event_id: {event_id}")
        seen.add(event_id)
        _parse_time(event.get("observed_at"), f"event[{idx}].observed_at")
        _text(event.get("applies_to_offer_id"), f"event[{idx}].applies_to_offer_id")
        _text(event.get("source_generation"), f"event[{idx}].source_generation")
    return current


def _effective_expiry(offer: dict[str, Any]) -> tuple[_dt.datetime | None, str]:
    issued = _parse_time(offer["issued_on"], "issued_offer.issued_on")
    validity = offer["validity"]
    mode = validity["mode"]
    if mode == "NO_EXPIRY_STATED":
        expiry = None
        basis = "NO_EXPIRY_STATED"
    elif mode == "VALID_UNTIL":
        expiry = _parse_time(validity["valid_until"], "issued_offer.validity.valid_until")
        basis = "EXPLICIT_VALID_UNTIL"
    else:
        expiry = issued + _dt.timedelta(seconds=_integer(validity["valid_for_seconds"], "valid_for_seconds", minimum=1))
        basis = "ISSUED_PLUS_VALID_FOR_SECONDS"

    if offer.get("buyer_deadline") is not None:
        deadline = _parse_time(offer["buyer_deadline"], "issued_offer.buyer_deadline")
        if expiry is None or deadline < expiry:
            expiry = deadline
            basis = f"{basis}+BUYER_DEADLINE_CAP"
    return expiry, basis


def _diff(issued: dict[str, Any], current: dict[str, Any]) -> list[dict[str, Any]]:
    fields = ["source_generation", "pricing_revision", "currency", "scope", "economics"]
    result = []
    for field in fields:
        if issued[field] != current[field]:
            result.append({"field": field, "issued": issued[field], "current": current[field]})
    return result


def _active_superseders(issued: dict[str, Any], current: dict[str, Any]) -> list[dict[str, Any]]:
    issued_at = _parse_time(issued["issued_on"], "issued_offer.issued_on")
    active = []
    for event in current["superseding_events"]:
        if event["applies_to_offer_id"] != issued["offer_id"]:
            continue
        if _parse_time(event["observed_at"], "event.observed_at") <= issued_at:
            continue
        active.append(event)
    return sorted(active, key=lambda e: (e["observed_at"], e["event_id"]))


def _evaluate_at(issued_offer: Any, current_offer: Any, now: _dt.datetime) -> dict[str, Any]:
    issued = _validate_offer(issued_offer)
    current = _validate_current(current_offer)
    if now.tzinfo is None or now.utcoffset() is None:
        raise GateError("runtime clock must be timezone-aware")
    now = now.astimezone(_dt.timezone.utc)

    if issued["offer_id"] != current["offer_id"]:
        raise GateError("offer_id mismatch")

    changes = _diff(issued, current)
    superseders = _active_superseders(issued, current)
    expiry, validity_basis = _effective_expiry(issued)

    if superseders:
        status = "SUPERSEDED"
        reason = "later amendment/redline/change-order evidence applies to this offer"
    elif any(item["field"] in {"pricing_revision", "currency", "scope", "economics"} for item in changes):
        status = "SUPERSEDED"
        reason = "current offer economics/scope/currency/revision differ from issued offer"
    elif issued["source_generation"] != current["source_generation"]:
        status = "HOLD_SOURCE_DRIFT"
        reason = "source generation changed after issuance without an explicit superseding economics delta"
    elif expiry is not None and expiry < _parse_time(issued["issued_on"], "issued_offer.issued_on"):
        status = "HOLD_NO_VALIDITY_BASIS"
        reason = "effective validity endpoint predates issuance"
    elif expiry is not None and now > expiry:
        status = "EXPIRED_REQUOTE_REQUIRED"
        reason = "effective validity endpoint has passed"
    elif issued["validity"]["mode"] == "NO_EXPIRY_STATED":
        status = "HOLD_NO_VALIDITY_BASIS"
        reason = "offer states no expiry; owner review is required before reuse"
    elif now < _parse_time(issued["issued_on"], "issued_offer.issued_on"):
        status = "HOLD_NO_VALIDITY_BASIS"
        reason = "runtime clock precedes offer issuance"
    else:
        status = "CURRENT_FOR_OWNER_USE"
        reason = "source/economics unchanged and explicit validity basis remains current"

    delta = {
        "offer_id": issued["offer_id"],
        "status": "PROPOSED_NOT_ACCEPTED",
        "issued_source_generation": issued["source_generation"],
        "current_source_generation": current["source_generation"],
        "changes": changes,
        "superseding_events": superseders,
        "buyer_acceptance_inferred": False,
        "payment_authority_inferred": False,
    }
    body = {
        "schema_version": 1,
        "status": status,
        "reason": reason,
        "offer_id": issued["offer_id"],
        "evaluated_at": now.isoformat().replace("+00:00", "Z"),
        "validity_basis": validity_basis,
        "effective_valid_until": None if expiry is None else expiry.isoformat().replace("+00:00", "Z"),
        "issued_offer_sha256": _sha(issued),
        "current_offer_sha256": _sha(current),
        "scope_sha256": _sha(issued["scope"]),
        "economics_sha256": _sha(issued["economics"]),
        "requote_delta": delta,
        "authority": {
            "owner_review_only": True,
            "buyer_acceptance": False,
            "contract_signed": False,
            "checkout_or_payment_rail_is_acceptance": False,
            "payment_authorized": False,
            "revenue_recognized": False,
            "outbound_authorized": False,
        },
    }
    body["receipt_sha256"] = _sha(body)
    return body


def evaluate_offer(issued_offer: Any, current_offer: Any) -> dict[str, Any]:
    return _evaluate_at(issued_offer, current_offer, _utc_now())


def verify_packet(issued_offer: Any, current_offer: Any, packet: Any) -> bool:
    if not isinstance(packet, dict):
        return False
    try:
        evaluated_at = _parse_time(packet.get("evaluated_at"), "packet.evaluated_at")
        expected = _evaluate_at(issued_offer, current_offer, evaluated_at)
        if _canonical(expected) != _canonical(packet):
            return False
        # Integrity at the packet's bound evaluation time is not enough to keep a
        # previously-current quote current forever. Re-evaluate against the trusted
        # runtime clock and fail closed if a packet that claimed CURRENT has since
        # expired, become superseded, or lost its validity basis.
        if packet.get("status") == "CURRENT_FOR_OWNER_USE":
            live = _evaluate_at(issued_offer, current_offer, _utc_now())
            if live.get("status") != "CURRENT_FOR_OWNER_USE":
                return False
    except GateError:
        return False
    return True


def _load(path: str) -> Any:
    try:
        text = Path(path).read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise GateError(f"cannot read {path}: {exc}") from None
    return strict_json_loads(text)


def _write_new(path: str, value: Any) -> None:
    target = Path(path)
    try:
        with target.open("xb") as fh:
            fh.write(_canonical(value))
    except FileExistsError:
        raise GateError(f"refusing to overwrite existing output: {path}") from None
    except OSError as exc:
        raise GateError(f"cannot write {path}: {exc}") from None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Proposal validity / requote owner-review gate")
    sub = parser.add_subparsers(dest="command", required=True)
    compile_p = sub.add_parser("compile")
    compile_p.add_argument("--issued", required=True)
    compile_p.add_argument("--current", required=True)
    compile_p.add_argument("--out", required=True)
    verify_p = sub.add_parser("verify")
    verify_p.add_argument("--issued", required=True)
    verify_p.add_argument("--current", required=True)
    verify_p.add_argument("--packet", required=True)
    ns = parser.parse_args(argv)
    try:
        issued = _load(ns.issued)
        current = _load(ns.current)
        if ns.command == "compile":
            _write_new(ns.out, evaluate_offer(issued, current))
            return 0
        packet = _load(ns.packet)
        if not verify_packet(issued, current, packet):
            raise GateError("verification failed")
        print("VERIFIED")
        return 0
    except GateError as exc:
        print(f"ERROR: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
