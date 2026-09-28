# SPDX-License-Identifier: Apache-2.0
"""Reproducible synthetic overhead screen for the S02 admission firewall.

This deliberately injects a constant evaluator. It measures Python firewall
bookkeeping only; it is not an official-engine runtime or game-strength test.
"""
from __future__ import annotations

import argparse
import json
import os
import statistics
import time
from pathlib import Path

import planner_mpc as p

BASE = {
    "farmer": ["NORTH"],
    "hands": [["WATER"]],
    "market": [["BUY_LAND"], ["SELL", "WHEAT", 4], ["HIRE"], []],
}
OBS = {
    "player": 0,
    "step": 24,
    "day": 1,
    "hour": 0,
    "farms": [
        {"farmer": [4, 4], "hands": [[4, 4]], "tiles": [[None]], "money": 3000},
        {"farmer": [4, 4], "hands": [], "tiles": [[None]], "money": 3000},
    ],
    "market": {},
    "town": {},
    "private": {},
}


def canonical(_obs, _cfg=None):
    return json.loads(json.dumps(BASE))


def candidate_fn(base, _obs, _cfg, limit=8):
    del limit
    candidate = json.loads(json.dumps(base))
    candidate["market"][0], candidate["market"][1] = (
        candidate["market"][1],
        candidate["market"][0],
    )
    return [json.loads(json.dumps(base)), candidate]


def evaluator(*_args, **_kwargs):
    return p.Evaluation(
        tuple(
            p.ScenarioResult(
                f"s{index}", True, True, True, 100.0, 102.0, 2.0, "synthetic"
            )
            for index in range(3)
        )
    )


def percentile(values: list[float], quantile: float) -> float:
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, int(round((len(ordered) - 1) * quantile))))
    return ordered[index]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--iterations", type=int, default=5000)
    parser.add_argument("--output", type=Path, default=Path("BENCHMARK.json"))
    args = parser.parse_args()
    if args.iterations <= 0:
        raise SystemExit("iterations must be positive")

    planner = p.Planner(
        canonical,
        mode="shadow",
        min_scenarios=3,
        min_cash_gain=1,
        candidate_fn=candidate_fn,
        evaluator=evaluator,
        log_path=os.devnull,
    )
    wall_ms: list[float] = []
    cpu_ms: list[float] = []
    for _ in range(args.iterations):
        wall_started = time.perf_counter_ns()
        cpu_started = time.process_time_ns()
        output = planner.act(OBS, {})
        cpu_ms.append((time.process_time_ns() - cpu_started) / 1_000_000.0)
        wall_ms.append((time.perf_counter_ns() - wall_started) / 1_000_000.0)
        if output != BASE:
            raise AssertionError("shadow mode changed canonical output")

    payload = {
        "schema": "titan.s02.guard.synthetic-overhead.v1",
        "scope": "synthetic injected evaluator; no official engine",
        "claim_boundary": (
            "Measures Python planner/firewall overhead only. Does not measure "
            "exact-engine transition cost or game strength."
        ),
        "mode": "shadow",
        "iterations": args.iterations,
        "wall_mean_ms": statistics.fmean(wall_ms),
        "wall_p50_ms": percentile(wall_ms, 0.50),
        "wall_p95_ms": percentile(wall_ms, 0.95),
        "wall_max_ms": max(wall_ms),
        "cpu_mean_ms": statistics.fmean(cpu_ms),
        "cpu_p50_ms": percentile(cpu_ms, 0.50),
        "cpu_p95_ms": percentile(cpu_ms, 0.95),
        "cpu_max_ms": max(cpu_ms),
    }
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
