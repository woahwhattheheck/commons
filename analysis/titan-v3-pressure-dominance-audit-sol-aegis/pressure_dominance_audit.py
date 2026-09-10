#!/usr/bin/env python3
"""Exact-engine audit for market-pressure stable partitions.

This module is evidence, not a canonical policy mutation. It demonstrates why
"same-sized proxy loss == 0" is not a sound certificate for demoting a SELL lot
behind an unknown rival market slot, and supplies a bounded fail-closed
certificate that is sound over every feasible rival quantity through the public
shed-capacity bound.
"""
from __future__ import annotations

import argparse
import copy
import importlib.util
import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable, Mapping, Sequence

HERE = Path(__file__).resolve().parent
ROOT = Path(os.environ.get("TITAN_REPO_ROOT", HERE.parents[1])).resolve()
MECHANICS_PATH = ROOT / "revenue/kaggriculture/cloud-execution-lab/mechanics.py"


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load module from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


mechanics = _load_module("_titan_pressure_dominance_mechanics", MECHANICS_PATH)
Quote = Callable[[str, int, Mapping[str, Any] | None], int | float]


def _checked_order(order: Any) -> tuple[str, int] | None:
    if not isinstance(order, list) or len(order) != 3 or order[0] != "SELL":
        return None
    item, quantity = order[1], order[2]
    if item not in mechanics.PRODUCTS:
        return None
    if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity <= 0:
        return None
    return item, quantity


def sale_receipt(
    order: Any,
    market: Mapping[str, Any],
    *,
    quote: Quote = mechanics.market_price,
    delay_units: int = 0,
) -> float | None:
    """Return the own SELL receipt after a hypothetical prior rival supply.

    The official market curve is floored at one dollar. Modeling inventory as
    advancing after floor-price units is conservative and receipt-equivalent:
    every later quote remains one. Invalid inputs fail closed as ``None``.
    """
    parsed = _checked_order(order)
    if (
        parsed is None
        or isinstance(delay_units, bool)
        or not isinstance(delay_units, int)
        or delay_units < 0
    ):
        return None
    item, quantity = parsed
    inventory = market.get("inventory", {})
    prices = market.get("prices", {})
    params = market.get("params")
    if not isinstance(inventory, Mapping) or not isinstance(prices, Mapping):
        return None
    stock = inventory.get(item)
    visible = prices.get(item)
    if isinstance(stock, bool) or not isinstance(stock, int):
        return None
    if isinstance(visible, bool) or not isinstance(visible, (int, float)):
        return None
    if quote(item, stock, params) != visible:
        return None
    total = 0.0
    try:
        for offset in range(quantity):
            value = quote(item, stock + delay_units + offset, params)
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or value < 1
            ):
                return None
            total += float(value)
    except (ArithmeticError, LookupError, TypeError, ValueError):
        return None
    return total


def delay_loss(
    order: Any,
    market: Mapping[str, Any],
    rival_units: int,
    *,
    quote: Quote = mechanics.market_price,
) -> float | None:
    now = sale_receipt(order, market, quote=quote, delay_units=0)
    delayed = sale_receipt(order, market, quote=quote, delay_units=rival_units)
    if now is None or delayed is None:
        return None
    return max(0.0, now - delayed)


def same_sized_proxy_loss(
    order: Any,
    market: Mapping[str, Any],
    *,
    quote: Quote = mechanics.market_price,
) -> float | None:
    parsed = _checked_order(order)
    if parsed is None:
        return None
    return delay_loss(order, market, parsed[1], quote=quote)


