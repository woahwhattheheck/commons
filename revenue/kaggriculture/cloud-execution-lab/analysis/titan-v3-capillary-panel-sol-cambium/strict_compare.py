# SPDX-License-Identifier: Apache-2.0
"""Add exact W/T/L non-regression to the repaired Capillary classifier."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

import compare as base

OPERATION = "TITAN-V3-PANEL-WTL-NONREGRESSION-GATE-20260910-02"
WORKFLOW = ".github/workflows/titan-v3-capillary-panel-sol-cambium.yml"


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


def _rank(outcome: str) -> int:
    return {"loss": -1, "tie": 0, "win": 1}[outcome]


def _sha256(path: Path, label: str) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError as exc:
        raise base.CompareError(
            f"cannot bind {label} at {path}: {type(exc).__name__}: {exc}"
        ) from exc


def classify(
    control: Mapping[str, Any],
    candidate: Mapping[str, Any],
    audit: Mapping[str, Any],
    evaluator_receipt: Mapping[str, Any],
) -> dict[str, Any]:
    """Compose the owner classifier and forbid every W/T/L regression."""
    report = base.classify(control, candidate, audit, evaluator_receipt)

    control_games = {_key(game): game for game in control["games"]}
    candidate_games = {_key(game): game for game in candidate["games"]}
    if set(control_games) != set(candidate_games):
        # The inherited validator proves this today. Retain the invariant here
        # so a future parent refactor cannot silently weaken outcome custody.
        raise base.CompareError("outcome gate panel cell set drift")

    report_cells = {
        (row["opponent"], row["seed"], row["candidate_seat"]): row
        for row in report["cells"]
    }
    if set(report_cells) != set(control_games):
        raise base.CompareError("outcome gate inherited cell receipt drift")

    transitions: dict[str, int] = {}
    control_counts = {"win": 0, "tie": 0, "loss": 0}
    candidate_counts = {"win": 0, "tie": 0, "loss": 0}
    new_losses = 0
    lost_wins = 0
    outcome_regressions = 0
    outcome_improvements = 0

    for key in sorted(control_games):
        _opponent, _seed, seat = key
        left = control_games[key]
        right = candidate_games[key]
        left_scores = [
            base.finite(value, f"control outcome score {key}")
            for value in left["scores"]
        ]
        right_scores = [
            base.finite(value, f"candidate outcome score {key}")
            for value in right["scores"]
        ]
        control_outcome = _outcome(left_scores[seat], left_scores[1 - seat])
        candidate_outcome = _outcome(
            right_scores[seat], right_scores[1 - seat]
        )
        control_counts[control_outcome] += 1
        candidate_counts[candidate_outcome] += 1
        transition = f"{control_outcome}->{candidate_outcome}"
        transitions[transition] = transitions.get(transition, 0) + 1

        new_loss = (
            candidate_outcome == "loss" and control_outcome != "loss"
        )
        lost_win = control_outcome == "win" and candidate_outcome != "win"
        outcome_delta = _rank(candidate_outcome) - _rank(control_outcome)
        outcome_regression = outcome_delta < 0
        outcome_improvement = outcome_delta > 0
        new_losses += int(new_loss)
        lost_wins += int(lost_win)
        outcome_regressions += int(outcome_regression)
        outcome_improvements += int(outcome_improvement)

        report_cells[key].update(
            {
                "control_outcome": control_outcome,
                "candidate_outcome": candidate_outcome,
                "outcome_transition": transition,
                "outcome_rank_delta": outcome_delta,
                "new_loss": new_loss,
                "lost_win": lost_win,
                "outcome_regression": outcome_regression,
                "outcome_improvement": outcome_improvement,
            }
        )

    metrics = report["metrics"]
    metrics.update(
        {
            "control_wins": control_counts["win"],
            "control_ties": control_counts["tie"],
            "control_losses": control_counts["loss"],
            "candidate_wins": candidate_counts["win"],
            "candidate_ties": candidate_counts["tie"],
            "candidate_losses": candidate_counts["loss"],
            "new_losses": new_losses,
            "lost_wins": lost_wins,
            "outcome_regressions": outcome_regressions,
            "outcome_improvements": outcome_improvements,
        }
    )
    criteria = report["criteria"]
    criteria.update(
        {
            "no_new_losses": new_losses == 0,
            "no_lost_wins": lost_wins == 0,
            "no_wtl_outcome_regressions": outcome_regressions == 0,
        }
    )
    report["advance"] = all(criteria.values())
    report["verdict"] = "advance" if report["advance"] else "reject"

    here = Path(__file__).resolve()
    repository = here.parents[5]
    report["identity"].update(
        {
            "inherited_classifier_sha256": _sha256(
                Path(base.__file__).resolve(), "inherited classifier"
            ),
            "outcome_classifier_sha256": _sha256(
                here, "outcome classifier"
            ),
            "outcome_contracts_sha256": _sha256(
                here.with_name("test_strict_compare.py"),
                "outcome contracts",
            ),
            "outcome_workflow_sha256": _sha256(
                repository / WORKFLOW, "outcome workflow"
            ),
        }
    )
    report["outcome_binding"] = {
        "operation": OPERATION,
        "valid": True,
        "objective_order": [
            "candidate own cash",
            "head-to-head margin",
            "W/T/L non-regression",
        ],
        "rule": (
            "no paired control win may become a tie or loss and no paired "
            "control tie may become a loss"
        ),
        "transitions": dict(sorted(transitions.items())),
    }
    return report


def markdown(report: Mapping[str, Any]) -> str:
    text = base.markdown(report).rstrip()
    metrics = report["metrics"]
    transitions = report["outcome_binding"]["transitions"]
    lines = [
        text,
        "",
        "## W/T/L non-regression",
        "",
        "| Metric | Value |",
        "|---|---:|",
        (
            "| Control W / T / L | "
            f"{metrics['control_wins']} / {metrics['control_ties']} / "
            f"{metrics['control_losses']} |"
        ),
        (
            "| Candidate W / T / L | "
            f"{metrics['candidate_wins']} / {metrics['candidate_ties']} / "
            f"{metrics['candidate_losses']} |"
        ),
        f"| New losses | {metrics['new_losses']} |",
        f"| Lost wins | {metrics['lost_wins']} |",
        f"| Outcome regressions | {metrics['outcome_regressions']} |",
        f"| Outcome improvements | {metrics['outcome_improvements']} |",
        "",
        "| Transition | Cells |",
        "|---|---:|",
    ]
    lines.extend(f"| `{name}` | {count} |" for name, count in transitions.items())
    lines += [
        "",
        "ADVANCE requires zero new losses, zero lost wins, and zero W/T/L "
        "rank regressions in addition to every inherited causal, own-cash, "
        "and margin gate.",
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
