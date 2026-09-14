from __future__ import annotations

import hmac
from datetime import datetime, timezone
from typing import Any, Mapping, Optional

from .model import (
    RECEIPT_SCHEMA,
    CapacityError,
    _normalize_demands,
    _normalize_policy,
    _normalize_reservations,
    _parse_utc,
    _require_dict,
    _require_sha,
    _utc_text,
    canonical_json,
    read_regular_file,
    sha256_hex,
    strict_json_loads,
    write_exclusive,
)

_RETAINED_ROOT_BLOCKER = "RETAINED_ROOT_AUTHORITY_UNAVAILABLE"


def _snapshot_blockers(policy: dict[str, Any], demand: dict[str, Any], reservations: dict[str, Any], now: datetime) -> list[str]:
    blockers: list[str] = []
    max_age = policy["max_age_seconds"]
    for label, text in (("POLICY", policy["snapshot_at"]), ("DEMAND", demand["snapshot_at"]), ("RESERVATIONS", reservations["snapshot_at"])):
        ts = _parse_utc(text, f"{label.lower()} snapshot")
        age = (now - ts).total_seconds()
        if age < 0:
            blockers.append(f"{label}_SNAPSHOT_FUTURE")
        elif age > max_age:
            blockers.append(f"{label}_SNAPSHOT_STALE")
    return sorted(blockers)


def _same_deal_identity(deal: Mapping[str, Any], reservation: Mapping[str, Any]) -> bool:
    return (
        deal["deal_id"] == reservation["deal_id"]
        and deal["buyer_id"] == reservation["buyer_id"]
        and deal["opportunity_id"] == reservation["opportunity_id"]
        and deal["service_class"] == reservation["service_class"]
        and deal["requested_units"] == reservation["units"]
        and deal["source_receipt_sha256"] == reservation["source_receipt_sha256"]
    )


def _trusted_now(now: Optional[datetime]) -> datetime:
    if now is None:
        return datetime.now(timezone.utc).replace(microsecond=0)
    if not isinstance(now, datetime) or now.tzinfo is None or now.utcoffset() is None:
        raise CapacityError("trusted time must be timezone-aware")
    return now.astimezone(timezone.utc).replace(microsecond=0)


