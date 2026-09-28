# SPDX-License-Identifier: Apache-2.0
"""Fail-closed aggregate bound for a trailing duplicate BUY_SEED order.

The canonical seed limiter bounds each row independently against post-unit stock.
This helper repairs only a mechanically strict subset where the market prefix up
through the final non-empty executable row consists entirely of fixed-price seed
orders.  It leaves all preceding rows untouched and can therefore remove only
seed units that the official per-unit market loop would actually buy at the final
row and that exceed the route's branch-compatible remaining planting demand.
"""
from __future__ import annotations

from copy import deepcopy
import math
from typing import Any, Mapping


def _nonnegative_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _positive_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def _money(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    value = float(value)
    if not math.isfinite(value) or value < 0:
        return None
    return value


def _seed_order(row: Any) -> tuple[str, int] | None:
    """Return a strict seed order, or ``None`` for anything ambiguous."""
    if not isinstance(row, list) or len(row) < 3 or row[0] != "BUY_SEED":
        return None
    crop = row[1]
    quantity = row[2]
    if not isinstance(crop, str) or not crop or not _positive_int(quantity):
        return None
    return crop, quantity


def _decline(action: Any, reason: str, **details: Any) -> tuple[Any, dict[str, Any]]:
    report: dict[str, Any] = {"changed": False, "reason": reason}
    report.update(details)
    return action, report


def cap_trailing_duplicate_seed(
    action: Any,
    *,
    post_unit_seeds: Mapping[str, int],
    remaining_demand: Mapping[str, int],
    cash: int | float,
    seed_costs: Mapping[str, int],
    max_orders: int = 10,
) -> tuple[Any, dict[str, Any]]:
    """Remove provably surplus fills from one trailing duplicate seed order.

    Safety boundary:

    * the final non-empty row in the engine's active prefix is ``BUY_SEED``;
    * that crop appears in at least one earlier active row;
    * every non-empty row through the target is a strict ``BUY_SEED`` row;
    * all seed prices are positive fixed integers;
    * the exact fixed-price simulation shows the surplus is local to the target
      row, so every preceding order has identical execution before and after;
    * no later active order exists whose execution could change when cash is
      saved.

    Declines return the original object by identity.  An accepted edit is a deep
    copy with exactly one market slot changed.
    """
    if not _positive_int(max_orders):
        return _decline(action, "invalid_max_orders")
    available_cash = _money(cash)
    if available_cash is None:
        return _decline(action, "invalid_cash")
    if not isinstance(action, dict):
        return _decline(action, "invalid_action")
    market = action.get("market")
    if not isinstance(market, list):
        return _decline(action, "invalid_market")

    prefix = market[:max_orders]
    nonempty = [index for index, row in enumerate(prefix) if row]
    if not nonempty:
        return _decline(action, "empty_prefix")
    target_index = nonempty[-1]
    target = _seed_order(prefix[target_index])
    if target is None:
        return _decline(action, "tail_not_strict_seed", target_index=target_index)
    target_crop, target_quantity = target

    parsed: list[tuple[str, int] | None] = []
    target_occurrences = 0
    for index, row in enumerate(prefix[: target_index + 1]):
        if row == []:
            parsed.append(None)
            continue
        order = _seed_order(row)
        if order is None:
            return _decline(
                action,
                "ambiguous_prefix_order",
                target_crop=target_crop,
                target_index=target_index,
                ambiguous_index=index,
            )
        parsed.append(order)
        if order[0] == target_crop:
            target_occurrences += 1
    if target_occurrences < 2:
        return _decline(
            action,
            "no_duplicate_target",
            target_crop=target_crop,
            target_index=target_index,
        )

    fills: list[int] = [0] * (target_index + 1)
    cash_after = available_cash
    for index, order in enumerate(parsed):
        if order is None:
            continue
        crop, requested = order
        cost = seed_costs.get(crop)
        if not _positive_int(cost):
            return _decline(
                action,
                "invalid_seed_cost",
                target_crop=target_crop,
                target_index=target_index,
                crop=crop,
                order_index=index,
            )
        fill = min(requested, int(cash_after // cost))
        fills[index] = fill
        cash_after -= fill * cost

    stock = post_unit_seeds.get(target_crop)
    bound = remaining_demand.get(target_crop)
    if not _nonnegative_int(stock):
        return _decline(
            action,
            "invalid_post_unit_stock",
            target_crop=target_crop,
            target_index=target_index,
        )
    if not _nonnegative_int(bound):
        return _decline(
            action,
            "invalid_remaining_demand",
            target_crop=target_crop,
            target_index=target_index,
        )

    demand_deficit = max(0, bound - stock)
    aggregate_fill = sum(
        fills[index]
        for index, order in enumerate(parsed)
        if order is not None and order[0] == target_crop
    )
    if aggregate_fill <= demand_deficit:
        return _decline(
            action,
            "within_aggregate_bound",
            target_crop=target_crop,
            target_index=target_index,
            aggregate_fill=aggregate_fill,
            demand_deficit=demand_deficit,
        )

    excess = aggregate_fill - demand_deficit
    target_fill = fills[target_index]
    if excess > target_fill:
        return _decline(
            action,
            "surplus_not_tail_local",
            target_crop=target_crop,
            target_index=target_index,
            aggregate_fill=aggregate_fill,
            demand_deficit=demand_deficit,
            excess_fill=excess,
            target_fill=target_fill,
        )

    retained_fill = target_fill - excess
    result = deepcopy(action)
    if retained_fill == 0:
        result["market"][target_index] = []
    else:
        edited = list(result["market"][target_index])
        edited[2] = retained_fill
        result["market"][target_index] = edited

    cost = seed_costs[target_crop]
    return result, {
        "changed": True,
        "reason": "trimmed_provable_tail_surplus",
        "target_crop": target_crop,
        "target_index": target_index,
        "original_quantity": target_quantity,
        "baseline_target_fill": target_fill,
        "retained_quantity": retained_fill,
        "aggregate_baseline_fill": aggregate_fill,
        "post_unit_stock": stock,
        "remaining_demand_bound": bound,
        "demand_deficit": demand_deficit,
        "removed_filled_units": excess,
        "cash_saved": excess * cost,
        "baseline_cash_after_prefix": cash_after,
    }
