#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Paired exact-8e3 realization report for H3c goose EOD rescue."""
from __future__ import annotations

import argparse
import json
import math
import statistics
from pathlib import Path

EXPECTED_ENGINE_REF = "28b6d8af3ce73926b3d0fda1410c1ddd8384ab8c"
EXPECTED_ENGINE_FILES = frozenset(("kaggriculture.py", "kaggriculture.json", "utils.py"))
EXPECTED_AGENT_RNG_SEED = 20260911
EXPECTED_OPPONENT = "v31_8e3"
EXPECTED_SEEDS = (2611151001, 2611151002, 2611151003, 2611151004)
EXPECTED_CELLS = frozenset(
    (EXPECTED_OPPONENT, seed, seat) for seed in EXPECTED_SEEDS for seat in (0, 1)
)


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _strict_score(value, label):
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError(f"{label}: score must be a finite JSON number, got {value!r}")
    return value


def _valid_sha256(value):
    return isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value)


def _expected_sha256(value, label):
    if not _valid_sha256(value):
        raise ValueError(f"{label}: expected source sha256 must be canonical lowercase hex")
    return value


def _validate_fingerprint(value, label, expected_entry):
    if not isinstance(value, dict):
        raise ValueError(f"{label}: fingerprint must be an object")
    if set(value) != {"entry", "callable", "sha256"}:
        raise ValueError(f"{label}: fingerprint keys mismatch {sorted(value)!r}")
    if value.get("entry") != expected_entry or value.get("callable") != "agent":
        raise ValueError(f"{label}: wrong fingerprint entry/callable {value!r}")
    if not _valid_sha256(value.get("sha256")):
        raise ValueError(f"{label}: invalid fingerprint sha256")
    return value


def validate_game(game, label):
    if not isinstance(game, dict):
        raise ValueError(f"{label}: game must be an object")
    opponent = game.get("opponent")
    seed = game.get("seed")
    seat = game.get("candidate_seat")
    if opponent != EXPECTED_OPPONENT or not isinstance(opponent, str):
        raise ValueError(f"{label}: wrong opponent {opponent!r}")
    if type(seed) is not int or seed not in EXPECTED_SEEDS:
        raise ValueError(f"{label}: invalid seed {seed!r}")
    if type(seat) is not int or seat not in (0, 1):
        raise ValueError(f"{label}: invalid candidate_seat {seat!r}")
    if game.get("status") != "complete" or not isinstance(game.get("status"), str):
        raise ValueError(f"{label}: incomplete/invalid status {game.get('status')!r}")
    if game.get("failure") is not None:
        raise ValueError(f"{label}: complete game has non-null failure {game.get('failure')!r}")
    scores = game.get("scores")
    if not isinstance(scores, list) or len(scores) != 2:
        raise ValueError(f"{label}: scores must be a two-element list")
    _strict_score(scores[0], f"{label}:scores[0]")
    _strict_score(scores[1], f"{label}:scores[1]")
    trace = game.get("trace_sha256")
    if not _valid_sha256(trace):
        raise ValueError(f"{label}: invalid trace_sha256 {trace!r}")
    daily_bank = game.get("daily_bank", [])
    if not isinstance(daily_bank, list):
        raise ValueError(f"{label}: daily_bank must be a list")
    return (opponent, seed, seat)


def validate_opponent_metadata(report, label):
    opponents = report.get("opponents")
    if not isinstance(opponents, dict) or set(opponents) != {EXPECTED_OPPONENT}:
        raise ValueError(f"{label}: opponent metadata must contain exactly {EXPECTED_OPPONENT!r}")
    return _validate_fingerprint(
        opponents[EXPECTED_OPPONENT], f"{label}:opponent", "baseline.py"
    )


def _validate_source_metadata(report, label, expected_candidate_entry):
    if type(report.get("schema_version")) is not int or report.get("schema_version") != 1:
        raise ValueError(f"{label}: wrong schema_version {report.get('schema_version')!r}")
    engine_hashes = report.get("engine_sha256")
    if not isinstance(engine_hashes, dict) or set(engine_hashes) != EXPECTED_ENGINE_FILES:
        raise ValueError(f"{label}: engine_sha256 shape mismatch")
    if any(not _valid_sha256(value) for value in engine_hashes.values()):
        raise ValueError(f"{label}: invalid engine source sha256")
    for field in ("loader_sha256", "evaluator_sha256"):
        if not _valid_sha256(report.get(field)):
            raise ValueError(f"{label}: invalid {field}")
    if type(report.get("agent_rng_seed")) is not int or report.get("agent_rng_seed") != EXPECTED_AGENT_RNG_SEED:
        raise ValueError(f"{label}: wrong agent_rng_seed {report.get('agent_rng_seed')!r}")
    candidate = _validate_fingerprint(
        report.get("candidate"), f"{label}:candidate", expected_candidate_entry
    )
    opponent = validate_opponent_metadata(report, label)
    return candidate, opponent


