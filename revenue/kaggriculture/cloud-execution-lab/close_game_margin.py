# SPDX-License-Identifier: Apache-2.0
"""Late-game seller ranking policy over already-admissible TITAN sale plans.

This module never invents orders, stock, cash, or market slots. It only ranks
plans that the canonical selected seller has already admitted.
"""
from __future__ import annotations

import math

MODES = ("off", "cash_max", "ahead", "behind", "auto")


def _finite_number(value):
    return (not isinstance(value, bool)
            and isinstance(value, (int, float))
            and math.isfinite(float(value)))


def build_margin_context(*, mode, now, last, own_cash, rival_cash,
                         rival_liquidation_bound, window=96, buffer=0):
    """Return a fail-closed ranking context built only from public evidence."""
    mode = str(mode or "off").strip().lower()
    if mode not in MODES:
        return {"active": False, "reason": "unsupported_mode", "mode": mode}

    ints = (now, last, own_cash, rival_cash, rival_liquidation_bound, window, buffer)
    if any(isinstance(value, bool) or not isinstance(value, int) for value in ints):
        return {"active": False, "reason": "non_plain_integer", "mode": mode}
    if window < 0 or buffer < 0 or rival_liquidation_bound < 0 or last < now:
        return {"active": False, "reason": "invalid_bound", "mode": mode}

    remaining = last - now
    gap = own_cash - rival_cash
    context = {
        "active": False,
        "reason": "off",
        "requested_mode": mode,
        "mode": mode,
        "now": now,
        "last": last,
        "remaining": remaining,
        "window": window,
        "buffer": buffer,
        "own_cash": own_cash,
        "rival_cash": rival_cash,
        "cash_gap": gap,
        "rival_liquidation_bound": rival_liquidation_bound,
    }
    if mode == "off":
        return context
    if remaining > window:
        context["reason"] = "outside_window"
        return context

    safe_ahead = gap > rival_liquidation_bound + buffer
    if mode == "auto":
        effective = "ahead" if safe_ahead else "behind"
    elif mode == "ahead":
        effective = "ahead" if safe_ahead else "cash_max"
    elif mode == "behind":
        effective = "cash_max" if safe_ahead else "behind"
    else:
        effective = mode

    context["mode"] = effective
    context["active"] = True
    context["reason"] = "late_window"
    context["safe_ahead"] = safe_ahead
    return context


def _scenario_metrics(info):
    scenarios = info.get("scenarios") if isinstance(info, dict) else None
    if not isinstance(scenarios, dict) or not scenarios:
        return None
    own = []
    carry = []
    rival = []
    for row in scenarios.values():
        if not isinstance(row, dict):
            return None
        values = (row.get("own_receipts"), row.get("rival_receipts"),
                  row.get("carry_units"))
        if not all(_finite_number(value) for value in values):
            return None
        own.append(float(values[0]))
        rival.append(float(values[1]))
        carry.append(float(values[2]))
    return {
        "own_receipt_floor": min(own),
        "own_receipt_ceiling": max(own),
        "rival_receipt_ceiling": max(rival),
        "carry_floor": min(carry),
        "carry_ceiling": max(carry),
    }


def rank_option(info, context, base_rank):
    """Return a deterministic policy rank plus diagnostics."""
    if not context or not context.get("active"):
        return base_rank, {"active": False, "reason": (context or {}).get("reason", "no_context")}

    metrics = _scenario_metrics(info)
    forced = bool(info.get("forced_feasibility", False)) if isinstance(info, dict) else False
    try:
        base_score = float(base_rank[1])
    except (TypeError, ValueError, IndexError):
        base_score = 0.0

    if metrics is None:
        rank = (forced, 0, 0.0, 0.0, base_score)
        return rank, {"active": True, "reason": "unsupported_report",
                      "mode": context.get("mode")}

    mode = context.get("mode")
    own_floor = metrics["own_receipt_floor"]
    carry_floor = metrics["carry_floor"]
    carry_ceiling = metrics["carry_ceiling"]
    gap = float(context["cash_gap"])
    rival_bound = float(context["rival_liquidation_bound"])
    margin_floor = gap + own_floor - rival_bound

    if mode == "ahead":
        rank = (forced, 1, carry_floor, margin_floor, base_score)
    elif mode in ("behind", "cash_max"):
        rank = (forced, 1, own_floor, -carry_ceiling, base_score)
    else:
        return base_rank, {"active": False, "reason": "inactive_effective_mode",
                           "mode": mode}

    report = {
        "active": True,
        "reason": "ranked",
        "requested_mode": context.get("requested_mode"),
        "mode": mode,
        "safe_ahead": bool(context.get("safe_ahead", False)),
        "cash_gap": context["cash_gap"],
        "rival_liquidation_bound": context["rival_liquidation_bound"],
        "margin_floor": margin_floor,
        **metrics,
    }
    return rank, report
