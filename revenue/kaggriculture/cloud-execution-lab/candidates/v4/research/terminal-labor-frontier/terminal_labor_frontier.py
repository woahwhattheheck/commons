# SPDX-License-Identifier: Apache-2.0
"""Current-native terminal labor frontier for TITAN V4.

This module is a narrow selected-action transform, not a second controller.  It
runs only on the final-day hour immediately before the existing terminal router
starts, models the current unit actions with the pinned mechanics module, then
asks the existing terminal route planner whether additional blank-inventory
hands create enough *current-quote* route value to repay exact Fibonacci hire
costs.  It never assumes a fixed number of hires is profitable.

The helper is dependency-injected on purpose: the V4 composer owns exact source
pins for ``mechanics`` and ``terminal`` and can fail closed on source drift.
"""
from __future__ import annotations

import copy
import math
from collections import Counter
from typing import Any, Mapping

KEY = "terminal_labor_frontier"
DEFAULT_MIN_SURPLUS = 250


def _uint(value: Any, name: str, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ValueError(f"{name} must be an integer >= {minimum}")
    return value


def _step(observation: Mapping[str, Any], day_len: int) -> int:
    raw = observation.get("step")
    if raw is not None:
        return _uint(raw, "step")
    return _uint(observation.get("day"), "day") * day_len + _uint(
        observation.get("hour"), "hour"
    )


def _unit_rows(action: Mapping[str, Any]) -> list:
    farmer = action.get("farmer", ["PASS"])
    hands = action.get("hands", [])
    if not isinstance(farmer, list) or not isinstance(hands, list):
        raise ValueError("unsupported unit action shape")
    return [farmer, *hands]


def _simulate_current_units(mechanics: Any, farm: dict, private: dict, action: Mapping[str, Any],
                            board: int, day: int, day_len: int, cap: int) -> None:
    """Apply current own unit rows with the engine's atomic seed-demand veto."""
    rows = _unit_rows(action)
    seed_demand = Counter(
        row[1]
        for row in rows
        if isinstance(row, list) and len(row) >= 2 and row[0] == "PLANT"
    )
    blocked = {
        crop
        for crop, qty in seed_demand.items()
        if qty > private.get("seeds", {}).get(crop, 0)
    }
    for idx, raw in enumerate(rows):
        row = raw
        if isinstance(row, list) and len(row) >= 2 and row[0] == "PLANT" and row[1] in blocked:
            row = ["PASS"]
        mechanics._apply_unit_action(farm, private, idx, row, board, day, day_len, cap)


def _terminal_value(terminal: Any, farm: dict, private: dict, start: int, final: int,
                    day: int, prices: Mapping[str, Any], cap: int) -> float | None:
    positions = [farm.get("farmer"), *farm.get("hands", [])]
    inventories = private.get("inventories", [])
    if len(inventories) < len(positions):
        return None
    safe_prices = {}
    for item, price in prices.items():
        if isinstance(price, bool) or not isinstance(price, (int, float)) or not math.isfinite(price):
            return None
        safe_prices[item] = max(1, price)
    routes, evaluations = terminal.assign_routes(
        farm,
        [dict(inventories[i]) for i in range(len(positions))],
        start,
        final,
        day,
        safe_prices,
        cap,
    )
    if not isinstance(routes, list) or not isinstance(evaluations, list):
        return None
    total = 0.0
    for row in evaluations:
        if row is None:
            continue
        try:
            value = row[0]
        except Exception:
            return None
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            return None
        total += max(0.0, float(value))
    return total


def terminal_hire_frontier(
    mechanics: Any,
    terminal: Any,
    observation: Mapping[str, Any],
    configuration: Mapping[str, Any] | None,
    selected_action: Mapping[str, Any],
    *,
    max_extra_hires: int = 10,
) -> dict:
    """Return a complete final-hour-1 marginal-hire frontier and limits.

    Only an all-HIRE market prefix is accepted.  This makes current cash a
    conservative exact funding bound and avoids pretending that a requested SELL
    is a realized receipt.  New hires are valued beginning at the existing
    terminal router's hour-2 start because HIRE executes after current unit rows.
    """
    report = {
        "eligible": False,
        "reason": "unsupported",
        "step": None,
        "terminal_start": None,
        "existing_action_hires": 0,
        "market_slots": 0,
        "baseline_current_quote_value": None,
        "frontier": [],
        "scope": (
            "current public quotes + existing terminal.assign_routes; "
            "not future rival prices, field EV, or promotion evidence"
        ),
    }
    try:
        cfg = dict(configuration or {})
        board = _uint(cfg.get("boardSize", 10), "boardSize", 1)
        day_len = _uint(cfg.get("turnsPerDay", 24), "turnsPerDay", 1)
        episode = _uint(cfg.get("episodeSteps", 720), "episodeSteps", 3)
        cap = _uint(cfg.get("shedCapacity", 100), "shedCapacity", 1)
        market_limit = _uint(cfg.get("maxMarketOrdersPerTurn", 10), "maxMarketOrdersPerTurn", 1)
        mult = _uint(cfg.get("farmHandCostMult", 1), "farmHandCostMult")
        max_extra_hires = _uint(max_extra_hires, "max_extra_hires")
        now = _step(observation, day_len)
        final = episode - 2
        day_start = (final // day_len) * day_len
        terminal_start = day_start + 2
        decision = day_start + 1
        report.update(step=now, terminal_start=terminal_start)
        if now != decision:
            report["reason"] = "not_terminal_hire_decision"
            return report
        if not isinstance(selected_action, Mapping):
            report["reason"] = "unsupported_action"
            return report
        queue = selected_action.get("market", [])
        if not isinstance(queue, list) or len(queue) > market_limit:
            report["reason"] = "unsupported_market_queue"
            return report
        if any(not (isinstance(order, list) and order and order[0] == "HIRE") for order in queue):
            report["reason"] = "nonhire_market_prefix"
            return report
        me = _uint(observation.get("player"), "player")
        farms = observation.get("farms")
        private_obs = observation.get("private")
        if not isinstance(farms, list) or me >= len(farms) or not isinstance(private_obs, Mapping):
            report["reason"] = "observation_shape"
            return report
        farm = copy.deepcopy(farms[me])
        private = copy.deepcopy(dict(private_obs))
        if len(farm.get("tiles", [])) != board or any(len(row) != board for row in farm["tiles"]):
            report["reason"] = "board_shape"
            return report
        _simulate_current_units(mechanics, farm, private, selected_action, board, now // day_len, day_len, cap)
        cash = farm.get("money")
        if isinstance(cash, bool) or not isinstance(cash, (int, float)) or not math.isfinite(cash) or cash < 0:
            report["reason"] = "cash"
            return report
        existing_action_hires = len(queue)
        for _ in range(existing_action_hires):
            cost = mechanics._hire_cost(farm["hires_today"], mult)
            if farm["money"] < cost:
                report["reason"] = "incumbent_hire_not_funded"
                return report
            mechanics._do_hire(farm, private, board, mult)
        prices = observation.get("market", {}).get("prices", {})
        if not isinstance(prices, Mapping):
            report["reason"] = "prices"
            return report
        baseline = _terminal_value(terminal, farm, private, terminal_start, final,
                                   now // day_len, prices, cap)
        if baseline is None:
            report["reason"] = "baseline_route_failure"
            return report
        slots = max(0, market_limit - len(queue))
        limit = min(slots, max_extra_hires)
        report.update(
            eligible=True,
            reason="ok",
            existing_action_hires=existing_action_hires,
            market_slots=slots,
            baseline_current_quote_value=baseline,
        )
        trial_farm = copy.deepcopy(farm)
        trial_private = copy.deepcopy(private)
        cumulative_cost = 0
        for extra in range(1, limit + 1):
            cost = mechanics._hire_cost(trial_farm["hires_today"], mult)
            if trial_farm["money"] < cost:
                break
            before = trial_farm["money"]
            mechanics._do_hire(trial_farm, trial_private, board, mult)
            paid = before - trial_farm["money"]
            if paid != cost:
                report["reason"] = "hire_cost_drift"
                report["eligible"] = False
                report["frontier"] = []
                return report
            cumulative_cost += cost
            gross = _terminal_value(terminal, trial_farm, trial_private, terminal_start, final,
                                    now // day_len, prices, cap)
            if gross is None:
                report["reason"] = "candidate_route_failure"
                report["eligible"] = False
                report["frontier"] = []
                return report
            gross_gain = gross - baseline
            report["frontier"].append({
                "extra_hires": extra,
                "cumulative_hire_cost": cumulative_cost,
                "gross_current_quote_gain": gross_gain,
                "net_current_quote_gain": gross_gain - cumulative_cost,
                "hands_after": len(trial_farm.get("hands", [])),
            })
        return report
    except Exception as exc:
        report["reason"] = f"fail_closed:{type(exc).__name__}"
        return report


def propose_terminal_hires(
    mechanics: Any,
    terminal: Any,
    observation: Mapping[str, Any],
    configuration: Mapping[str, Any] | None,
    selected_action: Mapping[str, Any],
    *,
    enabled: bool = False,
    min_surplus: int = DEFAULT_MIN_SURPLUS,
    max_extra_hires: int = 10,
) -> tuple[Mapping[str, Any], dict]:
    """Append the best positive marginal HIRE count or return exact parent."""
    if not enabled:
        return selected_action, {"changed": False, "reason": "disabled", "frontier": []}
    try:
        min_surplus = _uint(min_surplus, "min_surplus")
    except Exception:
        return selected_action, {"changed": False, "reason": "invalid_min_surplus", "frontier": []}
    report = terminal_hire_frontier(
        mechanics,
        terminal,
        observation,
        configuration,
        selected_action,
        max_extra_hires=max_extra_hires,
    )
    if not report.get("eligible"):
        return selected_action, dict(report, changed=False)
    qualified = [
        row for row in report["frontier"]
        if row["net_current_quote_gain"] >= min_surplus
    ]
    if not qualified:
        return selected_action, dict(report, changed=False, reason="no_surplus")
    best = max(qualified, key=lambda row: (row["net_current_quote_gain"], -row["extra_hires"]))
    out = copy.deepcopy(dict(selected_action))
    market = out.setdefault("market", [])
    market.extend([["HIRE"] for _ in range(best["extra_hires"])])
    return out, dict(report, changed=True, chosen=best)