def _allocation_core(policy: dict[str, Any], demand: dict[str, Any], reservations: dict[str, Any], now: datetime) -> dict[str, Any]:
    if demand["policy_id"] != policy["policy_id"] or reservations["policy_id"] != policy["policy_id"]:
        raise CapacityError("policy_id mismatch across generations")

    slots = {row["slot_id"]: row for row in policy["slots"]}
    deals = {row["deal_id"]: row for row in demand["deals"]}
    remaining = {slot_id: row["capacity_units"] for slot_id, row in slots.items()}
    active_by_deal: dict[str, dict[str, Any]] = {}
    blockers = _snapshot_blockers(policy, demand, reservations, now)

    for deal in demand["deals"]:
        if deal["stage"] in {"BUYER_ACCEPTED", "FUNDED_TO_START"}:
            accepted_at = _parse_utc(deal["accepted_at"], "deal.accepted_at")
            if accepted_at > now:
                blockers.append("DEAL_ACCEPTED_AT_FUTURE")

    for reservation in reservations["reservations"]:
        if reservation["state"] != "ACTIVE":
            continue
        slot = slots.get(reservation["slot_id"])
        if slot is None:
            blockers.append("ACTIVE_RESERVATION_UNKNOWN_SLOT")
            continue
        if reservation["service_class"] != slot["service_class"]:
            blockers.append("ACTIVE_RESERVATION_SERVICE_MISMATCH")
            continue

        # Corrupt/rebound/orphan reservations still consume capacity until
        # reconciled; invalid lineage must never free scarce capacity.
        remaining[reservation["slot_id"]] -= reservation["units"]
        if remaining[reservation["slot_id"]] < 0:
            blockers.append("ACTIVE_RESERVATION_OVERDRAW")
        if _parse_utc(slot["ends_at"], "slot.ends_at") <= now:
            blockers.append("ACTIVE_RESERVATION_SLOT_ENDED")

        if reservation["deal_id"] in active_by_deal:
            blockers.append("DEAL_RESERVATION_COLLISION")
        else:
            active_by_deal[reservation["deal_id"]] = reservation

        deal = deals.get(reservation["deal_id"])
        if deal is None:
            blockers.append("ACTIVE_RESERVATION_ORPHAN_DEAL")
        elif not _same_deal_identity(deal, reservation):
            blockers.append("ACTIVE_RESERVATION_DEAL_REBINDING")

    blockers = sorted(set(blockers))
    hard_block = bool(blockers)
    decisions: list[dict[str, Any]] = []

    eligible: list[dict[str, Any]] = []
    for deal in demand["deals"]:
        if deal["stage"] not in {"BUYER_ACCEPTED", "FUNDED_TO_START"}:
            decisions.append({
                "deal_id": deal["deal_id"],
                "decision": "INELIGIBLE",
                "slot_id": None,
                "units": 0,
                "existing_reservation": False,
                "reasons": ["STAGE_NOT_CAPACITY_ELIGIBLE"],
            })
            continue
        eligible.append(deal)

    def rank(deal: Mapping[str, Any]) -> tuple[Any, ...]:
        stage_rank = 0 if deal["stage"] == "FUNDED_TO_START" else 1
        return (
            stage_rank,
            _parse_utc(deal["deadline"], "deal.deadline"),
            _parse_utc(deal["accepted_at"], "deal.accepted_at"),
            deal["deal_id"],
        )

    for deal in sorted(eligible, key=rank):
        existing = active_by_deal.get(deal["deal_id"])
        if hard_block:
            decisions.append({
                "deal_id": deal["deal_id"],
                "decision": "CAPACITY_HOLD",
                "slot_id": existing["slot_id"] if existing else None,
                "units": existing["units"] if existing else 0,
                "existing_reservation": bool(existing),
                "reasons": ["GLOBAL_CAPACITY_STATE_HOLD"] + blockers,
            })
            continue
        if existing is not None:
            decisions.append({
                "deal_id": deal["deal_id"],
                "decision": "ALLOCATED_FOR_OWNER_REVIEW",
                "slot_id": existing["slot_id"],
                "units": existing["units"],
                "existing_reservation": True,
                "reasons": ["EXISTING_ACTIVE_RESERVATION"],
            })
            continue

        matching_service = [slot for slot in slots.values() if slot["service_class"] == deal["service_class"]]
        live_matching_service = [
            slot for slot in matching_service
            if _parse_utc(slot["ends_at"], "slot.ends_at") > now
        ]
        window_ok = [
            slot for slot in live_matching_service
            if _parse_utc(slot["starts_at"], "slot.starts_at") >= _parse_utc(deal["not_before"], "deal.not_before")
            and _parse_utc(slot["ends_at"], "slot.ends_at") <= _parse_utc(deal["deadline"], "deal.deadline")
        ]
        capacity_ok = [slot for slot in window_ok if remaining[slot["slot_id"]] >= deal["requested_units"]]
        if capacity_ok:
            chosen = sorted(capacity_ok, key=lambda s: (_parse_utc(s["starts_at"], "slot.starts_at"), _parse_utc(s["ends_at"], "slot.ends_at"), s["slot_id"]))[0]
            remaining[chosen["slot_id"]] -= deal["requested_units"]
            decisions.append({
                "deal_id": deal["deal_id"],
                "decision": "ALLOCATED_FOR_OWNER_REVIEW",
                "slot_id": chosen["slot_id"],
                "units": deal["requested_units"],
                "existing_reservation": False,
                "reasons": ["COMPATIBLE_CAPACITY_AVAILABLE"],
            })
        else:
            if not matching_service:
                reason = "NO_SERVICE_CLASS_SLOT"
            elif not window_ok:
                reason = "NO_SLOT_WITHIN_DEAL_WINDOW"
            else:
                reason = "INSUFFICIENT_REMAINING_CAPACITY"
            decisions.append({
                "deal_id": deal["deal_id"],
                "decision": "CAPACITY_HOLD",
                "slot_id": None,
                "units": 0,
                "existing_reservation": False,
                "reasons": [reason],
            })

    decisions.sort(key=lambda r: r["deal_id"])
    slot_balances = [
        {
            "slot_id": slot_id,
            "capacity_units": slots[slot_id]["capacity_units"],
            "remaining_units": remaining[slot_id],
        }
        for slot_id in sorted(slots)
    ]
    return {
        "global_blockers": blockers,
        "decisions": decisions,
        "slot_balances": slot_balances,
    }


