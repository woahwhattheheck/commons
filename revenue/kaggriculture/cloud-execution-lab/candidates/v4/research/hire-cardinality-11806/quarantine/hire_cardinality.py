# SPDX-License-Identifier: Apache-2.0
"""Final-action HIRE and worker-cardinality reconciliation.

The Kaggriculture engine treats illegal actions as silent no-ops.  In
particular, worker commands past the observed hand count are ignored and an
unaffordable HIRE does not add a worker.  A selected route can therefore carry
an impossible worker suffix for the rest of a day after one failed HIRE.

This module performs no planning and calls no policy.  At the final returned-
action boundary it removes only commands the engine cannot execute:

* hand-action suffixes beyond the currently observed hands;
* HIREs beyond the market-order limit; and
* HIREs in a HIRE/no-op-only executable prefix that current cash cannot fund.

Every rewrite is transition-equivalent to the original action under the public
engine semantics.  Mixed active market queues are left untouched because a
preceding sale or purchase can change the cash available to a later HIRE.
"""
from __future__ import annotations

import copy
import math
from typing import Any, Mapping

NO_ORDER = ["SELL", "WHEAT", 0]


def _uint(value: Any, minimum: int = 0) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        return None
    return value


def _finite_number(value: Any, minimum: float = 0.0) -> float | int | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    if not math.isfinite(value) or value < minimum:
        return None
    return value


def _is_hire(order: Any) -> bool:
    return isinstance(order, list) and bool(order) and order[0] == "HIRE"


def _is_no_order(mechanics: Any, order: Any) -> bool:
    products = getattr(mechanics, "PRODUCTS", ())
    return (
        isinstance(order, list)
        and len(order) == 3
        and order[0] == "SELL"
        and order[1] in products
        and order[2] == 0
    )


def _report() -> dict[str, Any]:
    return {
        "changed": False,
        "reason": "observation_unavailable",
        "scope": "final physical-equivalence guard; no policy or route mutation",
        "observed_hands": None,
        "returned_hand_actions_before": None,
        "returned_hand_actions_after": None,
        "current_hand_actions_clipped": 0,
        "market_orders": None,
        "market_limit": None,
        "hire_orders": 0,
        "executable_hires": 0,
        "cash_blocked_hires": 0,
        "order_limit_blocked_hires": 0,
        "removed_order_indices": [],
        "hire_costs": [],
        "cash_before": None,
        "cash_after_executable_hires": None,
        "expected_hands_after_action": None,
        "market_guard_applied": False,
        "engine_equivalence": (
            "rewrites only worker suffixes or market orders the engine would ignore"
        ),
    }


def reconcile_hire_cardinality(
    mechanics: Any,
    observation: Mapping[str, Any],
    configuration: Mapping[str, Any] | None,
    selected_action: Mapping[str, Any],
) -> tuple[dict, dict]:
    """Return a physically equivalent action with executable cardinalities.

    The cash proof is intentionally narrow.  It runs only when every market
    order in the engine-executable prefix is HIRE or a canonical zero-quantity
    SELL.  Active market orders make cash path-dependent, so that prefix is
    returned unchanged.  HIREs outside ``maxMarketOrdersPerTurn`` are always
    replaced because the engine never evaluates them.
    """
    out = copy.deepcopy(dict(selected_action))
    report = _report()
    cfg = dict(configuration or {})

    if not isinstance(observation, Mapping):
        return out, report
    player = _uint(observation.get("player"))
    farms = observation.get("farms")
    if player is None or not isinstance(farms, list) or player >= len(farms):
        return out, report
    farm = farms[player]
    if not isinstance(farm, Mapping) or not isinstance(farm.get("hands"), list):
        return out, report

    observed_hands = len(farm["hands"])
    report["observed_hands"] = observed_hands
    hands = out.get("hands")
    if isinstance(hands, list):
        report["returned_hand_actions_before"] = len(hands)
        if len(hands) > observed_hands:
            clipped = len(hands) - observed_hands
            out["hands"] = hands[:observed_hands]
            report["current_hand_actions_clipped"] = clipped
            report["changed"] = True
        report["returned_hand_actions_after"] = len(out.get("hands", []))

    queue = out.get("market", [])
    if not isinstance(queue, list):
        report["reason"] = (
            "current_hand_cardinality_only"
            if report["changed"] else "unsupported_market_queue"
        )
        return out, report
    report["market_orders"] = len(queue)

    limit = _uint(cfg.get("maxMarketOrdersPerTurn", 10), 0)
    if limit is None:
        report["reason"] = (
            "current_hand_cardinality_only"
            if report["changed"] else "invalid_market_limit"
        )
        return out, report
    report["market_limit"] = limit

    hire_indices = [i for i, order in enumerate(queue) if _is_hire(order)]
    report["hire_orders"] = len(hire_indices)
    removed: list[int] = []

    # The engine never evaluates the market suffix outside its order limit.
    for i in hire_indices:
        if i >= limit:
            out["market"][i] = list(NO_ORDER)
            removed.append(i)
            report["order_limit_blocked_hires"] += 1
            report["changed"] = True

    prefix = queue[:limit]
    if any(not (_is_hire(order) or _is_no_order(mechanics, order)) for order in prefix):
        report["removed_order_indices"] = removed
        report["reason"] = (
            "order_limit_and_hand_cardinality_only"
            if removed and report["current_hand_actions_clipped"]
            else "order_limit_only" if removed
            else "current_hand_cardinality_only"
            if report["current_hand_actions_clipped"]
            else "active_or_unknown_market_order"
        )
        return out, report

    cash = _finite_number(farm.get("money"))
    hires_today = _uint(farm.get("hires_today"))
    multiplier = _finite_number(cfg.get("farmHandCostMult", 1))
    if cash is None or hires_today is None or multiplier is None:
        report["removed_order_indices"] = removed
        report["reason"] = (
            "order_limit_and_hand_cardinality_only"
            if removed and report["current_hand_actions_clipped"]
            else "order_limit_only" if removed
            else "current_hand_cardinality_only"
            if report["current_hand_actions_clipped"]
            else "invalid_hire_state"
        )
        return out, report

    report["market_guard_applied"] = True
    report["cash_before"] = cash
    remaining = cash
    next_hire = hires_today
    executable_hires = 0

    for i, order in enumerate(prefix):
        if not _is_hire(order):
            continue
        try:
            cost = mechanics._hire_cost(next_hire, multiplier)
        except (AttributeError, TypeError, ValueError, OverflowError):
            report["reason"] = "invalid_hire_cost"
            report["removed_order_indices"] = removed
            return out, report
        cost = _finite_number(cost)
        if cost is None:
            report["reason"] = "invalid_hire_cost"
            report["removed_order_indices"] = removed
            return out, report
        report["hire_costs"].append(cost)
        if remaining >= cost:
            remaining -= cost
            next_hire += 1
            executable_hires += 1
            continue
        out["market"][i] = list(NO_ORDER)
        removed.append(i)
        report["cash_blocked_hires"] += 1
        report["changed"] = True

    report["executable_hires"] = executable_hires
    report["cash_after_executable_hires"] = remaining
    report["expected_hands_after_action"] = observed_hands + executable_hires
    report["removed_order_indices"] = sorted(removed)
    if report["cash_blocked_hires"] or report["order_limit_blocked_hires"]:
        report["reason"] = "impossible_hire_suffix_reconciled"
    elif report["current_hand_actions_clipped"]:
        report["reason"] = "current_hand_cardinality_reconciled"
    else:
        report["reason"] = "already_executable"
    return out, report
