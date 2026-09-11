#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Paired current-root activation/economics gate for Riot fert-daily sweep.

This evidence carrier compares the literal current V3.1 stack against the same
stack wrapped by the exact Riot donor. It uses observed control margins per
opponent/seed/seat; identical-agent self play is not assumed to have zero margin.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import statistics
import subprocess
import sys

PARENT_HEAD = "6e5e3c7cc5302d6db4b702cc4fd7c8ca721d7b8a"
CANONICAL_HEAD = "8e3d92a286806f9f9525973ee7d359b629a11487"
DONOR_COMMIT = "8638d0db7068f38966424c59181875d8b128a72a"
DONOR_BLOB = "cd6c1dd50a439f58bce9434db8d628ca8d6f978f"
ENGINE_REF = "28b6d8af3ce73926b3d0fda1410c1ddd8384ab8c"
RNG_SEED = 20260911
SEEDS = tuple(range(2611153001, 2611153009))
OPPONENTS = ("current_self", "arlene")
EXPECTED_KEYS = frozenset((opponent, seed, seat) for opponent in OPPONENTS for seed in SEEDS for seat in (0, 1))

LAB = Path("revenue/kaggriculture/cloud-execution-lab")
V3 = LAB / "candidates" / "v3"
GATE = V3 / "experiments" / "fert_daily_sweep_current_root"
BASELINE = GATE / "baseline.py"
CANDIDATE = GATE / "candidate.py"
DONOR = GATE / "donor.py"
EVALUATOR = LAB / "reference" / "evaluator" / "evaluate.py"
ENGINE = LAB / "reference" / "engine"
ARLENE = LAB / "reference" / "next-panel" / "vendor" / "arlene.py"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()


def fingerprint(path: Path) -> dict:
    return {"entry": path.name, "callable": "agent", "sha256": sha256(path)}


def strict_int(value, label: str) -> int:
    if type(value) is not int:
        raise AssertionError((label, "exact int required", value))
    return value


def finite_number(value, label: str) -> float:
    if type(value) not in (int, float) or not math.isfinite(float(value)):
        raise AssertionError((label, "finite non-bool number required", value))
    return float(value)


def strict_sha(value, label: str) -> str:
    if not isinstance(value, str) or len(value) != 64:
        raise AssertionError((label, "64-hex sha required", value))
    try:
        int(value, 16)
    except ValueError as exc:
        raise AssertionError((label, "64-hex sha required", value)) from exc
    return value


def run(command: list[object], cwd: Path) -> None:
    command = [str(value) for value in command]
    print("+", " ".join(command), flush=True)
    subprocess.run(command, cwd=cwd, check=True)


def run_evaluator(repo: Path, candidate: Path, output: Path) -> dict:
    command: list[object] = [
        sys.executable, "-B", repo / EVALUATOR,
        "--engine-dir", repo / ENGINE,
        "--candidate", candidate,
        "--opponent", f"current_self={repo / BASELINE}",
        "--opponent", f"arlene={repo / ARLENE}",
        "--seeds", ",".join(map(str, SEEDS)),
        "--rng-seed", str(RNG_SEED),
        "--game-timeout", "180",
        "--recheck-first",
        "--output", output,
    ]
    run(command, repo)
    return json.loads(output.read_text(encoding="utf-8"))


def strict_fingerprint(value, expected: dict, label: str) -> None:
    if not isinstance(value, dict):
        raise AssertionError((label, "fingerprint object required"))
    if value != expected:
        raise AssertionError((label, "fingerprint drift", value, expected))


