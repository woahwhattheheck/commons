"""Deterministic, offline swarm work-order allocation.

This module is intentionally authority-limited:
- it never performs network calls;
- it never sends external contact;
- outbound work requires an explicit active MUSE lease in the input;
- live CLAIM leases always fence an order from reassignment.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

SCHEMA_VERSION = "swarm-capacity-dispatcher/v1"
OPEN = "OPEN"
HOLD = "HOLD"
DNR = "DNR"


class ContractError(ValueError):
    """Raised for malformed dispatcher input."""


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _require_id(row: dict[str, Any], kind: str) -> str:
    value = row.get("id")
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ContractError(f"{kind}.id must be a non-empty trimmed string")
    return value


def _as_nonnegative_int(value: Any, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ContractError(f"{field} must be a non-negative integer")
    return value


def _as_bool(value: Any, field: str) -> bool:
    if not isinstance(value, bool):
        raise ContractError(f"{field} must be a boolean")
    return value


def _capabilities(value: Any, field: str) -> tuple[str, ...]:
    if not isinstance(value, list) or any(
        not isinstance(item, str) or not item.strip() or item != item.strip()
        for item in value
    ):
        raise ContractError(f"{field} must be a list of non-empty trimmed strings")
    if len(set(value)) != len(value):
        raise ContractError(f"{field} must not contain duplicates")
    return tuple(sorted(value))


def normalize_workers(workers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not isinstance(workers, list):
        raise ContractError("workers must be a list")
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for raw in workers:
        if not isinstance(raw, dict):
            raise ContractError("worker rows must be objects")
        wid = _require_id(raw, "worker")
        if wid in seen:
            raise ContractError(f"duplicate worker id: {wid}")
        seen.add(wid)
        out.append(
            {
                "id": wid,
                "capabilities": list(_capabilities(raw.get("capabilities", []), f"worker[{wid}].capabilities")),
                "capacity": _as_nonnegative_int(raw.get("capacity", 0), f"worker[{wid}].capacity"),
                "token_budget": _as_nonnegative_int(raw.get("token_budget", 0), f"worker[{wid}].token_budget"),
                "active": _as_bool(raw.get("active", True), f"worker[{wid}].active"),
            }
        )
    return sorted(out, key=lambda row: row["id"])


def normalize_orders(orders: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not isinstance(orders, list):
        raise ContractError("orders must be a list")
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for raw in orders:
        if not isinstance(raw, dict):
            raise ContractError("order rows must be objects")
        oid = _require_id(raw, "order")
        if oid in seen:
            raise ContractError(f"duplicate order id: {oid}")
        seen.add(oid)
        status = raw.get("status", OPEN)
        if status not in {OPEN, HOLD, DNR}:
            raise ContractError(f"order[{oid}].status must be OPEN, HOLD, or DNR")
        preferred = raw.get("preferred_workers", [])
        if not isinstance(preferred, list) or any(
            not isinstance(x, str) or not x.strip() or x != x.strip() for x in preferred
        ):
            raise ContractError(f"order[{oid}].preferred_workers must be a string list")
        if len(set(preferred)) != len(preferred):
            raise ContractError(f"order[{oid}].preferred_workers must not contain duplicates")
        out.append(
            {
                "id": oid,
                "required_capabilities": list(
                    _capabilities(raw.get("required_capabilities", []), f"order[{oid}].required_capabilities")
                ),
                "priority": _as_nonnegative_int(raw.get("priority", 0), f"order[{oid}].priority"),
                "revenue_usd_expected": _as_nonnegative_int(
                    raw.get("revenue_usd_expected", 0), f"order[{oid}].revenue_usd_expected"
                ),
                "impact": _as_nonnegative_int(raw.get("impact", 0), f"order[{oid}].impact"),
                "urgency": _as_nonnegative_int(raw.get("urgency", 0), f"order[{oid}].urgency"),
                "token_cost": _as_nonnegative_int(raw.get("token_cost", 0), f"order[{oid}].token_cost"),
                "outbound": _as_bool(raw.get("outbound", False), f"order[{oid}].outbound"),
                "status": status,
                "preferred_workers": sorted(preferred),
            }
        )
    return sorted(out, key=lambda row: row["id"])


def normalize_leases(leases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not isinstance(leases, list):
        raise ContractError("leases must be a list")
    out: list[dict[str, Any]] = []
    for idx, raw in enumerate(leases):
        if not isinstance(raw, dict):
            raise ContractError("lease rows must be objects")
        order_id = raw.get("order_id")
        owner = raw.get("owner")
        kind = raw.get("kind")
        if (
            not isinstance(order_id, str)
            or not order_id.strip()
            or order_id != order_id.strip()
        ):
            raise ContractError(f"lease[{idx}].order_id must be a non-empty trimmed string")
        if not isinstance(owner, str) or not owner.strip() or owner != owner.strip():
            raise ContractError(f"lease[{idx}].owner must be a non-empty trimmed string")
        if kind not in {"CLAIM", "MUSE"}:
            raise ContractError(f"lease[{idx}].kind must be CLAIM or MUSE")
        out.append(
            {
                "order_id": order_id,
                "owner": owner,
                "kind": kind,
                "active": _as_bool(raw.get("active", True), f"lease[{idx}].active"),
            }
        )
    return sorted(out, key=lambda row: (row["order_id"], row["kind"], row["owner"], not row["active"]))


def _order_score(order: dict[str, Any]) -> int:
    # Revenue deliberately dominates when known, followed by impact, urgency,
    # and explicit priority. All terms are integers for byte-stable replay.
    return (
        order["revenue_usd_expected"] * 1_000_000
        + order["impact"] * 10_000
        + order["urgency"] * 100
        + order["priority"]
    )


def _input_snapshot(
    workers: list[dict[str, Any]],
    orders: list[dict[str, Any]],
    leases: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "workers": workers,
        "orders": orders,
        "leases": leases,
    }


def dispatch(
    workers: list[dict[str, Any]],
    orders: list[dict[str, Any]],
    leases: list[dict[str, Any]],
) -> dict[str, Any]:
    """Allocate open work deterministically and return a digest-bound receipt."""

    workers_n = normalize_workers(workers)
    orders_n = normalize_orders(orders)
    leases_n = normalize_leases(leases)

    known_orders = {order["id"] for order in orders_n}
    unknown_lease_orders = sorted({lease["order_id"] for lease in leases_n} - known_orders)
    if unknown_lease_orders:
        raise ContractError(f"leases reference unknown orders: {unknown_lease_orders}")

    live_claims = {
        lease["order_id"]
        for lease in leases_n
        if lease["active"] and lease["kind"] == "CLAIM"
    }
    muse_leases = {
        lease["order_id"]
        for lease in leases_n
        if lease["active"] and lease["kind"] == "MUSE"
    }

    state = {
        worker["id"]: {
            "slots_used": 0,
            "tokens_used": 0,
            "capacity": worker["capacity"],
            "token_budget": worker["token_budget"],
            "capabilities": set(worker["capabilities"]),
            "active": worker["active"],
        }
        for worker in workers_n
    }

    assignments: list[dict[str, Any]] = []
    unassigned: list[dict[str, Any]] = []

    ranked = sorted(orders_n, key=lambda order: (-_order_score(order), order["id"]))
    for order in ranked:
        oid = order["id"]
        if order["status"] == DNR:
            unassigned.append({"order_id": oid, "reason": "DNR"})
            continue
        if order["status"] == HOLD:
            unassigned.append({"order_id": oid, "reason": "HOLD"})
            continue
        if oid in live_claims:
            unassigned.append({"order_id": oid, "reason": "LEASE_HELD"})
            continue
        if order["outbound"] and oid not in muse_leases:
            unassigned.append({"order_id": oid, "reason": "MUSE_LEASE_REQUIRED"})
            continue

        required = set(order["required_capabilities"])
        active_workers = [w for w in workers_n if state[w["id"]]["active"]]
        capable = [w for w in active_workers if required.issubset(state[w["id"]]["capabilities"])]
        if not capable:
            unassigned.append({"order_id": oid, "reason": "CAPABILITY_MISMATCH"})
            continue

        slot_available = [
            w for w in capable if state[w["id"]]["slots_used"] < state[w["id"]]["capacity"]
        ]
        if not slot_available:
            unassigned.append({"order_id": oid, "reason": "CAPACITY_EXHAUSTED"})
            continue

        token_available = [
            w
            for w in slot_available
            if state[w["id"]]["tokens_used"] + order["token_cost"] <= state[w["id"]]["token_budget"]
        ]
        if not token_available:
            unassigned.append({"order_id": oid, "reason": "TOKEN_BUDGET_EXHAUSTED"})
            continue

        preferred = set(order["preferred_workers"])
        # Prefer explicit worker hints, then the worker with the most remaining
        # token budget after assignment, then lexical id for stable ties.
        token_available.sort(
            key=lambda w: (
                0 if w["id"] in preferred else 1,
                -(
                    state[w["id"]]["token_budget"]
                    - state[w["id"]]["tokens_used"]
                    - order["token_cost"]
                ),
                w["id"],
            )
        )
        chosen = token_available[0]
        st = state[chosen["id"]]
        st["slots_used"] += 1
        st["tokens_used"] += order["token_cost"]
        assignments.append(
            {
                "order_id": oid,
                "worker_id": chosen["id"],
                "score": _order_score(order),
                "token_cost": order["token_cost"],
                "outbound": order["outbound"],
                "muse_lease_present": bool(order["outbound"] and oid in muse_leases),
            }
        )

    assignments.sort(key=lambda row: row["order_id"])
    unassigned.sort(key=lambda row: row["order_id"])
    utilization = [
        {
            "worker_id": wid,
            "slots_used": st["slots_used"],
            "capacity": st["capacity"],
            "tokens_used": st["tokens_used"],
            "token_budget": st["token_budget"],
        }
        for wid, st in sorted(state.items())
    ]

    snapshot = _input_snapshot(workers_n, orders_n, leases_n)
    receipt_core = {
        "schema_version": SCHEMA_VERSION,
        "input_sha256": _sha256(snapshot),
        "assignments": assignments,
        "unassigned": unassigned,
        "utilization": utilization,
        "authority": {
            "network": False,
            "external_contact": False,
            "spend": False,
            "muse_gate_enforced": True,
        },
    }
    return {**receipt_core, "receipt_sha256": _sha256(receipt_core)}


def verify_receipt(
    workers: list[dict[str, Any]],
    orders: list[dict[str, Any]],
    leases: list[dict[str, Any]],
    receipt: dict[str, Any],
) -> bool:
    """Return True iff receipt exactly matches a fresh deterministic replay."""

    if not isinstance(receipt, dict):
        return False
    try:
        expected = dispatch(workers, orders, leases)
    except (ContractError, ValueError, TypeError):
        return False
    return receipt == expected
