#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Fail-closed paired-cell tail admission for TITAN gameplay panels.

The incumbent panel gate aggregates own-cash and margin deltas.  Aggregation can
hide a catastrophic matched-cell regression when the remaining cells improve,
or when the rival loses even more cash.  This module re-derives every paired
cell directly from the retained control/candidate reports and admits only a
Pareto-safe changed-cell frontier.

No upstream summary, verdict, or claimed delta is trusted.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import statistics
from typing import Any, Mapping, Sequence

SCHEMA_VERSION = 1
POLICY_ID = "paired_cell_pareto_tail_floor_v1"
OPERATION = "TITAN-V3-PAIRED-CELL-TAIL-ADMISSION-20260910-01"
EXPECTED_EPISODE_STEPS = 720


class EvidenceError(ValueError):
    """Retained evidence is malformed, incomplete, or detached."""


def strict_load(path: Path, label: str) -> dict[str, Any]:
    """Load one finite JSON object while rejecting duplicate keys."""

    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        output: dict[str, Any] = {}
        for key, value in items:
            if key in output:
                raise EvidenceError(f"{label} has duplicate key {key!r}")
            output[key] = value
        return output

    def constant(value: str) -> Any:
        raise EvidenceError(f"{label} has non-finite JSON constant {value}")

    try:
        value = json.loads(
            Path(path).read_text(encoding="utf-8"),
            object_pairs_hook=pairs,
            parse_constant=constant,
        )
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise EvidenceError(f"cannot load {label}: {exc}") from exc
    if not isinstance(value, dict):
        raise EvidenceError(f"{label} root must be an object")
    return value


