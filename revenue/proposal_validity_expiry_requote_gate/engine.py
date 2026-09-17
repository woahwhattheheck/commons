from __future__ import annotations

import datetime as _dt
from typing import Any, Callable

from boundary import GateError, canonical, digest, exact_keys, integer, parse_time, sha, text, validate_tree

STATUSES = {"CURRENT_FOR_OWNER_USE", "EXPIRED_REQUOTE_REQUIRED", "SUPERSEDED", "HOLD_NO_VALIDITY_BASIS", "HOLD_SOURCE_DRIFT"}
EVENT_KINDS = {"AMENDMENT", "REDLINE", "CHANGE_ORDER", "REPRICE", "WITHDRAWAL"}
SOURCE_STATUS_CURRENT = "CURRENT"
_PAYMENT_ACTIVE_STATES = {"PRESENT", "ACTIVE", "LIVE", "CHARGEABLE"}
_ALLOWED_OFFER_KEYS = {"schema_version", "offer_id", "source_generation", "source_digest", "pricing_revision", "currency", "scope", "economics", "issued_on", "validity", "buyer_deadline", "payment_rail"}
_ALLOWED_CURRENT_KEYS = {"schema_version", "offer_id", "source_generation", "source_digest", "source_status", "source_observed_at", "pricing_revision", "currency", "scope", "economics", "payment_rail", "superseding_events"}
_ALLOWED_VALIDITY_KEYS = {"mode", "valid_until", "valid_for_seconds"}
_ALLOWED_EVENT_KEYS = {"kind", "event_id", "observed_at", "applies_to_offer_id", "source_generation", "source_digest"}


def _build_trusted_clock() -> Callable[[], _dt.datetime]:
    real_now, real_utc = _dt.datetime.now, _dt.timezone.utc
    return lambda: real_now(real_utc)


_TRUSTED_UTC_NOW = _build_trusted_clock()


def _utc_now() -> _dt.datetime:
    return _TRUSTED_UTC_NOW()


def _currency(value: Any) -> str:
    raw = text(value, "currency")
    if len(raw) != 3 or not raw.isascii() or not raw.isalpha() or raw.upper() != raw:
        raise GateError("currency: expected uppercase ISO-like three-letter code")
    return raw


