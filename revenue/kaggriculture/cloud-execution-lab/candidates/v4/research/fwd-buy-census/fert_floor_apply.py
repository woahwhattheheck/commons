# SPDX-License-Identifier: Apache-2.0
"""Source-pinned full-interpreter witnesses for Gemini's FERT floor-buy/apply seam.

This is an experiment, not a policy. It tests the strongest mechanically valid
core of the historical claim:

    BUY_PRODUCT FERTILIZER at the public $1 floor
      -> shed custody
      -> PICKUP into a farmer inventory
      -> FERTILIZE a live crop
      -> realize incremental crop yield under otherwise idle unit capacity.

Two constructed witnesses are retained deliberately:

* ``run_pair`` is the minimal one-water CARROT proof (+1 possible unit).
* ``run_amortized_pair`` executes a source-reachable MELON survival prefix from
  day 4 through the day-10 fertilizer window, then holds that crop through all
  three fertilizer-active days. One FERT plus the same two custody/application
  callbacks can therefore boost three common WATER callbacks while every
  intervening EOD transition is executed by the pinned interpreter.

Both deliberately charge the real market buy and use the real interpreter for
every custody/action transition. Positive constructed cash is mechanism evidence,
never field reachability or activation authority.
"""
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
from typing import Any

import opportunity_cost as oc

SCHEMA = "titan.v4.gemini-fert-floor-apply/v3"
ITEM = "FERTILIZER"
CROP = "CARROT"
AMORTIZED_CROP = "MELON"


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


