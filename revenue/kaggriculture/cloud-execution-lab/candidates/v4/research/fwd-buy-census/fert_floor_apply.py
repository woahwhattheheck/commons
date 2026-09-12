# SPDX-License-Identifier: Apache-2.0
"""Source-pinned full-interpreter witness for Gemini's FERT floor-buy/apply seam.

This is an experiment, not a policy.  It tests the strongest mechanically valid
core of the historical claim:

    BUY_PRODUCT FERTILIZER at the public $1 floor
      -> shed custody
      -> PICKUP into a farmer inventory
      -> FERTILIZE a live crop
      -> realize one extra crop unit under an otherwise idle unit schedule.

The experiment deliberately charges the real market buy and uses the real
interpreter for every custody/action transition.  It also records that the
path consumes two unit callbacks (PICKUP and FERTILIZE) before the common WATER,
so a positive constructed cash delta is not field or activation evidence.

The authenticated engine loader and primitive fixture/tick helpers come from the
existing fwd-buy-census source authority rather than a second engine model.
"""
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
from typing import Any

import opportunity_cost as oc

SCHEMA = "titan.v4.gemini-fert-floor-apply/v1"
ITEM = "FERTILIZER"
CROP = "CARROT"


def unit_action(row, *, market=()):
    if not isinstance(row, list) or not row or type(row[0]) is not str:
        raise ValueError("row must be a non-empty unit-action list")
    return {"farmer": copy.deepcopy(row), "hands": [],
            "market": copy.deepcopy(list(market))}


def floor_buy_threshold(engine: Any) -> int:
    """Lowest *pre-buy* FERT inventory whose one-unit post-buy quote is $1."""
    params = engine.MARKET_PARAMS[ITEM]
    start = int(params["I0"])
    # The current source is monotone linear above I0. Keep a bounded search so a
    # future source drift fails visibly instead of silently importing an algebraic
    # assumption about shape/rounding.
    for inventory in range(start, start + 100000):
        quote = engine.market_price(ITEM, inventory - 1)
        if quote == engine.PRICE_FLOOR:
            return inventory
    raise RuntimeError("FERTILIZER floor not reached in bounded source search")


def _fixture(engine: Any, seat: int, *, fert_inventory: int, cash: int = 3000):
    if type(fert_inventory) is not int or fert_inventory < 0:
        raise ValueError("fert_inventory must be a nonnegative exact int")
    if type(cash) is not int or cash < 0:
        raise ValueError("cash must be a nonnegative exact int")
    state, env = oc.fixture(engine, seat, cash=cash, wheat_inventory=10000, shops=0)
    obs = state[seat].observation
    obs.market["inventory"][ITEM] = fert_inventory
    engine._refresh_prices(obs.market)

    farm = obs.farms[seat]
    x, y = farm["farmer"]
    tile = engine._new_plant(CROP, 0, env.configuration.turnsPerDay)
    tile.update(yield_units=1, consecutive_unwatered=0,
                watered_today=False, fertilized_until_day=-1)
    farm["tiles"][y][x] = tile
    return state, env


def _tile_snapshot(state, seat):
    obs = state[seat].observation
    farm = obs.farms[seat]
    x, y = farm["farmer"]
    return copy.deepcopy(farm["tiles"][y][x])


def _tick(engine, state, env, seat, step, own_action):
    row = oc.tick(engine, state, env, seat, step, own_action)
    obs = state[seat].observation
    row["fert_market_inventory"] = obs.market["inventory"][ITEM]
    row["fert_market_price"] = obs.market["prices"][ITEM]
    row["tile"] = _tile_snapshot(state, seat)
    return row


