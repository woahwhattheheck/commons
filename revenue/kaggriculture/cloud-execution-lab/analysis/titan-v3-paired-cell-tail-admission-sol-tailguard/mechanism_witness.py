#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import paired_cell_tail_admission as target


def h(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def game(
    *,
    opponent: str,
    seed: int,
    seat: int,
    own: float,
    rival: float,
    action: str,
    trace: str,
) -> dict:
    scores = [own, rival] if seat == 0 else [rival, own]
    return {
        "opponent": opponent,
        "seed": seed,
        "candidate_seat": seat,
        "status": "complete",
        "failure": None,
        "episode_steps": 720,
        "steps": 719,
        "candidate_action_count": 719,
        "candidate_action_sha256": h(action),
        "trace_sha256": h(trace),
        "scores": scores,
        "bank_snapshot": list(scores),
    }


def report(games: list[dict]) -> dict:
    return {
        "progress": {
            "state": "complete",
            "planned_games": len(games),
            "recorded_games": len(games),
        },
        "games": games,
        "evaluator_sha256": h("tailguard-witness-evaluator"),
        "engine": {"ref": "witness-engine"},
        "opponents": {"arlene": "witness"},
        "seeds": sorted({row["seed"] for row in games}),
        "rng_seed": 20260910,
    }


def paired(rows: list[tuple[int, int, float, float, float, float]]) -> tuple[dict, dict]:
    control_games: list[dict] = []
    candidate_games: list[dict] = []
    for seed, seat, control_own, control_rival, candidate_own, candidate_rival in rows:
        control_games.append(
            game(
                opponent="arlene",
                seed=seed,
                seat=seat,
                own=control_own,
                rival=control_rival,
                action=f"control-action-{seed}-{seat}",
                trace=f"control-trace-{seed}-{seat}",
            )
        )
        candidate_games.append(
            game(
                opponent="arlene",
                seed=seed,
                seat=seat,
                own=candidate_own,
                rival=candidate_rival,
                action=f"candidate-action-{seed}-{seat}",
                trace=f"candidate-trace-{seed}-{seat}",
            )
        )
    return report(control_games), report(candidate_games)


def legacy_aggregate_snapshot(report_value: dict) -> dict:
    overall = report_value["overall"]
    conditions = {
        "candidate_action_activation": overall["action_changed_cells"] > 0,
        "positive_mean_own_cash": overall["mean_own_cash_delta"] > 0,
        "nonnegative_median_own_cash": overall["median_own_cash_delta"] >= 0,
        "nonnegative_cell_balance": (
            overall["positive_own_cells"] >= overall["negative_own_cells"]
        ),
        "positive_mean_margin": overall["mean_margin_delta"] > 0,
        "zero_new_losses": overall["new_losses"] == 0,
        "zero_lost_wins": overall["lost_wins"] == 0,
    }
    return {"conditions": conditions, "all_conditions_pass": all(conditions.values())}


def main() -> None:
    masked_rows = [
        (seed, seat, 100, 90, 110, 90)
        for seed in range(1, 5)
        for seat in (0, 1)
    ]
    masked_rows[-1] = (4, 1, 100, 90, 50, 0)
    control, candidate = paired(masked_rows)
    masked = target.assess(control, candidate)

    safe_control, safe_candidate = paired(
        [(1, 0, 100, 90, 110, 85), (1, 1, 100, 90, 102, 89)]
    )
    safe = target.assess(safe_control, safe_candidate)

    payload = {
        "schema_version": 1,
        "operation": target.OPERATION,
        "claim": (
            "aggregate-positive evidence cannot conceal one matched-cell "
            "TITAN own-cash regression"
        ),
        "aggregate_masked_tail": {
            "legacy_aggregate_snapshot": legacy_aggregate_snapshot(masked),
            "tail_gate_verdict": masked["verdict"],
            "mean_own_cash_delta": masked["overall"]["mean_own_cash_delta"],
            "median_own_cash_delta": masked["overall"]["median_own_cash_delta"],
            "mean_margin_delta": masked["overall"]["mean_margin_delta"],
            "new_losses": masked["overall"]["new_losses"],
            "lost_wins": masked["overall"]["lost_wins"],
            "hidden_cell": {
                key: masked["negative_own_changed_cells"][0][key]
                for key in (
                    "opponent",
                    "seed",
                    "candidate_seat",
                    "own_cash_delta",
                    "margin_delta",
                )
            },
        },
        "pareto_safe_frontier": {
            "tail_gate_verdict": safe["verdict"],
            "gates": safe["gates"],
        },
        "upstream_source_custody_required": True,
        "promotion_authority": False,
        "provider_action_authorized": False,
    }
    payload["content_sha256"] = target.canonical_sha256(payload)
    Path("MECHANISM-WITNESS.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
