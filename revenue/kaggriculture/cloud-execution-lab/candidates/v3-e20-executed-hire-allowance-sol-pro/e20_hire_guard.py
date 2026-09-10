# SPDX-License-Identifier: Apache-2.0
"""E20 low-demand HIRE limiter with executed-allowance custody.

The official engine increments ``hires_today`` only when ``_do_hire`` can pay
that HIRE at its literal executable market index.  A raw HIRE row is therefore
not proof that the daily allowance was consumed.  This repair drops later HIREs
only after the allowed earlier HIREs are provably executable from current cash,
before any preceding market order that can change money.  Ambiguity is an exact
no-op.  Rows outside the official ``q[:max(1, N)]`` prefix are never changed.

Lineage: exact one-tree handoff F0C0JPCAAQP, SHA-256
f68792bf7f0fb269864ef4ab25967292e2d4cd03439dbc5c52b98dfcebd1b728;
replaces overlay/e20_hire_guard.py SHA-256
3d841b271bd735d4edecfc05be31753bd94f5a5fcfb37e0fea24df4eeb7372ea.
"""
from __future__ import annotations

from copy import deepcopy
import math
from typing import Any, Mapping

_MONEY_OPS = frozenset({"HIRE", "BUY_LAND", "BUY_SEED", "BUY_PRODUCT", "BUY_ANIMAL", "SELL"})


def unwatered_crops(farm: Mapping[str, Any]) -> int:
    """Count actual engine PLANT tiles still needing today's WATER action."""
    count = 0
    for row in farm.get("tiles") or []:
        if not isinstance(row, list):
            continue
        for tile in row:
            if (
                isinstance(tile, Mapping)
                and tile.get("kind") == "PLANT"
                and not tile.get("watered_today", False)
            ):
                count += 1
    return count


def _literal_int(value: Any, *, minimum: int | None = None) -> int:
    if isinstance(value, bool):
        raise ValueError("boolean is not a literal integer")
    parsed = int(value)
    if minimum is not None and parsed < minimum:
        raise ValueError("integer below supported minimum")
    return parsed