def bounded_demotion_safe(
    order: Any,
    market: Mapping[str, Any],
    max_rival_units: int,
    *,
    quote: Quote = mechanics.market_price,
) -> bool:
    """Certify no own-receipt loss for every integer delay in ``[0, bound]``.

    This is the reference specification. A production implementation can use a
    single nonincreasing quote window plus endpoint equality to avoid repeated
    calls, but it must remain equivalent to this exhaustive bounded predicate.
    """
    if (
        isinstance(max_rival_units, bool)
        or not isinstance(max_rival_units, int)
        or max_rival_units < 0
    ):
        return False
    for rival_units in range(max_rival_units + 1):
        loss = delay_loss(order, market, rival_units, quote=quote)
        if loss is None or loss > 0:
            return False
    return True


def _stable_blocks(
    orders: Sequence[Any],
    classifications: Sequence[bool | None],
) -> list[Any]:
    """Move protected lots only across certified-safe lots; barriers split blocks."""
    result = copy.deepcopy(list(orders))
    start = 0
    while start < len(result):
        if classifications[start] is None:
            start += 1
            continue
        stop = start + 1
        while stop < len(result) and classifications[stop] is not None:
            stop += 1
        block = list(zip(result[start:stop], classifications[start:stop]))
        # False = exposed/not certified and therefore protected in parent order.
        # True = receipt-invariant through the bound and safe to demote.
        ranked = [pair for pair in block if pair[1] is False]
        ranked += [pair for pair in block if pair[1] is True]
        result[start:stop] = [order for order, _ in ranked]
        start = stop
    return result


def proxy_zero_partition(
    orders: Sequence[Any],
    market: Mapping[str, Any],
    *,
    quote: Quote = mechanics.market_price,
) -> list[Any]:
    """Reproduce the reviewed proposal: positive proxy lots before zero proxy lots."""
    scores = [same_sized_proxy_loss(order, market, quote=quote) for order in orders]
    classifications = [None if score is None else score == 0 for score in scores]
    return _stable_blocks(orders, classifications)


def certified_partition(
    orders: Sequence[Any],
    market: Mapping[str, Any],
    max_rival_units: int,
    *,
    quote: Quote = mechanics.market_price,
) -> list[Any]:
    """Stable partition using the full bounded receipt-invariance certificate."""
    classifications: list[bool | None] = []
    for order in orders:
        if _checked_order(order) is None:
            classifications.append(None)
        else:
            classifications.append(
                bounded_demotion_safe(
                    order,
                    market,
                    max_rival_units,
                    quote=quote,
                )
            )
    return _stable_blocks(orders, classifications)


def make_market(inventory_overrides: Mapping[str, int]) -> dict[str, Any]:
    inventory = dict.fromkeys(mechanics.PRODUCTS, mechanics.MARKET_I0)
    inventory.update(inventory_overrides)
    return {
        "inventory": inventory,
        "prices": {
            item: mechanics.market_price(item, stock)
            for item, stock in inventory.items()
        },
    }


def run_exact_market(
    own_orders: Sequence[Any],
    rival_orders: Sequence[Any],
    *,
    inventory_overrides: Mapping[str, int],
    shed_capacity: int = 100,
) -> tuple[int, int]:
    """Execute only the pinned official ``_process_market`` surface."""
    market = make_market(inventory_overrides)
    farms = [{"money": 0}, {"money": 0}]

    def stock(orders: Sequence[Any]) -> dict[str, int]:
        result: dict[str, int] = {}
        for order in orders:
            parsed = _checked_order(order)
            if parsed is not None:
                item, quantity = parsed
                result[item] = result.get(item, 0) + quantity
        return result

    privates = [{"shed": stock(own_orders)}, {"shed": stock(rival_orders)}]
    states = [
        SimpleNamespace(
            observation=SimpleNamespace(
                market=market,
                farms=farms,
                private=privates[0],
            ),
            action={"market": copy.deepcopy(list(own_orders))},
        ),
        SimpleNamespace(
            observation=SimpleNamespace(
                market=market,
                farms=farms,
                private=privates[1],
            ),
            action={"market": copy.deepcopy(list(rival_orders))},
        ),
    ]
    env = SimpleNamespace(
        configuration={
            "boardSize": 10,
            "maxMarketOrdersPerTurn": 10,
            "farmHandCostMult": 1,
            "shedCapacity": shed_capacity,
        }
    )
    mechanics._process_market(states, env)
    return int(farms[0]["money"]), int(farms[1]["money"])


