# SPDX-License-Identifier: Apache-2.0
"""R05/H8: fail-closed recovery for one stranded R04 route hand.

This wrapper never predicts an opponent, never spends sale receipts, and never
changes unit actions. It only appends/replaces an inert market row with one HIRE
when the returned R04 action already references exactly one productive hand that
does not physically exist and is not covered by an existing HIRE in the queue.
"""
from __future__ import annotations

from copy import deepcopy
import math
from typing import Any, Mapping

PASSIVE = {"PASS", "NORTH", "SOUTH", "EAST", "WEST"}
SEED_COST = {"WHEAT": 10, "CARROT": 20, "TOMATO": 50, "STRAWBERRY": 100, "MELON": 80}
ANIMAL_COST = {"GOOSE": 300, "COW": 400, "SHEEP": 500}
LAND_PRICES = (1000, 2000, 4000)
PRODUCTS = {"WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON",
            "EGG", "MILK", "WOOL", "FERTILIZER"}


def _uint(value: Any, name: str, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ValueError(f"{name} must be an integer >= {minimum}")
    return value


def _quantity(order: Any) -> int:
    if not isinstance(order, list) or len(order) < 3:
        raise ValueError("quantity order must have three fields")
    return _uint(order[2], "quantity")


def _cash(value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("cash must be numeric")
    value = float(value)
    if not math.isfinite(value) or value < 0:
        raise ValueError("cash must be finite and non-negative")
    return value


def _fib(n: int) -> int:
    a, b = 1, 1
    for _ in range(n):
        a, b = b, a + b
    return a


def _hire_cost(n_already_today: int, mult: int) -> int:
    return mult * _fib(n_already_today)


def _required_hands(action: Mapping[str, Any]) -> int:
    """Highest hand index with a non-PASS operation, expressed as a count."""
    hands = action.get("hands") or []
    if not isinstance(hands, list):
        raise ValueError("hands must be a list")
    required = 0
    for index, raw in enumerate(hands):
        if not isinstance(raw, list) or not raw or not isinstance(raw[0], str):
            raise ValueError("unsupported hand action")
        if raw[0] != "PASS":
            required = index + 1
    return required


def _fixed_cost_upper_bound(observation: Mapping[str, Any], queue: list,
                            config: Mapping[str, Any]) -> dict:
    """Prove the whole executed queue fits starting cash without SELL receipts."""
    player = _uint(observation["player"], "player")
    farm = observation["farms"][player]
    cash = _cash(farm["money"])
    hires = _uint(farm["hires_today"], "hires_today")
    unlocked = farm["unlocked_quadrants"]
    if not isinstance(unlocked, list) or not unlocked:
        raise ValueError("unlocked_quadrants")
    land_index = len(unlocked) - 1
    mult = _uint(config.get("farmHandCostMult", 1), "farmHandCostMult")
    limit = _uint(config.get("maxMarketOrdersPerTurn", 10), "maxMarketOrdersPerTurn")
    if limit <= 0:
        raise ValueError("zero market order limit")
    if len(queue) > limit:
        raise ValueError("queue exceeds market order limit")
    total = 0
    rows = []
    for slot, order in enumerate(queue):
        if order == []:
            continue
        if not isinstance(order, list) or not order or not isinstance(order[0], str):
            raise ValueError("unsupported market row")
        op, cost = order[0], 0
        if op == "HIRE":
            cost = _hire_cost(hires, mult)
            hires += 1
        elif op == "BUY_LAND":
            if land_index < len(LAND_PRICES):
                cost = LAND_PRICES[land_index]
                land_index += 1
        elif op == "BUY_SEED":
            q = _quantity(order)
            if order[1] not in SEED_COST:
                raise ValueError("unknown seed")
            cost = q * SEED_COST[order[1]]
        elif op == "BUY_ANIMAL":
            q = _quantity(order)
            if order[1] not in ANIMAL_COST:
                raise ValueError("unknown animal")
            cost = q * ANIMAL_COST[order[1]]
        elif op == "BUY_PRODUCT":
            if _quantity(order):
                raise ValueError("positive BUY_PRODUCT needs quote evidence")
        elif op == "SELL":
            _quantity(order)
            if order[1] not in PRODUCTS:
                raise ValueError("unknown sale product")
        elif op == "PASS":
            pass
        else:
            raise ValueError("unsupported market operation")
        total += cost
        rows.append({"slot": slot, "operation": op, "cost_upper_bound": cost,
                     "cash_floor_without_sales": cash - total})
    return {"certified": total <= cash, "starting_cash": cash,
            "fixed_cost_upper_bound": total, "rows": rows}


def _inert_row(order: Any) -> bool:
    return (
        order == [] or
        (isinstance(order, list) and len(order) >= 3 and order[0] == "SELL"
         and order[1] in PRODUCTS and isinstance(order[2], int)
         and not isinstance(order[2], bool) and order[2] == 0)
    )


def recover_stranded_hire(observation: Mapping[str, Any], action: Mapping[str, Any],
                           configuration: Mapping[str, Any] | None = None, *,
                           enabled: bool = True) -> tuple[dict, dict]:
    """Return one conservative HIRE repair or an unchanged deep copy."""
    out = deepcopy(dict(action))
    report = {"enabled": bool(enabled), "changed": False, "reason": "OFF",
              "scope": "one stranded returned-action hand; current cash only; no sale receipts"}
    if not enabled:
        return out, report
    try:
        cfg = dict(configuration or {})
        player = _uint(observation["player"], "player")
        farm = observation["farms"][player]
        active = len(farm["hands"])
        required = _required_hands(out)
        queue = out.get("market") or []
        if not isinstance(queue, list):
            raise ValueError("market must be a list")
        limit = _uint(cfg.get("maxMarketOrdersPerTurn", 10), "maxMarketOrdersPerTurn")
        if limit <= 0 or len(queue) > limit:
            raise ValueError("market order limit")
        existing = sum(1 for row in queue if isinstance(row, list) and row and row[0] == "HIRE")
        report.update(active_hands=active, required_hands=required, existing_hires=existing)
        future = active + existing
        if required <= future:
            report["reason"] = "HAND_DEMAND_ALREADY_COVERED"
            return out, report
        if required - future != 1:
            report["reason"] = "NOT_EXACTLY_ONE_MISSING_HAND"
            return out, report
        target = out["hands"][future]
        report["missing_hand_action"] = list(target)
        if target[0] in PASSIVE:
            report["reason"] = "MISSING_SLOT_NOT_PRODUCTIVE"
            return out, report

        baseline = _fixed_cost_upper_bound(observation, queue, cfg)
        report["baseline_certificate"] = baseline
        if not baseline["certified"]:
            report["reason"] = "BASE_QUEUE_NOT_FUNDED_WITHOUT_SALES"
            return out, report

        candidate = list(queue)
        inserted_at = None
        if len(candidate) < limit:
            inserted_at = len(candidate)
            candidate.append(["HIRE"])
        else:
            for index, row in enumerate(candidate):
                if _inert_row(row):
                    inserted_at = index
                    candidate[index] = ["HIRE"]
                    break
        if inserted_at is None:
            report["reason"] = "NO_INERT_MARKET_SLOT"
            return out, report

        cert = _fixed_cost_upper_bound(observation, candidate, cfg)
        report["candidate_certificate"] = cert
        if not cert["certified"]:
            report["reason"] = "RECOVERY_HIRE_NOT_FUNDED_WITHOUT_SALES"
            return out, report
        out["market"] = candidate
        report.update(changed=True, reason="RECOVER_ONE_STRANDED_PRODUCTIVE_HAND",
                      inserted_at=inserted_at,
                      incremental_fixed_cost=(cert["fixed_cost_upper_bound"]
                                              - baseline["fixed_cost_upper_bound"]))
        return out, report
    except (IndexError, KeyError, TypeError, ValueError, OverflowError) as error:
        report["reason"] = "FAIL_CLOSED_" + type(error).__name__
        report["detail"] = str(error)
        return out, report


_BASE = None
LAST_REPORT = None


def install(host=None, horizon=None, opening=None, row_order=None, evening_flush=None,
            sale_fertilizer=None, cattle_early=None):
    """Drop-in R04 install wrapper for isolated V3.1 evaluation."""
    global _BASE
    import r04_full_router as r04
    _BASE = r04.install(host, horizon, opening, row_order, evening_flush,
                        sale_fertilizer, cattle_early)

    def agent(observation, configuration=None):
        global LAST_REPORT
        base = _BASE(observation, configuration)
        result, LAST_REPORT = recover_stranded_hire(observation, base, configuration, enabled=True)
        return result

    return agent
