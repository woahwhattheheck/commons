#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Official-engine differential for B7 $1 EOD same-product replacement."""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from pathlib import Path

ENGINE_BLOB = "3c202c7ee921da239356789e266b694635103fc4"
HELPER_BLOB = "9c3591fe28d8b6be7511832b799d693ad89afbaf"
HERE = Path(__file__).resolve().parent
LAB = HERE.parents[4]
ENGINE = LAB / "reference" / "engine" / "kaggriculture.py"
HELPER = HERE / "eod_floor_replacement.py"
CFG = {"turnsPerDay": 24, "shedCapacity": 100, "maxMarketOrdersPerTurn": 10}


class CheckError(RuntimeError):
    pass


def git_blob(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(f"blob {len(data)}\0".encode("ascii") + data).hexdigest()


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise CheckError(f"cannot load {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def assert_sources():
    engine_blob = git_blob(ENGINE)
    helper_blob = git_blob(HELPER)
    if engine_blob != ENGINE_BLOB:
        raise CheckError(f"engine drift: {engine_blob}")
    if helper_blob != HELPER_BLOB:
        raise CheckError(f"helper drift: {helper_blob}")
    return {"engine": engine_blob, "helper": helper_blob}


def floor_stock(engine, item: str) -> int:
    """Find any exact-$1 stock using only the authenticated engine price ABI.

    Some official glut curves (notably EGG/log) reach the hard floor only at
    inventories orders of magnitude beyond ordinary play. A fixed linear scan
    is therefore not a valid checker oracle. Exponentially grow from the
    product's own T scale and require the engine itself to report the floor.
    """
    p = engine.MARKET_PARAMS[item]
    start = int(p["I0"])
    if engine.market_price(item, start, None) == 1:
        return start
    delta = max(1, int(p["T"]))
    for _ in range(64):
        stock = start + delta
        if engine.market_price(item, stock, None) == 1:
            return stock
        delta *= 2
    raise CheckError(f"no exact floor stock found for {item} within 64 doublings")


def base_state(engine, helper, item: str, room: int, overflow: int):
    farm = engine._new_farm(10, 100)
    private = engine._new_private()
    private["shed"][item] = 20
    private["shed"]["WHEAT"] = 80
    private["inventories"] = [{item: room + overflow}]
    market = engine._new_market()
    market["inventory"][item] = floor_stock(engine, item)
    engine._refresh_prices(market)
    obs = {
        "step": 23,
        "player": 0,
        "farms": [copy.deepcopy(farm)],
        "private": copy.deepcopy(private),
        "market": copy.deepcopy(market),
    }
    rows = [] if room == 0 else [["SELL", "WHEAT", room]]
    action = {"farmer": ["PASS"], "hands": [], "market": rows}
    decision = helper.analyze(obs, action, CFG, market_price_fn=engine.market_price)
    if not decision.get("admit"):
        raise CheckError(f"helper rejected {item=} {room=} {overflow=}: {decision}")
    if decision["proposal"] != ["SELL", item, overflow]:
        raise CheckError(f"proposal mismatch: {decision}")
    return farm, private, market, action, decision


def execute_sell_row(engine, farm, private, market, row):
    if not isinstance(row, list) or len(row) != 3 or row[0] != "SELL":
        raise CheckError(f"bad checker row {row}")
    item, requested = row[1], row[2]
    remaining = requested
    while remaining > 0:
        quote = engine.market_price(item, market["inventory"][item], market.get("params"))
        if not engine._commit_unit("SELL", item, quote, farm, private, market, 100):
            break
        remaining -= 1
    engine._refresh_prices(market)
    return requested - remaining


def run_cell(engine, helper, item: str, room: int, overflow: int):
    farm, private, market, action, decision = base_state(engine, helper, item, room, overflow)
    baseline_farm = copy.deepcopy(farm)
    baseline_private = copy.deepcopy(private)
    baseline_market = copy.deepcopy(market)
    candidate_farm = copy.deepcopy(farm)
    candidate_private = copy.deepcopy(private)
    candidate_market = copy.deepcopy(market)

    for row in action["market"]:
        sold0 = execute_sell_row(engine, baseline_farm, baseline_private, baseline_market, row)
        sold1 = execute_sell_row(engine, candidate_farm, candidate_private, candidate_market, row)
        if sold0 != row[2] or sold1 != row[2]:
            raise CheckError("prefix SELL did not execute exactly")

    proposal = decision["proposal"]
    before_public_x = candidate_market["inventory"][item]
    sold_replacement = execute_sell_row(engine, candidate_farm, candidate_private, candidate_market, proposal)
    if sold_replacement != overflow:
        raise CheckError("replacement SELL did not execute exactly")
    if candidate_market["inventory"][item] != before_public_x:
        raise CheckError("floor SELL changed public X inventory")
    if candidate_market != baseline_market:
        raise CheckError("public market post-prefix/post-replacement mismatch")

    engine._drop_inventories_to_shed(baseline_private, 100)
    engine._drop_inventories_to_shed(candidate_private, 100)
    if candidate_private["shed"] != baseline_private["shed"]:
        raise CheckError("final shed mismatch")
    if candidate_private["inventories"] != baseline_private["inventories"]:
        raise CheckError("final inventory mismatch")
    gain = candidate_farm["money"] - baseline_farm["money"]
    if gain != overflow:
        raise CheckError(f"cash gain mismatch: {gain} != {overflow}")
    return gain


def run_rival_floor_stability(engine, helper):
    checked = 0
    for item in sorted(helper.NONBUYABLE_PRODUCTS):
        market = engine._new_market()
        market["inventory"][item] = floor_stock(engine, item)
        engine._refresh_prices(market)
        before = copy.deepcopy(market)
        rival_farm = engine._new_farm(10, 100)
        rival_private = engine._new_private()
        rival_private["shed"][item] = 3
        quote = engine.market_price(item, market["inventory"][item], market.get("params"))
        if quote != 1:
            raise CheckError(f"non-floor rival setup {item}: {quote}")
        if not engine._commit_unit("SELL", item, quote, rival_farm, rival_private, market, 100):
            raise CheckError(f"rival SELL failed {item}")
        engine._refresh_prices(market)
        if market != before:
            raise CheckError(f"rival floor SELL changed public market for {item}")
        checked += 1
    return checked


def run():
    pins = assert_sources()
    engine = load("_b7_floor_engine", ENGINE)
    helper = load("_b7_floor_helper", HELPER)
    expected_nonbuyable = set(engine.PRODUCTS) - {"WHEAT", "FERTILIZER"}
    if set(helper.NONBUYABLE_PRODUCTS) != expected_nonbuyable:
        raise CheckError("non-buyable product domain drift")

    cells = 0
    gain = 0
    by_item = {}
    for item in sorted(helper.NONBUYABLE_PRODUCTS):
        item_cells = 0
        for room in (0, 1, 2, 3):
            for overflow in (1, 2, 3, 4):
                gain += run_cell(engine, helper, item, room, overflow)
                cells += 1
                item_cells += 1
        by_item[item] = item_cells

    rival = run_rival_floor_stability(engine, helper)
    return {
        "status": "PASS",
        "scope": "official-engine B7 floor SELL + EOD same-product replacement; default-OFF/unwired",
        "pins": pins,
        "cells": cells,
        "cash_gain_sum": gain,
        "cells_by_item": by_item,
        "rival_floor_sell_stability_items": rival,
        "nonbuyable_products": sorted(helper.NONBUYABLE_PRODUCTS),
    }


def main() -> int:
    print(json.dumps(run(), sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