def run_pair(engine: Any, *, seat: int = 0, fert_inventory: int | None = None,
             cash: int = 3000) -> dict:
    """Run a fixed idle-capacity control against the real floor-buy/apply path.

    The common path WATERs on day 3, HARVESTs, DROPs at the shed and liquidates
    all CARROT, then DIGs the expired annual tile.  The candidate uses otherwise
    idle callbacks 91 and 92 for PICKUP/FERTILIZE after buying one FERT at 90.
    Rival actions are PASS throughout.
    """
    if type(seat) is not int or seat not in (0, 1):
        raise ValueError("seat must be 0 or 1")
    if fert_inventory is None:
        fert_inventory = floor_buy_threshold(engine)
    world = _fixture(engine, seat, fert_inventory=fert_inventory, cash=cash)
    result = {}
    for arm in ("control", "floor_apply"):
        state, env = copy.deepcopy(world)
        trace = []
        for step in range(90, 97):
            market = []
            if arm == "floor_apply" and step == 90:
                market = [["BUY_PRODUCT", ITEM, 1]]
            if step == 91 and arm == "floor_apply":
                row = ["PICKUP", ITEM]
            elif step == 92 and arm == "floor_apply":
                row = ["FERTILIZE"]
            elif step == 93:
                row = ["WATER"]
            elif step == 94:
                row = ["HARVEST"]
            elif step == 95:
                row = ["DROP"]
                market = [["SELL", CROP, 100]]
            elif step == 96:
                row = ["DIG"]
            else:
                row = ["PASS"]
            trace.append(_tick(engine, state, env, seat, step,
                               unit_action(row, market=market)))
        result[arm] = oc.finish(state, seat, trace)

    control = result["control"]
    candidate = result["floor_apply"]
    prebuy_quote = engine.market_price(ITEM, fert_inventory - 1)
    candidate_harvest = candidate["trace"][4]["inventories"][0].get(CROP, 0)
    control_harvest = control["trace"][4]["inventories"][0].get(CROP, 0)
    result["certificate"] = {
        "schema": SCHEMA,
        "seat": seat,
        "fert_inventory_before": fert_inventory,
        "fert_one_unit_postbuy_quote": prebuy_quote,
        "source_price_floor": engine.PRICE_FLOOR,
        "at_price_floor": prebuy_quote == engine.PRICE_FLOOR,
        "candidate_harvest_units": candidate_harvest,
        "control_harvest_units": control_harvest,
        "incremental_harvest_units": candidate_harvest - control_harvest,
        "candidate_cash": candidate["cash"],
        "control_cash": control["cash"],
        "own_cash_delta": candidate["cash"] - control["cash"],
        "rival_cash_delta": candidate["rival_cash"] - control["rival_cash"],
        "same_final_physical": candidate["physical"] == control["physical"],
        "extra_unit_callbacks": ["PICKUP FERTILIZER", "FERTILIZE"],
        "extra_unit_callback_count": 2,
        "market_buy_rows": 1,
        "constructed_idle_capacity_only": True,
        "current_native_engagement_claim": False,
        "policy_claim": False,
        "activation_claim": False,
    }
    return result


def run_panel(engine: Any) -> dict:
    threshold = floor_buy_threshold(engine)
    rows = []
    for seat in (0, 1):
        for inventory in (threshold - 1, threshold, threshold + 100):
            pair = run_pair(engine, seat=seat, fert_inventory=inventory)
            rows.append(pair["certificate"])
    return {
        "schema": SCHEMA,
        "floor_prebuy_inventory_threshold": threshold,
        "cells": rows,
        "limits": [
            "Constructed idle-callback fixture; no natural/current-native reachability claim",
            "Two extra unit callbacks are real opportunity cost and are not assigned zero field value",
            "Rival is PASS; no opponent-robustness claim",
            "Positive cash in this fixture is mechanism evidence only, not promotion authority",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--engine-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        engine, hashes = oc.load_engine(args.engine_dir)
        report = run_panel(engine)
        report["engine_sha256"] = hashes
        report["full_interpreter_callbacks"] = oc.CALLBACKS
        args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    except (OSError, ValueError, RuntimeError) as exc:
        parser.exit(2, str(exc) + "\n")
    print(json.dumps({
        "floor_prebuy_inventory_threshold": report["floor_prebuy_inventory_threshold"],
        "cells": len(report["cells"]),
        "full_interpreter_callbacks": report["full_interpreter_callbacks"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
