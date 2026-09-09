#!/usr/bin/env python3
"""Run a complete official game while probing exact W14 one-step counterfactuals."""

from __future__ import annotations

import argparse
import copy
from collections import Counter
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys
import tempfile
import time
from typing import Any, Mapping, Sequence


PRODUCTIVE = ("CARE", "COLLECT_FERTILIZER", "FEED", "WATER", "FERTILIZE", "HARVEST")
ORDER_PAIRS = {
    frozenset(("FERTILIZE", "WATER")),
    frozenset(("WATER", "HARVEST")),
    frozenset(("HARVEST", "PLANT")),
    frozenset(("FERTILIZE", "HARVEST")),
}


def import_path(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path.resolve(strict=True))
    if spec is None or spec.loader is None:
        raise ValueError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def op(row: Any) -> str:
    return row[0] if isinstance(row, list) and row and isinstance(row[0], str) else "MALFORMED"


def units(action: Mapping[str, Any], count: int) -> list[list[Any]]:
    rows = [action.get("farmer") or ["PASS"], *(action.get("hands") or [])]
    rows.extend([["PASS"]] * max(0, count - len(rows)))
    return [list(row) if isinstance(row, list) else ["MALFORMED"] for row in rows[:count]]


def set_unit(action: Mapping[str, Any], worker: int, row: list[Any]) -> dict[str, Any]:
    out = copy.deepcopy(dict(action))
    if worker == 0:
        out["farmer"] = list(row)
        return out
    hands = out.setdefault("hands", [])
    while len(hands) < worker:
        hands.append(["PASS"])
    hands[worker - 1] = list(row)
    return out


def positions(observation: Mapping[str, Any], player: int) -> list[tuple[int, int]]:
    farm = observation["farms"][player]
    return [tuple(farm["farmer"]), *(tuple(p) for p in farm["hands"])]


