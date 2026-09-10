# SPDX-License-Identifier: Apache-2.0
"""Strengthen the Capillary panel with per-cell causality and win-facing gates."""
from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import statistics
from typing import Any, Mapping

import compare as base


def _key(game: Mapping[str, Any]) -> tuple[str, int, int]:
    return (
        str(game["opponent"]),
        int(game["seed"]),
        int(game["candidate_seat"]),
    )


def _outcome(own: float, rival: float) -> str:
    if own > rival:
        return "win"
    if own < rival:
        return "loss"
    return "tie"


def _outcome_rank(value: str) -> int:
    return {"loss": -1, "tie": 0, "win": 1}[value]


def _mean(values: list[float]) -> float:
    if not values:
        raise base.CompareError("cannot summarize an empty value set")
    return float(statistics.mean(values))


def classify(
    control: Mapping[str, Any],
    candidate: Mapping[str, Any],
    audit: Mapping[str, Any],
    evaluator_receipt: Mapping[str, Any],
) -> dict[str, Any]:
    """Run the inherited validator, then enforce causal and margin custody.

    The evaluator's full trace contains both returned actions, every interpreted
    bank snapshot, and the terminal observations. Therefore an equal tested
    action stream must have an equal trace and equal terminal scores. A changed
    tested action stream must also change the full trace because those exact
    action bytes are included in it. Any mismatch is evidence corruption or an
    uncontrolled source of nondeterminism, not candidate upside.
    """
    report = base.classify(control, candidate, audit, evaluator_receipt)

    control_games = {_key(game): game for game in control["games"]}
    candidate_games = {_key(game): game for game in candidate["games"]}
    if set(control_games) != set(candidate_games):
        # The inherited validator already proves this; retain a local invariant
        # so this module cannot silently become unsafe if its dependency changes.
        raise base.CompareError("strict gate panel cell set drift")

    cell_reports = {
        (row["opponent"], row["seed"], row["candidate_seat"]): row
        for row in report["cells"]
    }
    margin_strata: dict[tuple[str, int], list[float]] = defaultdict(list)
    new_losses = 0
    lost_wins = 0
    outcome_regressions = 0
    score_changed_cells = 0
    action_changed_score_unchanged_cells = 0

    for key in sorted(control_games):
        left = control_games[key]
        right = candidate_games[key]
        opponent, seed, seat = key

        action_changed = (
            left["candidate_action_sha256"]
            != right["candidate_action_sha256"]
        )
        trace_changed = left["trace_sha256"] != right["trace_sha256"]
        if action_changed != trace_changed:
            raise base.CompareError(
                f"candidate-action/full-trace causal mismatch at {key}: "
                f"action_changed={action_changed}, trace_changed={trace_changed}"
            )

        left_scores = tuple(float(value) for value in left["scores"])
        right_scores = tuple(float(value) for value in right["scores"])
        score_changed = left_scores != right_scores
        if not action_changed and score_changed:
            raise base.CompareError(
                f"action-identical cell changed terminal scores at {key}"
            )

        own_left = left_scores[seat]
        own_right = right_scores[seat]
        rival_left = left_scores[1 - seat]
        rival_right = right_scores[1 - seat]
        margin_delta = (own_right - rival_right) - (own_left - rival_left)
        margin_strata[(opponent, seat)].append(margin_delta)

        control_outcome = _outcome(own_left, rival_left)
        candidate_outcome = _outcome(own_right, rival_right)
        new_loss = candidate_outcome == "loss" and control_outcome != "loss"
        lost_win = control_outcome == "win" and candidate_outcome != "win"
        outcome_regression = (
            _outcome_rank(candidate_outcome) < _outcome_rank(control_outcome)
        )
        new_losses += int(new_loss)
        lost_wins += int(lost_win)
        outcome_regressions += int(outcome_regression)
        score_changed_cells += int(score_changed)
        action_changed_score_unchanged_cells += int(
            action_changed and not score_changed
        )

        row = cell_reports[key]
        row.update(
            {
                "trace_changed": trace_changed,
                "score_changed": score_changed,
                "control_trace_sha256": left["trace_sha256"],
                "candidate_trace_sha256": right["trace_sha256"],
                "control_outcome": control_outcome,
                "candidate_outcome": candidate_outcome,
                "new_loss": new_loss,
                "lost_win": lost_win,
                "outcome_regression": outcome_regression,
            }
        )

    strata_by_key = {
        (row["opponent"], row["candidate_seat"]): row
        for row in report["strata"]
    }
    for key, values in sorted(margin_strata.items()):
        row = strata_by_key[key]
        row.update(
            {
                "mean_margin_delta": _mean(values),
                "median_margin_delta": float(statistics.median(values)),
                "min_margin_delta": min(values),
                "max_margin_delta": max(values),
            }
        )

    metrics = report["metrics"]
    metrics.update(
        {
            "score_changed_cells": score_changed_cells,
            "action_changed_score_unchanged_cells": (
                action_changed_score_unchanged_cells
            ),
            "new_losses": new_losses,
            "lost_wins": lost_wins,
            "outcome_regressions": outcome_regressions,
        }
    )

    criteria = report["criteria"]
    criteria.update(
        {
            "per_cell_causal_binding_valid": True,
            "global_mean_margin_nonnegative": (
                metrics["mean_margin_delta"] >= 0
            ),
            "all_opponent_seat_margin_strata_nonnegative": all(
                row["mean_margin_delta"] >= 0 for row in report["strata"]
            ),
            "no_new_losses": new_losses == 0,
        }
    )
    report["advance"] = all(criteria.values())
    report["verdict"] = "advance" if report["advance"] else "reject"
    gate_files = {
        "strict_classifier_sha256": Path(__file__).resolve(),
        "inherited_classifier_sha256": Path(base.__file__).resolve(),
        "strict_contracts_sha256": Path(__file__).with_name(
            "test_strict_compare.py"
        ).resolve(),
    }
    for label, path in gate_files.items():
        try:
            report["identity"][label] = hashlib.sha256(path.read_bytes()).hexdigest()
        except OSError as exc:
            raise base.CompareError(
                f"cannot bind strict gate source {path}: {type(exc).__name__}: {exc}"
            ) from exc

    report["gate_revision"] = {
        "operation": "TITAN-V3-PANEL-CAUSAL-MARGIN-GATE-REPAIR-20260910-01",
        "causal_rule": (
            "candidate-action equality requires full-trace and both-score equality"
        ),
        "head_to_head_rules": [
            "global mean margin delta is nonnegative",
            "every opponent-by-seat mean margin delta is nonnegative",
            "no tie-or-win becomes a loss",
        ],
    }
    return report


