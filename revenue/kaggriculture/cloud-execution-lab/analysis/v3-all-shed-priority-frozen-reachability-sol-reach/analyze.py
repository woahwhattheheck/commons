# SPDX-License-Identifier: Apache-2.0
"""Fail-closed comparison for current TITAN reachability panels."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import statistics
from typing import Any, Mapping

EXPECTED_SEEDS = (
    539131249,
    1834999074,
    2609097301,
    2609097302,
    2609097303,
    2609097304,
    2611092201,
    2611092207,
)
EXPECTED_OPPONENT_SHA256 = (
    "1dc166ae2bf0c56a44fac4482f469b8812968c4cb32459cb9860f5077897a7d4"
)
EXPECTED_MAIN_SHA256 = (
    "c4c22d0f2b1071cadf6a9f74effccc8cb20ea9f4d10ca1cf9f1fe57351709dc1"
)


class AnalysisError(ValueError):
    """A panel is incomplete, ambiguous, detached, or malformed."""


def _strict_load(path: Path) -> dict[str, Any]:
    def pairs(items):
        result: dict[str, Any] = {}
        for key, value in items:
            if key in result:
                raise AnalysisError(f"duplicate key {key!r} in {path}")
            result[key] = value
        return result

    try:
        value = json.loads(
            path.read_bytes(),
            object_pairs_hook=pairs,
            parse_constant=lambda token: (_ for _ in ()).throw(
                AnalysisError(f"non-finite token {token!r} in {path}")
            ),
        )
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise AnalysisError(f"invalid JSON in {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise AnalysisError(f"panel must be one object: {path}")
    return value


def _finite_number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise AnalysisError(f"{label} is not numeric")
    result = float(value)
    if not math.isfinite(result):
        raise AnalysisError(f"{label} is not finite")
    return result


def _panel_identity(panel: Mapping[str, Any]) -> dict[str, Any]:
    candidate = panel.get("candidate")
    opponents = panel.get("opponents")
    if not isinstance(candidate, dict) or not isinstance(opponents, dict):
        raise AnalysisError("panel candidate/opponent identity missing")
    if candidate.get("entry") != "main.py" or candidate.get("callable") != "agent":
        raise AnalysisError("panel did not execute main.py::agent")
    if candidate.get("sha256") != EXPECTED_MAIN_SHA256:
        raise AnalysisError("canonical main.py identity drift")
    arlene = opponents.get("arlene")
    if not isinstance(arlene, dict) or arlene.get("sha256") != EXPECTED_OPPONENT_SHA256:
        raise AnalysisError("Arlene opponent identity drift")
    seeds = panel.get("seeds")
    if tuple(seeds or ()) != EXPECTED_SEEDS:
        raise AnalysisError(f"seed grid drift: {seeds!r}")
    if panel.get("agent_rng_seed") != 20260909:
        raise AnalysisError("agent RNG seed drift")
    return {
        key: panel.get(key)
        for key in (
            "engine_ref",
            "engine_sha256",
            "loader_sha256",
            "evaluator_sha256",
            "opponents",
            "seeds",
            "agent_rng_seed",
            "platform",
            "limits",
            "method",
        )
    }


def _games(panel: Mapping[str, Any]) -> dict[tuple[str, int, int], dict[str, Any]]:
    games = panel.get("games")
    if not isinstance(games, list):
        raise AnalysisError("games must be one list")
    result: dict[tuple[str, int, int], dict[str, Any]] = {}
    for index, game in enumerate(games):
        if not isinstance(game, dict):
            raise AnalysisError(f"game {index} is not one object")
        opponent = game.get("opponent")
        seed = game.get("seed")
        seat = game.get("candidate_seat")
        if opponent != "arlene" or type(seed) is not int or seat not in (0, 1):
            raise AnalysisError(f"invalid game key at index {index}")
        key = (opponent, seed, seat)
        if key in result:
            raise AnalysisError(f"duplicate game key {key}")
        if game.get("status") != "complete" or game.get("failure") is not None:
            raise AnalysisError(f"incomplete game {key}")
        if game.get("steps") != 719 or game.get("episode_steps") != 720:
            raise AnalysisError(f"lifecycle drift for {key}")
        if game.get("candidate_action_count") != 719:
            raise AnalysisError(f"candidate-action cardinality drift for {key}")
        action_sha = game.get("candidate_action_sha256")
        trace_sha = game.get("trace_sha256")
        if not isinstance(action_sha, str) or len(action_sha) != 64:
            raise AnalysisError(f"candidate action identity missing for {key}")
        if not isinstance(trace_sha, str) or len(trace_sha) != 64:
            raise AnalysisError(f"trace identity missing for {key}")
        scores = game.get("scores")
        if not isinstance(scores, list) or len(scores) != 2:
            raise AnalysisError(f"score pair missing for {key}")
        _finite_number(scores[0], f"{key} score0")
        _finite_number(scores[1], f"{key} score1")
        result[key] = game
    expected = {("arlene", seed, seat) for seed in EXPECTED_SEEDS for seat in (0, 1)}
    if set(result) != expected:
        raise AnalysisError(
            f"grid mismatch; missing={sorted(expected-set(result))}, "
            f"extra={sorted(set(result)-expected)}"
        )
    return result


def _outcome(own: float, rival: float) -> str:
    if own > rival:
        return "win"
    if own < rival:
        return "loss"
    return "tie"


def compare(control: Mapping[str, Any], candidate: Mapping[str, Any]) -> dict[str, Any]:
    if _panel_identity(control) != _panel_identity(candidate):
        raise AnalysisError("control/candidate evaluator or grid identity drift")
    controls = _games(control)
    candidates = _games(candidate)
    rows: list[dict[str, Any]] = []
    for key in sorted(controls):
        base = controls[key]
        arm = candidates[key]
        seat = key[2]
        rival_seat = 1 - seat
        base_own = _finite_number(base["scores"][seat], f"{key} base own")
        base_rival = _finite_number(base["scores"][rival_seat], f"{key} base rival")
        arm_own = _finite_number(arm["scores"][seat], f"{key} arm own")
        arm_rival = _finite_number(arm["scores"][rival_seat], f"{key} arm rival")
        own_delta = arm_own - base_own
        rival_delta = arm_rival - base_rival
        margin_delta = (arm_own - arm_rival) - (base_own - base_rival)
        rows.append(
            {
                "opponent": key[0],
                "seed": key[1],
                "seat": seat,
                "action_changed": (
                    base["candidate_action_sha256"] != arm["candidate_action_sha256"]
                ),
                "trace_changed": base["trace_sha256"] != arm["trace_sha256"],
                "own_delta": own_delta,
                "rival_delta": rival_delta,
                "margin_delta": margin_delta,
                "control_outcome": _outcome(base_own, base_rival),
                "candidate_outcome": _outcome(arm_own, arm_rival),
            }
        )

    own = [row["own_delta"] for row in rows]
    margins = [row["margin_delta"] for row in rows]
    changed = [row for row in rows if row["action_changed"]]
    score_changed = [
        row
        for row in rows
        if row["own_delta"] != 0 or row["rival_delta"] != 0
    ]
    new_losses = sum(
        row["control_outcome"] != "loss" and row["candidate_outcome"] == "loss"
        for row in rows
    )
    lost_wins = sum(
        row["control_outcome"] == "win" and row["candidate_outcome"] != "win"
        for row in rows
    )
    strata: dict[str, dict[str, Any]] = {}
    for seat in (0, 1):
        group = [row for row in rows if row["seat"] == seat]
        strata[f"arlene:seat{seat}"] = {
            "cells": len(group),
            "mean_own_delta": statistics.fmean(row["own_delta"] for row in group),
            "median_own_delta": statistics.median(row["own_delta"] for row in group),
            "mean_margin_delta": statistics.fmean(row["margin_delta"] for row in group),
            "negative_own_cells": sum(row["own_delta"] < 0 for row in group),
        }
    summary = {
        "cells": len(rows),
        "action_changed_cells": len(changed),
        "trace_changed_cells": sum(row["trace_changed"] for row in rows),
        "score_changed_cells": len(score_changed),
        "mean_own_delta": statistics.fmean(own),
        "median_own_delta": statistics.median(own),
        "min_own_delta": min(own),
        "max_own_delta": max(own),
        "positive_own_cells": sum(value > 0 for value in own),
        "zero_own_cells": sum(value == 0 for value in own),
        "negative_own_cells": sum(value < 0 for value in own),
        "mean_margin_delta": statistics.fmean(margins),
        "min_margin_delta": min(margins),
        "max_margin_delta": max(margins),
        "new_losses": new_losses,
        "lost_wins": lost_wins,
        "strata": strata,
    }
    return {"summary": summary, "rows": rows}


def analyze(
    control_path: Path,
    scheduler_path: Path,
    frozen_path: Path,
) -> dict[str, Any]:
    paths = {
        "control": control_path,
        "scheduler_only": scheduler_path,
        "frozen_priority": frozen_path,
    }
    panels = {name: _strict_load(path) for name, path in paths.items()}
    scheduler = compare(panels["control"], panels["scheduler_only"])
    frozen = compare(panels["control"], panels["frozen_priority"])

    scheduler_summary = scheduler["summary"]
    frozen_summary = frozen["summary"]
    scheduler_dormant = (
        scheduler_summary["action_changed_cells"] == 0
        and scheduler_summary["score_changed_cells"] == 0
        and scheduler_summary["trace_changed_cells"] == 0
    )
    frozen_gates = {
        "returned_action_activated": frozen_summary["action_changed_cells"] > 0,
        "positive_mean_own": frozen_summary["mean_own_delta"] > 0,
        "nonnegative_median_own": frozen_summary["median_own_delta"] >= 0,
        "no_negative_own_cells": frozen_summary["negative_own_cells"] == 0,
        "positive_mean_margin": frozen_summary["mean_margin_delta"] > 0,
        "no_new_losses": frozen_summary["new_losses"] == 0,
        "no_lost_wins": frozen_summary["lost_wins"] == 0,
        "nonnegative_strata": all(
            row["mean_own_delta"] >= 0 and row["mean_margin_delta"] >= 0
            for row in frozen_summary["strata"].values()
        ),
    }
    admitted = all(frozen_gates.values())
    classification = (
        "ADMIT_LIVE_FACTOR" if admitted else "REJECT_LIVE_FACTOR"
    )
    if scheduler_dormant:
        classification = "SCHEDULER_PREDECESSOR_DORMANT__" + classification
    result = {
        "schema_version": 1,
        "classification": classification,
        "scheduler_only": {
            **scheduler,
            "dormant": scheduler_dormant,
        },
        "frozen_priority": {
            **frozen,
            "gates": frozen_gates,
            "admitted": admitted,
        },
        "source_files": {
            name: {
                "path": str(path),
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
            for name, path in paths.items()
        },
    }
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--control", type=Path, required=True)
    parser.add_argument("--scheduler-only", type=Path, required=True)
    parser.add_argument("--frozen-priority", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = analyze(args.control, args.scheduler_only, args.frozen_priority)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
