# SPDX-License-Identifier: Apache-2.0
"""Conservative V5 DEADCAP certificate for returned BUY_SEED rows.

A current BUY_SEED happens after unit actions. Therefore it cannot fund a PLANT
in the same callback. If every declared still-reachable authored route contains
no later PLANT of that crop, the acquired seed has no route-authored consumer.
Removing only that market row preserves queue index/cap topology and cannot
change public market inventory because BUY_SEED is a private cash->seed transfer.

This helper is intentionally narrower than the historical DEADCAP oracle. It
never reasons about HIRE/land/animals/products, crop maturity, future prices, or
implicit route reachability. Any missing route-family proof is identity.
"""
from __future__ import annotations

import copy
from collections.abc import Mapping
from typing import Any

CROPS = frozenset(("WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON"))


def _effective_market_limit(configuration: Mapping | None) -> int | None:
    cfg = configuration if isinstance(configuration, Mapping) else {}
    try:
        # Pinned engine: max(1, int(maxMarketOrdersPerTurn)).
        return max(1, int(cfg.get("maxMarketOrdersPerTurn", 10)))
    except (TypeError, ValueError, OverflowError):
        return None


def parse_seed_buy(order: Any) -> tuple[str, int] | None:
    """Return engine-executable BUY_SEED crop/quantity, else None.

    Matches the pinned market grammar: list, len>=3, int() quantity coercion,
    positive quantity, and an official crop. Trailing fields are ignored by the
    engine and are deliberately accepted here without normalizing the row.
    """
    if not isinstance(order, list) or len(order) < 3 or order[0] != "BUY_SEED":
        return None
    crop = order[1]
    if not isinstance(crop, str) or crop not in CROPS:
        return None
    try:
        quantity = int(order[2])
    except (TypeError, ValueError, OverflowError):
        return None
    if quantity <= 0:
        return None
    return crop, quantity


def _route_future_plant(route: Any, crop: str, after_step: int) -> bool | None:
    """True/False for a well-formed authored route, None if proof is incomplete."""
    if not isinstance(route, list) or after_step < -1:
        return None
    for frame in route[after_step + 1 :]:
        if not isinstance(frame, Mapping):
            return None
        farmer = frame.get("farmer", ["PASS"])
        hands = frame.get("hands", [])
        if not isinstance(farmer, list) or not isinstance(hands, list):
            return None
        actions = [farmer, *hands]
        for action in actions:
            if not isinstance(action, list) or not action:
                # The pinned engine treats malformed/non-list unit actions as
                # inert, but an authored route proof refuses ambiguous objects.
                return None
            if action[0] == "PLANT":
                if len(action) < 2 or not isinstance(action[1], str):
                    return None
                if action[1] == crop:
                    return True
    return False


def no_future_plant_in_route_family(routes: Any, crop: str, after_step: int) -> bool | None:
    """Certify absence only when every supplied route is complete and plant-free."""
    if (not isinstance(routes, Mapping) or not routes or crop not in CROPS
            or isinstance(after_step, bool) or not isinstance(after_step, int)):
        return None
    for route in routes.values():
        seen = _route_future_plant(route, crop, after_step)
        if seen is None:
            return None
        if seen:
            return False
    return True


def transform_with_report(
    action: Any,
    *,
    step: Any,
    routes: Any,
    configuration: Mapping | None = None,
    enabled: Any = False,
    route_family_complete: Any = False,
    dynamic_unit_rewriters: Any = False,
) -> tuple[Any, dict[str, Any]]:
    """Return a copied action plus a fail-closed DEADCAP receipt.

    Engagement requires explicit exact booleans: ``enabled is True``,
    ``route_family_complete is True``, and ``dynamic_unit_rewriters is False``.
    This prevents a caller from treating an incomplete authored tape family as a
    proof when another runtime component may synthesize future PLANT actions.
    """
    result = copy.deepcopy(action)
    report: dict[str, Any] = {
        "enabled": enabled is True,
        "route_family_complete": route_family_complete is True,
        "dynamic_unit_rewriters": dynamic_unit_rewriters is True,
        "changed": False,
        "removed": [],
        "reason": "identity",
    }
    if enabled is not True:
        report["reason"] = "disabled"
        return result, report
    if route_family_complete is not True:
        report["reason"] = "incomplete_route_family"
        return result, report
    if dynamic_unit_rewriters is not False:
        report["reason"] = "dynamic_unit_rewriter_present"
        return result, report
    if isinstance(step, bool) or not isinstance(step, int) or step < 0:
        report["reason"] = "invalid_step"
        return result, report
    if not isinstance(result, dict) or not isinstance(result.get("market"), list):
        report["reason"] = "invalid_action"
        return result, report
    limit = _effective_market_limit(configuration)
    if limit is None:
        report["reason"] = "invalid_market_limit"
        return result, report

    market = result["market"]
    for index in range(min(len(market), limit)):
        parsed = parse_seed_buy(market[index])
        if parsed is None:
            continue
        crop, quantity = parsed
        dead = no_future_plant_in_route_family(routes, crop, step)
        if dead is None:
            report["reason"] = "route_proof_failed"
            return copy.deepcopy(action), report
        if not dead:
            continue
        market[index] = []
        report["removed"].append({"index": index, "crop": crop, "quantity": quantity})

    report["changed"] = bool(report["removed"])
    report["reason"] = "dead_seed_removed" if report["changed"] else "no_certified_dead_seed"
    return result, report


def transform(action: Any, **kwargs: Any) -> Any:
    return transform_with_report(action, **kwargs)[0]


def census_authored_routes(routes: Any, configuration: Mapping | None = None) -> dict[str, Any]:
    """Static over-approximation census of authored dead-seed purchase rows.

    Every route in the supplied family is treated as still reachable. This is
    intentionally conservative: a row is reported only when *none* of those
    routes ever PLANT that crop after the purchase step.
    """
    limit = _effective_market_limit(configuration)
    if limit is None or not isinstance(routes, Mapping) or not routes:
        return {"certified": False, "reason": "invalid_input", "rows": []}
    rows: list[dict[str, Any]] = []
    for route_id, route in routes.items():
        if not isinstance(route, list):
            return {"certified": False, "reason": "malformed_route", "rows": []}
        for step, frame in enumerate(route):
            if not isinstance(frame, Mapping):
                return {"certified": False, "reason": "malformed_frame", "rows": []}
            market = frame.get("market", [])
            if not isinstance(market, list):
                return {"certified": False, "reason": "malformed_market", "rows": []}
            for index, order in enumerate(market[:limit]):
                parsed = parse_seed_buy(order)
                if parsed is None:
                    continue
                crop, quantity = parsed
                dead = no_future_plant_in_route_family(routes, crop, step)
                if dead is None:
                    return {"certified": False, "reason": "route_proof_failed", "rows": []}
                if dead:
                    rows.append({
                        "route": str(route_id), "step": step, "index": index,
                        "crop": crop, "quantity": quantity,
                    })
    return {"certified": True, "reason": "ok", "rows": rows, "count": len(rows)}