def exact_cells(report: dict, candidate_path: Path, repo: Path, label: str) -> dict[tuple[str, int, int], dict]:
    if type(report.get("schema_version")) is not int or report.get("schema_version") != 1:
        raise AssertionError((label, "schema_version drift"))
    if report.get("engine_ref") != ENGINE_REF:
        raise AssertionError((label, "engine_ref drift", report.get("engine_ref")))
    if type(report.get("agent_rng_seed")) is not int or report.get("agent_rng_seed") != RNG_SEED:
        raise AssertionError((label, "agent_rng_seed drift", report.get("agent_rng_seed")))
    if report.get("seeds") != list(SEEDS) or any(type(seed) is not int for seed in report.get("seeds") or []):
        raise AssertionError((label, "seed metadata drift", report.get("seeds")))

    opponents = report.get("opponents")
    expected_opponents = {
        "current_self": fingerprint(repo / BASELINE),
        "arlene": fingerprint(repo / ARLENE),
    }
    if not isinstance(opponents, dict) or set(opponents) != set(expected_opponents):
        raise AssertionError((label, "opponent map drift", opponents))
    for name, expected in expected_opponents.items():
        strict_fingerprint(opponents[name], expected, f"{label}.opponents.{name}")
    strict_fingerprint(report.get("candidate"), fingerprint(candidate_path), f"{label}.candidate")

    reproducibility = report.get("reproducibility")
    if not isinstance(reproducibility, dict) or reproducibility.get("same_trace_and_scores") is not True:
        raise AssertionError((label, "reproducibility recheck failed", reproducibility))

    games = report.get("games")
    if not isinstance(games, list):
        raise AssertionError((label, "games array required"))
    rows: dict[tuple[str, int, int], dict] = {}
    for index, game in enumerate(games):
        if not isinstance(game, dict):
            raise AssertionError((label, index, "game object required"))
        if game.get("status") != "complete" or game.get("failure") is not None:
            raise AssertionError((label, index, "incomplete game", game.get("failure")))
        opponent = game.get("opponent")
        seed = strict_int(game.get("seed"), f"{label}[{index}].seed")
        seat = strict_int(game.get("candidate_seat"), f"{label}[{index}].candidate_seat")
        if opponent not in OPPONENTS or seed not in SEEDS or seat not in (0, 1):
            raise AssertionError((label, index, "cell identity drift", opponent, seed, seat))
        key = (opponent, seed, seat)
        if key in rows:
            raise AssertionError((label, "duplicate cell", key))
        scores = game.get("scores")
        if not isinstance(scores, list) or len(scores) != 2:
            raise AssertionError((label, key, "two scores required", scores))
        normalized = dict(game)
        normalized["scores"] = [
            finite_number(scores[0], f"{label}:{key}:score0"),
            finite_number(scores[1], f"{label}:{key}:score1"),
        ]
        normalized["trace_sha256"] = strict_sha(game.get("trace_sha256"), f"{label}:{key}:trace")
        rows[key] = normalized
    if frozenset(rows) != EXPECTED_KEYS:
        raise AssertionError((label, "exact Cartesian cell set mismatch", sorted(EXPECTED_KEYS - frozenset(rows)), sorted(frozenset(rows) - EXPECTED_KEYS)))
    return rows


def components(game: dict) -> tuple[float, float, float]:
    seat = strict_int(game["candidate_seat"], "candidate_seat")
    if seat not in (0, 1):
        raise AssertionError(("candidate_seat out of range", seat))
    own = finite_number(game["scores"][seat], "own")
    rival = finite_number(game["scores"][1 - seat], "rival")
    return own, rival, own - rival


