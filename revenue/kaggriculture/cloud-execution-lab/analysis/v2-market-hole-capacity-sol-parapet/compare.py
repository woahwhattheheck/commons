# SPDX-License-Identifier: Apache-2.0
"""Fail-closed comparison for the frozen-V2 executable-slot ablation."""
from __future__ import annotations

import argparse
from collections import defaultdict
import json
import math
import os
from pathlib import Path
import statistics
import tempfile
from typing import Any, Mapping

OPERATION = "titan-v2-market-hole-capacity-20260909-sol-parapet-01"
KIND = "executable_market_prefix_capacity"
ENGINE_REF = "28b6d8af3ce73926b3d0fda1410c1ddd8384ab8c"
V2_SCHEDULER_BLOB = "7c068b7078c3d7c09bb3836590ad42b0af934cdf"
EXPECTED_OPPONENTS = ("arlene", "v1")
EXPECTED_SEEDS = (539131249, 1834999074, 2609097301, 2611092207)
EXPECTED_REPLACEMENTS = {
    "capacity_admission",
    "prefix_allocation_and_hole_reuse",
    "pending_from_executable_prefix",
}
EXPECTED_MARKERS = {
    "all_shed_target_domain",
    "next_turn_rival_scenario",
    "delayed_rival_scenario",
    "full_continuation_value",
    "forced_feasibility_rank",
}


class CompareError(ValueError):
    """The reports or their source/execution custody are incomplete."""


