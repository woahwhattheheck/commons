#!/usr/bin/env python3
"""Source-bound oracle for Kaggriculture public-market negative-stock semantics.

This is a research mechanism oracle, not a gameplay policy.  It authenticates a
single captured official-engine snapshot and executes those exact bytes.  The
cases intentionally use the engine's own market parser/lockstep/commit and town
consumption functions rather than reimplementing their behavior.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import types
from pathlib import Path
from types import SimpleNamespace
from typing import Any

PINNED_ENGINE_GIT_BLOB = "3c202c7ee921da239356789e266b694635103fc4"
PINNED_ENGINE_SHA256 = "bc8a54879ef02c7ea64b8b333d6a976f0ea65c4949149d01f463f23bccee653e"


def _git_blob_id(data: bytes) -> str:
    header = f"blob {len(data)}\0".encode("ascii")
    return hashlib.sha1(header + data).hexdigest()


def capture_engine(engine_path: str | Path) -> bytes:
    """Read once and authenticate the exact bytes that will be executed."""
    data = Path(engine_path).read_bytes()
    git_blob = _git_blob_id(data)
    sha256 = hashlib.sha256(data).hexdigest()
    if git_blob != PINNED_ENGINE_GIT_BLOB or sha256 != PINNED_ENGINE_SHA256:
        raise RuntimeError(
            "official engine identity drift: "
            f"git_blob={git_blob} sha256={sha256}"
        )
    return data


def _exec_engine_snapshot(data: bytes) -> dict[str, Any]:
    """Execute the already-authenticated bytes without reopening their path.

    The official engine imports one Kaggle helper at module import time.  None of
    the mechanism cases below call that helper, so a tiny import-compatible stub
    keeps this oracle stdlib-only while leaving the market code itself literal.
    Existing modules are restored exactly after the snapshot is compiled/executed.
    """
    root_name = "kaggle_environments"
    utils_name = "kaggle_environments.utils"
    sentinel = object()
    old_root = sys.modules.get(root_name, sentinel)
    old_utils = sys.modules.get(utils_name, sentinel)

    root = types.ModuleType(root_name)
    root.__path__ = []  # mark as package for `from kaggle_environments.utils ...`
    utils = types.ModuleType(utils_name)
    utils.resolve_episode_seed = lambda *args, **kwargs: 0
    root.utils = utils
    sys.modules[root_name] = root
    sys.modules[utils_name] = utils

    namespace: dict[str, Any] = {
        "__name__": "_titan_v4_pinned_kaggriculture",
        "__file__": "<captured-kaggriculture.py>",
        "__package__": None,
    }
    try:
        exec(compile(data, "<captured-kaggriculture.py>", "exec"), namespace)
    finally:
        if old_root is sentinel:
            sys.modules.pop(root_name, None)
        else:
            sys.modules[root_name] = old_root
        if old_utils is sentinel:
            sys.modules.pop(utils_name, None)
        else:
            sys.modules[utils_name] = old_utils
    return namespace


def load_engine(engine_path: str | Path) -> tuple[dict[str, Any], dict[str, str]]:
    data = capture_engine(engine_path)
    identity = {
        "git_blob": _git_blob_id(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }
    return _exec_engine_snapshot(data), identity


def _states_for_market(
    engine: dict[str, Any],
    *,
    item: str,
    inventory: int,
    actions: tuple[list[list[Any]], list[list[Any]]],
    starting_money: float = 1_000_000_000.0,
) -> tuple[list[Any], Any]:
    farms = [
        engine["_new_farm"](10, starting_money),
        engine["_new_farm"](10, starting_money),
    ]
    privates = [engine["_new_private"](), engine["_new_private"]()]
    market = engine["_new_market"]()
    market["inventory"][item] = inventory
    town = {"unlocked_shops": []}

    observations = [
        SimpleNamespace(market=market, farms=farms, private=privates[0], town=town),
        SimpleNamespace(market=market, farms=farms, private=privates[1], town=town),
    ]
    states = [
        SimpleNamespace(observation=observations[0], action={"market": actions[0]}),
        SimpleNamespace(observation=observations[1], action={"market": actions[1]}),
    ]
    env = SimpleNamespace(
        configuration={
            "boardSize": 10,
            "maxMarketOrdersPerTurn": 10,
            "farmHandCostMult": 1,
            "shedCapacity": 100,
        }
    )
    return states, env


def run_buy_case(
    engine: dict[str, Any],
    *,
    item: str,
    starting_inventory: int,
    buyers: tuple[bool, bool],
) -> dict[str, Any]:
    if item not in ("WHEAT", "FERTILIZER"):
        raise ValueError("BUY_PRODUCT is official-engine legal only for WHEAT/FERTILIZER")
    actions = tuple(
        [["BUY_PRODUCT", item, 1]] if enabled else [] for enabled in buyers
    )
    states, env = _states_for_market(
        engine,
        item=item,
        inventory=starting_inventory,
        actions=actions,  # type: ignore[arg-type]
    )
    farms = states[0].observation.farms
    before_money = [farm["money"] for farm in farms]
    engine["_process_market"](states, env)
    market = states[0].observation.market
    return {
        "item": item,
        "starting_inventory": starting_inventory,
        "buyers": list(buyers),
        "ending_inventory": market["inventory"][item],
        "ending_price": market["prices"][item],
        "shed_units": [s.observation.private["shed"][item] for s in states],
        "money_spent": [before_money[i] - farms[i]["money"] for i in range(2)],
    }


def run_town_center_zero_stock(engine: dict[str, Any]) -> dict[str, Any]:
    farms = [engine["_new_farm"](10, 1_000_000.0), engine["_new_farm"](10, 1_000_000.0)]
    privates = [engine["_new_private"](), engine["_new_private"]()]
    market = engine["_new_market"]()
    for item in engine["PRODUCTS"]:
        market["inventory"][item] = 0
    town = {"unlocked_shops": []}
    observations = [
        SimpleNamespace(market=market, farms=farms, private=privates[0], town=town),
        SimpleNamespace(market=market, farms=farms, private=privates[1], town=town),
    ]
    states = [
        SimpleNamespace(observation=observations[0], action={}),
        SimpleNamespace(observation=observations[1], action={}),
    ]
    env = SimpleNamespace(
        configuration={
            "townShopSellInterval": 999,
            "townCenterSellInterval": 1,
        }
    )
    engine["_town_consume"](env, states, 1)
    return {
        "town_center_products": list(engine["TOWN_CENTER_PRODUCTS"]),
        "ending_inventory": {
            item: market["inventory"][item] for item in engine["PRODUCTS"]
        },
    }


def next_buy_quote(engine: dict[str, Any], item: str, current_inventory: int) -> int:
    """Mirror only the official quote call-site: quote at post-buy inventory."""
    return engine["market_price"](item, current_inventory - 1, None)


def procurement_cost_from_zero(engine: dict[str, Any], item: str, units: int) -> int:
    if item not in ("WHEAT", "FERTILIZER"):
        raise ValueError(item)
    if type(units) is not int or units < 0:
        raise ValueError("units must be a nonnegative plain int")
    return sum(next_buy_quote(engine, item, -offset) for offset in range(units))


def build_report(engine_path: str | Path) -> dict[str, Any]:
    engine, identity = load_engine(engine_path)
    buy_cases: dict[str, Any] = {}
    for item in ("WHEAT", "FERTILIZER"):
        buy_cases[item] = {
            "single_buyer_from_zero": run_buy_case(
                engine, item=item, starting_inventory=0, buyers=(True, False)
            ),
            "two_buyers_last_unit": run_buy_case(
                engine, item=item, starting_inventory=1, buyers=(True, True)
            ),
            "two_buyers_from_zero": run_buy_case(
                engine, item=item, starting_inventory=0, buyers=(True, True)
            ),
        }

    inventory_points = [0, -1, -10, -100, -1000]
    cost_sizes = [1, 10, 100, 1000]
    price_curves = {
        item: {
            "next_buy_quote_by_current_inventory": {
                str(inv): next_buy_quote(engine, item, inv) for inv in inventory_points
            },
            "cumulative_cost_from_zero": {
                str(n): procurement_cost_from_zero(engine, item, n) for n in cost_sizes
            },
        }
        for item in ("WHEAT", "FERTILIZER")
    }

    return {
        "schema": "titan.v4.phantom-supply.v1",
        "status": "MECHANISM_ONLY_NOT_POLICY",
        "engine": identity,
        "claims": {
            "buy_product_supply_floor": False,
            "town_consume_supply_floor": False,
            "negative_inventory_is_reachable": True,
            "negative_inventory_blocks_buy_product": False,
        },
        "buy_cases": buy_cases,
        "town_center_zero_stock": run_town_center_zero_stock(engine),
        "price_curves": price_curves,
        "boundaries": {
            "gameplay_ev": "NOT_ASSESSED",
            "current_v4_activation": "NOT_ASSESSED",
            "engine_patch": "OUT_OF_SCOPE",
        },
    }


def _validate_report(report: dict[str, Any]) -> None:
    assert report["engine"]["git_blob"] == PINNED_ENGINE_GIT_BLOB
    assert report["engine"]["sha256"] == PINNED_ENGINE_SHA256
    for item in ("WHEAT", "FERTILIZER"):
        cases = report["buy_cases"][item]
        assert cases["single_buyer_from_zero"]["ending_inventory"] == -1
        assert cases["single_buyer_from_zero"]["shed_units"] == [1, 0]
        assert cases["two_buyers_last_unit"]["ending_inventory"] == -1
        assert cases["two_buyers_last_unit"]["shed_units"] == [1, 1]
        assert cases["two_buyers_from_zero"]["ending_inventory"] == -2
        assert cases["two_buyers_from_zero"]["shed_units"] == [1, 1]
        quotes = list(
            report["price_curves"][item]["next_buy_quote_by_current_inventory"].values()
        )
        assert all(type(q) is int and q > 0 for q in quotes)
        assert quotes == sorted(quotes)
    town = report["town_center_zero_stock"]
    for item in town["town_center_products"]:
        assert town["ending_inventory"][item] == -1
    assert town["ending_inventory"]["FERTILIZER"] == 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--engine", required=True)
    parser.add_argument("--output")
    args = parser.parse_args(argv)
    report = build_report(args.engine)
    _validate_report(report)
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
