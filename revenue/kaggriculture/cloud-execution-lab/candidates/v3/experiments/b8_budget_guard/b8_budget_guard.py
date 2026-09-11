# SPDX-License-Identifier: Apache-2.0
"""B8 experiment: reserve provable later same-day native spend before additive investment.

This is deliberately narrow and default-off. R04's V219 and V233 already price
all rows in their current additive transaction and retain fixed safety floors.
B8 only asks a second question: is there a later same-day native tape purchase
whose cost is exact from public/own state today? If so, make that amount
unavailable to the existing V219/V233 budget test. The original request
functions still own every eligibility, capacity, order-cap, state, and row
construction decision.

State/market-dependent future costs (BUY_LAND, HIRE, BUY_PRODUCT), malformed
shape/type, or an unknown opcode make B8 fail open to the parent exactly rather
than inventing a reserve.
"""
from __future__ import annotations

import copy
import math

import r04_full_router as r04

_ORIGINAL_V219_REQUEST = r04._v219_request
_ORIGINAL_V233_REQUEST = r04._v233_request

_ANIMAL_COST = {"GOOSE": 300, "COW": 400, "SHEEP": 500}
_SEED_COST = {"WHEAT": 10, "CARROT": 20, "TOMATO": 50, "STRAWBERRY": 100, "MELON": 80}

REPORT = {
    "calls": 0,
    "proof_complete": 0,
    "parent_would_invest": 0,
    "activations": 0,
    "reserved_cash": 0,
    "v219_activations": 0,
    "v233_activations": 0,
    "trace": [],
}


def reset_report():
    for key in tuple(REPORT):
        REPORT[key] = [] if key == "trace" else 0


def _strict_nonnegative_int(value):
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else None


def _strict_nonnegative_money(value):
    """Accept official-engine numeric money, reject bool/non-finite/type poison."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    if not math.isfinite(value) or value < 0:
        return None
    return value


def _fixed_cost_of_future_actions(actions):
    """Return exact fixed purchase cost, or None when the bound is incomplete.

    Empty list rows are canonical market placeholders. Every non-empty row must
    otherwise be canonical before it can contribute *or* be ignored. In
    particular SELL contributes zero reserve only after item/quantity validation.
    BUY_LAND is intentionally incomplete here: the official engine prices the
    first/second/third extra quadrant at different values, so a context-free
    tape-row helper cannot certify an exact land obligation.
    """
    total = 0
    if not isinstance(actions, list):
        return None
    for planned in actions:
        if not isinstance(planned, dict) or "market" not in planned:
            return None
        market = planned["market"]
        if not isinstance(market, list):
            return None
        for order in market:
            if order == []:
                continue
            if not isinstance(order, list) or not order or not isinstance(order[0], str):
                return None
            op = order[0]
            if op == "SELL":
                if len(order) != 3 or not isinstance(order[1], str) or order[1] not in r04.PRODUCTS:
                    return None
                if _strict_nonnegative_int(order[2]) is None:
                    return None
                continue
            if op in ("BUY_LAND", "HIRE", "BUY_PRODUCT"):
                # BUY_LAND depends on unlocked-quadrant state; HIRE depends on
                # future hires_today; BUY_PRODUCT depends on the future quote.
                return None
            if op == "BUY_ANIMAL":
                if len(order) != 3 or not isinstance(order[1], str) or order[1] not in _ANIMAL_COST:
                    return None
                qty = _strict_nonnegative_int(order[2])
                if qty is None:
                    return None
                total += qty * _ANIMAL_COST[order[1]]
                continue
            if op == "BUY_SEED":
                if len(order) != 3 or not isinstance(order[1], str) or order[1] not in _SEED_COST:
                    return None
                qty = _strict_nonnegative_int(order[2])
                if qty is None:
                    return None
                total += qty * _SEED_COST[order[1]]
                continue
            return None
    return total


def _future_native_reserve(obs, native):
    try:
        step = obs["step"]
        player = obs["player"]
        farms = obs["farms"]
    except (KeyError, TypeError):
        return None
    if not isinstance(step, int) or isinstance(step, bool) or step < 0:
        return None
    if not isinstance(player, int) or isinstance(player, bool) or player < 0:
        return None
    if not isinstance(farms, list) or player >= len(farms) or not isinstance(farms[player], dict):
        return None
    money = _strict_nonnegative_money(farms[player].get("money"))
    if money is None:
        return None
    day, hour = divmod(step, 24)
    try:
        planned = r04._v219_native_day(native, day)
    except Exception:
        return None
    if not isinstance(planned, list) or hour >= len(planned):
        return None
    return _fixed_cost_of_future_actions(planned[hour + 1 :])


def _guard_request(layer, original, parent_report, obs, action, state, native):
    REPORT["calls"] += 1
    reserve = _future_native_reserve(obs, native)
    if reserve is None or reserve <= 0:
        return original(obs, action, state, native)
    REPORT["proof_complete"] += 1

    # Ask whether the unguarded parent would actually invest without consuming
    # its real state transition or telemetry. The real call below is the sole
    # authoritative mutation.
    try:
        shadow_state = copy.deepcopy(state)
        shadow_action = copy.deepcopy(action)
        report_snapshot = copy.deepcopy(parent_report)
        shadow = original(obs, shadow_action, shadow_state, native)
    except Exception:
        return original(obs, action, state, native)
    finally:
        if "report_snapshot" in locals():
            parent_report.clear()
            parent_report.update(report_snapshot)

    if shadow == action:
        return original(obs, action, state, native)
    REPORT["parent_would_invest"] += 1

    try:
        guarded_obs = copy.deepcopy(obs)
        player = guarded_obs["player"]
        real_money = _strict_nonnegative_money(guarded_obs["farms"][player]["money"])
        if real_money is None:
            return original(obs, action, state, native)
        guarded_obs["farms"][player]["money"] = max(0, real_money - reserve)
    except Exception:
        return original(obs, action, state, native)

    result = original(guarded_obs, action, state, native)
    if result == action:
        REPORT["activations"] += 1
        REPORT["reserved_cash"] += reserve
        REPORT[layer + "_activations"] += 1
        if len(REPORT["trace"]) < 256:
            REPORT["trace"].append({
                "step": int(obs["step"]),
                "layer": layer,
                "reserve": int(reserve),
                "money": real_money,
            })
    return result


def guarded_v219_request(obs, action, state, native):
    return _guard_request("v219", _ORIGINAL_V219_REQUEST, r04._V219_REPORT, obs, action, state, native)


def guarded_v233_request(obs, action, state, native):
    return _guard_request("v233", _ORIGINAL_V233_REQUEST, r04._V233_REPORT, obs, action, state, native)


def install(
    host=None,
    *,
    enabled=True,
    horizon=8,
    opening=0,
    row_order=True,
    evening_flush=True,
    sale_fertilizer=True,
    cattle_early=True,
):
    """Install exact V3.1 knobs plus the default-off B8 experiment seam."""
    r04._v219_request = guarded_v219_request if enabled else _ORIGINAL_V219_REQUEST
    r04._v233_request = guarded_v233_request if enabled else _ORIGINAL_V233_REQUEST
    return r04.install(
        host,
        horizon=horizon,
        opening=opening,
        row_order=row_order,
        evening_flush=evening_flush,
        sale_fertilizer=sale_fertilizer,
        cattle_early=cattle_early,
    )
