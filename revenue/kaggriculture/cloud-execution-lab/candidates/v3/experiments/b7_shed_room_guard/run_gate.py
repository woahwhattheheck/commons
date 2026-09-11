#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Cheap current-root B7 activation/economics screen.

Runs exact shipped-8e3 R04 baseline-vs-baseline, then B7-wrapped current R04
against the same baseline on the same 8 seeds x both seats.  This is offline
official-interpreter evidence only and cannot promote a default or package.
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
GATE_REL = V3_REL / "experiments" / "b7_shed_room_guard"
CANDIDATE_REL = GATE_REL / "candidate.py"
BASELINE_REL = GATE_REL / "baseline.py"
TRANSFORM_REL = V3_REL / "experiments" / "b7_shed_room_guard.py"


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(command: list[object], cwd: Path) -> None:
    print("+", " ".join(str(value) for value in command), flush=True)
    subprocess.run([str(value) for value in command], cwd=cwd, check=True)


def fingerprint(path: Path) -> dict:
    return {"entry": path.name, "callable": "agent", "sha256": sha256_file(path)}


def run_evaluator(repo: Path, candidate: Path, opponent: Path, label: str, output: Path) -> dict:
    command: list[object] = [
        sys.executable, "-B", repo / EVALUATOR_REL,
        "--engine-dir", repo / ENGINE_DIR_REL,
        "--candidate", candidate,
        "--opponent", f"{label}={opponent}",
        "--seeds", ",".join(str(seed) for seed in SEEDS),
        "--game-timeout", "180",
        "--recheck-first",
        "--output", output,
    ]
    run(command, repo)
    report = json.loads(output.read_text(encoding="utf-8"))
    if report.get("schema_version") != 1 or report.get("engine_ref") != ENGINE_REF:
        raise AssertionError("official evaluator schema/engine drift")
    if report.get("evaluator_sha256") != sha256_file(repo / EVALUATOR_REL):
        raise AssertionError("evaluator fingerprint mismatch")
    if report.get("candidate") != fingerprint(candidate):
        raise AssertionError(("candidate fingerprint mismatch", report.get("candidate"), fingerprint(candidate)))
    opponents = report.get("opponents")
    if opponents != {label: fingerprint(opponent)}:
        raise AssertionError(("opponent fingerprint mismatch", opponents, {label: fingerprint(opponent)}))
    replay = report.get("reproducibility") or {}
    if replay.get("same_trace_and_scores") is not True:
        raise AssertionError(("first-cell replay failed", replay))
    return report


def exact_cells(report: dict, label: str) -> dict[tuple[int, int], dict]:
    expected = {(seed, seat) for seed in SEEDS for seat in (0, 1)}
    rows: dict[tuple[int, int], dict] = {}
    games = report.get("games")
    if not isinstance(games, list):
        raise AssertionError("missing games array")
    for game in games:
        if not isinstance(game, dict) or game.get("opponent") != label:
            raise AssertionError(("unexpected game/opponent", game))
        key = (game.get("seed"), game.get("candidate_seat"))
        if key not in expected or key in rows:
            raise AssertionError(("unexpected/duplicate cell", key))
        if game.get("status") != "complete" or game.get("failure") is not None:
            raise AssertionError(("incomplete cell", key, game.get("failure")))
        scores = game.get("scores")
        if not (isinstance(scores, list) and len(scores) == 2 and all(type(v) in (int, float) for v in scores)):
            raise AssertionError(("invalid scores", key, scores))
        trace = game.get("trace_sha256")
        if not isinstance(trace, str) or len(trace) != 64:
            raise AssertionError(("invalid trace", key, trace))
        rows[key] = game
    if set(rows) != expected:
        raise AssertionError(("missing cells", sorted(expected - set(rows))))
    return rows


