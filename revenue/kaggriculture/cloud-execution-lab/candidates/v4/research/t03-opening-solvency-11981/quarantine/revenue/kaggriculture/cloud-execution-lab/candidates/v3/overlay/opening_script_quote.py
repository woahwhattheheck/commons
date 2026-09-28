# SPDX-License-Identifier: Apache-2.0
"""Conservative, deterministic market-queue quotation for T03."""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from opening_script_data import ANIMAL_COSTS, SEED_COSTS
from opening_script_state import fibonacci_hire, integer, land_cost, number, own_farm


def quote_market(
    obs: Mapping[str, Any],
    market: Sequence[Sequence[Any]],
    config: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Quote a queue without crediting uncertain same-turn SELL receipts.

    BUY_PRODUCT fails closed because its nonlinear per-unit market walk requires the
    engine quote function. HIRE starts at public ``hires_today`` and follows the exact
    Fibonacci sequence. Malformed or unsupported orders raise ``ValueError``.
    """
    if not isinstance(market, Sequence) or isinstance(market, (str, bytes)):
        raise ValueError("market queue must be a sequence")
    cfg = dict(config or {})
    farm = own_farm(obs)
    money = number(farm.get("money", 0.0))
    hires_today = integer(farm.get("hires_today", 0), minimum=0)
    hire_multiplier = number(cfg.get("farmHandCostMult", 1.0))
    total = 0.0
    lines: list[dict[str, Any]] = []
    queued_hires = 0
    queued_land = 0

    for index, raw in enumerate(market):
        if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
            raise ValueError("market order must be a sequence")
        order = list(raw)
        if not order:
            lines.append({"index": index, "op": "EMPTY", "cost": 0.0})
            continue
        op = order[0]
        cost = 0.0
        if op == "HIRE" and len(order) == 1:
            cost = hire_multiplier * fibonacci_hire(hires_today + queued_hires)
            queued_hires += 1
        elif op == "BUY_SEED" and len(order) == 3:
            item = str(order[1])
            quantity = integer(order[2], minimum=1)
            if item not in SEED_COSTS:
                raise ValueError("unknown seed")
            cost = float(SEED_COSTS[item] * quantity)
        elif op == "BUY_ANIMAL" and len(order) == 3:
            item = str(order[1])
            quantity = integer(order[2], minimum=1)
            if item not in ANIMAL_COSTS:
                raise ValueError("unknown animal")
            cost = float(ANIMAL_COSTS[item] * quantity)
        elif op == "BUY_PRODUCT" and len(order) == 3:
            raise ValueError("BUY_PRODUCT requires the engine quote function")
        elif op == "BUY_LAND" and len(order) == 1:
            cost = land_cost(farm, cfg, queued_land)
            queued_land += 1
        elif op == "SELL" and len(order) == 3:
            integer(order[2], minimum=1)
            cost = 0.0  # Never require an uncertain same-turn receipt for solvency.
        else:
            raise ValueError("unsupported market action grammar")
        total += cost
        lines.append({"index": index, "op": op, "cost": cost})

    return {
        "money": money,
        "cost": total,
        "remaining": money - total,
        "hires_today": hires_today,
        "queued_hires": queued_hires,
        "orders": lines,
    }