def _fixture(engine: Any, seat: int, *, fert_inventory: int, cash: int = 3000,
             crop: str = CROP, yield_units: int = 1, plant_day: int = 0,
             consecutive_unwatered: int = 0):
    if type(fert_inventory) is not int or fert_inventory < 0:
        raise ValueError("fert_inventory must be a nonnegative exact int")
    if type(cash) is not int or cash < 0:
        raise ValueError("cash must be a nonnegative exact int")
    if crop not in engine.CROPS:
        raise ValueError("unknown crop")
    if type(yield_units) is not int or yield_units < 0:
        raise ValueError("yield_units must be a nonnegative exact int")
    if type(plant_day) is not int or plant_day < 0:
        raise ValueError("plant_day must be a nonnegative exact int")
    if type(consecutive_unwatered) is not int or consecutive_unwatered < 0:
        raise ValueError("consecutive_unwatered must be a nonnegative exact int")
    state, env = oc.fixture(engine, seat, cash=cash, wheat_inventory=10000, shops=0)
    obs = state[seat].observation
    obs.market["inventory"][ITEM] = fert_inventory
    engine._refresh_prices(obs.market)

    farm = obs.farms[seat]
    x, y = farm["farmer"]
    tile = engine._new_plant(crop, plant_day, env.configuration.turnsPerDay)
    tile.update(yield_units=yield_units, consecutive_unwatered=consecutive_unwatered,
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


def _trace_at(arm: dict, step: int) -> dict:
    for row in arm["trace"]:
        if row["step"] == step:
            return row
    raise KeyError(step)


def _base_certificate(engine: Any, *, seat: int, fert_inventory: int,
                      control: dict, candidate: dict) -> dict:
    quote = engine.market_price(ITEM, fert_inventory - 1)
    return {
        "schema": SCHEMA,
        "seat": seat,
        "fert_inventory_before": fert_inventory,
        "fert_one_unit_postbuy_quote": quote,
        "source_price_floor": engine.PRICE_FLOOR,
        "at_price_floor": quote == engine.PRICE_FLOOR,
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


def run_pair(engine: Any, *, seat: int = 0, fert_inventory: int | None = None,
             cash: int = 3000) -> dict:
    """Minimal one-WATER CARROT control against the real floor-buy/apply path."""
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
    candidate_harvest = _trace_at(candidate, 94)["inventories"][0].get(CROP, 0)
    control_harvest = _trace_at(control, 94)["inventories"][0].get(CROP, 0)
    cert = _base_certificate(
        engine, seat=seat, fert_inventory=fert_inventory,
        control=control, candidate=candidate,
    )
    cert.update({
        "witness": "MINIMAL_ONE_WATER_CARROT",
        "crop": CROP,
        "candidate_harvest_units": candidate_harvest,
        "control_harvest_units": control_harvest,
        "incremental_harvest_units": candidate_harvest - control_harvest,
        "fertilizer_active_water_days_used": 1,
        "market_buy_step": 90,
    })
    result["certificate"] = cert
    return result


def run_amortized_pair(engine: Any, *, seat: int = 0,
                       fert_inventory: int | None = None,
                       cash: int = 3000) -> dict:
    """Use one FERT across a reachable three-day MELON WATER window.

    The fixture begins with a newly planted day-4 MELON, then executes the
    shared survival prefix through the official interpreter: WATER on days 4,
    6 and 8 keeps the crop live while all three calls remain before MELON's
    yield window (age < 6), so the pre-FERT yield at the end of day 9 is still
    zero. One FERTILIZE on day 10 is then active through day 12 inclusive.
    Candidate and control share all survival and production WATER callbacks;
    only BUY/PICKUP/FERTILIZE differ.
    """
    if type(seat) is not int or seat not in (0, 1):
        raise ValueError("seat must be 0 or 1")
    if fert_inventory is None:
        fert_inventory = floor_buy_threshold(engine)
    plant_day = 4
    start_step = plant_day * 24
    prefert_step = 10 * 24 - 1
    world = _fixture(
        engine, seat, fert_inventory=fert_inventory, cash=cash,
        crop=AMORTIZED_CROP, yield_units=0, plant_day=plant_day,
        consecutive_unwatered=1,
    )
    result = {}
    survival_water_steps = {4 * 24, 6 * 24, 8 * 24}
    water_steps = {10 * 24 + 3, 11 * 24, 12 * 24}
    harvest_step = 12 * 24 + 1
    liquidation_step = 12 * 24 + 2
    for arm in ("control", "floor_apply"):
        state, env = copy.deepcopy(world)
        trace = []
        for step in range(start_step, liquidation_step + 1):
            market = []
            if arm == "floor_apply" and step == 10 * 24:
                market = [["BUY_PRODUCT", ITEM, 1]]
            if arm == "floor_apply" and step == 10 * 24 + 1:
                row = ["PICKUP", ITEM]
            elif arm == "floor_apply" and step == 10 * 24 + 2:
                row = ["FERTILIZE"]
            elif step in survival_water_steps or step in water_steps:
                row = ["WATER"]
            elif step == harvest_step:
                row = ["HARVEST"]
            elif step == liquidation_step:
                row = ["DROP"]
                market = [["SELL", AMORTIZED_CROP, 100]]
            else:
                row = ["PASS"]
            trace.append(_tick(engine, state, env, seat, step,
                               unit_action(row, market=market)))
        result[arm] = oc.finish(state, seat, trace)

    control = result["control"]
    candidate = result["floor_apply"]
    candidate_harvest = _trace_at(candidate, harvest_step)["inventories"][0].get(
        AMORTIZED_CROP, 0)
    control_harvest = _trace_at(control, harvest_step)["inventories"][0].get(
        AMORTIZED_CROP, 0)
    prefert_candidate = _trace_at(candidate, prefert_step)["tile"]
    prefert_control = _trace_at(control, prefert_step)["tile"]
    cert = _base_certificate(
        engine, seat=seat, fert_inventory=fert_inventory,
        control=control, candidate=candidate,
    )
    cert.update({
        "witness": "AMORTIZED_THREE_DAY_MELON",
        "crop": AMORTIZED_CROP,
        "plant_day": plant_day,
        "candidate_harvest_units": candidate_harvest,
        "control_harvest_units": control_harvest,
        "incremental_harvest_units": candidate_harvest - control_harvest,
        "fertilizer_active_water_days_used": 3,
        "shared_survival_water_steps": sorted(survival_water_steps),
        "common_water_steps": sorted(water_steps),
        "prefert_snapshot_step": prefert_step,
        "prefert_candidate_tile": prefert_candidate,
        "prefert_control_tile": prefert_control,
        "market_buy_step": 10 * 24,
        "extra_unit_callbacks_per_incremental_unit": (
            2 / (candidate_harvest - control_harvest)
            if candidate_harvest > control_harvest else None
        ),
    })
    result["certificate"] = cert
    return result


def run_panel(engine: Any) -> dict:
    threshold = floor_buy_threshold(engine)
    rows = []
    for seat in (0, 1):
        for inventory in (threshold - 1, threshold, threshold + 100):
            pair = run_pair(engine, seat=seat, fert_inventory=inventory)
            rows.append(pair["certificate"])
    amortized = [
        run_amortized_pair(engine, seat=seat, fert_inventory=threshold)["certificate"]
        for seat in (0, 1)
    ]
    return {
        "schema": SCHEMA,
        "floor_prebuy_inventory_threshold": threshold,
        "minimal_cells": rows,
        "amortized_floor_cells": amortized,
        "limits": [
            "Constructed idle-callback fixtures; no natural/current-native reachability claim",
            "Two extra unit callbacks are real opportunity cost and are not assigned zero field value",
            "The amortized witness executes its shared survival prefix and reuses the same PICKUP/FERTILIZE cost across three common WATER days",
            "Rival is PASS; no opponent-robustness claim",
            "Positive cash in these fixtures is mechanism evidence only, not promotion authority",
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
        "minimal_cells": len(report["minimal_cells"]),
        "amortized_floor_cells": len(report["amortized_floor_cells"]),
        "full_interpreter_callbacks": report["full_interpreter_callbacks"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