def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", newline="\n", dir=path.parent, delete=False
        ) as handle:
            temporary = Path(handle.name)
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def strict_object(path: Path) -> dict[str, Any]:
    def reject_pairs(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise CompareError(f"duplicate JSON key {key!r} in {path}")
            result[key] = value
        return result

    try:
        value = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=reject_pairs,
            parse_constant=lambda token: (_ for _ in ()).throw(
                CompareError(f"non-finite JSON token {token} in {path}")
            ),
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise CompareError(f"cannot read {path}: {type(exc).__name__}: {exc}") from exc
    if not isinstance(value, dict):
        raise CompareError(f"{path} must contain one JSON object")
    return value


def number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise CompareError(f"{label} is not numeric")
    parsed = float(value)
    if not math.isfinite(parsed):
        raise CompareError(f"{label} is not finite")
    return parsed


def digest(value: Any, label: str, length: int = 64) -> str:
    if (
        not isinstance(value, str)
        or len(value) != length
        or any(char not in "0123456789abcdef" for char in value)
    ):
        raise CompareError(f"{label} is not a lowercase {length * 4}-bit digest")
    return value


def validate_receipt(receipt: Mapping[str, Any]) -> dict[str, Any]:
    if receipt.get("schema_version") != 1:
        raise CompareError("materialization receipt schema mismatch")
    if receipt.get("operation") != OPERATION or receipt.get("kind") != KIND:
        raise CompareError("materialization receipt operation/kind mismatch")
    source = receipt.get("source")
    control = receipt.get("control")
    candidate = receipt.get("candidate")
    ablation = receipt.get("ablation")
    if not all(isinstance(value, Mapping) for value in (source, control, candidate, ablation)):
        raise CompareError("materialization receipt is incomplete")
    if source.get("scheduler_git_blob_sha1") != V2_SCHEDULER_BLOB:
        raise CompareError("receipt is not bound to frozen V2 scheduler")
    if control.get("core_closure_sha256") != source.get("closure_sha256"):
        raise CompareError("control core is not the frozen V2 closure")
    if ablation.get("changed_files") != ["scheduler.py"]:
        raise CompareError("candidate is not scheduler-only")

    replacements = ablation.get("replacements")
    if not isinstance(replacements, Mapping) or set(replacements) != EXPECTED_REPLACEMENTS:
        raise CompareError("replacement set is incomplete or unexpected")
    expected_counts = {
        "old_before": 1,
        "old_after": 0,
        "new_before": 0,
        "new_after": 1,
    }
    for name, record in replacements.items():
        if not isinstance(record, Mapping) or dict(record) != expected_counts:
            raise CompareError(f"replacement cardinality is invalid for {name}")

    markers = ablation.get("preserved_v2_markers")
    if (
        not isinstance(markers, Mapping)
        or set(markers) != EXPECTED_MARKERS
        or any(value is not True for value in markers.values())
    ):
        raise CompareError("preserved V2 feature custody is incomplete")

    source_closure = digest(source.get("closure_sha256"), "source closure")
    candidate_core = digest(candidate.get("core_closure_sha256"), "candidate core closure")
    control_execution = digest(
        control.get("execution_closure_sha256"), "control execution closure"
    )
    candidate_execution = digest(
        candidate.get("execution_closure_sha256"), "candidate execution closure"
    )
    control_entry = digest(control.get("entrypoint_sha256"), "control entrypoint")
    candidate_entry = digest(candidate.get("entrypoint_sha256"), "candidate entrypoint")
    candidate_scheduler = digest(
        candidate.get("scheduler_sha256"), "candidate scheduler"
    )
    digest(source.get("scheduler_sha256"), "source scheduler")
    digest(candidate.get("scheduler_git_blob_sha1"), "candidate scheduler blob", 40)

    if source_closure == candidate_core:
        raise CompareError("candidate core closure equals control source closure")
    if control_execution == candidate_execution:
        raise CompareError("control and candidate execution closures are equal")
    if control_entry == candidate_entry:
        raise CompareError("control and candidate entrypoint identities are equal")
    if candidate_scheduler == source.get("scheduler_sha256"):
        raise CompareError("candidate scheduler bytes equal frozen V2")
    if control.get("entrypoint") != "sol_parapet_entry.py" or candidate.get(
        "entrypoint"
    ) != "sol_parapet_entry.py":
        raise CompareError("generated entrypoint path mismatch")

    return {
        "source_closure_sha256": source_closure,
        "candidate_core_closure_sha256": candidate_core,
        "control_execution_closure_sha256": control_execution,
        "candidate_execution_closure_sha256": candidate_execution,
        "control_entrypoint_sha256": control_entry,
        "candidate_entrypoint_sha256": candidate_entry,
    }


def report_fingerprint(
    report: Mapping[str, Any], label: str, expected_entry_sha256: str
) -> dict[str, Any]:
    if report.get("schema_version") != 1:
        raise CompareError(f"{label} report schema mismatch")
    if report.get("engine_ref") != ENGINE_REF:
        raise CompareError(f"{label} engine ref mismatch")
    candidate = report.get("candidate")
    if not isinstance(candidate, Mapping):
        raise CompareError(f"{label} candidate identity is missing")
    if candidate.get("sha256") != expected_entry_sha256:
        raise CompareError(f"{label} executed entrypoint does not match receipt")
    opponents = report.get("opponents")
    if not isinstance(opponents, Mapping) or set(opponents) != set(EXPECTED_OPPONENTS):
        raise CompareError(f"{label} opponent bank mismatch")
    seeds = report.get("seeds")
    if (
        not isinstance(seeds, list)
        or tuple(seeds) != EXPECTED_SEEDS
        or any(isinstance(seed, bool) or not isinstance(seed, int) for seed in seeds)
    ):
        raise CompareError(f"{label} seed grid mismatch")
    return {
        "engine_ref": report.get("engine_ref"),
        "engine_sha256": report.get("engine_sha256"),
        "loader_sha256": report.get("loader_sha256"),
        "evaluator_sha256": report.get("evaluator_sha256"),
        "opponents": dict(opponents),
        "seeds": list(seeds),
        "agent_rng_seed": report.get("agent_rng_seed"),
        "limits": report.get("limits"),
        "method": report.get("method"),
        "python": report.get("python"),
    }


def daily_map(game: Mapping[str, Any], label: str) -> dict[int, tuple[float, float]]:
    rows = game.get("daily_bank")
    if not isinstance(rows, list) or not rows:
        raise CompareError(f"{label} daily_bank is missing or empty")
    result: dict[int, tuple[float, float]] = {}
    for index, row in enumerate(rows):
        if not isinstance(row, Mapping):
            raise CompareError(f"{label} daily_bank row {index} is invalid")
        step, bank = row.get("step"), row.get("bank")
        if (
            isinstance(step, bool)
            or not isinstance(step, int)
            or step in result
            or not isinstance(bank, list)
            or len(bank) != 2
        ):
            raise CompareError(f"{label} daily_bank row {index} identity is invalid")
        result[step] = (
            number(bank[0], f"{label} daily bank 0 at {step}"),
            number(bank[1], f"{label} daily bank 1 at {step}"),
        )
    return result


def game_grid(
    report: Mapping[str, Any], label: str
) -> dict[tuple[str, int, int], dict[str, Any]]:
    games = report.get("games")
    if not isinstance(games, list):
        raise CompareError(f"{label} games is not a list")
    grid: dict[tuple[str, int, int], dict[str, Any]] = {}
    for index, game in enumerate(games):
        if not isinstance(game, Mapping):
            raise CompareError(f"{label} game {index} is not an object")
        opponent = game.get("opponent")
        seed = game.get("seed")
        seat = game.get("candidate_seat")
        if isinstance(seed, bool) or not isinstance(seed, int):
            raise CompareError(f"{label} game {index} seed must be an integer")
        if isinstance(seat, bool) or not isinstance(seat, int):
            raise CompareError(f"{label} game {index} seat must be an integer")
        key = (opponent, seed, seat)
        if (
            opponent not in EXPECTED_OPPONENTS
            or seed not in EXPECTED_SEEDS
            or seat not in (0, 1)
            or key in grid
        ):
            raise CompareError(f"{label} invalid or duplicate game identity {key!r}")
        if game.get("status") != "complete" or game.get("failure") is not None:
            raise CompareError(f"{label} incomplete cell {key}: {game.get('failure')}")
        if game.get("steps") != 719 or game.get("episode_steps") != 720:
            raise CompareError(f"{label} wrong episode coverage for {key}")
        scores = game.get("scores")
        if not isinstance(scores, list) or len(scores) != 2:
            raise CompareError(f"{label} score vector is invalid for {key}")
        copied = dict(game)
        copied["scores"] = [
            number(scores[0], f"{label} {key} score 0"),
            number(scores[1], f"{label} {key} score 1"),
        ]
        copied["trace_sha256"] = digest(
            game.get("trace_sha256"), f"{label} {key} trace"
        )
        copied["_daily"] = daily_map(game, f"{label} {key}")
        grid[key] = copied
    expected = {
        (opponent, seed, seat)
        for opponent in EXPECTED_OPPONENTS
        for seed in EXPECTED_SEEDS
        for seat in (0, 1)
    }
    if set(grid) != expected:
        raise CompareError(
            f"{label} grid mismatch; missing={sorted(expected-set(grid))}, "
            f"extra={sorted(set(grid)-expected)}"
        )
    return grid


def first_daily_divergence(
    control: Mapping[str, Any], candidate: Mapping[str, Any]
) -> int | None:
    left, right = control["_daily"], candidate["_daily"]
    if set(left) != set(right):
        raise CompareError("control/candidate daily checkpoint grids differ")
    for step in sorted(left):
        if left[step] != right[step]:
            return step
    return None


def _summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    deltas = [row["own_delta"] for row in rows]
    return {
        "cells": len(rows),
        "changed_cells": sum(row["trace_changed"] for row in rows),
        "positive_cells": sum(delta > 0 for delta in deltas),
        "zero_cells": sum(delta == 0 for delta in deltas),
        "negative_cells": sum(delta < 0 for delta in deltas),
        "mean_own_delta": statistics.mean(deltas),
        "median_own_delta": statistics.median(deltas),
        "minimum_own_delta": min(deltas),
        "maximum_own_delta": max(deltas),
        "mean_margin_delta": statistics.mean(row["margin_delta"] for row in rows),
    }


def compare(
    control: Mapping[str, Any],
    candidate: Mapping[str, Any],
    receipt: Mapping[str, Any],
    *,
    git_head: str,
) -> dict[str, Any]:
    closure = validate_receipt(receipt)
    left_fp = report_fingerprint(
        control, "control", closure["control_entrypoint_sha256"]
    )
    right_fp = report_fingerprint(
        candidate, "candidate", closure["candidate_entrypoint_sha256"]
    )
    if left_fp != right_fp:
        raise CompareError("control/candidate engine, opponent, grid, or limits drift")
    left = game_grid(control, "control")
    right = game_grid(candidate, "candidate")
    if set(left) != set(right):
        raise CompareError("paired game grids differ")

    rows: list[dict[str, Any]] = []
    for key in sorted(left):
        opponent, seed, seat = key
        baseline, repaired = left[key], right[key]
        baseline_own = baseline["scores"][seat]
        baseline_rival = baseline["scores"][1 - seat]
        repaired_own = repaired["scores"][seat]
        repaired_rival = repaired["scores"][1 - seat]
        rows.append(
            {
                "opponent": opponent,
                "seed": seed,
                "seat": seat,
                "control_own": baseline_own,
                "control_rival": baseline_rival,
                "candidate_own": repaired_own,
                "candidate_rival": repaired_rival,
                "own_delta": repaired_own - baseline_own,
                "rival_delta": repaired_rival - baseline_rival,
                "margin_delta": (repaired_own - repaired_rival)
                - (baseline_own - baseline_rival),
                "trace_changed": baseline["trace_sha256"]
                != repaired["trace_sha256"],
                "first_daily_bank_divergence_step": first_daily_divergence(
                    baseline, repaired
                ),
            }
        )

    overall = _summary(rows)
    grouped_opponent: dict[str, list[dict[str, Any]]] = defaultdict(list)
    grouped_stratum: dict[tuple[str, int], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped_opponent[row["opponent"]].append(row)
        grouped_stratum[(row["opponent"], row["seat"])].append(row)
    by_opponent = {
        opponent: _summary(values)
        for opponent, values in sorted(grouped_opponent.items())
    }
    by_opponent_seat = {
        f"{opponent}:seat{seat}": _summary(values)
        for (opponent, seat), values in sorted(grouped_stratum.items())
    }

    if overall["changed_cells"] == 0:
        verdict, reason, exit_code = (
            "NO_ACTION_SIGNAL",
            "the executable-slot repair never changed a complete game trace",
            4,
        )
    elif all(row["own_delta"] == 0 and row["rival_delta"] == 0 for row in rows):
        verdict, reason, exit_code = (
            "ACTION_NO_SCORE_SIGNAL",
            "traces changed but every terminal score remained identical",
            4,
        )
    elif (
        overall["mean_own_delta"] > 0
        and overall["median_own_delta"] >= 0
        and overall["positive_cells"] >= overall["negative_cells"]
        and all(value["mean_own_delta"] >= 0 for value in by_opponent_seat.values())
    ):
        verdict, reason, exit_code = (
            "UPSIDE_SCREEN",
            "mean own cash improved with nonnegative median and no opponent×seat mean regression",
            0,
        )
    elif overall["mean_own_delta"] < 0:
        verdict, reason, exit_code = (
            "REGRESSION",
            "the executable-slot repair lowered mean own cash",
            1,
        )
    else:
        verdict, reason, exit_code = (
            "MIXED",
            "play changed without broad, seat-balanced own-cash upside",
            1,
        )

    return {
        "schema_version": 1,
        "operation": OPERATION,
        "git_head": git_head,
        "verdict": verdict,
        "reason": reason,
        "exit_code": exit_code,
        "promotion_boundary": "FULL_CURRENT_V1_V2_MATCHED_PANEL_REQUIRED",
        "closure": closure,
        "grid": {
            "seeds": list(EXPECTED_SEEDS),
            "opponents": list(EXPECTED_OPPONENTS),
            "both_seats": True,
            "cells_per_arm": len(rows),
        },
        "overall": overall,
        "by_opponent": by_opponent,
        "by_opponent_seat": by_opponent_seat,
        "rows": rows,
    }


def markdown(report: Mapping[str, Any]) -> str:
    lines = [
        "# Titan V2 executable-slot capacity ablation",
        "",
        f"- verdict: `{report.get('verdict', 'INVALID')}`",
        f"- reason: {report.get('reason', 'unknown')}",
        f"- tested head: `{report.get('git_head', 'unknown')}`",
        f"- boundary: `{report.get('promotion_boundary', 'NO_PROMOTION')}`",
    ]
    overall = report.get("overall")
    if isinstance(overall, Mapping):
        lines += [
            "",
            "## Overall",
            "",
            f"- cells: {overall.get('cells')}",
            f"- changed cells: {overall.get('changed_cells')}",
            f"- mean own-cash delta: {overall.get('mean_own_delta')}",
            f"- median own-cash delta: {overall.get('median_own_delta')}",
            f"- positive / zero / negative: {overall.get('positive_cells')} / "
            f"{overall.get('zero_cells')} / {overall.get('negative_cells')}",
            f"- mean margin delta: {overall.get('mean_margin_delta')}",
        ]
    strata = report.get("by_opponent_seat")
    if isinstance(strata, Mapping):
        lines += ["", "## Opponent × seat", ""]
        for name, value in sorted(strata.items()):
            lines.append(
                f"- `{name}`: mean own {value.get('mean_own_delta')}; "
                f"changed {value.get('changed_cells')}/{value.get('cells')}"
            )
    lines += [
        "",
        "This is a compact causal screen over frozen V2, not a promotion or hosted leaderboard claim.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--control", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--head", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--markdown", type=Path, required=True)
    args = parser.parse_args()
    try:
        report = compare(
            strict_object(args.control),
            strict_object(args.candidate),
            strict_object(args.receipt),
            git_head=args.head,
        )
    except CompareError as exc:
        report = {
            "schema_version": 1,
            "operation": OPERATION,
            "git_head": args.head,
            "verdict": "INVALID",
            "reason": str(exc),
            "exit_code": 2,
            "promotion_boundary": "NO_PROMOTION_FROM_INVALID_EVIDENCE",
        }
    atomic_write(
        args.output,
        json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n",
    )
    atomic_write(args.markdown, markdown(report))
    print(
        json.dumps(
            {
                "verdict": report["verdict"],
                "reason": report["reason"],
                "exit_code": report["exit_code"],
                "overall": report.get("overall"),
            },
            sort_keys=True,
        )
    )
    return int(report["exit_code"])


if __name__ == "__main__":
    raise SystemExit(main())
