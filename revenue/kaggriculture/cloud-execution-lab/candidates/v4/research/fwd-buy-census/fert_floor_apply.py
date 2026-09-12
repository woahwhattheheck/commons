# SPDX-License-Identifier: Apache-2.0
"""Source-pinned full-interpreter witnesses for Gemini's FERT floor-buy/apply seam.

Research only; this module does not mutate runtime policy.

``run_pair`` preserves the original constructed one-WATER CARROT mechanism proof.
``run_amortized_pair`` is stricter: it creates an empty day-4 board state with a
real MELON seed, executes PLANT through the official interpreter at step 96,
then executes every survival, fertilizer-custody, production and harvest callback.
"""
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
from typing import Any

import opportunity_cost as oc

SCHEMA = "titan.v4.gemini-fert-floor-apply/v4"
ITEM = "FERTILIZER"
CROP = "CARROT"
AMORTIZED_CROP = "MELON"


def unit_action(row, *, market=()):
    if not isinstance(row, list) or not row or type(row[0]) is not str:
        raise ValueError("row must be a non-empty unit-action list")
    return {
        "farmer": copy.deepcopy(row),
        "hands": [],
        "market": copy.deepcopy(list(market)),
    }


def floor_buy_threshold(engine: Any) -> int:
    """Lowest pre-buy FERT inventory whose one-unit post-buy quote is $1."""
    params = engine.MARKET_PARAMS[ITEM]
    start = int(params["I0"])
    for inventory in range(start, start + 100000):
        if engine.market_price(ITEM, inventory - 1) == engine.PRICE_FLOOR:
            return inventory
    raise RuntimeError("FERTILIZER floor not reached in bounded source search")


def _fixture(
    engine: Any,
    seat: int,
    *,
    fert_inventory: int,
    cash: int = 3000,
    crop: str = CROP,
    yield_units: int = 1,
    plant_day: int = 0,
    consecutive_unwatered: int = 0,
):
    """Constructed fixture retained for the minimal mechanism-only witness."""
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
    tile.update(
        yield_units=yield_units,
        consecutive_unwatered=consecutive_unwatered,
        watered_today=False,
        fertilized_until_day=-1,
    )
    farm["tiles"][y][x] = tile
    return state, env


def _amortized_fixture(
    engine: Any,
    seat: int,
    *,
    fert_inventory: int,
    cash: int = 3000,
):
    """Reachable pre-PLANT day-4 fixture: empty tile plus one real MELON seed."""
    if type(seat) is not int or seat not in (0, 1):
        raise ValueError("seat must be 0 or 1")
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
    if farm["tiles"][y][x] is not None:
        raise RuntimeError("default day-4 planting tile must be empty")
    obs.private["seeds"][AMORTIZED_CROP] = 1
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
    row["seeds"] = copy.deepcopy(obs.private["seeds"])
    return row


def _trace_at(arm: dict, step: int) -> dict:
    for row in arm["trace"]:
        if row["step"] == step:
            return row
    raise KeyError(step)


def _base_certificate(engine: Any, *, seat: int, fert_inventory: int, control: dict, candidate: dict) -> dict:
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


def run_pair(engine: Any, *, seat: int = 0, fert_inventory: int | None = None, cash: int = 3000) -> dict:
    """Minimal constructed one-WATER CARROT control against real buy/custody/apply."""
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
            trace.append(_tick(engine, state, env, seat, step, unit_action(row, market=market)))
        result[arm] = oc.finish(state, seat, trace)

    control = result["control"]
    candidate = result["floor_apply"]
    candidate_harvest = _trace_at(candidate, 94)["inventories"][0].get(CROP, 0)
    control_harvest = _trace_at(control, 94)["inventories"][0].get(CROP, 0)
    cert = _base_certificate(
        engine,
        seat=seat,
        fert_inventory=fert_inventory,
        control=control,
        candidate=candidate,
    )
    cert.update(
        {
            "witness": "MINIMAL_ONE_WATER_CARROT",
            "crop": CROP,
            "candidate_harvest_units": candidate_harvest,
            "control_harvest_units": control_harvest,
            "incremental_harvest_units": candidate_harvest - control_harvest,
            "fertilizer_active_water_days_used": 1,
            "market_buy_step": 90,
            "source_reachable_prefix_claim": False,
        }
    )
    result["certificate"] = cert
    return result


