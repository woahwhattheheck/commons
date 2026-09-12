#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Current-native FLOORDRAIN reachability census on the official interpreter.

Research/execution evidence only.  This does not wire or activate the existing
floor_capacity_relief helper.  It executes the authenticated current-native
agent against itself and observes BOTH seats after the authored UNIT phase but
before MARKET on EOD callbacks.  At that exact boundary it projects the
engine's deterministic EOD shed drop and asks the already-merged helper whether
any floor-price capacity relief would be legal while WHEAT/FERTILIZER are fully
protected.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

EXPECTED_HELPER_BLOB = "f162562d445b6f6a864ba43c884b7e96dcfbbd41"
EXPECTED_ENGINE_BLOB = "3c202c7ee921da239356789e266b694635103fc4"
EXPECTED_NATIVE_MAIN_SHA256 = "c4c22d0f2b1071cadf6a9f74effccc8cb20ea9f4d10ca1cf9f1fe57351709dc1"
DEFAULT_SEEDS = (17, 101, 6607, 2026091201, 2026091207, 2026091213, 2026091219, 9922999)
HERE = Path(__file__).resolve().parent
HELPER_PATH = HERE / "floor_capacity_relief.py"


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _git_blob(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _telemetry() -> dict:
    return {
        "overflow_callbacks": 0,
        "baseline_discard_units": 0,
        "baseline_discard_by_item": {},
        "floor_seen_callbacks": 0,
        "floor_seen_by_item": {},
        "eligible_callbacks": 0,
        "eligible_units": 0,
        "eligible_by_item": {},
        "preserved_units": 0,
        "events": [],
    }


def _add_count(table: dict, key: str, amount: int = 1) -> None:
    table[key] = table.get(key, 0) + amount


def _census_boundary(engine, helper, state, env, seat: int, out: dict) -> None:
    cfg = env.configuration
    step = int(state[0].observation.get("step", 0))
    turns = max(1, int(engine.get(cfg, "turnsPerDay", 24)))
    if (step + 1) % turns != 0:
        return

    max_orders = max(1, int(engine.get(cfg, "maxMarketOrdersPerTurn", 10)))
    capacity = int(engine.get(cfg, "shedCapacity", 100))
    player = state[seat]
    action = player.action if isinstance(player.action, dict) else {}
    rows = action.get("market", [])
    if not isinstance(rows, list):
        rows = []
    remaining = max(0, max_orders - len(rows))
    private = player.observation.private
    shed = dict(private.get("shed", {}))
    inventories = [dict(inv) for inv in private.get("inventories", [])]

    projection = helper.project_eod_drop(shed, inventories, capacity)
    if projection.discarded_units <= 0:
        return
    out["overflow_callbacks"] += 1
    out["baseline_discard_units"] += projection.discarded_units
    for item in projection.discarded_sequence:
        _add_count(out["baseline_discard_by_item"], item)

    market = state[0].observation.market
    prices = dict(market.get("prices", {}))
    floor_items = [item for item, n in shed.items() if n > 0 and prices.get(item) == helper.PRICE_FLOOR]
    if floor_items:
        out["floor_seen_callbacks"] += 1
        for item in floor_items:
            _add_count(out["floor_seen_by_item"], item)

    protected = {
        "WHEAT": int(shed.get("WHEAT", 0)),
        "FERTILIZER": int(shed.get("FERTILIZER", 0)),
    }
    shadows = {item: float(engine.MARKET_PARAMS[item]["base"]) for item in engine.PRODUCTS}
    incoming = {item: float(prices.get(item, 0)) for item in engine.PRODUCTS}
    plan = helper.plan_floor_capacity_relief(
        shed=shed,
        inventories=inventories,
        capacity=capacity,
        floor_quotes=prices,
        shed_shadow_values=shadows,
        incoming_retention_values=incoming,
        protected_min=protected,
        available_market_rows=remaining,
    )
    if plan.orders:
        out["eligible_callbacks"] += 1
        out["eligible_units"] += sum(plan.drained_units.values())
        out["preserved_units"] += len(plan.preserved_sequence)
        for item, n in plan.drained_units.items():
            _add_count(out["eligible_by_item"], item, n)

    out["events"].append({
        "step": step,
        "rows_used": len(rows),
        "rows_remaining": remaining,
        "shed_total": sum(shed.values()),
        "actor_inventory_total": sum(sum(inv.values()) for inv in inventories),
        "discarded": list(projection.discarded_sequence),
        "floor_items": floor_items,
        "plan_reason": plan.reason,
        "plan_orders": [list(order) for order in plan.orders],
        "declared_value_gain": plan.declared_value_gain,
        "protected_wheat": protected["WHEAT"],
        "protected_fertilizer": protected["FERTILIZER"],
    })


def _manual_step(engine, helper, state, env, telemetry: list[dict]) -> None:
    obs0 = state[0].observation
    cfg = env.configuration
    turns = max(1, int(engine.get(cfg, "turnsPerDay", 24)))
    board = int(engine.get(cfg, "boardSize", 10))
    capacity = int(engine.get(cfg, "shedCapacity", 100))
    step = int(engine.get(obs0, "step", 0))
    day = step // turns

    for i, player in enumerate(state):
        action = player.action if isinstance(player.action, dict) else {}
        farmer = action.get("farmer", ["PASS"])
        hands = action.get("hands", [])
        if not isinstance(hands, list):
            hands = []
        unit_actions = [farmer, *hands]
        demand: dict[str, int] = {}
        for command in unit_actions:
            if isinstance(command, list) and len(command) >= 2 and command[0] == "PLANT":
                demand[command[1]] = demand.get(command[1], 0) + 1
        seeds = player.observation.private.get("seeds", {})
        blocked = {crop for crop, n in demand.items() if n > seeds.get(crop, 0)}

        def allowed(command):
            if isinstance(command, list) and len(command) >= 2 and command[0] == "PLANT" and command[1] in blocked:
                return ["PASS"]
            return command

        engine._apply_unit_action(obs0.farms[i], player.observation.private, 0, allowed(farmer), board, day, turns, capacity)
        for hand_index, command in enumerate(hands):
            engine._apply_unit_action(obs0.farms[i], player.observation.private, hand_index + 1, allowed(command), board, day, turns, capacity)

    _census_boundary(engine, helper, state, env, 0, telemetry[0])
    _census_boundary(engine, helper, state, env, 1, telemetry[1])

    engine._process_market(state, env)
    engine._town_consume(env, state, step)
    for farm in obs0.farms:
        engine._decay_plants(farm, step)
    if (step + 1) % turns == 0:
        engine._end_of_day(state, env, day)

    next_step = step + 1
    obs0.day = next_step // turns
    obs0.hour = next_step % turns
    for i in range(1, len(state)):
        state[i].observation.farms = obs0.farms
        state[i].observation.market = obs0.market
        state[i].observation.town = obs0.town
        state[i].observation.day = obs0.day
        state[i].observation.hour = obs0.hour
    if step >= cfg.episodeSteps - 2:
        for player in state:
            player.status = "DONE"
            player.reward = float(obs0.farms[player.observation.player]["money"])


def _census_game(engine, helper, evaluator, engine_dir: Path, loader: Path, native: Path, seed: int, rng_seed: int) -> dict:
    cfg = evaluator.Struct({
        key: value.get("default") if isinstance(value, dict) else value
        for key, value in engine.specification["configuration"].items()
    })
    cfg.seed = seed
    env = evaluator.Struct(configuration=cfg, done=False, info={})
    state = [evaluator.Struct(observation=evaluator.Struct(), action={}, status="ACTIVE", reward=0) for _ in range(2)]
    engine.interpreter(state, env)
    if cfg.get("seed") is not None:
        raise ValueError("Environment seed must be hidden from agents")

    actors = []
    trace = hashlib.sha256()
    telemetry = [_telemetry(), _telemetry()]
    try:
        for seat in (0, 1):
            actor = evaluator.Actor(str(native), engine_dir, loader, rng_seed + seat, 10.0)
            actors.append(actor)
            if actor.ready.get("kind") != "ready":
                return {"status": "failed", "failure": {"seat": seat, "phase": "startup", **actor.ready}}
        for step in range(cfg.episodeSteps):
            actions = []
            for seat, actor in enumerate(actors):
                state[seat].observation.step = step
                state[seat].observation.remainingOverageTime = 0
                response = actor.act(state[seat].observation, cfg, 2.0)
                if response.get("kind") != "action":
                    return {"status": "failed", "failure": {"seat": seat, "step": step, **response}}
                actions.append(response["action"])
            for seat in (0, 1):
                state[seat].action = actions[seat]
            _manual_step(engine, helper, state, env, telemetry)
            bank = [float(state[0].observation.farms[i]["money"]) for i in (0, 1)]
            trace.update(evaluator.encoded({"step": step, "actions": actions, "bank": bank}))
            if all(player.status == "DONE" for player in state):
                scores = [player.reward for player in state]
                trace.update(evaluator.encoded([player.observation for player in state]))
                return {
                    "status": "complete",
                    "seed": seed,
                    "scores": scores,
                    "steps": step + 1,
                    "trace_sha256": trace.hexdigest(),
                    "seat_telemetry": telemetry,
                }
        return {"status": "failed", "failure": {"kind": "incomplete"}}
    finally:
        for actor in actors:
            actor.close()


def _summarize(games: list[dict]) -> dict:
    summary = {
        "seed_games": len(games),
        "complete_seed_games": sum(game.get("status") == "complete" for game in games),
        "seat_cells": 0,
        "overflow_seat_cells": 0,
        "overflow_callbacks": 0,
        "baseline_discard_units": 0,
        "baseline_discard_by_item": {},
        "floor_seen_callbacks": 0,
        "eligible_callbacks": 0,
        "eligible_units": 0,
    }
    for game in games:
        for telemetry in game.get("seat_telemetry", []):
            summary["seat_cells"] += 1
            summary["overflow_seat_cells"] += int(telemetry["overflow_callbacks"] > 0)
            for key in ("overflow_callbacks", "baseline_discard_units", "floor_seen_callbacks", "eligible_callbacks", "eligible_units"):
                summary[key] += telemetry[key]
            for item, n in telemetry["baseline_discard_by_item"].items():
                _add_count(summary["baseline_discard_by_item"], item, n)
    return summary


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime", type=Path, required=True, help="extracted authenticated titan-current runtime root")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seeds", default=",".join(map(str, DEFAULT_SEEDS)))
    parser.add_argument("--rng-seed", type=int, default=20260907)
    parser.add_argument("--skip-control", action="store_true", help="skip official-vs-manual trace identity control")
    parser.add_argument("--runtime-artifact-id", type=int, default=10180428228)
    parser.add_argument("--runtime-tar-sha256", default="b567942e4fb4e0571ebf9f8eaaf143d4a9156df3289f09a98db37823ef4d68d9")
    args = parser.parse_args(argv)

    runtime = args.runtime.resolve()
    evaluator_path = runtime / "checks/reference/evaluator/evaluate.py"
    loader_path = runtime / "checks/reference/evaluator/loader.py"
    engine_dir = runtime / "checks/reference/engine"
    native = runtime / "main.py"
    helper = _load(HELPER_PATH, "floordrain_current_native_helper")
    evaluator = _load(evaluator_path, "floordrain_current_native_evaluator")

    if _git_blob(HELPER_PATH) != EXPECTED_HELPER_BLOB:
        raise SystemExit(f"FLOORDRAIN helper drift: {_git_blob(HELPER_PATH)}")
    if helper.ENGINE_BLOB_SHA != EXPECTED_ENGINE_BLOB or not helper.verify_engine_blob(engine_dir / "kaggriculture.py"):
        raise SystemExit("official engine pin mismatch")
    if _sha256(native) != EXPECTED_NATIVE_MAIN_SHA256:
        raise SystemExit(f"native main drift: {_sha256(native)}")
    engine, engine_hashes = evaluator.get_engine(engine_dir, loader_path)

    seeds = [int(token) for token in args.seeds.split(",") if token.strip()]
    if not seeds:
        raise SystemExit("at least one seed required")

    control = None
    if not args.skip_control:
        regular = evaluator.play(engine, [str(native), str(native)], engine_dir, loader_path, seeds[0], 0, args.rng_seed, action_timeout=2.0)
        manual = _census_game(engine, helper, evaluator, engine_dir, loader_path, native, seeds[0], args.rng_seed)
        control = {
            "seed": seeds[0],
            "regular_status": regular.get("status"),
            "manual_status": manual.get("status"),
            "regular_scores": regular.get("scores"),
            "manual_scores": manual.get("scores"),
            "regular_trace_sha256": regular.get("trace_sha256"),
            "manual_trace_sha256": manual.get("trace_sha256"),
        }
        control["trace_identity"] = (
            control["regular_status"] == control["manual_status"] == "complete"
            and control["regular_scores"] == control["manual_scores"]
            and control["regular_trace_sha256"] == control["manual_trace_sha256"]
        )
        if not control["trace_identity"]:
            raise SystemExit("manual observer path is not trace-identical to official interpreter")
        games = [manual]
        remaining = seeds[1:]
    else:
        games, remaining = [], seeds

    for seed in remaining:
        game = _census_game(engine, helper, evaluator, engine_dir, loader_path, native, seed, args.rng_seed)
        games.append(game)
        compact = {"seed": seed, "status": game.get("status"), "scores": game.get("scores")}
        if game.get("status") == "complete":
            compact["seats"] = [
                {key: telemetry[key] for key in ("overflow_callbacks", "baseline_discard_units", "floor_seen_callbacks", "eligible_callbacks", "eligible_units")}
                for telemetry in game["seat_telemetry"]
            ]
        print(json.dumps(compact, sort_keys=True), flush=True)

    summary = _summarize(games)
    disposition = "COLD_CURRENT_NATIVE_TESTED_PANEL" if summary["eligible_callbacks"] == 0 else "ENGAGED_RESEARCH_ONLY"
    result = {
        "schema": "titan.v4.floordrain.current-native-census.v1",
        "disposition": disposition,
        "method": (
            "Authenticated current-native agent vs itself. BOTH seats observed after authored UNIT and before MARKET on EOD callbacks. "
            "No action mutation. Existing FLOORDRAIN helper evaluated with WHEAT/FERTILIZER fully protected, shed shadow=official base price, "
            "incoming retention=current public quote. Admission requires projected overflow and an unprotected shed product quoted exactly $1."
        ),
        "identities": {
            "runtime_artifact_id": args.runtime_artifact_id,
            "runtime_tar_sha256": args.runtime_tar_sha256,
            "native_main_sha256": _sha256(native),
            "official_engine_git_blob": EXPECTED_ENGINE_BLOB,
            "official_engine_sha256": engine_hashes["kaggriculture.py"],
            "evaluator_sha256": _sha256(evaluator_path),
            "loader_sha256": _sha256(loader_path),
            "floordrain_helper_git_blob": EXPECTED_HELPER_BLOB,
            "floordrain_helper_sha256": _sha256(HELPER_PATH),
        },
        "official_interpreter_control": control,
        "seeds": seeds,
        "summary": summary,
        "limits": [
            "Current-native opponent is the exact same authenticated runtime agent, not an external strong gauntlet.",
            "Zero admissions means COLD only for this tested runtime/panel; it does not falsify the synthetic floor-relief mechanism or future stacks.",
            "No ON economics are claimed when admission count is zero because a correctly guarded ON arm would be exact OFF identity.",
        ],
        "games": games,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    print("SUMMARY " + json.dumps(summary, sort_keys=True), flush=True)
    return int(summary["complete_seed_games"] != len(seeds))


if __name__ == "__main__":
    raise SystemExit(main())
