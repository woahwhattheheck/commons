# SPDX-License-Identifier: Apache-2.0
"""Strict paired control/candidate classifier for the fertilizer-liquidity arm."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import statistics
from typing import Any


class PanelError(ValueError):
    pass


def _load(path: Path) -> dict[str, Any]:
    def reject_constant(value):
        raise PanelError(f"nonfinite_json:{value}")

    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise PanelError(f"duplicate_json_key:{key}")
            result[key] = value
        return result

    value = json.loads(
        path.read_text(encoding="utf-8"),
        parse_constant=reject_constant,
        object_pairs_hook=pairs,
    )
    if not isinstance(value, dict):
        raise PanelError("report_not_object")
    return value


def _number(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise PanelError(f"invalid_number:{name}")
    return float(value)


def _grid(report: dict[str, Any], label: str) -> dict[tuple[str, int, int], dict[str, Any]]:
    games = report.get("games")
    if not isinstance(games, list):
        raise PanelError(f"{label}:games_not_list")
    result = {}
    for game in games:
        if not isinstance(game, dict) or game.get("status") != "complete":
            raise PanelError(f"{label}:incomplete_game")
        opponent = game.get("opponent")
        seed = game.get("seed")
        seat = game.get("candidate_seat")
        if not isinstance(opponent, str) or not opponent:
            raise PanelError(f"{label}:invalid_opponent")
        if type(seed) is not int or type(seat) is not int or seat not in (0, 1):
            raise PanelError(f"{label}:invalid_cell_identity")
        scores = game.get("scores")
        if not isinstance(scores, list) or len(scores) != 2:
            raise PanelError(f"{label}:invalid_scores")
        _number(scores[0], f"{label}:score0")
        _number(scores[1], f"{label}:score1")
        trace = game.get("trace_sha256")
        if not isinstance(trace, str) or len(trace) != 64:
            raise PanelError(f"{label}:invalid_trace")
        key = (opponent, seed, seat)
        if key in result:
            raise PanelError(f"{label}:duplicate_cell")
        result[key] = game
    return result


def _events(directory: Path) -> dict[str, Any]:
    rows = []
    if directory.is_dir():
        for path in sorted(directory.glob("worker-*.jsonl")):
            for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                try:
                    row = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise PanelError(f"invalid_event_json:{path.name}:{line_number}") from exc
                if row.get("schema") != "titan-day10-fertilizer-liquidity-event/v1":
                    raise PanelError("invalid_event_schema")
                if type(row.get("step")) is not int or type(row.get("player")) is not int:
                    raise PanelError("invalid_event_identity")
                if type(row.get("changed")) is not bool:
                    raise PanelError("invalid_event_changed")
                rows.append(row)
    changed = [row for row in rows if row["changed"]]
    return {
        "files": len(list(directory.glob("worker-*.jsonl"))) if directory.is_dir() else 0,
        "rows": len(rows),
        "changed_rows": len(changed),
        "changed_steps": sorted({row["step"] for row in changed}),
        "changed_quantities": [row.get("quantity", 0) for row in changed],
        "reason_counts": {
            reason: sum(row.get("reason") == reason for row in rows)
            for reason in sorted({str(row.get("reason")) for row in rows})
        },
    }


def classify(control_path: Path, candidate_path: Path, event_directory: Path) -> dict[str, Any]:
    control = _load(control_path)
    candidate = _load(candidate_path)
    for key in ("engine_ref", "engine_sha256", "loader_sha256", "evaluator_sha256", "seeds", "agent_rng_seed", "limits"):
        if control.get(key) != candidate.get(key):
            raise PanelError(f"execution_identity_mismatch:{key}")
    if control.get("opponents") != candidate.get("opponents"):
        raise PanelError("opponent_identity_mismatch")
    c_fingerprint = control.get("candidate") or {}
    n_fingerprint = candidate.get("candidate") or {}
    if c_fingerprint.get("sha256") == n_fingerprint.get("sha256"):
        raise PanelError("control_candidate_entry_alias")

    old = _grid(control, "control")
    new = _grid(candidate, "candidate")
    if set(old) != set(new) or not old:
        raise PanelError("paired_grid_mismatch")

    cells = []
    for key in sorted(old):
        opponent, seed, seat = key
        before, after = old[key], new[key]
        before_scores, after_scores = before["scores"], after["scores"]
        before_own = _number(before_scores[seat], "control_own")
        after_own = _number(after_scores[seat], "candidate_own")
        before_rival = _number(before_scores[1 - seat], "control_rival")
        after_rival = _number(after_scores[1 - seat], "candidate_rival")
        cells.append(
            {
                "opponent": opponent,
                "seed": seed,
                "candidate_seat": seat,
                "trace_changed": before["trace_sha256"] != after["trace_sha256"],
                "control_own": before_own,
                "candidate_own": after_own,
                "own_delta": after_own - before_own,
                "rival_delta": after_rival - before_rival,
                "margin_delta": (after_own - after_rival) - (before_own - before_rival),
            }
        )
    own = [row["own_delta"] for row in cells]
    events = _events(event_directory)
    seat_means = {
        str(seat): statistics.mean(row["own_delta"] for row in cells if row["candidate_seat"] == seat)
        for seat in (0, 1)
    }
    opponent_means = {
        opponent: statistics.mean(row["own_delta"] for row in cells if row["opponent"] == opponent)
        for opponent in sorted({row["opponent"] for row in cells})
    }
    trace_changes = sum(row["trace_changed"] for row in cells)
    mean_own = statistics.mean(own)
    median_own = statistics.median(own)
    positive = sum(value > 0 for value in own)
    negative = sum(value < 0 for value in own)
    if not trace_changes or not events["changed_rows"]:
        verdict = "NO_ACTION_SIGNAL"
    elif mean_own > 0 and median_own >= 0 and min(seat_means.values()) >= 0 and min(opponent_means.values()) >= 0 and positive >= negative:
        verdict = "ADVANCE"
    elif mean_own < 0 or min(seat_means.values()) < 0 or min(opponent_means.values()) < 0:
        verdict = "REGRESSION"
    else:
        verdict = "MIXED"
    return {
        "schema": "titan-day10-fertilizer-liquidity-panel/v1",
        "verdict": verdict,
        "cells": len(cells),
        "trace_changed_cells": trace_changes,
        "mean_own_delta": mean_own,
        "median_own_delta": median_own,
        "min_own_delta": min(own),
        "max_own_delta": max(own),
        "positive_cells": positive,
        "negative_cells": negative,
        "zero_cells": len(own) - positive - negative,
        "mean_rival_delta": statistics.mean(row["rival_delta"] for row in cells),
        "mean_margin_delta": statistics.mean(row["margin_delta"] for row in cells),
        "seat_mean_own_delta": seat_means,
        "opponent_mean_own_delta": opponent_means,
        "events": events,
        "control_candidate": control.get("candidate"),
        "tested_candidate": candidate.get("candidate"),
        "execution": {
            "engine_ref": candidate.get("engine_ref"),
            "engine_sha256": candidate.get("engine_sha256"),
            "loader_sha256": candidate.get("loader_sha256"),
            "evaluator_sha256": candidate.get("evaluator_sha256"),
            "seeds": candidate.get("seeds"),
            "agent_rng_seed": candidate.get("agent_rng_seed"),
            "limits": candidate.get("limits"),
        },
        "paired_cells": cells,
    }


def _markdown(result: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# TITAN V3 day-10 fertilizer liquidity panel",
            "",
            f"**Verdict:** `{result['verdict']}`",
            "",
            f"- Paired cells: {result['cells']}",
            f"- Candidate action-trace changes: {result['trace_changed_cells']}",
            f"- Instrumented changed rows: {result['events']['changed_rows']}",
            f"- Mean own-cash delta: {result['mean_own_delta']:+.3f}",
            f"- Median own-cash delta: {result['median_own_delta']:+.3f}",
            f"- Mean margin delta: {result['mean_margin_delta']:+.3f}",
            f"- Positive / zero / negative: {result['positive_cells']} / {result['zero_cells']} / {result['negative_cells']}",
            f"- Seat means: `{json.dumps(result['seat_mean_own_delta'], sort_keys=True)}`",
            f"- Opponent means: `{json.dumps(result['opponent_mean_own_delta'], sort_keys=True)}`",
            "",
            "This is an official-interpreter development panel, not hosted Kaggle scoring or submission authorization.",
            "",
        ]
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--control", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--events", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--markdown", type=Path, required=True)
    args = parser.parse_args()
    result = classify(args.control, args.candidate, args.events)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    args.markdown.write_text(_markdown(result), encoding="utf-8")
    print(json.dumps({key: result[key] for key in ("verdict", "cells", "trace_changed_cells", "mean_own_delta", "median_own_delta", "mean_margin_delta")}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