def paired(control: dict, candidate: dict, opponent: str) -> tuple[dict, list[dict]]:
    cells = []
    for seed in SEEDS:
        for seat in (0, 1):
            key = (opponent, seed, seat)
            before, after = control[key], candidate[key]
            b_own, b_rival, b_margin = components(before)
            a_own, a_rival, a_margin = components(after)
            delta_own = a_own - b_own
            delta_rival = a_rival - b_rival
            delta_margin = a_margin - b_margin
            if not math.isclose(delta_margin, delta_own - delta_rival, rel_tol=0.0, abs_tol=1e-9):
                raise AssertionError(("paired arithmetic mismatch", key, delta_margin, delta_own, delta_rival))
            trace_changed = before["trace_sha256"] != after["trace_sha256"]
            if not trace_changed and (delta_own != 0.0 or delta_rival != 0.0 or delta_margin != 0.0):
                raise AssertionError(("score changed without trace change", key))
            cells.append({
                "seed": seed,
                "candidate_seat": seat,
                "trace_changed": trace_changed,
                "control_margin": b_margin,
                "candidate_margin": a_margin,
                "delta_own": delta_own,
                "delta_rival": delta_rival,
                "delta_margin": delta_margin,
                "control_scores": before["scores"],
                "candidate_scores": after["scores"],
                "control_trace_sha256": before["trace_sha256"],
                "candidate_trace_sha256": after["trace_sha256"],
            })
    margins = [row["delta_margin"] for row in cells]
    summary = {
        "cells": len(cells),
        "trace_changed_cells": sum(row["trace_changed"] for row in cells),
        "positive": sum(value > 0 for value in margins),
        "zero": sum(value == 0 for value in margins),
        "negative": sum(value < 0 for value in margins),
        "mean_delta_own": statistics.mean(row["delta_own"] for row in cells),
        "mean_delta_rival": statistics.mean(row["delta_rival"] for row in cells),
        "mean_delta_margin": statistics.mean(margins),
        "median_delta_margin": statistics.median(margins),
        "min_delta_margin": min(margins),
        "max_delta_margin": max(margins),
    }
    return summary, cells


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    repo = args.repo_root.resolve()
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)

    if git_blob_sha(repo / DONOR) != DONOR_BLOB:
        raise AssertionError("exact Riot donor blob drift")

    control_raw = output / "control-raw.json"
    candidate_raw = output / "candidate-raw.json"
    control_report = run_evaluator(repo, repo / BASELINE, control_raw)
    candidate_report = run_evaluator(repo, repo / CANDIDATE, candidate_raw)
    if control_report.get("opponents") != candidate_report.get("opponents"):
        raise AssertionError("opponent fingerprint mapping drifted across arms")

    control = exact_cells(control_report, repo / BASELINE, repo, "control")
    candidate = exact_cells(candidate_report, repo / CANDIDATE, repo, "candidate")
    summaries = {}
    all_cells = {}
    for opponent in OPPONENTS:
        summary, cells = paired(control, candidate, opponent)
        summaries[opponent] = summary
        all_cells[opponent] = cells

    changed = sum(summary["trace_changed_cells"] for summary in summaries.values())
    negatives = sum(summary["negative"] for summary in summaries.values())
    positives = sum(summary["positive"] for summary in summaries.values())
    if changed == 0:
        disposition = "KILL_INACTIVE_CURRENTROOT"
    elif negatives:
        disposition = "HOLD_NEGATIVE_PAIRED_CELL"
    elif positives:
        disposition = "PASS_WIDEN_ONLY"
    else:
        disposition = "HOLD_NO_POSITIVE_MARGIN"

    receipt = {
        "schema": "titan-v31-fert-daily-currentroot-gate/v1",
        "parent_head": PARENT_HEAD,
        "canonical_head": CANONICAL_HEAD,
        "engine_ref": ENGINE_REF,
        "donor": {"commit": DONOR_COMMIT, "blob": DONOR_BLOB},
        "composition": "exact shipped parent first; donor rewrites only PASS workers remaining after B5 CARROT+JIT",
        "current_tuple": {
            "horizon": 8,
            "opening": 0,
            "row_order": True,
            "evening_flush": True,
            "sale_fertilizer": True,
            "cattle_early": True,
            "kill_late_water": False,
            "strawberry_endgame": False,
            "no_late_sale_advance": True,
            "no_late_sale_advance_step": 648,
            "strawberry_topup": True,
            "b5_carrot_fertilizer": True,
            "b5_jit_fertilize": True,
        },
        "seeds": list(SEEDS),
        "summaries": summaries,
        "cells": all_cells,
        "disposition": disposition,
        "truth_boundary": "Offline official-interpreter current-root screen only. PASS earns wider post-L3/row-shed composition work; it is not production/default/package/Kaggle authority.",
    }
    (output / "receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    lines = ["## Fert-daily sweep — current-root paired gate", ""]
    for opponent in OPPONENTS:
        s = summaries[opponent]
        lines.append(f"{opponent}: **{s['positive']}+ / {s['negative']}- / {s['zero']}=**, trace deltas **{s['trace_changed_cells']}/{s['cells']}**, mean ΔM **{s['mean_delta_margin']:+.3f}**.")
    lines += ["", f"**Disposition: `{disposition}`**", "", "Evidence only; any survivor must recompose above the then-current convergence root."]
    (output / "receipt.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"disposition": disposition, "summaries": summaries}, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
