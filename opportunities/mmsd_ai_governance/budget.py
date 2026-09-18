from __future__ import annotations

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any


class BudgetError(ValueError):
    pass


def _money(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, (str, int, float, Decimal)):
        raise BudgetError(f"{name}: money value required")
    try:
        dec = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise BudgetError(f"{name}: invalid money") from exc
    if not dec.is_finite() or dec < 0:
        raise BudgetError(f"{name}: non-negative finite money required")
    cents = (dec * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    if cents != dec * 100:
        raise BudgetError(f"{name}: at most two decimal places")
    if cents > 1_000_000_000:
        raise BudgetError(f"{name}: unreasonable amount")
    return int(cents)


def validate_budget(packet: Any) -> dict[str, Any]:
    if not isinstance(packet, dict):
        raise BudgetError("budget packet must be object")
    expected = {
        "workstreams",
        "milestones",
        "pricing_structure_known",
        "buyer_max_total",
        "owner_approved",
    }
    if set(packet) != expected:
        raise BudgetError(
            f"budget keys mismatch missing={sorted(expected-set(packet))} extra={sorted(set(packet)-expected)}"
        )

    workstreams = packet["workstreams"]
    if not isinstance(workstreams, dict) or not workstreams or len(workstreams) > 30:
        raise BudgetError("workstreams must be a non-empty object")
    ws_cents: dict[str, int] = {}
    for key, value in workstreams.items():
        if not isinstance(key, str) or not key or len(key) > 80:
            raise BudgetError("invalid workstream id")
        ws_cents[key] = _money(value, f"workstreams.{key}")

    milestones = packet["milestones"]
    if not isinstance(milestones, list) or not milestones or len(milestones) > 50:
        raise BudgetError("milestones must be a non-empty list")
    seen: set[str] = set()
    ms_cents: list[dict[str, Any]] = []
    for idx, raw in enumerate(milestones):
        if not isinstance(raw, dict) or set(raw) != {"milestone_id", "amount"}:
            raise BudgetError(f"milestones[{idx}] invalid")
        mid = raw["milestone_id"]
        if not isinstance(mid, str) or not mid or len(mid) > 80 or mid in seen:
            raise BudgetError(f"milestones[{idx}].milestone_id invalid")
        seen.add(mid)
        ms_cents.append({"milestone_id": mid, "amount_cents": _money(raw["amount"], f"milestones[{idx}].amount")})

    pricing_known = packet["pricing_structure_known"]
    owner_approved = packet["owner_approved"]
    if type(pricing_known) is not bool or type(owner_approved) is not bool:
        raise BudgetError("pricing_structure_known and owner_approved must be bool")
    if owner_approved and not pricing_known:
        raise BudgetError("owner approval cannot precede pricing-structure evidence")

    buyer_max = packet["buyer_max_total"]
    buyer_max_cents = None if buyer_max is None else _money(buyer_max, "buyer_max_total")

    workstream_total = sum(ws_cents.values())
    milestone_total = sum(m["amount_cents"] for m in ms_cents)
    if workstream_total != milestone_total:
        raise BudgetError("workstream and milestone totals differ")
    if buyer_max_cents is not None and workstream_total > buyer_max_cents:
        raise BudgetError("budget exceeds buyer maximum")

    return {
        "math_valid": True,
        "owner_approved": owner_approved,
        "pricing_structure_known": pricing_known,
        "buyer_max_total_cents": buyer_max_cents,
        "total_cents": workstream_total,
        "workstreams_cents": dict(sorted(ws_cents.items())),
        "milestones_cents": ms_cents,
    }