def _scope(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or not value:
        raise GateError(f"{label}: expected non-empty object")
    validate_tree(value, label)
    return value


def _economics(value: Any, label: str) -> dict[str, Any]:
    value = _scope(value, label)
    for key, item in value.items():
        if key.endswith("_minor_units"):
            integer(item, f"{label}.{key}", minimum=0)
    return value


def _rail(value: Any, label: str) -> dict[str, Any] | None:
    if value is None:
        return None
    if not isinstance(value, dict) or not value:
        raise GateError(f"{label}: expected non-empty object or null")
    validate_tree(value, label)
    for key in ("state", "checkout_url", "rail_id"):
        if key in value:
            text(value[key], f"{label}.{key}")
    return value


def _validate_offer(offer: Any) -> dict[str, Any]:
    if not isinstance(offer, dict):
        raise GateError("issued_offer: expected object")
    exact_keys(offer, _ALLOWED_OFFER_KEYS, "issued_offer")
    if offer.get("schema_version") != 1:
        raise GateError("issued_offer.schema_version: expected 1")
    text(offer.get("offer_id"), "issued_offer.offer_id")
    text(offer.get("source_generation"), "issued_offer.source_generation")
    if offer.get("source_digest") is not None:
        digest(offer["source_digest"], "issued_offer.source_digest")
    text(offer.get("pricing_revision"), "issued_offer.pricing_revision")
    _currency(offer.get("currency")); _scope(offer.get("scope"), "issued_offer.scope"); _economics(offer.get("economics"), "issued_offer.economics")
    parse_time(offer.get("issued_on"), "issued_offer.issued_on")
    validity = offer.get("validity")
    if not isinstance(validity, dict):
        raise GateError("issued_offer.validity: expected object")
    exact_keys(validity, _ALLOWED_VALIDITY_KEYS, "issued_offer.validity")
    mode = text(validity.get("mode"), "issued_offer.validity.mode")
    if mode == "VALID_UNTIL":
        if set(validity) != {"mode", "valid_until"}: raise GateError("VALID_UNTIL requires exactly mode + valid_until")
        parse_time(validity["valid_until"], "issued_offer.validity.valid_until")
    elif mode == "VALID_FOR_SECONDS":
        if set(validity) != {"mode", "valid_for_seconds"}: raise GateError("VALID_FOR_SECONDS requires exactly mode + valid_for_seconds")
        integer(validity["valid_for_seconds"], "issued_offer.validity.valid_for_seconds", minimum=1)
    elif mode == "NO_EXPIRY_STATED":
        if set(validity) != {"mode"}: raise GateError("NO_EXPIRY_STATED accepts only mode")
    else:
        raise GateError("issued_offer.validity.mode: unsupported mode")
    if offer.get("buyer_deadline") is not None: parse_time(offer["buyer_deadline"], "issued_offer.buyer_deadline")
    _rail(offer.get("payment_rail"), "issued_offer.payment_rail")
    return offer


def _validate_current(current: Any) -> dict[str, Any]:
    if not isinstance(current, dict): raise GateError("current_offer: expected object")
    exact_keys(current, _ALLOWED_CURRENT_KEYS, "current_offer")
    if current.get("schema_version") != 1: raise GateError("current_offer.schema_version: expected 1")
    text(current.get("offer_id"), "current_offer.offer_id"); text(current.get("source_generation"), "current_offer.source_generation")
    if current.get("source_digest") is not None: digest(current["source_digest"], "current_offer.source_digest")
    if current.get("source_status") is not None: text(current["source_status"], "current_offer.source_status")
    if current.get("source_observed_at") is not None: parse_time(current["source_observed_at"], "current_offer.source_observed_at")
    text(current.get("pricing_revision"), "current_offer.pricing_revision"); _currency(current.get("currency")); _scope(current.get("scope"), "current_offer.scope"); _economics(current.get("economics"), "current_offer.economics"); _rail(current.get("payment_rail"), "current_offer.payment_rail")
    events = current.get("superseding_events")
    if not isinstance(events, list): raise GateError("current_offer.superseding_events: expected list")
    seen: set[str] = set()
    for idx, event in enumerate(events):
        if not isinstance(event, dict): raise GateError(f"current_offer.superseding_events[{idx}]: expected object")
        exact_keys(event, _ALLOWED_EVENT_KEYS, f"current_offer.superseding_events[{idx}]")
        if text(event.get("kind"), f"event[{idx}].kind") not in EVENT_KINDS: raise GateError(f"event[{idx}].kind: unsupported kind")
        event_id = text(event.get("event_id"), f"event[{idx}].event_id")
        if event_id in seen: raise GateError("duplicate superseding event_id")
        seen.add(event_id); parse_time(event.get("observed_at"), f"event[{idx}].observed_at"); text(event.get("applies_to_offer_id"), f"event[{idx}].applies_to_offer_id"); text(event.get("source_generation"), f"event[{idx}].source_generation")
        if event.get("source_digest") is not None: digest(event["source_digest"], f"event[{idx}].source_digest")
    return current


def _effective_expiry(offer: dict[str, Any]) -> tuple[_dt.datetime | None, str]:
    issued = parse_time(offer["issued_on"], "issued_offer.issued_on"); validity = offer["validity"]; mode = validity["mode"]
    if mode == "NO_EXPIRY_STATED": expiry, basis = None, "NO_EXPIRY_STATED"
    elif mode == "VALID_UNTIL": expiry, basis = parse_time(validity["valid_until"], "issued_offer.validity.valid_until"), "EXPLICIT_VALID_UNTIL"
    else: expiry, basis = issued + _dt.timedelta(seconds=integer(validity["valid_for_seconds"], "valid_for_seconds", minimum=1)), "ISSUED_PLUS_VALID_FOR_SECONDS"
    if offer.get("buyer_deadline") is not None:
        deadline = parse_time(offer["buyer_deadline"], "issued_offer.buyer_deadline")
        if expiry is None or deadline < expiry: expiry, basis = deadline, f"{basis}+BUYER_DEADLINE_CAP"
    return expiry, basis


def _diff(issued: dict[str, Any], current: dict[str, Any]) -> list[dict[str, Any]]:
    return [{"field": f, "issued": issued.get(f), "current": current.get(f)} for f in ("source_generation", "source_digest", "pricing_revision", "currency", "scope", "economics") if issued.get(f) != current.get(f)]


def _source_problem(issued: dict[str, Any], current: dict[str, Any], now: _dt.datetime) -> str | None:
    if any(current.get(k) is None for k in ("source_digest", "source_status", "source_observed_at")) or issued.get("source_digest") is None: return "controlling source currentness evidence is incomplete"
    if current["source_status"] != SOURCE_STATUS_CURRENT: return "controlling source status is not CURRENT"
    observed, issued_at = parse_time(current["source_observed_at"], "current_offer.source_observed_at"), parse_time(issued["issued_on"], "issued_offer.issued_on")
    if observed < issued_at: return "controlling source observation predates offer issuance"
    if observed > now: return "controlling source observation is in the future"
    return None


def _payment_problem(issued: dict[str, Any], current: dict[str, Any]) -> str | None:
    a, b = issued.get("payment_rail"), current.get("payment_rail")
    if a is None and b is None: return None
    if a is None or b is None or canonical(a) != canonical(b): return "payment road identity/state drift"
    state = b.get("state") if isinstance(b, dict) else None
    if state is not None and text(state, "current_offer.payment_rail.state").upper() not in _PAYMENT_ACTIVE_STATES: return "payment road is not current/active"
    return None


def _event_problem(issued: dict[str, Any], current: dict[str, Any]) -> str | None:
    issued_at = parse_time(issued["issued_on"], "issued_offer.issued_on")
    if current.get("source_observed_at") is None: return None
    source_observed = parse_time(current["source_observed_at"], "current_offer.source_observed_at")
    for event in current["superseding_events"]:
        if event["applies_to_offer_id"] != issued["offer_id"]: continue
        event_at = parse_time(event["observed_at"], "event.observed_at")
        if event_at <= issued_at: continue
        if event_at > source_observed: return "superseding evidence postdates controlling source observation"
        if event.get("source_generation") != current.get("source_generation"): return "superseding evidence source generation is not current"
        if event.get("source_digest") != current.get("source_digest"): return "superseding evidence source digest is not current"
    return None


def _superseders(issued: dict[str, Any], current: dict[str, Any]) -> list[dict[str, Any]]:
    issued_at = parse_time(issued["issued_on"], "issued_offer.issued_on")
    rows = [e for e in current["superseding_events"] if e["applies_to_offer_id"] == issued["offer_id"] and parse_time(e["observed_at"], "event.observed_at") > issued_at]
    return sorted(rows, key=lambda e: (e["observed_at"], e["event_id"]))


def _evaluate_at(issued_offer: Any, current_offer: Any, now: _dt.datetime) -> dict[str, Any]:
    issued, current = _validate_offer(issued_offer), _validate_current(current_offer)
    if now.tzinfo is None or now.utcoffset() is None: raise GateError("runtime clock must be timezone-aware")
    now = now.astimezone(_dt.timezone.utc)
    if issued["offer_id"] != current["offer_id"]: raise GateError("offer_id mismatch")
    issued_at = parse_time(issued["issued_on"], "issued_offer.issued_on"); changes = _diff(issued, current); expiry, basis = _effective_expiry(issued)
    sp = _source_problem(issued, current, now); ep = None if sp else _event_problem(issued, current); pp = None if sp else _payment_problem(issued, current); supers = [] if sp or ep else _superseders(issued, current)
    semantic = [r for r in changes if r["field"] in {"pricing_revision", "currency", "scope", "economics"}]; identity = [r for r in changes if r["field"] in {"source_generation", "source_digest"}]
    if sp: status, reason = "HOLD_SOURCE_DRIFT", sp
    elif ep: status, reason = "HOLD_SOURCE_DRIFT", ep
    elif pp: status, reason = "HOLD_SOURCE_DRIFT", pp
    elif supers: status, reason = "SUPERSEDED", "later source-bound amendment/redline/change-order/reprice/withdrawal evidence applies to this offer"
    elif semantic: status, reason = "SUPERSEDED", "current offer economics/scope/currency/revision differ from issued offer"
    elif identity: status, reason = "HOLD_SOURCE_DRIFT", "controlling source generation/digest changed without an explicit commercial delta"
    elif expiry is not None and expiry < issued_at: status, reason = "HOLD_NO_VALIDITY_BASIS", "effective validity endpoint predates issuance"
    elif expiry is not None and now > expiry: status, reason = "EXPIRED_REQUOTE_REQUIRED", "effective validity endpoint has passed"
    elif issued["validity"]["mode"] == "NO_EXPIRY_STATED": status, reason = "HOLD_NO_VALIDITY_BASIS", "offer states no expiry; owner review is required before reuse"
    elif now < issued_at: status, reason = "HOLD_NO_VALIDITY_BASIS", "runtime clock precedes offer issuance"
    else: status, reason = "CURRENT_FOR_OWNER_USE", "source/economics/payment road unchanged and explicit validity remains current"
    delta = {"offer_id": issued["offer_id"], "status": "PROPOSED_NOT_ACCEPTED", "issued_source_generation": issued["source_generation"], "issued_source_digest": issued.get("source_digest"), "current_source_generation": current["source_generation"], "current_source_digest": current.get("source_digest"), "current_source_status": current.get("source_status"), "current_source_observed_at": current.get("source_observed_at"), "changes": changes, "superseding_events": supers, "payment_road_current": pp is None, "buyer_acceptance_inferred": False, "payment_authority_inferred": False}
    body = {"schema_version": 1, "status": status, "reason": reason, "offer_id": issued["offer_id"], "evaluated_at": now.isoformat().replace("+00:00", "Z"), "validity_basis": basis, "effective_valid_until": None if expiry is None else expiry.isoformat().replace("+00:00", "Z"), "issued_offer_sha256": sha(issued), "current_offer_sha256": sha(current), "scope_sha256": sha(issued["scope"]), "economics_sha256": sha(issued["economics"]), "requote_delta": delta, "authority": {"owner_review_only": True, "buyer_acceptance": False, "contract_signed": False, "checkout_or_payment_rail_is_acceptance": False, "payment_authorized": False, "revenue_recognized": False, "outbound_authorized": False}}
    body["receipt_sha256"] = sha(body); return body


def _projection(packet: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in packet.items() if k not in {"evaluated_at", "receipt_sha256"}}


def _verify_packet_at(issued_offer: Any, current_offer: Any, packet: Any, now: _dt.datetime) -> bool:
    if not isinstance(packet, dict): return False
    try:
        if now.tzinfo is None or now.utcoffset() is None: return False
        now = now.astimezone(_dt.timezone.utc); evaluated_at = parse_time(packet.get("evaluated_at"), "packet.evaluated_at")
        if evaluated_at > now: return False
        expected = _evaluate_at(issued_offer, current_offer, evaluated_at)
        if canonical(expected) != canonical(packet): return False
        return canonical(_projection(expected)) == canonical(_projection(_evaluate_at(issued_offer, current_offer, now)))
    except GateError:
        return False


def _build_public_api(clock: Callable[[], _dt.datetime]):
    return (lambda issued, current: _evaluate_at(issued, current, clock())), (lambda issued, current, packet: _verify_packet_at(issued, current, packet, clock()))


evaluate_offer, verify_packet = _build_public_api(_TRUSTED_UTC_NOW)
