#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Strict paired reducer for the B10 exact-a612 cheap screen."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import statistics

ENGINE_REF = "28b6d8af3ce73926b3d0fda1410c1ddd8384ab8c"
OPPONENT = "a612"
SEEDS = (2611151001, 2611151002, 2611151003, 2611151004)
EXPECTED = frozenset((OPPONENT, seed, seat) for seed in SEEDS for seat in (0, 1))


def load(path: str) -> dict:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if type(value) is not dict:
        raise ValueError("report must be an object")
    return value


def finite_number(value, label: str):
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError(f"{label} must be a finite JSON number")
    return value


def validate(report: dict, label: str) -> dict[tuple[str, int, int], dict]:
    if report.get("engine_ref") != ENGINE_REF:
        raise ValueError(f"{label}: engine ref drift")
    seeds = report.get("seeds")
    if type(seeds) is not list or tuple(seeds) != SEEDS or any(type(seed) is not int for seed in seeds):
        raise ValueError(f"{label}: seed panel drift {seeds!r}")
    games = report.get("games")
    if type(games) is not list:
        raise ValueError(f"{label}: games must be a list")
    indexed = {}
    for index, game in enumerate(games):
        if type(game) is not dict:
            raise ValueError(f"{label}[{index}]: game must be object")
        opponent = game.get("opponent")
        seed = game.get("seed")
        seat = game.get("candidate_seat")
        key = (opponent, seed, seat)
        if type(opponent) is not str or opponent != OPPONENT:
            raise ValueError(f"{label}[{index}]: bad opponent")
        if type(seed) is not int or seed not in SEEDS:
            raise ValueError(f"{label}[{index}]: bad seed {seed!r}")
        if type(seat) is not int or seat not in (0, 1):
            raise ValueError(f"{label}[{index}]: bad seat {seat!r}")
        if key in indexed:
            raise ValueError(f"{label}: duplicate cell {key!r}")
        if game.get("status") != "complete" or game.get("failure") is not None:
            raise ValueError(f"{label}[{index}]: incomplete/failed game")
        scores = game.get("scores")
        if type(scores) is not list or len(scores) != 2:
            raise ValueError(f"{label}[{index}]: bad scores")
        finite_number(scores[0], f"{label}[{index}].scores[0]")
        finite_number(scores[1], f"{label}[{index}].scores[1]")
        trace = game.get("trace_sha256")
        if type(trace) is not str or len(trace) != 64 or any(ch not in "0123456789abcdef" for ch in trace):
            raise ValueError(f"{label}[{index}]: bad trace sha")
        indexed[key] = game
    if frozenset(indexed) != EXPECTED:
        raise ValueError(f"{label}: exact cell set mismatch")
    return indexed


def relative_scores(game: dict) -> tuple[float, float]:
    seat = game["candidate_seat"]
    scores = game["scores"]
    return scores[seat], scores[1 - seat]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("control")
    parser.add_argument("candidate")
    parser.add_argument("--json-out", required=True)
    parser.add_argument("--markdown-out", required=True)
    args = parser.parse_args()

    control_raw, candidate_raw = load(args.control), load(args.candidate)
    control, candidate = validate(control_raw, "control"), validate(candidate_raw, "candidate")
    if control_raw.get("opponents") != candidate_raw.get("opponents"):
        raise SystemExit("opponent fingerprint mismatch")

    rows = []
    for key in sorted(EXPECTED):
        c, b = control[key], candidate[key]
        c_own, c_rival = relative_scores(c)
        b_own, b_rival = relative_scores(b)
        rows.append({
            "opponent": key[0],
            "seed": key[1],
            "candidate_seat": key[2],
            "control_scores": c["scores"],
            "candidate_scores": b["scores"],
            "trace_changed": c["trace_sha256"] != b["trace_sha256"],
            "delta_own": b_own - c_own,
            "delta_rival": b_rival - c_rival,
            "delta_margin": (b_own - b_rival) - (c_own - c_rival),
        })

    trace_changed = sum(row["trace_changed"] for row in rows)
    pos = sum(row["delta_margin"] > 0 for row in rows)
    neg = sum(row["delta_margin"] < 0 for row in rows)
    zero = len(rows) - pos - neg
    mean_own = statistics.mean(row["delta_own"] for row in rows)
    mean_rival = statistics.mean(row["delta_rival"] for row in rows)
    mean_margin = statistics.mean(row["delta_margin"] for row in rows)

    if trace_changed == 0:
        disposition = "REJECT_ZERO_TRACE_DELTA_CURRENT_A612"
    elif neg:
        disposition = "HOLD_NEGATIVE_CURRENT_A612_CELL"
    elif mean_margin <= 0:
        disposition = "HOLD_NONPOSITIVE_MEAN_MARGIN"
    elif pos:
        disposition = "PROMISING_WIDEN_OPPONENT_D3_REQUIRED"
    else:
        disposition = "HOLD_NO_POSITIVE_MARGIN_REALIZATION"

    receipt = {
        "schema": "titan-v31-a612-b10-public-supply/v1",
        "engine_ref": ENGINE_REF,
        "seeds": list(SEEDS),
        "cells": rows,
        "summary": {
            "paired_cells": len(rows),
            "trace_changed_cells": trace_changed,
            "delta_margin_signs": {"positive": pos, "negative": neg, "zero": zero},
            "mean_delta_own": mean_own,
            "mean_delta_rival": mean_rival,
            "mean_delta_margin": mean_margin,
            "disposition": disposition,
        },
        "truth_boundary": (
            "Trace difference is only an activation proxy. A positive cheap screen requires "
            "materially different opponent widening plus D3 externality coverage before any package/default work."
        ),
    }
    Path(args.json_out).write_text(json.dumps(receipt, indent=2, allow_nan=False) + "\n", encoding="utf-8")

    lines = [
        "## B10 public-supply ordering — exact a612 cheap screen",
        "",
        f"Paired cells **{len(rows)}** · trace deltas **{trace_changed}/{len(rows)}** · ΔM signs **{pos}+ / {neg}- / {zero}=**.",
        "",
        f"Mean Δown **{mean_own:+.3f}** · mean Δrival **{mean_rival:+.3f}** · mean ΔM **{mean_margin:+.3f}**.",
        "",
        f"**Disposition: `{disposition}`**",
        "",
        "| seed | seat | trace Δ | Δown | Δrival | ΔM |",
        "|---:|---:|:---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            f"| {row['seed']} | {row['candidate_seat']} | {'yes' if row['trace_changed'] else 'no'} | "
            f"{row['delta_own']:+.0f} | {row['delta_rival']:+.0f} | {row['delta_margin']:+.0f} |"
        )
    lines += ["", receipt["truth_boundary"]]
    Path(args.markdown_out).write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(receipt["summary"], sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