def _finite_money(value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("money is not finite numeric")
    money = float(value)
    if not math.isfinite(money):
        raise ValueError("money is not finite numeric")
    return money


def _last_action_step(config: Mapping[str, Any]) -> int:
    return max(0, _literal_int(config.get("episodeSteps", 720), minimum=2) - 2)


def _market_limit(config: Mapping[str, Any]) -> int:
    return max(1, _literal_int(config.get("maxMarketOrdersPerTurn", 10)))


def _fib(index: int) -> int:
    """Match the official engine: fib(0)=1, fib(1)=1, fib(2)=2, ..."""
    a, b = 1, 1
    for _ in range(index):
        a, b = b, a + b
    return a


def _is_hire(order: Any) -> bool:
    return isinstance(order, list) and bool(order) and order[0] == "HIRE"


def _can_change_money(order: Any) -> bool:
    """Conservative engine-recognized money-effect barrier.

    Malformed and unknown rows are engine no-ops.  Any syntactically recognized
    market operation before a HIRE makes its affordability path dependent on
    live execution, so E20 declines to guess.
    """
    if not isinstance(order, list) or not order:
        return False
    op = order[0]
    if op in ("HIRE", "BUY_LAND"):
        return True
    if op not in _MONEY_OPS or len(order) < 3:
        return False
    try:
        quantity = _literal_int(order[2])
    except (TypeError, ValueError, OverflowError):
        return False
    return quantity > 0


def apply_hire_guard(
    obs: Mapping[str, Any],
    action: Mapping[str, Any],
    config: Mapping[str, Any] | None = None,
    *,
    enabled: bool = False,
):
    report: dict[str, Any] = {
        "enabled": bool(enabled),
        "reason": "NO_OP",
        "changed": False,
        "dropped_indices": [],
        "certified_hire_indices": [],
    }
    if not enabled:
        report["reason"] = "OFF"
        return action, report

    cfg = dict(config or {})
    try:
        step = _literal_int(obs.get("step", 0), minimum=0)
        last_action_step = _last_action_step(cfg)
        market_limit = _market_limit(cfg)
        max_hires = _literal_int(cfg.get("e20_max_hires_per_day", 3), minimum=0)
        minimum_unwatered = _literal_int(
            cfg.get("e20_min_unwatered_crops", 3), minimum=0
        )
        hire_multiplier = _literal_int(cfg.get("farmHandCostMult", 1), minimum=1)
    except (TypeError, ValueError, OverflowError):
        report["reason"] = "BAD_CONFIG_OR_STEP"
        return action, report

    report["max_market_orders_per_turn"] = market_limit
    if step >= last_action_step:
        report["reason"] = "NO_EDIT_TERMINAL_STEP"
        return action, report

    farms = obs.get("farms") or []
    try:
        player = _literal_int(obs.get("player", 0), minimum=0)
    except (TypeError, ValueError, OverflowError):
        report["reason"] = "BAD_PLAYER_OR_FARM"
        return action, report
    if player >= len(farms) or not isinstance(farms[player], Mapping):
        report["reason"] = "BAD_PLAYER_OR_FARM"
        return action, report
    farm = farms[player]
    try:
        hires_today = _literal_int(farm.get("hires_today", 0), minimum=0)
        money = _finite_money(farm.get("money", 0))
    except (TypeError, ValueError, OverflowError):
        report["reason"] = "BAD_PUBLIC_FARM_STATE"
        return action, report

    demand = unwatered_crops(farm)
    report.update(
        hires_today=hires_today,
        max_hires_per_day=max_hires,
        unwatered_crops=demand,
        minimum_unwatered_crops=minimum_unwatered,
        hire_cost_multiplier=hire_multiplier,
    )
    if demand >= minimum_unwatered:
        report["reason"] = "DEMAND_JUSTIFIES_HIRES"
        return action, report

    raw_market = action.get("market", []) if isinstance(action, Mapping) else []
    if not isinstance(raw_market, list):
        report["reason"] = "BAD_MARKET_QUEUE"
        return action, report
    executable = raw_market[:market_limit]
    hire_indices = [index for index, order in enumerate(executable) if _is_hire(order)]
    report["executable_hire_indices"] = hire_indices
    report["inert_suffix_hire_indices"] = [
        index
        for index, order in enumerate(raw_market[market_limit:], start=market_limit)
        if _is_hire(order)
    ]
    if not hire_indices:
        report["reason"] = "NO_EXECUTABLE_HIRE"
        return action, report

    remaining_allowance = max(0, max_hires - hires_today)
    report["remaining_allowance"] = remaining_allowance
    if len(hire_indices) <= remaining_allowance:
        report["reason"] = "HIRES_WITHIN_LOW_DEMAND_ALLOWANCE"
        return action, report

    # At the cap, no additional HIRE is allowed; affordability is irrelevant.
    if remaining_allowance == 0:
        certified: list[int] = []
    else:
        certified = []
        simulated_money = money
        simulated_hires = hires_today
        for index, order in enumerate(executable):
            if _is_hire(order):
                cost = hire_multiplier * _fib(simulated_hires)
                if simulated_money < cost:
                    report.update(
                        reason="UNCERTAIN_ALLOWED_HIRE_EXECUTION",
                        uncertainty_index=index,
                        uncertainty="UNFUNDED_HIRE_MAY_BE_FUNDED_LATER",
                        required_cost=cost,
                        certified_hire_indices=certified,
                    )
                    return action, report
                simulated_money -= cost
                simulated_hires += 1
                certified.append(index)
                if len(certified) == remaining_allowance:
                    break
                continue
            if _can_change_money(order):
                report.update(
                    reason="UNCERTAIN_ALLOWED_HIRE_EXECUTION",
                    uncertainty_index=index,
                    uncertainty="PRECEDING_MONEY_CHANGING_ORDER",
                    certified_hire_indices=certified,
                )
                return action, report
        if len(certified) != remaining_allowance:
            # Defensive: the earlier cardinality test says a later excess HIRE
            # exists, but do not mutate unless every allowed success was proved.
            report.update(
                reason="UNCERTAIN_ALLOWED_HIRE_EXECUTION",
                uncertainty="ALLOWANCE_NOT_CERTIFIED",
                certified_hire_indices=certified,
            )
            return action, report

    allowed = set(certified)
    drop_indices = [index for index in hire_indices if index not in allowed]
    if not drop_indices:
        report.update(
            reason="HIRES_WITHIN_LOW_DEMAND_ALLOWANCE",
            certified_hire_indices=certified,
        )
        return action, report

    out = deepcopy(action)
    out_market = list(out.get("market") or [])
    for index in drop_indices:
        out_market[index] = []
    out["market"] = out_market
    report.update(
        reason="E20_DROP_CERTIFIED_EXCESS_LOW_DEMAND_HIRES",
        changed=True,
        dropped_indices=drop_indices,
        certified_hire_indices=certified,
    )
    return out, report
