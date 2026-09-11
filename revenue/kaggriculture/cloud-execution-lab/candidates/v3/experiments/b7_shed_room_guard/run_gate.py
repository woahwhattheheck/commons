#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Run the exact B7 shed-room guard against its ready-V3.1 R04 parent.

The gate first runs baseline-vs-baseline on the same frozen seed x seat panel, then
B7-vs-baseline.  B7 returns the parent action object until it actually rewrites a
lossy DROP, so a candidate trace hash that differs from the matching control cell is
a direct live-activation witness.  Scores are paired to the same control cell to
report delta-own, delta-rival, and delta-margin separately.

This is an offline official-interpreter screen, not a hosted Kaggle result and not a
promotion decision.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import statistics
import subprocess
import sys

ENGINE_REF = "28b6d8af3ce73926b3d0fda1410c1ddd8384ab8c"
SEEDS = tuple(range(2611151001, 2611151009))
LAB_REL = Path("revenue/kaggriculture/cloud-execution-lab")
V3_REL = LAB_REL / "candidates" / "v3"
EVALUATOR_REL = LAB_REL / "reference" / "evaluator" / "evaluate.py"
ENGINE_DIR_REL = LAB_REL / "reference" / "engine"
CANDIDATE_REL = V3_REL / "experiments" / "b7_shed_room_guard" / "candidate.py"
BASELINE_REL = V3_REL / "experiments" / "b7_shed_room_guard" / "baseline.py"
TRANSFORM_REL = V3_REL / "experiments" / "b7_shed_room_guard.py"


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(args: list[object], *, cwd: Path) -> None:
    print("+", " ".join(str(value) for value in args), flush=True)
    subprocess.run([str(value) for value in args], cwd=cwd, check=True)


def run_evaluator(
    repo: Path,
    *,
    candidate: Path,
    opponent: Path,
    label: str,
    output: Path,
    recheck_first: bool,
) -> dict:
    args: list[object] = [
        sys.executable,
        "-B",
        repo / EVALUATOR_REL,
        "--engine-dir",
        repo / ENGINE_DIR_REL,
        "--candidate",
        candidate,
        "--opponent",
        f"{label}={opponent}",
        "--seeds",
        ",".join(str(seed) for seed in SEEDS),
        "--game-timeout",
        "180",
        "--output",
        output,
    ]
    if recheck_first:
        args.append("--recheck-first")
    run(args, cwd=repo)
    report = json.loads(output.read_text(encoding="utf-8"))
    if report.get("engine_ref") != ENGINE_REF:
        raise AssertionError(f"evaluator engine ref drift: {report.get('engine_ref')!r}")
    return report


def exact_cells(report: dict, label: str) -> dict[tuple[int, int], dict]:
    games = report.get("games")
    if not isinstance(games, list):
        raise AssertionError("evaluator report has no games array")
    expected = {(seed, seat) for seed in SEEDS for seat in (0, 1)}
    rows: dict[tuple[int, int], dict] = {}
    for game in games:
        if not isinstance(game, dict):
            raise AssertionError("evaluator game row is not an object")
        if game.get("opponent") != label:
            raise AssertionError(f"unexpected opponent label {game.get('opponent')!r}")
        seed, seat = game.get("seed"), game.get("candidate_seat")
        key = (seed, seat)
        if key not in expected or key in rows:
            raise AssertionError(f"unexpected/duplicate evaluator cell: {key!r}")
        if game.get("status") != "complete" or game.get("failure") is not None:
            raise AssertionError(f"incomplete evaluator cell {key}: {game.get('failure')!r}")
        scores = game.get("scores")
        if not (
            isinstance(scores, list)
            and len(scores) == 2
            and all(type(value) in (int, float) for value in scores)
        ):
            raise AssertionError(f"invalid scores for {key}: {scores!r}")
        trace = game.get("trace_sha256")
        if not isinstance(trace, str) or len(trace) != 64:
            raise AssertionError(f"invalid trace hash for {key}: {trace!r}")
        rows[key] = game
    if set(rows) != expected:
        raise AssertionError(f"missing evaluator cells: {sorted(expected - set(rows))}")
    return rows


