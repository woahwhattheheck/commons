#!/usr/bin/env python3
"""Matched official-engine panel for W14 last-tick crop-harvest composition."""

from __future__ import annotations

import argparse
import copy
from collections import Counter
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import statistics
import sys
import tempfile
import time
from typing import Any, Mapping, Sequence


OPERATION = "titan-frontier-W14-realized-rule-composition-20260909-01"


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


def encoded(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode()


def digest(value: Any) -> str:
    return hashlib.sha256(encoded(value)).hexdigest()


def validate_variant_telemetry(value: Any, cleaned_action: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError("variant action omitted mapping _w14 telemetry")
    if value.get("schema_version") != 1:
        raise ValueError("variant telemetry schema mismatch")
    applied = value.get("applied")
    if not isinstance(applied, bool):
        raise ValueError("variant telemetry applied must be boolean")
    reason = value.get("reason")
    if not isinstance(reason, str) or not reason:
        raise ValueError("variant telemetry reason missing")
    activations = value.get("activations")
    if not isinstance(activations, list):
        raise ValueError("variant telemetry activations must be a list")
    if applied != bool(activations):
        raise ValueError("variant telemetry activation flag mismatch")
    if value.get("output_action_sha256") != digest(cleaned_action):
        raise ValueError("variant telemetry output hash mismatch")
    for index, row in enumerate(activations):
        if not isinstance(row, Mapping):
            raise ValueError(f"activation {index} is not a mapping")
        worker = row.get("worker")
        visible_yield = row.get("visible_yield")
        if (
            isinstance(worker, bool)
            or not isinstance(worker, int)
            or worker < 0
            or isinstance(visible_yield, bool)
            or not isinstance(visible_yield, int)
            or visible_yield <= 0
            or row.get("replacement_action") != ["HARVEST"]
            or not isinstance(row.get("crop"), str)
        ):
            raise ValueError(f"activation {index} malformed")
    return copy.deepcopy(dict(value))


def play(
    evaluator,
    engine,
    specs: Sequence[str],
    cache: Path,
    loader: Path,
    seed: int,
    candidate_seat: int,
    rng_seed: int,
    *,
    expect_telemetry: bool,
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
        evaluator.Struct(
            observation=evaluator.Struct(),
            action={},
            status="ACTIVE",
            reward=0,
        )
        for _ in range(2)
    ]
    actors = []
    trace = hashlib.sha256()
    telemetry_trace = hashlib.sha256()
    activations: list[dict[str, Any]] = []
    reason_counts: Counter[str] = Counter()
    started = time.perf_counter()
    initial_cpu = time.process_time()
    result: dict[str, Any] = {
        "seed": seed,
        "candidate_seat": candidate_seat,
        "status": "failed",
        "scores": None,
        "failure": None,
        "steps": 0,
        "daily_bank": [],
        "telemetry_mode": expect_telemetry,
    }
    try:
        engine.interpreter(state, env)
        if cfg.get("seed") is not None:
            raise ValueError("environment seed exposed to agent")
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
                result["failure"] = {
                    "seat": seat,
                    "step": 0,
                    "phase": "startup",
                    **actor.ready,
                }
                return result

        for step in range(cfg.episodeSteps):
            actions: list[dict[str, Any]] = []
            for seat, actor in enumerate(actors):
                remaining = game_timeout - (time.perf_counter() - started)
                if remaining <= 0:
                    result["failure"] = {
                        "kind": "game_timeout",
                        "seat": None,
                        "step": step,
                    }
                    return result
                state[seat].observation.step = step
                state[seat].observation.remainingOverageTime = 0
                response = actor.act(
                    state[seat].observation,
                    cfg,
                    min(action_timeout, remaining),
                )
                if response.get("kind") != "action":
                    result["failure"] = {
                        "seat": seat,
                        "step": step,
                        "phase": "action",
                        **response,
                    }
                    return result
                raw = response["action"]
                if not isinstance(raw, dict):
                    raise TypeError("agent action is not a mapping")
                cleaned = copy.deepcopy(raw)
                telemetry = cleaned.pop("_w14", None)
                if seat == candidate_seat and expect_telemetry:
                    receipt = validate_variant_telemetry(telemetry, cleaned)
                    reason_counts[receipt["reason"]] += 1
                    telemetry_trace.update(encoded({"step": step, "receipt": receipt}))
                    for activation in receipt["activations"]:
                        activations.append(
                            {
                                "step": step,
                                "day": step // int(cfg.turnsPerDay),
                                "hour": step % int(cfg.turnsPerDay),
                                **copy.deepcopy(dict(activation)),
                            }
                        )
                elif telemetry is not None:
                    raise ValueError("unexpected _w14 telemetry on baseline or opponent action")
                actions.append(cleaned)

            for seat, action in enumerate(actions):
                state[seat].action = action
            engine.interpreter(state, env)
            result["steps"] += 1
            bank = [
                float(state[0].observation.farms[index]["money"])
                for index in range(2)
            ]
            trace.update(encoded({"step": step, "actions": actions, "bank": bank}))
            done = all(row.status == "DONE" for row in state)
            if (step + 1) % int(cfg.turnsPerDay) == 0 or done:
                result["daily_bank"].append({"step": step, "bank": bank})
            if done:
                scores = [row.reward for row in state]
                if not all(
                    isinstance(score, (int, float))
                    and not isinstance(score, bool)
                    and math.isfinite(score)
                    for score in scores
                ):
                    raise ValueError("nonfinite or missing terminal score")
                result.update(status="complete", scores=scores)
                env.done = True
                return result
        result["failure"] = {
            "kind": "incomplete",
            "seat": None,
            "step": result["steps"],
        }
    except Exception as exc:
        result["failure"] = {
            "kind": "runner_error",
            "seat": None,
            "step": result["steps"],
            "error": f"{type(exc).__name__}: {exc}"[:1000],
        }
    finally:
        for actor in actors:
            actor.close()
        result["actors"] = [actor.report() for actor in actors]
        result["wall_seconds"] = time.perf_counter() - started
        result["driver_cpu_seconds"] = time.process_time() - initial_cpu
        trace.update(encoded([row.observation for row in state]))
        result["trace_sha256"] = trace.hexdigest()
        result["telemetry_trace_sha256"] = (
            telemetry_trace.hexdigest() if expect_telemetry else None
        )
        result["activation_count"] = len(activations)
        result["visible_yield_harvested"] = sum(
            row["visible_yield"] for row in activations
        )
        result["activation_crops"] = dict(
            sorted(Counter(row["crop"] for row in activations).items())
        )
        result["activation_days"] = dict(
            sorted(Counter(str(row["day"]) for row in activations).items())
        )
        result["telemetry_reason_counts"] = dict(sorted(reason_counts.items()))
        result["activations"] = activations
    return result


def outcome(margin: float) -> str:
    if margin > 0:
        return "win"
    if margin < 0:
        return "loss"
    return "tie"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evaluator", type=Path, required=True)
    parser.add_argument("--loader", type=Path, required=True)
    parser.add_argument("--engine-dir", type=Path, required=True)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--variant", type=Path, required=True)
    parser.add_argument("--opponent", type=Path, required=True)
    parser.add_argument("--environment-seeds", type=int, nargs="+", required=True)
    parser.add_argument("--candidate-seats", type=int, nargs="+", default=(0, 1))
    parser.add_argument("--rng-seed", type=int, default=20260907)
    parser.add_argument("--action-timeout", type=float, default=1.0)
    parser.add_argument("--startup-timeout", type=float, default=10.0)
    parser.add_argument("--game-timeout", type=float, default=180.0)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--archive-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)

    if len(set(args.environment_seeds)) != len(args.environment_seeds):
        raise ValueError("environment seeds must be unique")
    if len(set(args.candidate_seats)) != len(args.candidate_seats):
        raise ValueError("candidate seats must be unique")
    if any(
        isinstance(value, bool) or not isinstance(value, int) or value not in (0, 1)
        for value in args.candidate_seats
    ):
        raise ValueError("candidate seats must be exactly 0 or 1")

    evaluator = import_path(args.evaluator, "w14_matched_evaluator")
    engine, engine_hashes = evaluator.get_engine(args.engine_dir, args.loader)
    expected = {
        (seed, seat)
        for seed in args.environment_seeds
        for seat in args.candidate_seats
    }
    pairs: list[dict[str, Any]] = []
    seen: set[tuple[int, int]] = set()
    for seed in args.environment_seeds:
        for seat in args.candidate_seats:
            key = (seed, seat)
            if key in seen:
                raise AssertionError(f"duplicate scheduled cell {key}")
            seen.add(key)
            baseline_specs = [str(args.baseline.resolve()), str(args.opponent.resolve())]
            variant_specs = [str(args.variant.resolve()), str(args.opponent.resolve())]
            if seat == 1:
                baseline_specs.reverse()
                variant_specs.reverse()
            baseline = play(
                evaluator,
                engine,
                baseline_specs,
                args.engine_dir,
                args.loader,
                seed,
                seat,
                args.rng_seed,
                expect_telemetry=False,
                action_timeout=args.action_timeout,
                startup_timeout=args.startup_timeout,
                game_timeout=args.game_timeout,
            )
            variant = play(
                evaluator,
                engine,
                variant_specs,
                args.engine_dir,
                args.loader,
                seed,
                seat,
                args.rng_seed,
                expect_telemetry=True,
                action_timeout=args.action_timeout,
                startup_timeout=args.startup_timeout,
                game_timeout=args.game_timeout,
            )
            if baseline["status"] != "complete" or variant["status"] != "complete":
                raise AssertionError(
                    f"incomplete pair {key}: baseline={baseline['failure']} variant={variant['failure']}"
                )
            if baseline["steps"] != 719 or variant["steps"] != 719:
                raise AssertionError(f"unexpected complete step count for {key}")
            baseline_candidate = float(baseline["scores"][seat])
            baseline_opponent = float(baseline["scores"][1 - seat])
            variant_candidate = float(variant["scores"][seat])
            variant_opponent = float(variant["scores"][1 - seat])
            baseline_margin = baseline_candidate - baseline_opponent
            variant_margin = variant_candidate - variant_opponent
            pairs.append(
                {
                    "cell_key": {"environment_seed": seed, "candidate_seat": seat},
                    "baseline": baseline,
                    "variant": variant,
                    "baseline_candidate_score": baseline_candidate,
                    "variant_candidate_score": variant_candidate,
                    "baseline_opponent_score": baseline_opponent,
                    "variant_opponent_score": variant_opponent,
                    "baseline_margin": baseline_margin,
                    "variant_margin": variant_margin,
                    "candidate_score_delta": variant_candidate - baseline_candidate,
                    "opponent_score_delta": variant_opponent - baseline_opponent,
                    "relative_margin_delta": variant_margin - baseline_margin,
                    "baseline_outcome": outcome(baseline_margin),
                    "variant_outcome": outcome(variant_margin),
                    "loss_converted": baseline_margin < 0 and variant_margin > 0,
                    "win_lost": baseline_margin > 0 and variant_margin < 0,
                }
            )

    if seen != expected:
        raise AssertionError(
            f"schedule mismatch missing={sorted(expected - seen)} unexpected={sorted(seen - expected)}"
        )
    baseline_margins = [row["baseline_margin"] for row in pairs]
    variant_margins = [row["variant_margin"] for row in pairs]
    margin_deltas = [row["relative_margin_delta"] for row in pairs]
    candidate_deltas = [row["candidate_score_delta"] for row in pairs]
    report = {
        "schema_version": 1,
        "operation": OPERATION,
        "source_commit": args.source_commit,
        "archive_sha256": args.archive_sha256,
        "engine_sha256": engine_hashes,
        "evaluator_sha256": sha256(args.evaluator),
        "loader_sha256": sha256(args.loader),
        "baseline_sha256": sha256(args.baseline),
        "variant_sha256": sha256(args.variant),
        "opponent_sha256": sha256(args.opponent),
        "environment_seeds": args.environment_seeds,
        "candidate_seats": args.candidate_seats,
        "agent_rng_seed": args.rng_seed,
        "aggregate": {
            "complete_pairs": len(pairs),
            "baseline_wins": sum(row["baseline_outcome"] == "win" for row in pairs),
            "baseline_ties": sum(row["baseline_outcome"] == "tie" for row in pairs),
            "baseline_losses": sum(row["baseline_outcome"] == "loss" for row in pairs),
            "variant_wins": sum(row["variant_outcome"] == "win" for row in pairs),
            "variant_ties": sum(row["variant_outcome"] == "tie" for row in pairs),
            "variant_losses": sum(row["variant_outcome"] == "loss" for row in pairs),
            "losses_converted": sum(row["loss_converted"] for row in pairs),
            "wins_lost": sum(row["win_lost"] for row in pairs),
            "improved_relative_margin": sum(delta > 0 for delta in margin_deltas),
            "equal_relative_margin": sum(delta == 0 for delta in margin_deltas),
            "worse_relative_margin": sum(delta < 0 for delta in margin_deltas),
            "mean_baseline_margin": statistics.mean(baseline_margins),
            "mean_variant_margin": statistics.mean(variant_margins),
            "mean_relative_margin_delta": statistics.mean(margin_deltas),
            "median_relative_margin_delta": statistics.median(margin_deltas),
            "minimum_relative_margin_delta": min(margin_deltas),
            "maximum_relative_margin_delta": max(margin_deltas),
            "mean_candidate_score_delta": statistics.mean(candidate_deltas),
            "total_activations": sum(row["variant"]["activation_count"] for row in pairs),
            "total_visible_yield_harvested": sum(
                row["variant"]["visible_yield_harvested"] for row in pairs
            ),
        },
        "pairs": pairs,
        "conclusion_gate": {
            "all_exact_pairs_complete": len(pairs) == len(expected),
            "at_least_one_activation_every_pair": all(
                row["variant"]["activation_count"] > 0 for row in pairs
            ),
            "nonnegative_every_pair": all(delta >= 0 for delta in margin_deltas),
            "strictly_positive_mean_relative_margin": statistics.mean(margin_deltas) > 0,
            "default_activation_authorized": False,
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", dir=args.output.parent, delete=False, encoding="utf-8"
    ) as handle:
        json.dump(report, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write("\n")
        temporary = handle.name
    Path(temporary).replace(args.output)
    print(json.dumps(report["aggregate"], sort_keys=True))
    print(json.dumps(report["conclusion_gate"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