def markdown(report: Mapping[str, Any]) -> str:
    text = base.markdown(report).rstrip()
    metrics = report["metrics"]
    lines = [
        text,
        "",
        "## Causal and head-to-head custody",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Score-changed cells | {metrics['score_changed_cells']} |",
        (
            "| Action-changed / score-unchanged cells | "
            f"{metrics['action_changed_score_unchanged_cells']} |"
        ),
        f"| New losses | {metrics['new_losses']} |",
        f"| Lost wins | {metrics['lost_wins']} |",
        f"| Outcome regressions | {metrics['outcome_regressions']} |",
        "",
        "| Opponent | Seat | Mean margin Δ | Median | Min | Max |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for row in report["strata"]:
        lines.append(
            f"| {row['opponent']} | {row['candidate_seat']} | "
            f"{row['mean_margin_delta']:+.6f} | "
            f"{row['median_margin_delta']:+.6f} | "
            f"{row['min_margin_delta']:+.6f} | "
            f"{row['max_margin_delta']:+.6f} |"
        )
    lines += [
        "",
        "Any candidate-action/full-trace mismatch or action-identical score "
        "change is INVALID and raises before a verdict is written.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--control", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--audit", type=Path, required=True)
    parser.add_argument("--evaluator-receipt", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--markdown", type=Path, required=True)
    args = parser.parse_args()
    report = classify(
        base.strict_json(args.control),
        base.strict_json(args.candidate),
        base.strict_json(args.audit),
        base.strict_json(args.evaluator_receipt),
    )
    base.atomic_text(
        args.output,
        json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n",
    )
    base.atomic_text(args.markdown, markdown(report))
    print(
        json.dumps(
            {
                "verdict": report["verdict"],
                "criteria": report["criteria"],
                "metrics": report["metrics"],
            },
            sort_keys=True,
        )
    )
    return 0 if report["advance"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
