#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Compare exact-control and H1 evaluator receipts cell by cell.

A trace delta is the cheap activation proxy: the evaluator hashes every emitted
action plus bank state.  A terminal score delta is stronger realization
 evidence because the pinned official interpreter's reward is money only.
This script does not promote H1; it classifies a small screen for the next gate.
"""
from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path

EXPECTED_ENGINE_REF = "28b6d8af3ce73926b3d0fda1410c1ddd8384ab8c"


def load(path: str):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def cell_key(game):
    return (game["opponent"], int(game["seed"]), int(game["candidate_seat"]))


def score_pair(game):
    seat = int(game["candidate_seat"])
    scores = game["scores"]
    return float(scores[seat]), float(scores[1 - seat])


def first_bank_divergence(control, candidate):
    c_rows = control.get("daily_bank", [])
    h_rows = candidate.get("daily_bank", [])
    for c_row, h_row in zip(c_rows, h_rows):
        if c_row != h_row:
            return {"control": c_row, "h1": h_row}
    if len(c_rows) != len(h_rows):
        return {"control_rows": len(c_rows), "h1_rows": len(h_rows)}
    return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("control")
    parser.add_argument("candidate")
    parser.add_argument("--json-out", required=True)
    parser.add_argument("--markdown-out", required=True)
    args = parser.parse_args()

    control, h1 = load(args.control), load(args.candidate)
    for label, report in (("control", control), ("h1", h1)):
        if report.get("engine_ref") != EXPECTED_ENGINE_REF:
            raise SystemExit(f"{label}: wrong engine ref {report.get('engine_ref')!r}")
        if report.get("seeds") != control.get("seeds"):
            raise SystemExit(f"{label}: seed panel mismatch")
        if report.get("opponents") != control.get("opponents"):
            raise SystemExit(f"{label}: opponent fingerprint mismatch")

    control_games = {cell_key(g): g for g in control.get("games", [])}
    h1_games = {cell_key(g): g for g in h1.get("games", [])}
    if not control_games or control_games.keys() != h1_games.keys():
        raise SystemExit("paired cell set mismatch or empty panel")

    cells = []
    for key in sorted(control_games):
        c_game, h_game = control_games[key], h1_games[key]
        if c_game.get("status") != "complete" or h_game.get("status") != "complete":
            raise SystemExit(f"incomplete paired cell {key}: {c_game.get('status')} / {h_game.get('status')}")
        c_own, c_rival = score_pair(c_game)
        h_own, h_rival = score_pair(h_game)
        d_own = h_own - c_own
        d_rival = h_rival - c_rival
        d_margin = (h_own - h_rival) - (c_own - c_rival)
        cells.append({
            "opponent": key[0],
            "seed": key[1],
            "candidate_seat": key[2],
            "control_scores": c_game["scores"],
            "h1_scores": h_game["scores"],
            "trace_changed": c_game.get("trace_sha256") != h_game.get("trace_sha256"),
            "control_trace_sha256": c_game.get("trace_sha256"),
            "h1_trace_sha256": h_game.get("trace_sha256"),
            "delta_own": d_own,
            "delta_rival": d_rival,
            "delta_margin": d_margin,
            "first_daily_bank_divergence": first_bank_divergence(c_game, h_game),
        })

    trace_changed = sum(bool(c["trace_changed"]) for c in cells)
    money_changed = sum(bool(c["delta_own"] or c["delta_rival"]) for c in cells)
    positives = sum(c["delta_margin"] > 0 for c in cells)
    negatives = sum(c["delta_margin"] < 0 for c in cells)
    ties = len(cells) - positives - negatives
    mean_down = statistics.mean(c["delta_own"] for c in cells)
    mean_drival = statistics.mean(c["delta_rival"] for c in cells)
    mean_dm = statistics.mean(c["delta_margin"] for c in cells)

    if trace_changed == 0:
        disposition = "REJECT_ZERO_ACTION_TRACE_DELTA"
    elif money_changed == 0:
        disposition = "HOLD_ACTION_DELTA_NO_MONEY_REALIZATION"
    elif negatives:
        disposition = "HOLD_NEGATIVE_CHEAP_SCREEN"
    elif positives:
        disposition = "PROMISING_CHEAP_SCREEN_WIDEN_REQUIRED"
    else:
        disposition = "HOLD_MONEY_DELTA_MARGIN_NEUTRAL"

    result = {
        "schema": "titan-v31-h1-realization-gate/v1",
        "engine_ref": EXPECTED_ENGINE_REF,
        "seeds": control["seeds"],
        "cells": cells,
        "summary": {
            "paired_cells": len(cells),
            "trace_changed_cells": trace_changed,
            "money_changed_cells": money_changed,
            "delta_margin_signs": {"positive": positives, "negative": negatives, "zero": ties},
            "mean_delta_own": mean_down,
            "mean_delta_rival": mean_drival,
            "mean_delta_margin": mean_dm,
            "disposition": disposition,
        },
        "truth_boundary": (
            "Trace change is an activation proxy, not a causal unit-flow proof. "
            "Terminal score change is money realization under the pinned money-only reward. "
            "A promising cheap screen still requires activation->inventory->deposit->sale telemetry "
            "and opponent-diverse D3 evidence before integration."
        ),
    }
    Path(args.json_out).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")

    lines = [
        "## H1 realization gate — exact paired cheap screen",
        "",
        f"Engine: `{EXPECTED_ENGINE_REF}`. Cells: **{len(cells)}**. "
        f"Action-trace deltas: **{trace_changed}/{len(cells)}**; money deltas: **{money_changed}/{len(cells)}**.",
        "",
        f"ΔM signs: **{positives}+ / {negatives}- / {ties}=**. "
        f"Mean Δown **{mean_down:+.3f}**, Δrival **{mean_drival:+.3f}**, ΔM **{mean_dm:+.3f}**.",
        "",
        f"**Disposition: `{disposition}`**",
        "",
        "| seed | seat | trace Δ | Δown | Δrival | ΔM | first daily bank divergence |",
        "|---:|---:|:---:|---:|---:|---:|:---|",
    ]
    for cell in cells:
        divergence = cell["first_daily_bank_divergence"]
        compact = "—" if divergence is None else json.dumps(divergence, separators=(",", ":"))
        lines.append(
            f"| {cell['seed']} | {cell['candidate_seat']} | {'yes' if cell['trace_changed'] else 'no'} | "
            f"{cell['delta_own']:+.0f} | {cell['delta_rival']:+.0f} | {cell['delta_margin']:+.0f} | `{compact}` |"
        )
    lines += [
        "",
        "Truth boundary: trace change is only an activation proxy. A terminal-score delta is real money realization "
        "because the pinned interpreter rewards terminal money only. Even a positive screen is **HOLD** until "
        "activation→inventory→deposit→sale telemetry plus opponent-diverse D3 evidence is durable.",
    ]
    Path(args.markdown_out).write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(result["summary"], sort_keys=True))


if __name__ == "__main__":
    main()