def margin(game: dict) -> float:
    seat = game["candidate_seat"]
    if type(seat) is not int or seat not in (0, 1):
        raise AssertionError(f"invalid candidate seat: {seat!r}")
    scores = game["scores"]
    return float(scores[seat]) - float(scores[1 - seat])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    repo = args.repo_root.resolve()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    candidate = repo / CANDIDATE_REL
    baseline = repo / BASELINE_REL
    transform = repo / TRANSFORM_REL
    for required in (candidate, baseline, transform, repo / EVALUATOR_REL):
        if not required.is_file():
            raise FileNotFoundError(required)

    control_path = output_dir / "b7-control-baseline-vs-baseline.json"
    candidate_path = output_dir / "b7-candidate-vs-baseline.json"
    control_report = run_evaluator(
        repo,
        candidate=baseline,
        opponent=baseline,
        label="b7_baseline_identity",
        output=control_path,
        recheck_first=True,
    )
    candidate_report = run_evaluator(
        repo,
        candidate=candidate,
        opponent=baseline,
        label="b7_parent",
        output=candidate_path,
        recheck_first=True,
    )

    for name, report in (("control", control_report), ("candidate", candidate_report)):
        replay = report.get("reproducibility") or {}
        if replay.get("same_trace_and_scores") is not True:
            raise AssertionError(f"{name} first-cell reproducibility check failed: {replay!r}")

    controls = exact_cells(control_report, "b7_baseline_identity")
    candidates = exact_cells(candidate_report, "b7_parent")

    cells = []
    for key in sorted(controls):
        control = controls[key]
        candidate_row = candidates[key]
        control_seat = control["candidate_seat"]
        candidate_seat = candidate_row["candidate_seat"]
        if control_seat != candidate_seat:
            raise AssertionError(f"seat mismatch for {key}: {control_seat} vs {candidate_seat}")
        control_margin = margin(control)
        if control_margin != 0.0:
            raise AssertionError(f"baseline identity cell {key} is not an exact tie: {control_margin}")
        seat = candidate_seat
        control_scores = control["scores"]
        candidate_scores = candidate_row["scores"]
        own_delta = float(candidate_scores[seat]) - float(control_scores[seat])
        rival_delta = float(candidate_scores[1 - seat]) - float(control_scores[1 - seat])
        margin_delta = margin(candidate_row) - control_margin
        trace_changed = candidate_row["trace_sha256"] != control["trace_sha256"]
        if not trace_changed and (own_delta != 0.0 or rival_delta != 0.0 or margin_delta != 0.0):
            raise AssertionError(f"score changed without action/bank trace change in {key}")
        cells.append(
            {
                "seed": key[0],
                "candidate_seat": seat,
                "trace_changed": trace_changed,
                "control_trace_sha256": control["trace_sha256"],
                "candidate_trace_sha256": candidate_row["trace_sha256"],
                "control_scores": control_scores,
                "candidate_scores": candidate_scores,
                "delta_own": own_delta,
                "delta_rival": rival_delta,
                "delta_margin": margin_delta,
            }
        )

    margin_deltas = [row["delta_margin"] for row in cells]
    own_deltas = [row["delta_own"] for row in cells]
    rival_deltas = [row["delta_rival"] for row in cells]
    changed = [row for row in cells if row["trace_changed"]]
    score_changed = [row for row in cells if row["delta_margin"] != 0.0]
    summary = {
        "scheduled": len(cells),
        "trace_changed_cells": len(changed),
        "score_changed_cells": len(score_changed),
        "wins": sum(value > 0 for value in margin_deltas),
        "ties": sum(value == 0 for value in margin_deltas),
        "losses": sum(value < 0 for value in margin_deltas),
        "mean_delta_own": statistics.mean(own_deltas),
        "mean_delta_rival": statistics.mean(rival_deltas),
        "mean_delta_margin": statistics.mean(margin_deltas),
        "median_delta_margin": statistics.median(margin_deltas),
        "min_delta_margin": min(margin_deltas),
        "max_delta_margin": max(margin_deltas),
    }
    if not changed:
        disposition = "inactive_zero_trace_changes"
    elif summary["mean_delta_margin"] > 0:
        disposition = "active_positive_mean"
    elif summary["mean_delta_margin"] == 0:
        disposition = "active_zero_mean"
    else:
        disposition = "active_negative_mean"

    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()
    receipt = {
        "schema": "titan-v31-b7-shed-room-gate/v1",
        "truth_boundary": (
            "Exact offline official-interpreter paired screen only; not a hosted Kaggle score, "
            "not a default/package promotion decision. Trace divergence is an activation witness, "
            "not proof that saved units were eventually monetized."
        ),
        "head": head,
        "engine_ref": ENGINE_REF,
        "seeds": list(SEEDS),
        "source": {
            "candidate": CANDIDATE_REL.as_posix(),
            "candidate_sha256": sha256_file(candidate),
            "baseline": BASELINE_REL.as_posix(),
            "baseline_sha256": sha256_file(baseline),
            "transform": TRANSFORM_REL.as_posix(),
            "transform_sha256": sha256_file(transform),
            "evaluator_sha256": sha256_file(repo / EVALUATOR_REL),
        },
        "summary": summary,
        "disposition": disposition,
        "cells": cells,
        "raw": {
            "control": control_path.name,
            "candidate": candidate_path.name,
        },
    }
    receipt_path = output_dir / "b7-execution-receipt.json"
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("B7_GATE_RESULT", json.dumps({"disposition": disposition, **summary}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