def margin(game: dict) -> float:
    seat = game["candidate_seat"]
    return float(game["scores"][seat]) - float(game["scores"][1 - seat])


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
    for path in (candidate, baseline, transform, repo / EVALUATOR_REL):
        if not path.is_file():
            raise FileNotFoundError(path)

    control_path = output_dir / "b7-control.json"
    candidate_path = output_dir / "b7-candidate.json"
    control_report = run_evaluator(repo, baseline, baseline, "b7_currentroot_identity", control_path)
    candidate_report = run_evaluator(repo, candidate, baseline, "b7_currentroot_parent", candidate_path)
    controls = exact_cells(control_report, "b7_currentroot_identity")
    candidates = exact_cells(candidate_report, "b7_currentroot_parent")

    cells = []
    for key in sorted(controls):
        control = controls[key]
        changed = candidates[key]
        if control["candidate_seat"] != changed["candidate_seat"]:
            raise AssertionError(("seat mismatch", key))
        if margin(control) != 0.0:
            raise AssertionError(("identity control not tied", key, margin(control)))
        seat = changed["candidate_seat"]
        own = float(changed["scores"][seat]) - float(control["scores"][seat])
        rival = float(changed["scores"][1 - seat]) - float(control["scores"][1 - seat])
        delta = margin(changed)
        trace_changed = changed["trace_sha256"] != control["trace_sha256"]
        if not trace_changed and (own != 0.0 or rival != 0.0 or delta != 0.0):
            raise AssertionError(("score changed without trace change", key))
        cells.append({
            "seed": key[0], "candidate_seat": seat, "trace_changed": trace_changed,
            "delta_own": own, "delta_rival": rival, "delta_margin": delta,
            "control_trace_sha256": control["trace_sha256"],
            "candidate_trace_sha256": changed["trace_sha256"],
            "control_scores": control["scores"], "candidate_scores": changed["scores"],
        })

    deltas = [row["delta_margin"] for row in cells]
    own = [row["delta_own"] for row in cells]
    rival = [row["delta_rival"] for row in cells]
    summary = {
        "scheduled": len(cells),
        "trace_changed_cells": sum(row["trace_changed"] for row in cells),
        "score_changed_cells": sum(row["delta_margin"] != 0.0 for row in cells),
        "wins": sum(value > 0 for value in deltas),
        "ties": sum(value == 0 for value in deltas),
        "losses": sum(value < 0 for value in deltas),
        "mean_delta_own": statistics.mean(own),
        "mean_delta_rival": statistics.mean(rival),
        "mean_delta_margin": statistics.mean(deltas),
        "median_delta_margin": statistics.median(deltas),
        "min_delta_margin": min(deltas),
        "max_delta_margin": max(deltas),
    }
    if summary["trace_changed_cells"] == 0:
        disposition = "KILL_INACTIVE"
    elif summary["losses"] > 0:
        disposition = "HOLD_NEGATIVE_CELL"
    elif summary["mean_delta_margin"] > 0:
        disposition = "PASS_WIDEN_ONLY"
    else:
        disposition = "HOLD_NO_POSITIVE_MARGIN"

    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()
    receipt = {
        "schema": "titan-v31-b7-currentroot-gate/v1",
        "truth_boundary": "Offline official-interpreter cheap screen only; no default/package/Kaggle authority. PASS only earns current-successor/opponent-diverse widening.",
        "head": head,
        "engine_ref": ENGINE_REF,
        "seeds": list(SEEDS),
        "source": {
            "candidate": CANDIDATE_REL.as_posix(), "candidate_sha256": sha256_file(candidate),
            "baseline": BASELINE_REL.as_posix(), "baseline_sha256": sha256_file(baseline),
            "transform": TRANSFORM_REL.as_posix(), "transform_sha256": sha256_file(transform),
            "evaluator": EVALUATOR_REL.as_posix(), "evaluator_sha256": sha256_file(repo / EVALUATOR_REL),
        },
        "summary": summary,
        "disposition": disposition,
        "cells": cells,
        "raw": {"control": control_path.name, "candidate": candidate_path.name},
    }
    (output_dir / "b7-currentroot-receipt.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("B7_CURRENTROOT_RESULT", json.dumps({"disposition": disposition, **summary}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