def false_zero_scan(
    *,
    inventory_start: int = 9950,
    inventory_stop: int = 10050,
    max_quantity: int = 8,
    max_rival_units: int = 100,
) -> dict[str, Any]:
    """Count local proxy plateaus exposed inside the public rival bound."""
    counts = {item: 0 for item in mechanics.PRODUCTS}
    worst: dict[str, Any] | None = None
    total = 0
    for item in mechanics.PRODUCTS:
        for inventory in range(inventory_start, inventory_stop + 1):
            market = make_market({item: inventory})
            for quantity in range(1, max_quantity + 1):
                order = ["SELL", item, quantity]
                proxy = same_sized_proxy_loss(order, market)
                bounded = delay_loss(order, market, max_rival_units)
                if proxy == 0 and bounded is not None and bounded > 0:
                    total += 1
                    counts[item] += 1
                    record = {
                        "item": item,
                        "inventory": inventory,
                        "quantity": quantity,
                        "loss_at_bound": int(bounded),
                    }
                    if (
                        worst is None
                        or record["loss_at_bound"] > worst["loss_at_bound"]
                    ):
                        worst = record
    return {
        "inventory_range_inclusive": [inventory_start, inventory_stop],
        "quantity_range_inclusive": [1, max_quantity],
        "rival_bound": max_rival_units,
        "false_zero_cells": total,
        "by_product": counts,
        "worst_cell": worst,
    }


def finding() -> dict[str, Any]:
    market = make_market({"TOMATO": 9999, "MILK": 9999})
    parent = [["SELL", "TOMATO", 1], ["SELL", "MILK", 1]]
    rival = [["SELL", "TOMATO", 2], []]
    proxy_candidate = proxy_zero_partition(parent, market)
    certified_candidate = certified_partition(parent, market, 100)
    parent_cash = run_exact_market(
        parent,
        rival,
        inventory_overrides={"TOMATO": 9999, "MILK": 9999},
    )
    proxy_cash = run_exact_market(
        proxy_candidate,
        rival,
        inventory_overrides={"TOMATO": 9999, "MILK": 9999},
    )
    certified_cash = run_exact_market(
        certified_candidate,
        rival,
        inventory_overrides={"TOMATO": 9999, "MILK": 9999},
    )
    return {
        "schema": "titan-pressure-dominance-audit/v1",
        "claim": "same-sized proxy zero is not a bounded demotion certificate",
        "witness": {
            "inventory": {"TOMATO": 9999, "MILK": 9999},
            "parent_orders": parent,
            "rival_orders": rival,
            "proxy_scores": {
                "TOMATO": int(same_sized_proxy_loss(parent[0], market) or 0),
                "MILK": int(same_sized_proxy_loss(parent[1], market) or 0),
            },
            "proxy_candidate_orders": proxy_candidate,
            "certified_candidate_orders": certified_candidate,
            "parent_cash": {"own": parent_cash[0], "rival": parent_cash[1]},
            "proxy_candidate_cash": {
                "own": proxy_cash[0],
                "rival": proxy_cash[1],
            },
            "certified_candidate_cash": {
                "own": certified_cash[0],
                "rival": certified_cash[1],
            },
            "proxy_delta": {
                "own": proxy_cash[0] - parent_cash[0],
                "margin": (
                    (proxy_cash[0] - proxy_cash[1])
                    - (parent_cash[0] - parent_cash[1])
                ),
            },
            "tomato_safe_through_100": bounded_demotion_safe(
                parent[0],
                market,
                100,
            ),
        },
        "plateau_scan": false_zero_scan(),
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", type=Path, help="write canonical JSON receipt")
    args = parser.parse_args(argv)
    payload = finding()
    rendered = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if args.write:
        args.write.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