def _validate_reproducibility(report, label):
    repro = report.get("reproducibility")
    if not isinstance(repro, dict):
        raise ValueError(f"{label}: reproducibility must be an object")
    if repro.get("checked") is not True or repro.get("same_trace_and_scores") is not True:
        raise ValueError(f"{label}: reproducibility check did not pass")
    original = repro.get("original_trace")
    replay = repro.get("replay_trace")
    if not _valid_sha256(original) or not _valid_sha256(replay) or original != replay:
        raise ValueError(f"{label}: reproducibility trace mismatch")


def validate_report(report, label, expected_candidate_entry="baseline.py"):
    if not isinstance(report, dict):
        raise ValueError(f"{label}: report must be an object")
    if report.get("engine_ref") != EXPECTED_ENGINE_REF:
        raise ValueError(f"{label}: wrong engine ref {report.get('engine_ref')!r}")
    _validate_source_metadata(report, label, expected_candidate_entry)
    _validate_reproducibility(report, label)
    seeds = report.get("seeds")
    if not isinstance(seeds, list) or len(seeds) != len(EXPECTED_SEEDS):
        raise ValueError(f"{label}: seed panel shape mismatch")
    if any(type(seed) is not int for seed in seeds) or tuple(seeds) != EXPECTED_SEEDS:
        raise ValueError(f"{label}: seed panel mismatch {seeds!r}")
    games = report.get("games")
    if not isinstance(games, list):
        raise ValueError(f"{label}: games must be a list")
    indexed = {}
    for index, game in enumerate(games):
        cell = validate_game(game, f"{label}:games[{index}]")
        if cell in indexed:
            raise ValueError(f"{label}: duplicate paired cell {cell!r}")
        indexed[cell] = game
    if frozenset(indexed) != EXPECTED_CELLS:
        missing = sorted(EXPECTED_CELLS - frozenset(indexed))
        extra = sorted(frozenset(indexed) - EXPECTED_CELLS)
        raise ValueError(f"{label}: exact paired cell set mismatch missing={missing!r} extra={extra!r}")
    return indexed


def validate_pair_metadata(control, candidate):
    """Bind the two reports to the same evaluator/engine/opponent execution custody."""
    shared_fields = (
        "engine_ref", "engine_sha256", "loader_sha256", "evaluator_sha256",
        "opponents", "seeds", "agent_rng_seed", "limits",
    )
    for field in shared_fields:
        if control.get(field) != candidate.get(field):
            raise ValueError(f"paired receipt metadata drift: {field}")
    control_fp = control["candidate"]
    opponent_fp = control["opponents"][EXPECTED_OPPONENT]
    if control_fp != opponent_fp:
        raise ValueError("control candidate fingerprint must equal the baseline opponent fingerprint")
    if candidate["opponents"][EXPECTED_OPPONENT] != opponent_fp:
        raise ValueError("candidate arm opponent fingerprint drift")
    if candidate["candidate"]["sha256"] == opponent_fp["sha256"]:
        raise ValueError("H3c candidate entry fingerprint unexpectedly equals baseline")


def validate_actual_byte_fingerprints(
    control, candidate, expected_baseline_sha256, expected_candidate_sha256,
    expected_evaluator_sha256,
):
    """Bind report fingerprints to the literal checked-out source bytes used by the gate."""
    baseline_sha = _expected_sha256(expected_baseline_sha256, "baseline")
    candidate_sha = _expected_sha256(expected_candidate_sha256, "candidate")
    evaluator_sha = _expected_sha256(expected_evaluator_sha256, "evaluator")
    checks = (
        (control["candidate"]["sha256"], baseline_sha, "control candidate"),
        (control["opponents"][EXPECTED_OPPONENT]["sha256"], baseline_sha, "control opponent"),
        (candidate["opponents"][EXPECTED_OPPONENT]["sha256"], baseline_sha, "candidate opponent"),
        (candidate["candidate"]["sha256"], candidate_sha, "H3c candidate"),
        (control["evaluator_sha256"], evaluator_sha, "control evaluator"),
        (candidate["evaluator_sha256"], evaluator_sha, "candidate evaluator"),
    )
    for actual, expected, label in checks:
        if actual != expected:
            raise ValueError(f"{label} fingerprint does not match checked-out bytes: {actual!r} != {expected!r}")


def score_pair(game):
    seat = game["candidate_seat"]
    scores = game["scores"]
    return scores[seat], scores[1 - seat]


def first_bank_divergence(control, candidate):
    c_rows = control.get("daily_bank", [])
    h_rows = candidate.get("daily_bank", [])
    for c_row, h_row in zip(c_rows, h_rows):
        if c_row != h_row:
            return {"control": c_row, "h3c": h_row}
    if len(c_rows) != len(h_rows):
        return {"control_rows": len(c_rows), "h3c_rows": len(h_rows)}
    return None


