"""Input normalization and identity de-duplication for regulated handoff evidence."""
from __future__ import annotations
from typing import Any
try:
    from .base import EVENT_KINDS, _fail, _obj, _text, _sha, _boolean, _integer, _decimal, _decimal_text, _timestamp, sha256_json
except ImportError:
    from base import EVENT_KINDS, _fail, _obj, _text, _sha, _boolean, _integer, _decimal, _decimal_text, _timestamp, sha256_json

def _normalize_contract(raw: Any) -> dict[str, Any]:
    contract = _obj(raw, "contract")
    sources = contract.get("allowed_source_systems")
    if not isinstance(sources, list) or not sources or len(sources) > 64:
        _fail("INVALID_INPUT", "contract.allowed_source_systems must contain 1-64 entries")
    allowed_sources = [_text(v, "allowed_source_systems[]", max_len=120) for v in sources]
    if len(set(allowed_sources)) != len(allowed_sources):
        _fail("INVALID_INPUT", "contract.allowed_source_systems must be unique")

    temp = _obj(contract.get("temperature"), "contract.temperature")
    min_c = _decimal(temp.get("min_c"), "contract.temperature.min_c")
    max_c = _decimal(temp.get("max_c"), "contract.temperature.max_c")
    if min_c > max_c:
        _fail("INVALID_INPUT", "temperature min_c exceeds max_c")
    window = _integer(temp.get("max_evidence_age_seconds"), "contract.temperature.max_evidence_age_seconds", minimum=0, maximum=7 * 86400)

    initial = _text(contract.get("initial_custodian"), "contract.initial_custodian", max_len=160)
    final = contract.get("required_final_custodian")
    final_custodian = None if final in (None, "") else _text(final, "contract.required_final_custodian", max_len=160)
    min_transfers = _integer(contract.get("minimum_custody_transfers", 1), "contract.minimum_custody_transfers", minimum=0, maximum=10000)

    return {
        "allowed_source_systems": sorted(allowed_sources),
        "initial_custodian": initial,
        "required_final_custodian": final_custodian,
        "minimum_custody_transfers": min_transfers,
        "temperature": {
            "min_c": _decimal_text(min_c),
            "max_c": _decimal_text(max_c),
            "max_evidence_age_seconds": window,
            "required_for_each_transfer": _boolean(temp.get("required_for_each_transfer", True), "contract.temperature.required_for_each_transfer"),
        },
    }


def _normalize_event(raw: Any, index: int) -> dict[str, Any]:
    event = _obj(raw, f"events[{index}]")
    kind = _text(event.get("kind"), f"events[{index}].kind", max_len=40).lower()
    if kind not in EVENT_KINDS:
        _fail("INVALID_INPUT", f"events[{index}].kind unsupported")
    occurred_text, occurred_dt = _timestamp(event.get("occurred_at"), f"events[{index}].occurred_at")
    normalized: dict[str, Any] = {
        "event_id": _text(event.get("event_id"), f"events[{index}].event_id", max_len=160),
        "shipment_id": _text(event.get("shipment_id"), f"events[{index}].shipment_id", max_len=160),
        "shipment_fingerprint_sha256": _sha(event.get("shipment_fingerprint_sha256"), f"events[{index}].shipment_fingerprint_sha256"),
        "kind": kind,
        "occurred_at": occurred_text,
        "source_system": _text(event.get("source_system"), f"events[{index}].source_system", max_len=120),
        "source_event_id": _text(event.get("source_event_id"), f"events[{index}].source_event_id", max_len=160),
    }
    normalized["_occurred_dt"] = occurred_dt

    if kind == "custody_transfer":
        normalized.update({
            "from_custodian": _text(event.get("from_custodian"), f"events[{index}].from_custodian", max_len=160),
            "to_custodian": _text(event.get("to_custodian"), f"events[{index}].to_custodian", max_len=160),
            "actor_id": _text(event.get("actor_id"), f"events[{index}].actor_id", max_len=160),
            "location_id": _text(event.get("location_id"), f"events[{index}].location_id", max_len=160),
            "evidence_ref": _text(event.get("evidence_ref"), f"events[{index}].evidence_ref", max_len=300),
        })
        temp_id = event.get("temperature_event_id")
        normalized["temperature_event_id"] = None if temp_id in (None, "") else _text(temp_id, f"events[{index}].temperature_event_id", max_len=160)
    elif kind == "temperature":
        normalized.update({
            "sensor_id": _text(event.get("sensor_id"), f"events[{index}].sensor_id", max_len=160),
            "temperature_c": _decimal_text(_decimal(event.get("temperature_c"), f"events[{index}].temperature_c")),
            "evidence_ref": _text(event.get("evidence_ref"), f"events[{index}].evidence_ref", max_len=300),
        })
    elif kind == "exception_open":
        normalized.update({
            "exception_id": _text(event.get("exception_id"), f"events[{index}].exception_id", max_len=160),
            "code": _text(event.get("code"), f"events[{index}].code", max_len=120),
            "evidence_ref": _text(event.get("evidence_ref"), f"events[{index}].evidence_ref", max_len=300),
        })
    elif kind == "exception_resolve":
        normalized.update({
            "exception_id": _text(event.get("exception_id"), f"events[{index}].exception_id", max_len=160),
            "resolution_ref": _text(event.get("resolution_ref"), f"events[{index}].resolution_ref", max_len=300),
        })
    else:  # checkpoint
        normalized.update({
            "actor_id": _text(event.get("actor_id"), f"events[{index}].actor_id", max_len=160),
            "location_id": _text(event.get("location_id"), f"events[{index}].location_id", max_len=160),
            "evidence_ref": _text(event.get("evidence_ref"), f"events[{index}].evidence_ref", max_len=300),
        })
    return normalized


def _event_public(event: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in event.items() if not k.startswith("_")}


def _deduplicate(events: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int]:
    by_event: dict[str, tuple[str, dict[str, Any]]] = {}
    by_lineage: dict[tuple[str, str], tuple[str, str]] = {}
    duplicate_count = 0
    for event in events:
        public = _event_public(event)
        digest = sha256_json(public)
        event_id = event["event_id"]
        prior = by_event.get(event_id)
        if prior:
            if prior[0] != digest:
                _fail("EVENT_ID_CONFLICT", f"event_id {event_id!r} was reused with changed payload")
            duplicate_count += 1
            continue
        lineage_key = (event["source_system"], event["source_event_id"])
        lineage_prior = by_lineage.get(lineage_key)
        if lineage_prior and lineage_prior != (event_id, digest):
            _fail("SOURCE_LINEAGE_CONFLICT", f"source lineage {lineage_key!r} maps to multiple events")
        by_event[event_id] = (digest, event)
        by_lineage[lineage_key] = (event_id, digest)
    return [entry[1] for entry in by_event.values()], duplicate_count