def stable(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def state_payload(state: Sequence[Any]) -> list[dict[str, Any]]:
    return [
        {
            "status": row.status,
            "reward": row.reward,
            "observation": row.observation,
        }
        for row in state
    ]


def state_sha256(state: Sequence[Any]) -> str:
    return hashlib.sha256(stable(state_payload(state))).hexdigest()


def own_metrics(state: Sequence[Any], seat: int) -> dict[str, Any]:
    observation = state[seat].observation
    player = int(observation["player"])
    farm = observation["farms"][player]
    private = observation["private"]
    stock: Counter[str] = Counter(private.get("shed", {}))
    for inventory in private.get("inventories", []):
        stock.update(inventory)
    tile_yield: Counter[str] = Counter()
    flags = Counter()
    for row in farm.get("tiles", []):
        for tile in row:
            if not isinstance(tile, dict):
                continue
            if tile.get("kind") == "PLANT":
                item = str(tile.get("crop"))
                tile_yield[item] += int(tile.get("yield_units", 0))
                flags[f"watered:{item}"] += bool(tile.get("watered_today"))
                flags[f"fertilized:{item}"] += int(tile.get("fertilized_until_day", -1)) >= int(observation.get("day", 0))
            elif "animal" in tile:
                animal = str(tile.get("animal"))
                tile_yield[animal] += int(tile.get("yield_units", 0))
                flags[f"fed:{animal}"] += bool(tile.get("fed_today"))
                flags[f"cared:{animal}"] += bool(tile.get("cared_today"))
                flags[f"pending_care:{animal}"] += int(tile.get("pending_care_bonus", 0))
                flags[f"fertilizer_available:{animal}"] += bool(tile.get("fertilizer_available"))
    return {
        "money": farm.get("money"),
        "hires_today": farm.get("hires_today"),
        "hands": len(farm.get("hands", [])),
        "shed": dict(sorted(private.get("shed", {}).items())),
        "seeds": dict(sorted(private.get("seeds", {}).items())),
        "stock": dict(sorted(stock.items())),
        "tile_yield": dict(sorted(tile_yield.items())),
        "flags": dict(sorted(flags.items())),
    }


def numeric_delta(actual: Mapping[str, Any], variant: Mapping[str, Any]) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for key in ("money", "hires_today", "hands"):
        a, b = actual.get(key), variant.get(key)
        if isinstance(a, (int, float)) and not isinstance(a, bool) and isinstance(b, (int, float)) and not isinstance(b, bool):
            if b != a:
                output[key] = b - a
    for section in ("shed", "seeds", "stock", "tile_yield", "flags"):
        left = actual.get(section, {})
        right = variant.get(section, {})
        delta = {
            key: right.get(key, 0) - left.get(key, 0)
            for key in sorted(set(left) | set(right))
            if right.get(key, 0) != left.get(key, 0)
        }
        if delta:
            output[section] = delta
    return output


def run_step(engine, state: Sequence[Any], env: Any, actions: Sequence[Mapping[str, Any]]):
    branch_state = copy.deepcopy(state)
    branch_env = copy.deepcopy(env)
    for seat, action in enumerate(actions):
        branch_state[seat].action = copy.deepcopy(dict(action))
    engine.interpreter(branch_state, branch_env)
    return branch_state, branch_env


def probe_step(
    engine,
    state: Sequence[Any],
    env: Any,
    actions: Sequence[Mapping[str, Any]],
    candidate_seat: int,
    step: int,
) -> list[dict[str, Any]]:
    observation = state[candidate_seat].observation
    player = int(observation["player"])
    count = 1 + len(observation["farms"][player].get("hands", []))
    selected = units(actions[candidate_seat], count)
    worker_positions = positions(observation, player)
    actual_state, _ = run_step(engine, state, env, actions)
    actual_sha = state_sha256(actual_state)
    actual_metrics = own_metrics(actual_state, candidate_seat)
    findings: list[dict[str, Any]] = []

    if step % 24 == 23:
        market = list(actions[candidate_seat].get("market") or [])
        for worker, row in enumerate(selected):
            if op(row) != "PICKUP":
                continue
            pass_action = set_unit(actions[candidate_seat], worker, ["PASS"])
            variant_actions = list(actions)
            variant_actions[candidate_seat] = pass_action
            pass_state, _ = run_step(engine, state, env, variant_actions)
            pass_sha = state_sha256(pass_state)
            finding = {
                "kind": "eod_pickup_roundtrip",
                "step": step,
                "day": step // 24,
                "worker": worker,
                "position": list(worker_positions[worker]),
                "action": row,
                "market": market,
                "pass_state_equivalent": pass_sha == actual_sha,
                "actual_state_sha256": actual_sha,
                "pass_state_sha256": pass_sha,
                "pass_delta": numeric_delta(actual_metrics, own_metrics(pass_state, candidate_seat)),
                "productive_replacements": [],
            }
            for replacement in PRODUCTIVE:
                trial_action = set_unit(actions[candidate_seat], worker, [replacement])
                trial_actions = list(actions)
                trial_actions[candidate_seat] = trial_action
                trial_state, _ = run_step(engine, state, env, trial_actions)
                trial_sha = state_sha256(trial_state)
                if trial_sha == pass_sha:
                    continue
                finding["productive_replacements"].append(
                    {
                        "action": [replacement],
                        "state_sha256": trial_sha,
                        "delta_vs_actual": numeric_delta(
                            actual_metrics, own_metrics(trial_state, candidate_seat)
                        ),
                    }
                )
            findings.append(finding)

    for earlier in range(count):
        for later in range(earlier + 1, count):
            first, second = selected[earlier], selected[later]
            if frozenset((op(first), op(second))) not in ORDER_PAIRS:
                continue
            if worker_positions[earlier] != worker_positions[later]:
                continue
            swapped = set_unit(actions[candidate_seat], earlier, second)
            swapped = set_unit(swapped, later, first)
            variant_actions = list(actions)
            variant_actions[candidate_seat] = swapped
            variant_state, _ = run_step(engine, state, env, variant_actions)
            variant_sha = state_sha256(variant_state)
            if variant_sha == actual_sha:
                continue
            findings.append(
                {
                    "kind": "co_located_order_swap",
                    "step": step,
                    "day": step // 24,
                    "hour": step % 24,
                    "position": list(worker_positions[earlier]),
                    "workers": [earlier, later],
                    "actual_actions": [first, second],
                    "swapped_actions": [second, first],
                    "actual_state_sha256": actual_sha,
                    "variant_state_sha256": variant_sha,
                    "delta_vs_actual": numeric_delta(
                        actual_metrics, own_metrics(variant_state, candidate_seat)
                    ),
                }
            )
    return findings


def play_probe(
    evaluator,
    engine,
    specs: Sequence[str],
    cache: Path,
    loader: Path,
    seed: int,
    candidate_seat: int,
    rng_seed: int,
    action_timeout: float,
    startup_timeout: float,
    game_timeout: float,
) -> dict[str, Any]:
    cfg = evaluator.Struct(
        {
            key: value.get("default") if isinstance(value, dict) else value
            for key, value in engine.specification["configuration"].items()
        }
    )
    cfg.seed = seed
    env = evaluator.Struct(configuration=cfg, done=False, info={})
    state = [
        evaluator.Struct(observation=evaluator.Struct(), action={}, status="ACTIVE", reward=0)
        for _ in range(2)
    ]
    started = time.perf_counter()
    actors = []
    findings: list[dict[str, Any]] = []
    action_trace = hashlib.sha256()
    result: dict[str, Any] = {
        "seed": seed,
        "candidate_seat": candidate_seat,
        "rng_seed": rng_seed,
        "status": "failed",
        "scores": None,
        "failure": None,
        "steps": 0,
    }
    try:
        engine.interpreter(state, env)
        if cfg.get("seed") is not None:
            raise ValueError("Environment seed exposed")
        for seat, spec in enumerate(specs):
            actor = evaluator.Actor(
                spec,
                cache,
                loader,
                rng_seed + (seat != candidate_seat),
                startup_timeout,
            )
            actors.append(actor)
            if actor.ready.get("kind") != "ready":
                result["failure"] = {"seat": seat, "phase": "startup", **actor.ready}
                return result
        for step in range(cfg.episodeSteps):
            actions = []
            for seat, actor in enumerate(actors):
                remaining = game_timeout - (time.perf_counter() - started)
                if remaining <= 0:
                    result["failure"] = {"kind": "game_timeout", "seat": None, "step": step}
                    return result
                state[seat].observation.step = step
                state[seat].observation.remainingOverageTime = 0
                response = actor.act(
                    state[seat].observation,
                    cfg,
                    min(action_timeout, remaining),
                )
                if response.get("kind") != "action":
                    result["failure"] = {"seat": seat, "step": step, "phase": "action", **response}
                    return result
                actions.append(response["action"])
            action_trace.update(stable(actions[candidate_seat]))
            findings.extend(probe_step(engine, state, env, actions, candidate_seat, step))
            for seat, action in enumerate(actions):
                state[seat].action = action
            engine.interpreter(state, env)
            result["steps"] += 1
            if all(row.status == "DONE" for row in state):
                scores = [row.reward for row in state]
                if not all(isinstance(score, (int, float)) and math.isfinite(score) for score in scores):
                    raise ValueError("nonfinite score")
                result.update(status="complete", scores=scores)
                env.done = True
                break
        if result["status"] != "complete" and result["failure"] is None:
            result["failure"] = {"kind": "incomplete", "step": result["steps"]}
    except Exception as exc:
        result["failure"] = {
            "kind": "probe_error",
            "step": result["steps"],
            "error": f"{type(exc).__name__}: {exc}"[:1000],
        }
    finally:
        for actor in actors:
            actor.close()
        result["actors"] = [actor.report() for actor in actors]
        result["wall_seconds"] = time.perf_counter() - started
        result["candidate_action_trace_sha256"] = action_trace.hexdigest()
        result["findings"] = findings
        result["finding_counts"] = dict(sorted(Counter(row["kind"] for row in findings).items()))
        result["state_equivalent_eod_pickups"] = sum(
            row.get("kind") == "eod_pickup_roundtrip" and row.get("pass_state_equivalent")
            for row in findings
        )
        result["productive_eod_pickup_replacements"] = sum(
            len(row.get("productive_replacements", []))
            for row in findings
            if row.get("kind") == "eod_pickup_roundtrip"
        )
    return result


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evaluator", type=Path, required=True)
    parser.add_argument("--loader", type=Path, required=True)
    parser.add_argument("--engine-dir", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--opponent", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=261140014)
    parser.add_argument("--candidate-seat", type=int, choices=(0, 1), default=0)
    parser.add_argument("--rng-seed", type=int, default=20260907)
    parser.add_argument("--action-timeout", type=float, default=1.0)
    parser.add_argument("--startup-timeout", type=float, default=10.0)
    parser.add_argument("--game-timeout", type=float, default=180.0)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--archive-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)

    evaluator = import_path(args.evaluator, "w14_official_evaluator")
    engine, engine_hashes = evaluator.get_engine(args.engine_dir, args.loader)
    specs = [str(args.candidate.resolve()), str(args.opponent.resolve())]
    if args.candidate_seat == 1:
        specs.reverse()
    game = play_probe(
        evaluator,
        engine,
        specs,
        args.engine_dir,
        args.loader,
        args.seed,
        args.candidate_seat,
        args.rng_seed,
        args.action_timeout,
        args.startup_timeout,
        args.game_timeout,
    )
    report = {
        "schema_version": 1,
        "operation": "titan-frontier-W14-realized-rule-composition-20260909-01",
        "source_commit": args.source_commit,
        "archive_sha256": args.archive_sha256,
        "evaluator_sha256": sha256(args.evaluator),
        "loader_sha256": sha256(args.loader),
        "candidate_sha256": sha256(args.candidate),
        "opponent_sha256": sha256(args.opponent),
        "engine_sha256": engine_hashes,
        "game": game,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", dir=args.output.parent, delete=False) as handle:
        json.dump(report, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write("\n")
        temporary = handle.name
    Path(temporary).replace(args.output)
    print(
        json.dumps(
            {
                "status": game["status"],
                "scores": game["scores"],
                "steps": game["steps"],
                "finding_counts": game["finding_counts"],
                "state_equivalent_eod_pickups": game["state_equivalent_eod_pickups"],
                "productive_eod_pickup_replacements": game["productive_eod_pickup_replacements"],
            },
            sort_keys=True,
        )
    )
    return int(game["status"] != "complete")


if __name__ == "__main__":
    raise SystemExit(main())
