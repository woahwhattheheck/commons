# SPDX-License-Identifier: Apache-2.0
"""Fail-closed live-only town-shop inventory reservation.

Leaderboard loss traces expose a shed->town-shop revenue path that is absent
from the pinned reference engine.  This helper therefore does *not* claim
pinned-engine economic authority.  It only provides a conservative, opt-in
returned-action transform for live A/B: on an exact visible shop callback,
retain the minimum currently-held shed quantity demanded by unlocked shops by
reducing already-authored executable SELL quantities.

The transform never invents or reorders market rows.  It refuses any edit that
would have to delete a SELL row, because deleting a row could pull a previously
capped suffix into the executable maxMarketOrdersPerTurn prefix.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any

SCHEMA = "titan.v5.shop-first-live-canary/v1"

SHOPS = {
    "BAKERY": ("EGG", "WHEAT"),
    "PIZZA_SHOP": ("MILK", "TOMATO", "WHEAT"),
    "BRUNCH_SPOT": ("EGG", "WHEAT", "STRAWBERRY"),
    "YARN_STORE": ("WOOL",),
    "ICE_CREAM_SHOP": ("STRAWBERRY", "MILK", "WHEAT"),
    "PET_CAFE": ("CARROT",),
    "SMOOTHIE_SHOP": ("STRAWBERRY", "MILK"),
    "FARMERS_MARKET": ("WHEAT", "CARROT", "TOMATO", "STRAWBERRY"),
}


def _report(step: Any, status: str, **extra: Any) -> dict[str, Any]:
    out = {"schema": SCHEMA, "step": step, "status": status, "changed": False}
    out.update(extra)
    return out


def _configuration_int(configuration: Any, key: str, default: int) -> int | None:
    cfg = configuration or {}
    if not isinstance(cfg, dict):
        return None
    value = cfg.get(key, default)
    if type(value) is not int or value <= 0:
        return None
    return value


def _shop_demand(unlocked: Any) -> dict[str, int] | None:
    if not isinstance(unlocked, list):
        return None
    demand: dict[str, int] = {}
    for shop in unlocked:
        if type(shop) is not str or shop not in SHOPS:
            return None
        products = SHOPS[shop]
        multiplier = 2 if len(products) == 1 else 1
        for item in products:
            demand[item] = demand.get(item, 0) + multiplier
    return demand


def apply(observation: Any, action: Any, configuration: Any = None) -> tuple[Any, dict[str, Any]]:
    """Reserve visible shop-demand inventory without changing queue topology.

    Only the executable market-row prefix is considered.  For each demanded
    item, a reduction is needed only when baseline executable SELL quantity
    would leave fewer than min(current shed, visible demand) units.  Reductions
    are taken from the latest matching rows first so earlier queue behavior is
    disturbed as little as possible, and every row stays a positive SELL.
    """
    if not isinstance(observation, dict):
        return action, _report(None, "observation_shape_drift")
    step = observation.get("step")
    if type(step) is not int or step < 0:
        return action, _report(step, "step_shape_drift")

    interval = _configuration_int(configuration, "townShopSellInterval", 4)
    maximum = _configuration_int(configuration, "maxMarketOrdersPerTurn", 10)
    if interval is None or maximum is None:
        return action, _report(step, "configuration_shape_drift")
    if step % interval != 0:
        return action, _report(step, "not_shop_callback")

    town = observation.get("town")
    if not isinstance(town, dict):
        return action, _report(step, "town_shape_drift")
    demand = _shop_demand(town.get("unlocked_shops"))
    if demand is None:
        return action, _report(step, "shop_shape_drift")
    if not demand:
        return action, _report(step, "no_unlocked_shop_demand", demand={})

    private = observation.get("private")
    shed = private.get("shed") if isinstance(private, dict) else None
    if not isinstance(shed, dict):
        return action, _report(step, "shed_shape_drift", demand=demand)
    for item in demand:
        value = shed.get(item, 0)
        if type(value) is not int or value < 0:
            return action, _report(step, "shed_quantity_drift", demand=demand, item=item)

    if not isinstance(action, dict):
        return action, _report(step, "action_shape_drift", demand=demand)
    market = action.get("market")
    if not isinstance(market, list):
        return action, _report(step, "market_shape_drift", demand=demand)

    prefix = market[:maximum]
    by_item: dict[str, list[tuple[int, int]]] = {}
    for index, row in enumerate(prefix):
        if not (isinstance(row, list) and len(row) >= 1):
            continue
        if row[0] != "SELL" or len(row) < 2 or row[1] not in demand:
            continue
        if len(row) < 3 or type(row[2]) is not int or row[2] <= 0:
            return action, _report(step, "sell_shape_drift", demand=demand, row_index=index)
        by_item.setdefault(row[1], []).append((index, row[2]))

    reductions: dict[str, int] = {}
    plans: dict[str, list[tuple[int, int]]] = {}
    for item, wanted in demand.items():
        current = int(shed.get(item, 0))
        reserve = min(current, wanted)
        rows = by_item.get(item, [])
        total_sell = sum(qty for _, qty in rows)
        baseline_remaining = max(0, current - total_sell)
        reduction = max(0, reserve - baseline_remaining)
        if reduction <= 0:
            continue
        # Keep every authored row present and positive.  If that cannot retain
        # the full reserve, fail closed rather than exposing a capped suffix.
        capacity = sum(max(0, qty - 1) for _, qty in rows)
        if capacity < reduction:
            return action, _report(
                step,
                "row_deletion_required",
                demand=demand,
                item=item,
                reserve=reserve,
                baseline_remaining=baseline_remaining,
                required_reduction=reduction,
                reducible_without_deletion=capacity,
            )
        remaining = reduction
        edits: list[tuple[int, int]] = []
        for index, qty in reversed(rows):
            take = min(remaining, qty - 1)
            if take:
                edits.append((index, qty - take))
                remaining -= take
            if remaining == 0:
                break
        if remaining:
            return action, _report(step, "internal_capacity_mismatch", demand=demand, item=item)
        reductions[item] = reduction
        plans[item] = edits

    if not plans:
        return action, _report(step, "reserve_already_preserved", demand=demand)

    out = deepcopy(action)
    edited_rows: list[dict[str, Any]] = []
    for item, edits in plans.items():
        for index, new_qty in edits:
            old_qty = out["market"][index][2]
            out["market"][index][2] = new_qty
            edited_rows.append(
                {"item": item, "row_index": index, "before": old_qty, "after": new_qty}
            )

    return out, {
        "schema": SCHEMA,
        "step": step,
        "status": "shop_reserve_preserved",
        "changed": True,
        "demand": demand,
        "reductions": reductions,
        "edited_rows": edited_rows,
        "live_only": True,
    }