def compile_bytes(
    policy_bytes: bytes,
    demand_bytes: bytes,
    reservations_bytes: bytes,
    *,
    expected_policy_sha256: str,
    expected_demand_sha256: str,
    expected_reservations_sha256: str,
    now: Optional[datetime] = None,
) -> dict[str, Any]:
    """Compile a caller-bound historical/test receipt, never CURRENT authority."""
    expected_policy_sha256 = _require_sha(expected_policy_sha256, "expected_policy_sha256")
    expected_demand_sha256 = _require_sha(expected_demand_sha256, "expected_demand_sha256")
    expected_reservations_sha256 = _require_sha(expected_reservations_sha256, "expected_reservations_sha256")
    actual_policy = sha256_hex(policy_bytes)
    actual_demand = sha256_hex(demand_bytes)
    actual_reservations = sha256_hex(reservations_bytes)
    if not hmac.compare_digest(actual_policy, expected_policy_sha256):
        raise CapacityError("policy bytes do not match retained SHA-256")
    if not hmac.compare_digest(actual_demand, expected_demand_sha256):
        raise CapacityError("demand bytes do not match retained SHA-256")
    if not hmac.compare_digest(actual_reservations, expected_reservations_sha256):
        raise CapacityError("reservation bytes do not match retained SHA-256")

    policy = _normalize_policy(strict_json_loads(policy_bytes))
    demand = _normalize_demands(strict_json_loads(demand_bytes))
    reservations = _normalize_reservations(strict_json_loads(reservations_bytes))
    trusted_now = _trusted_now(now)
    core = _allocation_core(policy, demand, reservations, trusted_now)
    policy_semantic_sha256 = sha256_hex(canonical_json(policy))
    demand_semantic_sha256 = sha256_hex(canonical_json(demand))
    reservations_semantic_sha256 = sha256_hex(canonical_json(reservations))
    allocation_material = {
        "policy_semantic_sha256": policy_semantic_sha256,
        "demand_semantic_sha256": demand_semantic_sha256,
        "reservations_semantic_sha256": reservations_semantic_sha256,
        "policy_id": policy["policy_id"],
        "policy_generation": policy["generation"],
        "demand_generation": demand["generation"],
        "reservations_generation": reservations["generation"],
        "global_blockers": core["global_blockers"],
        "decisions": core["decisions"],
        "slot_balances": core["slot_balances"],
    }
    allocation_digest = sha256_hex(canonical_json(allocation_material))
    historical_state = (
        "HISTORICAL_INTEGRITY_ONLY"
        if not core["global_blockers"]
        else "HISTORICAL_HOLD_CURRENTNESS_OR_RESERVATION_STATE"
    )
    receipt = {
        "schema": RECEIPT_SCHEMA,
        "evaluated_at": _utc_text(trusted_now),
        "current_state": historical_state,
        "policy": {"policy_id": policy["policy_id"], "generation": policy["generation"], "sha256": actual_policy},
        "demand": {"generation": demand["generation"], "sha256": actual_demand},
        "reservations": {"generation": reservations["generation"], "sha256": actual_reservations},
        "global_blockers": core["global_blockers"],
        "decisions": core["decisions"],
        "slot_balances": core["slot_balances"],
        "allocation_sha256": allocation_digest,
        "authority": {
            "buyer_contact_authorized": False,
            "schedule_commitment_authorized": False,
            "provider_send_authorized": False,
            "payment_mutation_authorized": False,
            "contract_acceptance_authorized": False,
            "staffing_commitment_authorized": False,
            "deployment_authorized": False,
            "revenue_recognition_authorized": False,
        },
    }
    receipt["receipt_sha256"] = sha256_hex(canonical_json(receipt))
    return receipt