def main():
    p = argparse.ArgumentParser()
    p.add_argument("control")
    p.add_argument("candidate")
    p.add_argument("--json-out", required=True)
    p.add_argument("--markdown-out", required=True)
    p.add_argument("--expected-baseline-sha256", required=True)
    p.add_argument("--expected-candidate-sha256", required=True)
    p.add_argument("--expected-evaluator-sha256", required=True)
    args = p.parse_args()
    control, candidate = load(args.control), load(args.candidate)
    try:
        cg = validate_report(control, "control", "baseline.py")
        hg = validate_report(candidate, "candidate", "candidate.py")
        validate_pair_metadata(control, candidate)
        validate_actual_byte_fingerprints(
            control, candidate,
            args.expected_baseline_sha256,
            args.expected_candidate_sha256,
            args.expected_evaluator_sha256,
        )
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    cells = []
    for cell_key in sorted(EXPECTED_CELLS):
        c, h = cg[cell_key], hg[cell_key]
        c_own, c_rival = score_pair(c)
        h_own, h_rival = score_pair(h)
        d_own = h_own - c_own
        d_rival = h_rival - c_rival
        d_margin = (h_own - h_rival) - (c_own - c_rival)
        cells.append({
            "opponent": cell_key[0], "seed": cell_key[1], "candidate_seat": cell_key[2],
            "control_scores": c["scores"], "candidate_scores": h["scores"],
            "trace_changed": c["trace_sha256"] != h["trace_sha256"],
            "delta_own": d_own, "delta_rival": d_rival, "delta_margin": d_margin,
            "first_daily_bank_divergence": first_bank_divergence(c, h),
        })
    trace_changed = sum(row["trace_changed"] for row in cells)
    money_changed = sum(bool(row["delta_own"] or row["delta_rival"]) for row in cells)
    pos = sum(row["delta_margin"] > 0 for row in cells)
    neg = sum(row["delta_margin"] < 0 for row in cells)
    tie = len(cells) - pos - neg
    mean_own = statistics.mean(row["delta_own"] for row in cells)
    mean_rival = statistics.mean(row["delta_rival"] for row in cells)
    mean_margin = statistics.mean(row["delta_margin"] for row in cells)
    if trace_changed == 0:
        disposition = "REJECT_ZERO_ACTION_TRACE_DELTA_CURRENT_STACK"
    elif money_changed == 0:
        disposition = "HOLD_ACTION_DELTA_NO_MONEY_REALIZATION"
    elif neg:
        disposition = "HOLD_NEGATIVE_CURRENT_STACK_CELL"
    elif pos:
        disposition = "PROMISING_CURRENT_STACK_WIDEN_TO_OPPONENT_PANEL"
    else:
        disposition = "HOLD_MARGIN_NEUTRAL"
    result = {
        "schema": "titan-v31-h3c-8e3-realization/v2",
        "engine_ref": EXPECTED_ENGINE_REF,
        "agent_rng_seed": EXPECTED_AGENT_RNG_SEED,
        "seeds": list(EXPECTED_SEEDS),
        "opponent": EXPECTED_OPPONENT,
        "control_candidate": control["candidate"],
        "h3c_candidate": candidate["candidate"],
        "opponent_fingerprint": control["opponents"][EXPECTED_OPPONENT],
        "checked_out_source_sha256": {
            "baseline.py": args.expected_baseline_sha256,
            "candidate.py": args.expected_candidate_sha256,
            "evaluate.py": args.expected_evaluator_sha256,
        },
        "cells": cells,
        "summary": {
            "paired_cells": len(cells), "trace_changed_cells": trace_changed,
            "money_changed_cells": money_changed,
            "delta_margin_signs": {"positive": pos, "negative": neg, "zero": tie},
            "mean_delta_own": mean_own, "mean_delta_rival": mean_rival,
            "mean_delta_margin": mean_margin, "disposition": disposition,
        },
        "truth_boundary": "Trace delta is an activation proxy. Promotion requires opponent-diverse paired own/rival/margin evidence on the then-current canonical stack.",
    }
    Path(args.json_out).write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    lines = [
        "## H3c goose rescue — shipped 8e3 current-root realization", "",
        f"Engine `{EXPECTED_ENGINE_REF}` · RNG `{EXPECTED_AGENT_RNG_SEED}` · **{len(cells)}** paired cells · trace deltas **{trace_changed}/{len(cells)}** · money deltas **{money_changed}/{len(cells)}**.", "",
        f"ΔM signs **{pos}+ / {neg}- / {tie}=** · mean Δown **{mean_own:+.3f}** · mean Δrival **{mean_rival:+.3f}** · mean ΔM **{mean_margin:+.3f}**.", "",
        f"**Disposition: `{disposition}`**", "",
        "| seed | seat | trace Δ | Δown | Δrival | ΔM | first daily-bank divergence |",
        "|---:|---:|:---:|---:|---:|---:|:---|",
    ]
    for row in cells:
        div = row["first_daily_bank_divergence"]
        compact = "—" if div is None else json.dumps(div, separators=(",", ":"), allow_nan=False)
        lines.append(f"| {row['seed']} | {row['candidate_seat']} | {'yes' if row['trace_changed'] else 'no'} | {row['delta_own']:+.0f} | {row['delta_rival']:+.0f} | {row['delta_margin']:+.0f} | `{compact}` |")
    lines += ["", "This is execution evidence only. Any positive result still requires an opponent-diverse D3-style widen before package/default work."]
    Path(args.markdown_out).write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(result["summary"], sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
