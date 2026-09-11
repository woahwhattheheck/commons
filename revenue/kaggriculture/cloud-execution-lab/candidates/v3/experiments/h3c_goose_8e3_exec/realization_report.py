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
    fingerprint = opponents[EXPECTED_OPPONENT]
    if not isinstance(fingerprint, dict):
        raise ValueError(f"{label}: opponent fingerprint must be an object")
    if fingerprint.get("entry") != "baseline.py" or fingerprint.get("callable") != "agent":
        raise ValueError(f"{label}: wrong opponent fingerprint entry/callable {fingerprint!r}")
    if not _valid_sha256(fingerprint.get("sha256")):
        raise ValueError(f"{label}: invalid opponent fingerprint sha256")


def validate_report(report, label):
    if not isinstance(report, dict):
        raise ValueError(f"{label}: report must be an object")
    if report.get("engine_ref") != EXPECTED_ENGINE_REF:
        raise ValueError(f"{label}: wrong engine ref {report.get('engine_ref')!r}")
    validate_opponent_metadata(report, label)
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
    args = p.parse_args()
    control, candidate = load(args.control), load(args.candidate)
    try:
        cg = validate_report(control, "control")
        hg = validate_report(candidate, "candidate")
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
        "schema": "titan-v31-h3c-8e3-realization/v1",
        "engine_ref": EXPECTED_ENGINE_REF,
        "seeds": list(EXPECTED_SEEDS),
        "opponent": EXPECTED_OPPONENT,
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
        f"Engine `{EXPECTED_ENGINE_REF}` · **{len(cells)}** paired cells · trace deltas **{trace_changed}/{len(cells)}** · money deltas **{money_changed}/{len(cells)}**.", "",
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
