"""Deterministic custody/temperature/exception evidence evaluation."""
from __future__ import annotations
import copy
import hashlib
from decimal import Decimal
from typing import Any
try:
    from .base import BUNDLE_SCHEMA, RECEIPT_SCHEMA, SCHEMA_VERSION, _fail, _obj, _text, _sha, _decimal_text, canonical_json, sha256_json
    from .normalize import _normalize_contract, _normalize_event, _event_public, _deduplicate
except ImportError:
    from base import BUNDLE_SCHEMA, RECEIPT_SCHEMA, SCHEMA_VERSION, _fail, _obj, _text, _sha, _decimal_text, canonical_json, sha256_json
    from normalize import _normalize_contract, _normalize_event, _event_public, _deduplicate

def evaluate_bundle(raw_bundle: Any) -> dict[str, Any]:
    bundle = _obj(raw_bundle, "bundle")
    if bundle.get("schema") != BUNDLE_SCHEMA:
        _fail("INVALID_INPUT", f"bundle.schema must be {BUNDLE_SCHEMA}")
    shipment = _obj(bundle.get("shipment"), "shipment")
    shipment_id = _text(shipment.get("shipment_id"), "shipment.shipment_id", max_len=160)
    fingerprint = _sha(shipment.get("fingerprint_sha256"), "shipment.fingerprint_sha256")
    contract = _normalize_contract(bundle.get("contract"))
    raw_events = bundle.get("events")
    if not isinstance(raw_events, list) or not raw_events or len(raw_events) > 10000:
        _fail("INVALID_INPUT", "events must contain 1-10000 entries")
    normalized = [_normalize_event(event, index) for index, event in enumerate(raw_events)]
    events, duplicate_count = _deduplicate(normalized)
    events.sort(key=lambda e: (e["_occurred_dt"], e["source_system"], e["source_event_id"], e["event_id"]))

    reasons: set[str] = set()
    event_map = {event["event_id"]: event for event in events}
    allowed_sources = set(contract["allowed_source_systems"])

    for event in events:
        if event["shipment_id"] != shipment_id:
            reasons.add("SHIPMENT_ID_MISMATCH")
        if event["shipment_fingerprint_sha256"] != fingerprint:
            reasons.add("SHIPMENT_FINGERPRINT_MISMATCH")
        if event["source_system"] not in allowed_sources:
            reasons.add("UNKNOWN_SOURCE_SYSTEM")

    transfers = [e for e in events if e["kind"] == "custody_transfer"]
    transfer_timestamps: dict[str, int] = {}
    for transfer in transfers:
        transfer_timestamps[transfer["occurred_at"]] = transfer_timestamps.get(transfer["occurred_at"], 0) + 1
    if any(count > 1 for count in transfer_timestamps.values()):
        reasons.add("AMBIGUOUS_SIMULTANEOUS_CUSTODY_TRANSFERS")

    current_custodian = contract["initial_custodian"]
    custody_history: list[dict[str, Any]] = []
    for transfer in transfers:
        if transfer["from_custodian"] != current_custodian:
            reasons.add("CUSTODY_CHAIN_DISCONTINUITY")
        if transfer["from_custodian"] == transfer["to_custodian"]:
            reasons.add("CUSTODY_NOOP_TRANSFER")
        current_custodian = transfer["to_custodian"]
        custody_history.append({
            "event_id": transfer["event_id"],
            "occurred_at": transfer["occurred_at"],
            "from_custodian": transfer["from_custodian"],
            "to_custodian": transfer["to_custodian"],
            "actor_id": transfer["actor_id"],
            "location_id": transfer["location_id"],
            "temperature_event_id": transfer["temperature_event_id"],
        })

    if len(transfers) < contract["minimum_custody_transfers"]:
        reasons.add("INSUFFICIENT_CUSTODY_TRANSFERS")
    required_final = contract["required_final_custodian"]
    if required_final is not None and current_custodian != required_final:
        reasons.add("FINAL_CUSTODIAN_MISMATCH")

    temp_policy = contract["temperature"]
    min_c = Decimal(temp_policy["min_c"])
    max_c = Decimal(temp_policy["max_c"])
    window = temp_policy["max_evidence_age_seconds"]
    temperature_bindings: list[dict[str, Any]] = []
    for transfer in transfers:
        temp_id = transfer["temperature_event_id"]
        if temp_id is None:
            if temp_policy["required_for_each_transfer"]:
                reasons.add("MISSING_TEMPERATURE_EVIDENCE")
            continue
        sample = event_map.get(temp_id)
        if sample is None:
            reasons.add("MISSING_TEMPERATURE_EVIDENCE")
            continue
        if sample["kind"] != "temperature":
            reasons.add("INVALID_TEMPERATURE_EVIDENCE_KIND")
            continue
        delta_seconds = abs((sample["_occurred_dt"] - transfer["_occurred_dt"]).total_seconds())
        sample_temp = Decimal(sample["temperature_c"])
        if delta_seconds > window:
            reasons.add("STALE_TEMPERATURE_EVIDENCE")
        if not (min_c <= sample_temp <= max_c):
            reasons.add("TEMPERATURE_OUT_OF_RANGE")
        temperature_bindings.append({
            "transfer_event_id": transfer["event_id"],
            "temperature_event_id": sample["event_id"],
            "temperature_c": sample["temperature_c"],
            "sensor_id": sample["sensor_id"],
            "delta_seconds": _decimal_text(Decimal(str(delta_seconds))),
        })

    open_exceptions: dict[str, dict[str, Any]] = {}
    exception_history: list[dict[str, Any]] = []
    for event in events:
        if event["kind"] == "exception_open":
            exception_id = event["exception_id"]
            if exception_id in open_exceptions:
                reasons.add("AMBIGUOUS_EXCEPTION_OPEN")
            else:
                open_exceptions[exception_id] = event
            exception_history.append({"event_id": event["event_id"], "exception_id": exception_id, "action": "OPEN", "occurred_at": event["occurred_at"]})
        elif event["kind"] == "exception_resolve":
            exception_id = event["exception_id"]
            if exception_id not in open_exceptions:
                reasons.add("EXCEPTION_RESOLVE_WITHOUT_OPEN")
            else:
                del open_exceptions[exception_id]
            exception_history.append({"event_id": event["event_id"], "exception_id": exception_id, "action": "RESOLVE", "occurred_at": event["occurred_at"]})
    if open_exceptions:
        reasons.add("UNRESOLVED_EXCEPTION")

    public_events = [_event_public(event) for event in events]
    event_digests = [{"event_id": event["event_id"], "sha256": sha256_json(event)} for event in public_events]
    lineage = [{"event_id": e["event_id"], "source_system": e["source_system"], "source_event_id": e["source_event_id"]} for e in public_events]
    decision = "HOLD" if reasons else "PASS_EVIDENCE"

    core = {
        "schema": RECEIPT_SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "decision": decision,
        "reasons": sorted(reasons),
        "shipment": {"shipment_id": shipment_id, "fingerprint_sha256": fingerprint},
        "contract_sha256": sha256_json(contract),
        "canonical_events_sha256": sha256_json(public_events),
        "input_event_count": len(raw_events),
        "unique_event_count": len(events),
        "exact_duplicate_count": duplicate_count,
        "canonical_event_ids": [event["event_id"] for event in public_events],
        "event_digests": event_digests,
        "source_lineage_sha256": sha256_json(lineage),
        "custody": {
            "initial_custodian": contract["initial_custodian"],
            "current_custodian": current_custodian,
            "required_final_custodian": required_final,
            "transfers": custody_history,
        },
        "temperature_bindings": temperature_bindings,
        "exception_history": exception_history,
        "open_exception_ids": sorted(open_exceptions),
        "authority": {
            "clinical_release": False,
            "regulatory_compliance": False,
            "route_authorized": False,
            "dispatch_authorized": False,
            "temperature_excursion_disposition": False,
            "buyer_acceptance": False,
            "production_mutation": False,
        },
    }
    return {**core, "receipt_sha256": sha256_json(core)}


def verify_receipt(receipt: Any) -> bool:
    if not isinstance(receipt, dict) or receipt.get("schema") != RECEIPT_SCHEMA:
        return False
    digest = receipt.get("receipt_sha256")
    if not isinstance(digest, str) or len(digest) != 64:
        return False
    core = copy.deepcopy(receipt)
    core.pop("receipt_sha256", None)
    return hashlib.sha256(canonical_json(core).encode("utf-8")).hexdigest() == digest.lower()
