#!/usr/bin/env python3
"""Exact both-seat panel for hour-23 work erased by the daily reset."""

from __future__ import annotations

import argparse
import copy
from collections import Counter, defaultdict
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
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


def tile_at(observation: Mapping[str, Any], player: int, position: tuple[int, int]) -> Any:
    x, y = position
    rows = observation["farms"][player].get("tiles", [])
    if not (0 <= y < len(rows) and 0 <= x < len(rows[y])):
        return None
    return copy.deepcopy(rows[y][x])


def make_reset_probe(base):
    inherited_probe = base.probe_step

    def reset_probe(
        engine,
        state: Sequence[Any],
        env: Any,
        actions: Sequence[Mapping[str, Any]],
        candidate_seat: int,
        step: int,
    ) -> list[dict[str, Any]]:
        findings = inherited_probe(
            engine, state, env, actions, candidate_seat, step
        )
        if step % 24 != 23:
            return findings

        observation = state[candidate_seat].observation
        player = int(observation["player"])
        farm = observation["farms"][player]
        count = 1 + len(farm.get("hands", []))
        selected = base.units(actions[candidate_seat], count)
        worker_positions = base.positions(observation, player)
        actual_state, _ = base.run_step(engine, state, env, actions)
        actual_sha = base.state_sha256(actual_state)
        actual_metrics = base.own_metrics(actual_state, candidate_seat)
        groups: dict[tuple[int, int], list[dict[str, Any]]] = defaultdict(list)
        for worker, row in enumerate(selected):
            groups[worker_positions[worker]].append(
                {"worker": worker, "action": copy.deepcopy(row)}
            )

        for worker, row in enumerate(selected):
            pass_action = base.set_unit(actions[candidate_seat], worker, ["PASS"])
            pass_actions = list(actions)
            pass_actions[candidate_seat] = pass_action
            pass_state, _ = base.run_step(engine, state, env, pass_actions)
            pass_sha = base.state_sha256(pass_state)
            if pass_sha != actual_sha:
                continue

            position = worker_positions[worker]
            replacement_rows: list[dict[str, Any]] = []
            for replacement in base.PRODUCTIVE:
                trial_action = base.set_unit(
                    actions[candidate_seat], worker, [replacement]
                )
                trial_actions = list(actions)
                trial_actions[candidate_seat] = trial_action
                trial_state, _ = base.run_step(engine, state, env, trial_actions)
                trial_sha = base.state_sha256(trial_state)
                if trial_sha == pass_sha:
                    continue
                replacement_rows.append(
                    {
                        "action": [replacement],
                        "state_sha256": trial_sha,
                        "delta_vs_actual": base.numeric_delta(
                            actual_metrics,
                            base.own_metrics(trial_state, candidate_seat),
                        ),
                    }
                )

            # PASS slots with no productive alternative are uninteresting noise.
            # Non-PASS rows remain evidence of work erased by reset even when no
            # replacement is available in this state.
            if base.op(row) == "PASS" and not replacement_rows:
                continue
            findings.append(
                {
                    "kind": "eod_reset_equivalent_slot",
                    "step": step,
                    "day": step // 24,
                    "hour": step % 24,
                    "worker": worker,
                    "position": list(position),
                    "selected_action": copy.deepcopy(row),
                    "selected_op": base.op(row),
                    "pass_state_equivalent": True,
                    "actual_state_sha256": actual_sha,
                    "pass_state_sha256": pass_sha,
                    "tile_before": tile_at(observation, player, position),
                    "worker_inventory_before": copy.deepcopy(
                        observation["private"]["inventories"][worker]
                    ),
                    "shed_before": copy.deepcopy(observation["private"]["shed"]),
                    "co_located_selected": copy.deepcopy(groups[position]),
                    "market": copy.deepcopy(
                        list(actions[candidate_seat].get("market") or [])
                    ),
                    "productive_replacements": replacement_rows,
                }
            )
        return findings

    return reset_probe


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description=__doc__)
    value.add_argument("--trace-probe", type=Path, required=True)
    value.add_argument("--evaluator", type=Path, required=True)
    value.add_argument("--loader", type=Path, required=True)
    value.add_argument("--engine-dir", type=Path, required=True)
    value.add_argument("--candidate", type=Path, required=True)
    value.add_argument("--opponent", type=Path, required=True)
    value.add_argument("--environment-seed", type=int, default=261140014)
    value.add_argument("--rng-seeds", type=int, nargs="+", required=True)
    value.add_argument("--candidate-seats", type=int, nargs="+", default=(0, 1))
    value.add_argument("--action-timeout", type=float, default=1.0)
    value.add_argument("--startup-timeout", type=float, default=10.0)
    value.add_argument("--game-timeout", type=float, default=180.0)
    value.add_argument("--source-commit", required=True)
    value.add_argument("--archive-sha256", required=True)
    value.add_argument("--output", type=Path, required=True)
    return value