def _root_authority_hold(receipt: dict[str, Any]) -> dict[str, Any]:
    blocker = _RETAINED_ROOT_BLOCKER
    global_blockers = sorted(set(receipt["global_blockers"] + [blocker]))
    held: list[dict[str, Any]] = []
    for raw in receipt["decisions"]:
        row = dict(raw)
        if row["decision"] != "INELIGIBLE":
            row["decision"] = "CAPACITY_HOLD"
            row["reasons"] = ["GLOBAL_CAPACITY_STATE_HOLD"] + global_blockers
            if not row["existing_reservation"]:
                row["slot_id"] = None
                row["units"] = 0
        held.append(row)

    receipt = dict(receipt)
    receipt["current_state"] = "HOLD_RETAINED_ROOT_AUTHORITY"
    receipt["global_blockers"] = global_blockers
    receipt["decisions"] = held
    receipt["allocation_sha256"] = sha256_hex(canonical_json({
        "authority_mode": "FAIL_CLOSED_WITHOUT_RETAINED_ROOTS",
        "policy": receipt["policy"],
        "demand": receipt["demand"],
        "reservations": receipt["reservations"],
        "global_blockers": global_blockers,
        "decisions": held,
        "slot_balances": receipt["slot_balances"],
    }))
    receipt.pop("receipt_sha256", None)
    receipt["receipt_sha256"] = sha256_hex(canonical_json(receipt))
    return receipt


def compile_current_bytes(
    policy_bytes: bytes,
    demand_bytes: bytes,
    reservations_bytes: bytes,
) -> dict[str, Any]:
    """Production-current entry point; process UTC and no caller-root authority."""
    candidate = compile_bytes(
        policy_bytes,
        demand_bytes,
        reservations_bytes,
        expected_policy_sha256=sha256_hex(policy_bytes),
        expected_demand_sha256=sha256_hex(demand_bytes),
        expected_reservations_sha256=sha256_hex(reservations_bytes),
        now=None,
    )
    return _root_authority_hold(candidate)


def verify_historical_bytes(
    policy_bytes: bytes,
    demand_bytes: bytes,
    reservations_bytes: bytes,
    receipt_bytes: bytes,
    *,
    expected_policy_sha256: str,
    expected_demand_sha256: str,
    expected_reservations_sha256: str,
) -> bool:
    """Verify only caller-bound historical integrity; never current authority."""
    try:
        receipt = _require_dict(strict_json_loads(receipt_bytes), "receipt")
        if receipt.get("schema") != RECEIPT_SCHEMA:
            return False
        historical_time = _parse_utc(receipt.get("evaluated_at"), "receipt.evaluated_at")
        historical = compile_bytes(
            policy_bytes,
            demand_bytes,
            reservations_bytes,
            expected_policy_sha256=expected_policy_sha256,
            expected_demand_sha256=expected_demand_sha256,
            expected_reservations_sha256=expected_reservations_sha256,
            now=historical_time,
        )
        return hmac.compare_digest(canonical_json(historical), canonical_json(receipt))
    except CapacityError:
        return False


def verify_current_receipt_bytes(
    policy_bytes: bytes,
    demand_bytes: bytes,
    reservations_bytes: bytes,
    receipt_bytes: bytes,
) -> bool:
    """Fail closed until an independent retained-root authority is wired in."""
    try:
        receipt = _require_dict(strict_json_loads(receipt_bytes), "receipt")
        if receipt.get("schema") != RECEIPT_SCHEMA:
            return False
        current = compile_current_bytes(policy_bytes, demand_bytes, reservations_bytes)
        if current["current_state"] != "HOLD_RETAINED_ROOT_AUTHORITY":
            return False
        return False
    except CapacityError:
        return False


def verify_current_bytes(
    policy_bytes: bytes,
    demand_bytes: bytes,
    reservations_bytes: bytes,
    receipt_bytes: bytes,
    *,
    expected_policy_sha256: str,
    expected_demand_sha256: str,
    expected_reservations_sha256: str,
    now: Optional[datetime] = None,
) -> bool:
    """Compatibility name: caller roots/time can never verify CURRENT authority."""
    del now
    if not verify_historical_bytes(
        policy_bytes,
        demand_bytes,
        reservations_bytes,
        receipt_bytes,
        expected_policy_sha256=expected_policy_sha256,
        expected_demand_sha256=expected_demand_sha256,
        expected_reservations_sha256=expected_reservations_sha256,
    ):
        return False
    return False