def canonical_sha256(value: Any) -> str:
    payload = json.dumps(
        value, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def digest(value: Any, label: str) -> str:
    if not isinstance(value, str) or len(value) != 64:
        raise EvidenceError(f"{label} must be a SHA-256 digest")
    try:
        int(value, 16)
    except ValueError as exc:
        raise EvidenceError(f"{label} must be a SHA-256 digest") from exc
    return value.lower()


def true_int(value: Any, label: str, *, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise EvidenceError(f"{label} must be an integer >= {minimum}")
    return value


def finite(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise EvidenceError(f"{label} must be numeric")
    result = float(value)
    if not math.isfinite(result):
        raise EvidenceError(f"{label} must be finite")
    return result


def outcome(own: float, rival: float) -> str:
    if own > rival:
        return "win"
    if own < rival:
        return "loss"
    return "tie"


def _identity(game: Mapping[str, Any], label: str) -> tuple[str, int, int]:
    opponent = game.get("opponent")
    seed = game.get("seed")
    seat = game.get("candidate_seat")
    if not isinstance(opponent, str) or not opponent.strip():
        raise EvidenceError(f"{label} opponent must be a nonempty string")
    if type(seed) is not int or seed < 0:
        raise EvidenceError(f"{label} seed must be a nonnegative integer")
    if type(seat) is not int or seat not in (0, 1):
        raise EvidenceError(f"{label} candidate_seat must be 0 or 1")
    return opponent, seed, seat


def _scores(game: Mapping[str, Any], key: tuple[str, int, int], label: str) -> tuple[float, float]:
    scores = game.get("scores")
    bank = game.get("bank_snapshot")
    if not isinstance(scores, list) or len(scores) != 2:
        raise EvidenceError(f"{label} cell {key} scores must be a two-element list")
    if not isinstance(bank, list) or len(bank) != 2:
        raise EvidenceError(f"{label} cell {key} bank_snapshot must be a two-element list")
    score_values = tuple(finite(value, f"{label} score {key}") for value in scores)
    bank_values = tuple(finite(value, f"{label} bank {key}") for value in bank)
    if score_values != bank_values:
        raise EvidenceError(f"{label} cell {key} scores differ from terminal bank")
    return score_values


def _index_report(
    report: Mapping[str, Any],
    label: str,
    *,
    expected_episode_steps: int,
) -> dict[tuple[str, int, int], dict[str, Any]]:
    if not isinstance(report, Mapping):
        raise EvidenceError(f"{label} report must be an object")
    progress = report.get("progress")
    games = report.get("games")
    if not isinstance(progress, Mapping) or progress.get("state") != "complete":
        raise EvidenceError(f"{label} is not a complete final report")
    if not isinstance(games, list) or not games:
        raise EvidenceError(f"{label} games must be a nonempty list")
    planned = true_int(progress.get("planned_games"), f"{label} planned_games", minimum=1)
    recorded = true_int(progress.get("recorded_games"), f"{label} recorded_games", minimum=1)
    if planned != recorded or recorded != len(games):
        raise EvidenceError(f"{label} progress/game cardinality mismatch")

    output: dict[tuple[str, int, int], dict[str, Any]] = {}
    for offset, raw in enumerate(games):
        if not isinstance(raw, dict):
            raise EvidenceError(f"{label} game {offset} must be an object")
        key = _identity(raw, f"{label} game {offset}")
        if key in output:
            raise EvidenceError(f"{label} has duplicate paired cell {key}")
        if raw.get("status") != "complete" or raw.get("failure") is not None:
            raise EvidenceError(f"{label} cell {key} is not complete")
        episode_steps = true_int(
            raw.get("episode_steps"), f"{label} episode_steps {key}", minimum=2
        )
        steps = true_int(raw.get("steps"), f"{label} steps {key}", minimum=1)
        action_count = true_int(
            raw.get("candidate_action_count"),
            f"{label} candidate_action_count {key}",
            minimum=1,
        )
        if episode_steps != expected_episode_steps or steps != expected_episode_steps - 1:
            raise EvidenceError(
                f"{label} cell {key} lacks full {expected_episode_steps}/{expected_episode_steps - 1} lifecycle"
            )
        if action_count != steps:
            raise EvidenceError(f"{label} cell {key} action count differs from steps")
        _scores(raw, key, label)
        digest(raw.get("candidate_action_sha256"), f"{label} action SHA-256 {key}")
        digest(raw.get("trace_sha256"), f"{label} trace SHA-256 {key}")
        output[key] = raw
    return output


def _report_binding(control: Mapping[str, Any], candidate: Mapping[str, Any]) -> dict[str, Any]:
    left = digest(control.get("evaluator_sha256"), "control evaluator SHA-256")
    right = digest(candidate.get("evaluator_sha256"), "candidate evaluator SHA-256")
    if left != right:
        raise EvidenceError("control/candidate evaluator SHA-256 mismatch")

    # Bind optional immutable panel descriptors whenever the evaluator emits them.
    equal_fields: dict[str, Any] = {}
    for field in ("engine", "configuration", "opponents", "seeds", "rng_seed"):
        left_present = field in control
        right_present = field in candidate
        if left_present != right_present:
            raise EvidenceError(f"control/candidate presence mismatch for {field}")
        if left_present:
            if control[field] != candidate[field]:
                raise EvidenceError(f"control/candidate {field} mismatch")
            equal_fields[field] = control[field]
    return {
        "evaluator_sha256": left,
        "equal_optional_fields": sorted(equal_fields),
        "optional_fields_sha256": canonical_sha256(equal_fields),
    }


def _descriptor_grid(
    report: Mapping[str, Any],
    actual: set[tuple[str, int, int]],
) -> dict[str, Any]:
    """Bind an optional dynamic opponent×seed×seat grid to retained cells."""
    seeds_present = "seeds" in report
    opponents_present = "opponents" in report
    if seeds_present != opponents_present:
        raise EvidenceError("panel descriptors must provide seeds and opponents together")
    if not seeds_present:
        return {
            "bound": False,
            "reason": "seeds_and_opponents_not_reported",
            "actual_cells": len(actual),
        }

    raw_seeds = report["seeds"]
    if not isinstance(raw_seeds, list) or not raw_seeds:
        raise EvidenceError("panel seeds must be a nonempty list")
    seeds: list[int] = []
    for offset, value in enumerate(raw_seeds):
        seeds.append(true_int(value, f"panel seeds[{offset}]"))
    if len(set(seeds)) != len(seeds):
        raise EvidenceError("panel seeds contain duplicates")

    raw_opponents = report["opponents"]
    if isinstance(raw_opponents, Mapping):
        opponent_values = list(raw_opponents)
    elif isinstance(raw_opponents, list):
        opponent_values = raw_opponents
    else:
        raise EvidenceError("panel opponents must be an object or list")
    opponents: list[str] = []
    for offset, value in enumerate(opponent_values):
        if not isinstance(value, str) or not value.strip():
            raise EvidenceError(f"panel opponents[{offset}] must be a nonempty string")
        opponents.append(value)
    if not opponents or len(set(opponents)) != len(opponents):
        raise EvidenceError("panel opponents must be nonempty and unique")

    expected = {
        (opponent, seed, seat)
        for opponent in opponents
        for seed in seeds
        for seat in (0, 1)
    }
    if actual != expected:
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        raise EvidenceError(
            "retained cells do not match descriptor opponent×seed×seat grid: "
            f"missing={missing!r}, extra={extra!r}"
        )
    descriptor = {
        "opponents": sorted(opponents),
        "seeds": sorted(seeds),
        "candidate_seats": [0, 1],
    }
    return {
        "bound": True,
        "expected_cells": len(expected),
        "descriptor_sha256": canonical_sha256(descriptor),
        **descriptor,
    }


def _mean(values: Sequence[float]) -> float | None:
    return statistics.mean(values) if values else None


def _median(values: Sequence[float]) -> float | None:
    return statistics.median(values) if values else None


def aggregate(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    own = [float(row["own_cash_delta"]) for row in rows]
    rival = [float(row["rival_cash_delta"]) for row in rows]
    margins = [float(row["margin_delta"]) for row in rows]
    return {
        "cells": len(rows),
        "action_changed_cells": sum(bool(row["candidate_action_changed"]) for row in rows),
        "trace_changed_cells": sum(bool(row["trace_changed"]) for row in rows),
        "mean_own_cash_delta": _mean(own),
        "median_own_cash_delta": _median(own),
        "min_own_cash_delta": min(own) if own else None,
        "max_own_cash_delta": max(own) if own else None,
        "total_own_cash_delta": sum(own),
        "positive_own_cells": sum(value > 0 for value in own),
        "zero_own_cells": sum(value == 0 for value in own),
        "negative_own_cells": sum(value < 0 for value in own),
        "mean_rival_cash_delta": _mean(rival),
        "mean_margin_delta": _mean(margins),
        "min_margin_delta": min(margins) if margins else None,
        "positive_margin_cells": sum(value > 0 for value in margins),
        "zero_margin_cells": sum(value == 0 for value in margins),
        "negative_margin_cells": sum(value < 0 for value in margins),
        "new_losses": sum(bool(row["new_loss"]) for row in rows),
        "lost_wins": sum(bool(row["lost_win"]) for row in rows),
    }


def _group(
    rows: Sequence[dict[str, Any]],
    fields: Sequence[str],
) -> dict[str, dict[str, Any]]:
    buckets: dict[tuple[Any, ...], list[dict[str, Any]]] = {}
    for row in rows:
        key = tuple(row[field] for field in fields)
        buckets.setdefault(key, []).append(row)
    return {
        "|".join(str(value) for value in key): aggregate(bucket)
        for key, bucket in sorted(buckets.items(), key=lambda item: tuple(map(str, item[0])))
    }


def assess(
    control_report: Mapping[str, Any],
    candidate_report: Mapping[str, Any],
    *,
    expected_episode_steps: int = EXPECTED_EPISODE_STEPS,
) -> dict[str, Any]:
    """Re-derive matched-cell evidence and return an admission receipt."""
    if type(expected_episode_steps) is not int or expected_episode_steps < 2:
        raise EvidenceError("expected_episode_steps must be an integer >= 2")
    binding = _report_binding(control_report, candidate_report)
    control = _index_report(
        control_report, "control", expected_episode_steps=expected_episode_steps
    )
    candidate = _index_report(
        candidate_report, "candidate", expected_episode_steps=expected_episode_steps
    )
    if set(control) != set(candidate):
        missing = sorted(set(control) - set(candidate))
        extra = sorted(set(candidate) - set(control))
        raise EvidenceError(
            f"control/candidate paired grid mismatch: missing={missing!r}, extra={extra!r}"
        )
    descriptor_grid = _descriptor_grid(control_report, set(control))

    rows: list[dict[str, Any]] = []
    for key in sorted(control):
        opponent, seed, seat = key
        left = control[key]
        right = candidate[key]
        left_episode = true_int(left.get("episode_steps"), f"control episode_steps {key}")
        right_episode = true_int(right.get("episode_steps"), f"candidate episode_steps {key}")
        left_steps = true_int(left.get("steps"), f"control steps {key}")
        right_steps = true_int(right.get("steps"), f"candidate steps {key}")
        if (left_episode, left_steps) != (right_episode, right_steps):
            raise EvidenceError(f"control/candidate lifecycle mismatch for {key}")

        left_scores = _scores(left, key, "control")
        right_scores = _scores(right, key, "candidate")
        control_own = left_scores[seat]
        candidate_own = right_scores[seat]
        control_rival = left_scores[1 - seat]
        candidate_rival = right_scores[1 - seat]
        own_delta = candidate_own - control_own
        rival_delta = candidate_rival - control_rival
        margin_delta = own_delta - rival_delta

        control_action = digest(
            left.get("candidate_action_sha256"), f"control action SHA-256 {key}"
        )
        candidate_action = digest(
            right.get("candidate_action_sha256"), f"candidate action SHA-256 {key}"
        )
        control_trace = digest(left.get("trace_sha256"), f"control trace SHA-256 {key}")
        candidate_trace = digest(right.get("trace_sha256"), f"candidate trace SHA-256 {key}")
        action_changed = control_action != candidate_action
        trace_changed = control_trace != candidate_trace
        if trace_changed and not action_changed:
            raise EvidenceError(f"trace changed without returned-action activation for {key}")
        if (own_delta != 0 or rival_delta != 0) and not action_changed:
            raise EvidenceError(f"terminal score changed without returned-action activation for {key}")

        before = outcome(control_own, control_rival)
        after = outcome(candidate_own, candidate_rival)
        rows.append(
            {
                "opponent": opponent,
                "seed": seed,
                "candidate_seat": seat,
                "control_own_cash": control_own,
                "candidate_own_cash": candidate_own,
                "own_cash_delta": own_delta,
                "control_rival_cash": control_rival,
                "candidate_rival_cash": candidate_rival,
                "rival_cash_delta": rival_delta,
                "control_margin": control_own - control_rival,
                "candidate_margin": candidate_own - candidate_rival,
                "margin_delta": margin_delta,
                "control_outcome": before,
                "candidate_outcome": after,
                "new_loss": before != "loss" and after == "loss",
                "lost_win": before == "win" and after != "win",
                "control_candidate_action_sha256": control_action,
                "candidate_candidate_action_sha256": candidate_action,
                "candidate_action_changed": action_changed,
                "control_trace_sha256": control_trace,
                "candidate_trace_sha256": candidate_trace,
                "trace_changed": trace_changed,
            }
        )

    changed = [row for row in rows if row["candidate_action_changed"]]
    overall = aggregate(rows)
    changed_summary = aggregate(changed)
    negative_own = [row for row in changed if float(row["own_cash_delta"]) < 0]
    negative_margin = [row for row in changed if float(row["margin_delta"]) < 0]
    gates = {
        "candidate_action_activation": bool(changed),
        "nonnegative_own_every_changed_cell": bool(changed)
        and all(float(row["own_cash_delta"]) >= 0 for row in changed),
        "strict_positive_own_some_changed_cell": any(
            float(row["own_cash_delta"]) > 0 for row in changed
        ),
        "nonnegative_margin_every_changed_cell": bool(changed)
        and all(float(row["margin_delta"]) >= 0 for row in changed),
        "zero_new_losses": all(not bool(row["new_loss"]) for row in changed),
        "zero_lost_wins": all(not bool(row["lost_win"]) for row in changed),
    }
    if not gates["candidate_action_activation"]:
        verdict = "INACTIVE"
    elif all(gates.values()):
        verdict = "ADMIT"
    else:
        verdict = "REJECT"

    result = {
        "schema_version": SCHEMA_VERSION,
        "operation": OPERATION,
        "policy_id": POLICY_ID,
        "verdict": verdict,
        "input_binding": binding,
        "descriptor_grid": descriptor_grid,
        "expected_episode_steps": expected_episode_steps,
        "paired_cells": len(rows),
        "gates": gates,
        "overall": overall,
        "changed_cells": changed_summary,
        "by_opponent_seat": _group(rows, ("opponent", "candidate_seat")),
        "by_seed": _group(rows, ("seed",)),
        "negative_own_changed_cells": negative_own,
        "negative_margin_changed_cells": negative_margin,
        "cells": rows,
        "promotion_authorized": False,
        "provider_action_authorized": False,
        "hosted_leaderboard_claim": False,
        "upstream_source_custody_required": True,
    }
    result["receipt_sha256"] = canonical_sha256(result)
    return result


def render_markdown(report: Mapping[str, Any]) -> str:
    gates = report["gates"]
    overall = report["overall"]
    changed = report["changed_cells"]
    lines = [
        "# TITAN V3 paired-cell tail admission",
        "",
        f"- Operation: `{report['operation']}`",
        f"- Policy: `{report['policy_id']}`",
        f"- Verdict: **{report['verdict']}**",
        f"- Paired cells: **{report['paired_cells']}**",
        f"- Action-changed cells: **{changed['cells']}**",
        f"- Mean TITAN own-cash delta: **{overall['mean_own_cash_delta']:.3f}**",
        f"- Minimum changed-cell TITAN own-cash delta: **{changed['min_own_cash_delta']}**",
        f"- Minimum changed-cell margin delta: **{changed['min_margin_delta']}**",
        "",
        "## Gates",
        "",
        "| Gate | Pass |",
        "|---|---|",
    ]
    for name, passed in gates.items():
        lines.append(f"| `{name}` | {'PASS' if passed else 'FAIL'} |")
    lines += [
        "",
        "## Regressing changed cells",
        "",
        "| Opponent | Seed | Seat | Own delta | Margin delta | Outcome |",
        "|---|---:|---:|---:|---:|---|",
    ]
    regressions: dict[tuple[str, int, int], Mapping[str, Any]] = {}
    for row in list(report["negative_own_changed_cells"]) + list(
        report["negative_margin_changed_cells"]
    ):
        regressions[(row["opponent"], row["seed"], row["candidate_seat"])] = row
    if regressions:
        for key in sorted(regressions):
            row = regressions[key]
            lines.append(
                f"| `{row['opponent']}` | {row['seed']} | {row['candidate_seat']} | "
                f"{row['own_cash_delta']:.3f} | {row['margin_delta']:.3f} | "
                f"`{row['control_outcome']}→{row['candidate_outcome']}` |"
            )
    else:
        lines.append("| — | — | — | — | — | — |")
    lines += [
        "",
        "This is a fail-closed development evidence gate. It does not authorize promotion, provider actions, or a Kaggle submission.",
        "",
    ]
    return "\n".join(lines)


def write_json(path: Path, value: Any) -> None:
    Path(path).write_text(
        json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description=__doc__)
    value.add_argument("--control", type=Path, required=True)
    value.add_argument("--candidate", type=Path, required=True)
    value.add_argument("--output", type=Path, required=True)
    value.add_argument("--markdown", type=Path)
    value.add_argument("--expected-episode-steps", type=int, default=EXPECTED_EPISODE_STEPS)
    return value


def main(argv: Sequence[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        report = assess(
            strict_load(args.control, "control"),
            strict_load(args.candidate, "candidate"),
            expected_episode_steps=args.expected_episode_steps,
        )
    except EvidenceError as exc:
        raise SystemExit(f"evidence error: {exc}") from exc
    write_json(args.output, report)
    if args.markdown is not None:
        args.markdown.write_text(render_markdown(report), encoding="utf-8")
    print(
        json.dumps(
            {
                "verdict": report["verdict"],
                "gates": report["gates"],
                "receipt_sha256": report["receipt_sha256"],
            },
            sort_keys=True,
        )
    )
    return 0 if report["verdict"] == "ADMIT" else 1


if __name__ == "__main__":
    raise SystemExit(main())