def main(argv: Sequence[str] | None = None) -> int:
    args = parser().parse_args(argv)
    if any(seat not in (0, 1) for seat in args.candidate_seats):
        raise ValueError("candidate seats must be 0 or 1")
    if len(set(args.rng_seeds)) != len(args.rng_seeds):
        raise ValueError("rng seeds must be unique")
    if len(set(args.candidate_seats)) != len(args.candidate_seats):
        raise ValueError("candidate seats must be unique")

    base = import_path(args.trace_probe, "w14_trace_probe_base")
    evaluator = import_path(args.evaluator, "w14_reset_panel_evaluator")
    engine, engine_hashes = evaluator.get_engine(args.engine_dir, args.loader)
    base.probe_step = make_reset_probe(base)

    expected = {
        (args.environment_seed, rng_seed, seat)
        for rng_seed in args.rng_seeds
        for seat in args.candidate_seats
    }
    games: list[dict[str, Any]] = []
    seen: set[tuple[int, int, int]] = set()
    for rng_seed in args.rng_seeds:
        for candidate_seat in args.candidate_seats:
            key = (args.environment_seed, rng_seed, candidate_seat)
            if key in seen:
                raise AssertionError(f"duplicate scheduled cell: {key}")
            seen.add(key)
            specs = [
                str(args.candidate.resolve()),
                str(args.opponent.resolve()),
            ]
            if candidate_seat == 1:
                specs.reverse()
            game = base.play_probe(
                evaluator,
                engine,
                specs,
                args.engine_dir,
                args.loader,
                args.environment_seed,
                candidate_seat,
                rng_seed,
                args.action_timeout,
                args.startup_timeout,
                args.game_timeout,
            )
            game["cell_key"] = {
                "environment_seed": args.environment_seed,
                "rng_seed": rng_seed,
                "candidate_seat": candidate_seat,
            }
            reset_rows = [
                row
                for row in game.get("findings", [])
                if row.get("kind") == "eod_reset_equivalent_slot"
            ]
            game["reset_equivalent_slots"] = len(reset_rows)
            game["reset_equivalent_nonpass_slots"] = sum(
                row.get("selected_op") != "PASS" for row in reset_rows
            )
            game["reset_productive_replacements"] = sum(
                len(row.get("productive_replacements", [])) for row in reset_rows
            )
            games.append(game)

    if seen != expected:
        raise AssertionError(
            f"cell-set mismatch missing={sorted(expected - seen)} "
            f"unexpected={sorted(seen - expected)}"
        )
    incomplete = [
        row["cell_key"]
        for row in games
        if row.get("status") != "complete" or row.get("steps") != 719
    ]
    if incomplete:
        raise AssertionError(f"incomplete official cells: {incomplete}")

    trace_counts = Counter(
        row["candidate_action_trace_sha256"] for row in games
    )
    reset_findings = [
        finding
        for game in games
        for finding in game.get("findings", [])
        if finding.get("kind") == "eod_reset_equivalent_slot"
    ]
    productive = [
        {
            "cell_key": game["cell_key"],
            "score": game["scores"],
            "step": finding["step"],
            "day": finding["day"],
            "worker": finding["worker"],
            "position": finding["position"],
            "selected_action": finding["selected_action"],
            "tile_before": finding["tile_before"],
            "worker_inventory_before": finding["worker_inventory_before"],
            "co_located_selected": finding["co_located_selected"],
            "market": finding["market"],
            "productive_replacements": finding["productive_replacements"],
        }
        for game in games
        for finding in game.get("findings", [])
        if finding.get("kind") == "eod_reset_equivalent_slot"
        and finding.get("productive_replacements")
    ]
    report = {
        "schema_version": 1,
        "operation": OPERATION,
        "source_commit": args.source_commit,
        "archive_sha256": args.archive_sha256,
        "trace_probe_sha256": sha256(args.trace_probe),
        "evaluator_sha256": sha256(args.evaluator),
        "loader_sha256": sha256(args.loader),
        "candidate_sha256": sha256(args.candidate),
        "opponent_sha256": sha256(args.opponent),
        "engine_sha256": engine_hashes,
        "scheduled_cells": [
            {
                "environment_seed": key[0],
                "rng_seed": key[1],
                "candidate_seat": key[2],
            }
            for key in sorted(expected)
        ],
        "aggregate": {
            "complete_games": len(games),
            "unique_candidate_action_traces": len(trace_counts),
            "candidate_action_trace_counts": dict(sorted(trace_counts.items())),
            "reset_equivalent_slots": len(reset_findings),
            "reset_equivalent_nonpass_slots": sum(
                row.get("selected_op") != "PASS" for row in reset_findings
            ),
            "productive_reset_slots": len(productive),
            "productive_replacement_options": sum(
                len(row["productive_replacements"]) for row in productive
            ),
        },
        "productive_reset_slots": productive,
        "games": games,
        "conclusion_gate": {
            "full_game_cells_complete": len(games) == len(expected),
            "at_least_two_distinct_candidate_traces": len(trace_counts) >= 2,
            "realized_productive_reset_slot_found": bool(productive),
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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
