#!/usr/bin/env python3
"""Exact-engine audit for market-pressure ordering claims.

This module is evidence, not a canonical policy mutation. It demonstrates three
independent reasons that a same-sized sale-pressure proxy cannot establish a
universal own-cash dominance theorem:

1. integer-rounded local plateaus hide larger rival sale exposure;
2. a raw-public-inventory certificate ignores prior executable queue rows; and
3. hidden rival BUY_PRODUCT demand can make a later WHEAT/FERTILIZER sale more
   valuable than the promoted sale.

The bounded helper is intentionally named ``raw_bounded_demotion_safe``: it is
the disproved intermediate repair, retained only so its predecessor killer is
executable. ``bidirectional_flat_invariant`` is a conservative invariance
primitive, not a strength or reordering claim.
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

BUYABLE_PRODUCTS = frozenset(("WHEAT", "FERTILIZER"))


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load module from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


mechanics = _load_module("_titan_pressure_dominance_mechanics", MECHANICS_PATH)
Quote = Callable[[str, int, Mapping[str, Any] | None], int]


def _checked_order(order: Any) -> tuple[str, int] | None:
    if not isinstance(order, list) or len(order) != 3 or order[0] != "SELL":
        return None
    item, quantity = order[1], order[2]
    if item not in mechanics.PRODUCTS:
        return None
    if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity <= 0:
        return None
    return item, quantity


def _checked_nonnegative_int(value: Any) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return None
    return value


def _quote_at(
    quote: Quote,
    item: str,
    inventory: int,
    params: Mapping[str, Any] | None,
) -> int | None:
    if _checked_nonnegative_int(inventory) is None:
        return None
    try:
        value = quote(item, inventory, params)
    except (ArithmeticError, LookupError, TypeError, ValueError):
        return None
    # The pinned canonical quote is an exact integer. Reject bools, floats,
    # NaN/inf, and implementation-defined numeric coercions fail-closed.
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        return None
    return value


def _market_stock(
    item: str,
    market: Mapping[str, Any],
    *,
    quote: Quote,
) -> tuple[int, Mapping[str, Any] | None] | None:
    inventory = market.get("inventory", {})
    visible_prices = market.get("prices", {})
    params = market.get("params")
    if not isinstance(inventory, Mapping) or not isinstance(visible_prices, Mapping):
        return None
    stock = inventory.get(item)
    visible = visible_prices.get(item)
    if _checked_nonnegative_int(stock) is None:
        return None
    if isinstance(visible, bool) or not isinstance(visible, int) or visible < 1:
        return None
    expected = _quote_at(quote, item, stock, params)
    if expected is None or expected != visible:
        return None
    return stock, params


def sale_receipt(
    order: Any,
    market: Mapping[str, Any],
    *,
    quote: Quote = mechanics.market_price,
    delay_units: int = 0,
) -> int | None:
    """Own SELL receipt after a hypothetical contiguous prior supply delay.

    This helper models an inventory displacement, not a complete market row.
    It is exact for the local proxy and deliberately insufficient as a
    universal queue certificate; the audit contains two predecessor killers for
    that overreach.
    """
    parsed = _checked_order(order)
    delay = _checked_nonnegative_int(delay_units)
    if parsed is None or delay is None:
        return None
    item, quantity = parsed
    resolved = _market_stock(item, market, quote=quote)
    if resolved is None:
        return None
    stock, params = resolved
    total = 0
    for offset in range(quantity):
        value = _quote_at(quote, item, stock + delay + offset, params)
        if value is None:
            return None
        total += value
    return total


def delay_loss(
    order: Any,
    market: Mapping[str, Any],
    displacement: int,
    *,
    quote: Quote = mechanics.market_price,
) -> int | None:
    now = sale_receipt(order, market, quote=quote, delay_units=0)
    delayed = sale_receipt(order, market, quote=quote, delay_units=displacement)
    if now is None or delayed is None:
        return None
    return max(0, now - delayed)


def same_sized_proxy_loss(
    order: Any,
    market: Mapping[str, Any],
    *,
    quote: Quote = mechanics.market_price,
) -> int | None:
    parsed = _checked_order(order)
    if parsed is None:
        return None
    return delay_loss(order, market, parsed[1], quote=quote)


def raw_bounded_demotion_safe(
    order: Any,
    market: Mapping[str, Any],
    max_rival_sell_units: int,
    *,
    quote: Quote = mechanics.market_price,
) -> bool:
    """Disproved intermediate repair retained as an executable predecessor.

    It checks every contiguous upward displacement from raw public inventory.
    That closes the rounded-plateau witness, but not queue-prefix displacement
    or hidden BUY_PRODUCT demand. Do not use this as a production certificate.
    """
    bound = _checked_nonnegative_int(max_rival_sell_units)
    if bound is None:
        return False
    baseline = sale_receipt(order, market, quote=quote, delay_units=0)
    if baseline is None:
        return False
    for displacement in range(bound + 1):
        value = sale_receipt(
            order,
            market,
            quote=quote,
            delay_units=displacement,
        )
        if value is None or value != baseline:
            return False
    return True


def bidirectional_flat_invariant(
    order: Any,
    market: Mapping[str, Any],
    *,
    max_prior_buys: int,
    max_prior_sales: int,
    quote: Quote = mechanics.market_price,
) -> bool:
    """Conservative quote-invariance primitive over a bidirectional envelope.

    The interval includes possible opponent purchases below public inventory and
    possible prior/interleaved sales above it. Constant integer quotes across
    this full window are sufficient for the lot's receipt to be invariant to
    ordering inside that envelope. This function does not itself prove that a
    policy's supplied bounds are complete, nor that another promoted lot is
    safe; those obligations stay with the caller.
    """
    parsed = _checked_order(order)
    buys = _checked_nonnegative_int(max_prior_buys)
    sales = _checked_nonnegative_int(max_prior_sales)
    if parsed is None or buys is None or sales is None:
        return False
    item, quantity = parsed
    resolved = _market_stock(item, market, quote=quote)
    if resolved is None:
        return False
    stock, params = resolved
    low = stock - buys
    high = stock + sales + quantity - 1
    if low < 0:
        return False
    expected = _quote_at(quote, item, low, params)
    if expected is None:
        return False
    for inventory in range(low + 1, high + 1):
        if _quote_at(quote, item, inventory, params) != expected:
            return False
    return True


def _stable_blocks(
    orders: Sequence[Any],
    classifications: Sequence[bool | None],
) -> list[Any]:
    """Move exposed lots before locally-safe lots, preserving barriers/order."""
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
        # False = exposed/not certified and therefore ranked first.
        # True = locally classified safe and demoted by the reviewed repairs.
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
    """Reproduce the reviewed proposal: positive proxy lots before zero lots."""
    scores = [same_sized_proxy_loss(order, market, quote=quote) for order in orders]
    classifications = [None if score is None else score == 0 for score in scores]
    return _stable_blocks(orders, classifications)


def raw_bounded_partition(
    orders: Sequence[Any],
    market: Mapping[str, Any],
    max_rival_sell_units: int,
    *,
    quote: Quote = mechanics.market_price,
) -> list[Any]:
    """Reproduce the disproved raw-state bounded repair."""
    classifications: list[bool | None] = []
    for order in orders:
        if _checked_order(order) is None:
            classifications.append(None)
        else:
            classifications.append(
                raw_bounded_demotion_safe(
                    order,
                    market,
                    max_rival_sell_units,
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


def _sale_stock(orders: Sequence[Any]) -> dict[str, int]:
    result: dict[str, int] = {}
    for order in orders:
        parsed = _checked_order(order)
        if parsed is not None:
            item, quantity = parsed
            result[item] = result.get(item, 0) + quantity
    return result


def run_exact_market(
    own_orders: Sequence[Any],
    rival_orders: Sequence[Any],
    *,
    inventory_overrides: Mapping[str, int],
    starting_money: tuple[int, int] = (0, 0),
    shed_capacity: int = 100,
) -> dict[str, Any]:
    """Execute only the pinned official ``_process_market`` surface."""
    market = make_market(inventory_overrides)
    farms = [{"money": starting_money[0]}, {"money": starting_money[1]}]
    privates = [
        {"shed": _sale_stock(own_orders), "seeds": {}, "inventories": [{}]},
        {"shed": _sale_stock(rival_orders), "seeds": {}, "inventories": [{}]},
    ]
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
    return {
        "money": {"own": int(farms[0]["money"]), "rival": int(farms[1]["money"])},
        "market_inventory": {
            item: int(market["inventory"][item])
            for item in sorted(inventory_overrides)
        },
        "sheds": [
            {item: int(value) for item, value in sorted(private["shed"].items())}
            for private in privates
        ],
    }


def false_zero_scan(
    *,
    inventory_start: int = 9950,
    inventory_stop: int = 10050,
    max_quantity: int = 8,
    max_rival_sell_units: int = 100,
) -> dict[str, Any]:
    """Count local proxy plateaus exposed inside a raw upward displacement."""
    counts = {item: 0 for item in mechanics.PRODUCTS}
    worst: dict[str, Any] | None = None
    total = 0
    for item in mechanics.PRODUCTS:
        for inventory in range(inventory_start, inventory_stop + 1):
            market = make_market({item: inventory})
            for quantity in range(1, max_quantity + 1):
                order = ["SELL", item, quantity]
                proxy = same_sized_proxy_loss(order, market)
                bounded = delay_loss(order, market, max_rival_sell_units)
                if proxy == 0 and bounded is not None and bounded > 0:
                    total += 1
                    counts[item] += 1
                    record = {
                        "item": item,
                        "inventory": inventory,
                        "quantity": quantity,
                        "loss_at_bound": bounded,
                    }
                    if (
                        worst is None
                        or record["loss_at_bound"] > worst["loss_at_bound"]
                    ):
                        worst = record
    return {
        "inventory_range_inclusive": [inventory_start, inventory_stop],
        "quantity_range_inclusive": [1, max_quantity],
        "rival_sell_bound": max_rival_sell_units,
        "false_zero_cells": total,
        "by_product": counts,
        "worst_cell": worst,
    }


def _money_delta(parent: Mapping[str, Any], candidate: Mapping[str, Any]) -> dict[str, int]:
    parent_money = parent["money"]
    candidate_money = candidate["money"]
    return {
        "own": candidate_money["own"] - parent_money["own"],
        "rival": candidate_money["rival"] - parent_money["rival"],
        "margin": (
            candidate_money["own"]
            - candidate_money["rival"]
            - parent_money["own"]
            + parent_money["rival"]
        ),
    }


def proxy_zero_witness() -> dict[str, Any]:
    market = make_market({"TOMATO": 9999, "MILK": 9999})
    parent_orders = [["SELL", "TOMATO", 1], ["SELL", "MILK", 1]]
    rival_orders = [["SELL", "TOMATO", 2], []]
    candidate_orders = proxy_zero_partition(parent_orders, market)
    bounded_orders = raw_bounded_partition(parent_orders, market, 100)
    parent = run_exact_market(
        parent_orders,
        rival_orders,
        inventory_overrides={"TOMATO": 9999, "MILK": 9999},
    )
    candidate = run_exact_market(
        candidate_orders,
        rival_orders,
        inventory_overrides={"TOMATO": 9999, "MILK": 9999},
    )
    bounded = run_exact_market(
        bounded_orders,
        rival_orders,
        inventory_overrides={"TOMATO": 9999, "MILK": 9999},
    )
    return {
        "inventory": {"MILK": 9999, "TOMATO": 9999},
        "parent_orders": parent_orders,
        "rival_orders": rival_orders,
        "same_sized_proxy_scores": {
            "TOMATO": same_sized_proxy_loss(parent_orders[0], market),
            "MILK": same_sized_proxy_loss(parent_orders[1], market),
        },
        "proxy_candidate_orders": candidate_orders,
        "raw_bounded_orders": bounded_orders,
        "parent": parent,
        "proxy_candidate": candidate,
        "raw_bounded_candidate": bounded,
        "proxy_delta": _money_delta(parent, candidate),
    }


def raw_prefix_witness() -> dict[str, Any]:
    market = make_market({"WHEAT": 10066, "MILK": 9999})
    parent_orders = [
        ["SELL", "WHEAT", 78],
        ["SELL", "WHEAT", 1],
        ["SELL", "MILK", 1],
    ]
    rival_orders = [[], ["SELL", "WHEAT", 100], []]
    candidate_orders = raw_bounded_partition(parent_orders, market, 100)
    parent = run_exact_market(
        parent_orders,
        rival_orders,
        inventory_overrides={"WHEAT": 10066, "MILK": 9999},
    )
    candidate = run_exact_market(
        candidate_orders,
        rival_orders,
        inventory_overrides={"WHEAT": 10066, "MILK": 9999},
    )
    return {
        "inventory": {"MILK": 9999, "WHEAT": 10066},
        "parent_orders": parent_orders,
        "rival_orders": rival_orders,
        "same_sized_proxy_scores": [
            same_sized_proxy_loss(order, market)
            for order in parent_orders
        ],
        "middle_raw_safe_through_100": raw_bounded_demotion_safe(
            parent_orders[1],
            market,
            100,
        ),
        "raw_bounded_candidate_orders": candidate_orders,
        "parent": parent,
        "candidate": candidate,
        "delta": _money_delta(parent, candidate),
        "actual_middle_parent_start_inventory": 10144,
        "actual_middle_candidate_start_inventory": 10244,
        "actual_middle_parent_quote": mechanics.market_price("WHEAT", 10144),
        "actual_middle_candidate_quote": mechanics.market_price("WHEAT", 10244),
    }


def rival_buy_witness() -> dict[str, Any]:
    market = make_market({"EGG": 10139, "WHEAT": 10000})
    parent_orders = [["SELL", "EGG", 1], ["SELL", "WHEAT", 1]]
    rival_orders = [["BUY_PRODUCT", "WHEAT", 1], []]
    candidate_orders = raw_bounded_partition(parent_orders, market, 100)
    parent = run_exact_market(
        parent_orders,
        rival_orders,
        inventory_overrides={"EGG": 10139, "WHEAT": 10000},
        starting_money=(0, 1000),
    )
    candidate = run_exact_market(
        candidate_orders,
        rival_orders,
        inventory_overrides={"EGG": 10139, "WHEAT": 10000},
        starting_money=(0, 1000),
    )
    return {
        "inventory": {"EGG": 10139, "WHEAT": 10000},
        "starting_money": {"own": 0, "rival": 1000},
        "parent_orders": parent_orders,
        "rival_orders": rival_orders,
        "same_sized_proxy_scores": {
            "EGG": same_sized_proxy_loss(parent_orders[0], market),
            "WHEAT": same_sized_proxy_loss(parent_orders[1], market),
        },
        "egg_raw_safe_through_100": raw_bounded_demotion_safe(
            parent_orders[0],
            market,
            100,
        ),
        "raw_bounded_candidate_orders": candidate_orders,
        "quotes": {
            "egg_public": mechanics.market_price("EGG", 10139),
            "egg_plus_100": mechanics.market_price("EGG", 10239),
            "wheat_precommit_sell": mechanics.market_price("WHEAT", 10000),
            "wheat_post_buy": mechanics.market_price("WHEAT", 9999),
            "wheat_after_sell": mechanics.market_price("WHEAT", 10001),
        },
        "parent": parent,
        "candidate": candidate,
        "delta": _money_delta(parent, candidate),
        "egg_bidirectional_flat_0_buy_100_sell": bidirectional_flat_invariant(
            parent_orders[0],
            market,
            max_prior_buys=0,
            max_prior_sales=100,
        ),
        "wheat_bidirectional_flat_1_buy_100_sell": bidirectional_flat_invariant(
            parent_orders[1],
            market,
            max_prior_buys=1,
            max_prior_sales=100,
        ),
    }


def finding() -> dict[str, Any]:
    return {
        "schema": "titan-pressure-dominance-audit/v2",
        "claims_disproved": [
            "same-sized proxy zero certifies safe demotion",
            "raw-public-inventory 0..shedCapacity sale-delay invariance certifies safe demotion",
            "demoted-lot sale-supply invariance alone establishes universal own-cash dominance",
        ],
        "witness_proxy_zero": proxy_zero_witness(),
        "witness_raw_prefix": raw_prefix_witness(),
        "witness_rival_buy": rival_buy_witness(),
        "plateau_scan": false_zero_scan(),
        "production_disposition": {
            "universal_strict_dominance": "HOLD",
            "required_scope": [
                "exact or conservative queue-prefix inventory envelopes",
                "both promoted and demoted lots",
                "opponent BUY and SELL feasibility",
                "quote-all then commit-all row semantics",
                "active-prefix and shed/cash bounds",
                "parent-order fallback on ambiguity",
            ],
        },
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