def run_amortized_pair(
    engine: Any,
    *,
    seat: int = 0,
    fert_inventory: int | None = None,
    cash: int = 3000,
) -> dict:
    """Execute a real day-4 MELON PLANT and amortize one FERT over three WATERs.

    PLANT executes at step 96 from an empty tile and a real MELON seed. Because
    official annual crops start with one held yield unit, the reachable pre-FERT
    crop has yield=1 rather than the impossible yield=0 used by the predecessor.
    Common production WATERs at ages 6/7/8 therefore finish 6 vs 4, a +2 theorem.
    Harvest waits until age 10 (day 14), as required by MELON.first_yield_day.
    """
    if type(seat) is not int or seat not in (0, 1):
        raise ValueError("seat must be 0 or 1")
    if fert_inventory is None:
        fert_inventory = floor_buy_threshold(engine)

    plant_step = 4 * 24
    first_postplant_water_step = plant_step + 1
    prefert_step = 10 * 24 - 1
    market_buy_step = 10 * 24
    survival_water_steps = {first_postplant_water_step, 6 * 24, 8 * 24}
    production_water_steps = {10 * 24 + 3, 11 * 24, 12 * 24}
    harvest_step = 14 * 24
    liquidation_step = harvest_step + 1

    world = _amortized_fixture(engine, seat, fert_inventory=fert_inventory, cash=cash)
    result = {}
    for arm in ("control", "floor_apply"):
        state, env = copy.deepcopy(world)
        trace = []
        for step in range(plant_step, liquidation_step + 1):
            market = []
            if arm == "floor_apply" and step == market_buy_step:
                market = [["BUY_PRODUCT", ITEM, 1]]

            if step == plant_step:
                row = ["PLANT", AMORTIZED_CROP]
            elif arm == "floor_apply" and step == market_buy_step + 1:
                row = ["PICKUP", ITEM]
            elif arm == "floor_apply" and step == market_buy_step + 2:
                row = ["FERTILIZE"]
            elif step in survival_water_steps or step in production_water_steps:
                row = ["WATER"]
            elif step == harvest_step:
                row = ["HARVEST"]
            elif step == liquidation_step:
                row = ["DROP"]
                market = [["SELL", AMORTIZED_CROP, 100]]
            else:
                row = ["PASS"]
            trace.append(_tick(engine, state, env, seat, step, unit_action(row, market=market)))
        result[arm] = oc.finish(state, seat, trace)

    control = result["control"]
    candidate = result["floor_apply"]
    candidate_harvest = _trace_at(candidate, harvest_step)["inventories"][0].get(AMORTIZED_CROP, 0)
    control_harvest = _trace_at(control, harvest_step)["inventories"][0].get(AMORTIZED_CROP, 0)
    prefert_candidate = _trace_at(candidate, prefert_step)["tile"]
    prefert_control = _trace_at(control, prefert_step)["tile"]
    cert = _base_certificate(
        engine,
        seat=seat,
        fert_inventory=fert_inventory,
        control=control,
        candidate=candidate,
    )
    cert.update(
        {
            "witness": "AMORTIZED_REACHABLE_MELON",
            "crop": AMORTIZED_CROP,
            "plant_day": 4,
            "plant_step": plant_step,
            "first_postplant_water_step": first_postplant_water_step,
            "candidate_harvest_units": candidate_harvest,
            "control_harvest_units": control_harvest,
            "incremental_harvest_units": candidate_harvest - control_harvest,
            "fertilizer_active_water_days_used": 3,
            "shared_survival_water_steps": sorted(survival_water_steps),
            "common_water_steps": sorted(production_water_steps),
            "prefert_snapshot_step": prefert_step,
            "prefert_candidate_tile": prefert_candidate,
            "prefert_control_tile": prefert_control,
            "market_buy_step": market_buy_step,
            "harvest_step": harvest_step,
            "liquidation_step": liquidation_step,
            "source_reachable_prefix_claim": True,
            "extra_unit_callbacks_per_incremental_unit": (
                2 / (candidate_harvest - control_harvest)
                if candidate_harvest > control_harvest
                else None
            ),
        }
    )
    result["certificate"] = cert
    return result


def run_panel(engine: Any) -> dict:
    threshold = floor_buy_threshold(engine)
    rows = []
    for seat in (0, 1):
        for inventory in (threshold - 1, threshold, threshold + 100):
            rows.append(run_pair(engine, seat=seat, fert_inventory=inventory)["certificate"])
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
            "Minimal CARROT cells are constructed mechanism witnesses, not source-reachable-prefix claims",
            "Reachable MELON arm executes PLANT, all EOD transitions, custody/application, and harvest through the pinned interpreter",
            "Two extra unit callbacks are real opportunity cost and are not assigned zero field value",
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
    print(
        json.dumps(
            {
                "floor_prebuy_inventory_threshold": report["floor_prebuy_inventory_threshold"],
                "minimal_cells": len(report["minimal_cells"]),
                "amortized_floor_cells": len(report["amortized_floor_cells"]),
                "full_interpreter_callbacks": report["full_interpreter_callbacks"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
