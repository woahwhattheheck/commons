#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Reduce matched current-canonical B5 control/candidate evaluator receipts.

This is an interaction screen, not a promotion gate. It requires complete, unique,
finite, seat-aware paired cells and treats any negative own-score or competitive-margin
cell as a HOLD before a wider opponent-diverse D3 receipt is attempted.
"""
from __future__ import annotations

import argparse
import json
import math
import statistics
from pathlib import Path

ENGINE_REF = "28b6d8af3ce73926b3d0fda1410c1ddd8384ab8c"


def load(path):
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise SystemExit(f"{path}: receipt must be an object")
    return value


def strict_int(value, label):
    if type(value) is not int:
        raise SystemExit(f"{label}: expected exact integer")
    return value


def finite_number(value, label):
    if type(value) not in (int, float) or isinstance(value, bool) or not math.isfinite(float(value)):
        raise SystemExit(f"{label}: expected finite number")
    return float(value)


def normalized_games(report, label):
    if report.get("engine_ref") != ENGINE_REF:
        raise SystemExit(f"{label}: wrong engine ref {report.get('engine_ref')!r}")
    seeds = report.get("seeds")
    opponents = report.get("opponents")
    games = report.get("games")
    if not isinstance(seeds, list) or not seeds or not isinstance(opponents, list) or not opponents:
        raise SystemExit(f"{label}: missing seeds/opponents metadata")
    if not isinstance(games, list) or not games:
        raise SystemExit(f"{label}: missing games")
    for i, seed in enumerate(seeds):
        strict_int(seed, f"{label}.seeds[{i}]")
    result = {}
    for index, game in enumerate(games):
        if not isinstance(game, dict):
            raise SystemExit(f"{label}.games[{index}]: expected object")
        if game.get("status") != "complete":
            raise SystemExit(f"{label}.games[{index}]: incomplete status {game.get('status')!r}")
        opponent = game.get("opponent")
        if not isinstance(opponent, str) or not opponent:
            raise SystemExit(f"{label}.games[{index}]: bad opponent")
        seed = strict_int(game.get("seed"), f"{label}.games[{index}].seed")
        seat = strict_int(game.get("candidate_seat"), f"{label}.games[{index}].candidate_seat")
        if seat not in (0, 1):
            raise SystemExit(f"{label}.games[{index}]: seat must be 0/1")
        scores = game.get("scores")
        if not isinstance(scores, list) or len(scores) != 2:
            raise SystemExit(f"{label}.games[{index}]: scores must be [seat0, seat1]")
        scores = [finite_number(scores[0], "score0"), finite_number(scores[1], "score1")]
        trace = game.get("trace_sha256")
        if not isinstance(trace, str) or not trace:
            raise SystemExit(f"{label}.games[{index}]: missing trace sha")
        key = (opponent, seed, seat)
        if key in result:
            raise SystemExit(f"{label}: duplicate paired cell {key!r}")
        row = dict(game)
        row["scores"] = scores
        result[key] = row
    expected = len(seeds) * len(opponents) * 2
    if len(result) != expected:
        raise SystemExit(f"{label}: expected {expected} cartesian cells, found {len(result)}")
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("control")
    parser.add_argument("candidate")
    parser.add_argument("--json-out", required=True)
    parser.add_argument("--markdown-out", required=True)
    args = parser.parse_args()

    control_raw, candidate_raw = load(args.control), load(args.candidate)
    if control_raw.get("seeds") != candidate_raw.get("seeds"):
        raise SystemExit("seed metadata mismatch")
    if control_raw.get("opponents") != candidate_raw.get("opponents"):
        raise SystemExit("opponent metadata mismatch")
    control = normalized_games(control_raw, "control")
    candidate = normalized_games(candidate_raw, "candidate")
    if control.keys() != candidate.keys():
        raise SystemExit("paired cell key mismatch")

    cells = []
    for key in sorted(control):
        c, b = control[key], candidate[key]
        seat = key[2]
        c_own, c_rival = c["scores"][seat], c["scores"][1 - seat]
        b_own, b_rival = b["scores"][seat], b["scores"][1 - seat]
        d_own = b_own - c_own
        d_rival = b_rival - c_rival
        d_margin = d_own - d_rival
        cells.append({
            "opponent": key[0],
            "seed": key[1],
            "candidate_seat": seat,
            "control_scores": c["scores"],
            "candidate_scores": b["scores"],
            "trace_changed": c["trace_sha256"] != b["trace_sha256"],
            "delta_own": d_own,
            "delta_rival": d_rival,
            "delta_margin": d_margin,
        })

    trace_changed = sum(cell["trace_changed"] for cell in cells)
    positive = sum(cell["delta_margin"] > 0 for cell in cells)
    negative = sum(cell["delta_margin"] < 0 for cell in cells)
    ties = len(cells) - positive - negative
    own_negative = sum(cell["delta_own"] < 0 for cell in cells)
    mean_own = statistics.mean(cell["delta_own"] for cell in cells)
    mean_rival = statistics.mean(cell["delta_rival"] for cell in cells)
    mean_margin = statistics.mean(cell["delta_margin"] for cell in cells)

    if trace_changed == 0:
        disposition = "REJECT_ZERO_ACTION_TRACE_DELTA"
    elif negative or own_negative:
        disposition = "HOLD_NEGATIVE_CURRENT_CANONICAL_CELL"
    elif positive:
        disposition = "PROMISING_CURRENT_CANONICAL_WIDEN_D3_REQUIRED"
    else:
        disposition = "HOLD_MARGIN_NEUTRAL"

    summary = {
        "paired_cells": len(cells),
        "trace_changed_cells": trace_changed,
        "delta_margin_signs": {"positive": positive, "negative": negative, "zero": ties},
        "own_negative_cells": own_negative,
        "mean_delta_own": mean_own,
        "mean_delta_rival": mean_rival,
        "mean_delta_margin": mean_margin,
        "disposition": disposition,
    }
    payload = {
        "schema": "titan-v31-b5-a612-interaction-screen/v1",
        "engine_ref": ENGINE_REF,
        "seeds": control_raw["seeds"],
        "opponents": control_raw["opponents"],
        "cells": cells,
        "summary": summary,
        "truth_boundary": (
            "This is a current-canonical interaction screen using materialized a612 R04/H4/L3 bytes "
            "with the score-facing cattle-off tuple. Trace change is only an activation proxy. "
            "A promising result still requires opponent-diverse D3 product-externality coverage before integration."
        ),
    }
    Path(args.json_out).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    lines = [
        "## B5 CARROT JIT — current canonical interaction screen",
        "",
        f"Cells **{len(cells)}**; trace deltas **{trace_changed}/{len(cells)}**; "
        f"ΔM signs **{positive}+ / {negative}- / {ties}=**; own-negative cells **{own_negative}**.",
        "",
        f"Mean Δown **{mean_own:+.3f}**, Δrival **{mean_rival:+.3f}**, ΔM **{mean_margin:+.3f}**.",
        "",
        f"**Disposition: `{disposition}`**",
        "",
        "| seed | seat | trace Δ | Δown | Δrival | ΔM |",
        "|---:|---:|:---:|---:|---:|---:|",
    ]
    for cell in cells:
        lines.append(
            f"| {cell['seed']} | {cell['candidate_seat']} | {'yes' if cell['trace_changed'] else 'no'} | "
            f"{cell['delta_own']:+.0f} | {cell['delta_rival']:+.0f} | {cell['delta_margin']:+.0f} |"
        )
    lines += [
        "",
        "Truth boundary: this screen detects interaction with current canonical H4 + rival-gated L3 and the "
        "preferred cattle-off score tuple. It is not a default/package promotion receipt; third-opponent and "
        "product-externality D3 coverage remain mandatory.",
    ]
    Path(args.markdown_out).write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    main()
