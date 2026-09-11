#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Paired exact-current-stack realization report for H3c goose EOD rescue."""
from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path

EXPECTED_ENGINE_REF = "28b6d8af3ce73926b3d0fda1410c1ddd8384ab8c"


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def key(game):
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
    for label, report in (("control", control), ("candidate", candidate)):
        if report.get("engine_ref") != EXPECTED_ENGINE_REF:
            raise SystemExit(f"{label}: wrong engine ref {report.get('engine_ref')!r}")
        if report.get("seeds") != control.get("seeds"):
            raise SystemExit(f"{label}: seed panel mismatch")
        if report.get("opponents") != control.get("opponents"):
            raise SystemExit(f"{label}: opponent fingerprint mismatch")

    cg = {key(g): g for g in control.get("games", [])}
    hg = {key(g): g for g in candidate.get("games", [])}
    if not cg or cg.keys() != hg.keys():
        raise SystemExit("paired cell set mismatch or empty panel")

    cells = []
    for cell_key in sorted(cg):
        c, h = cg[cell_key], hg[cell_key]
        if c.get("status") != "complete" or h.get("status") != "complete":
            raise SystemExit(f"incomplete paired cell {cell_key}")
        c_own, c_rival = score_pair(c)
        h_own, h_rival = score_pair(h)
        d_own = h_own - c_own
        d_rival = h_rival - c_rival
        d_margin = (h_own - h_rival) - (c_own - c_rival)
        cells.append({
            "opponent": cell_key[0],
            "seed": cell_key[1],
            "candidate_seat": cell_key[2],
            "control_scores": c["scores"],
            "candidate_scores": h["scores"],
            "trace_changed": c.get("trace_sha256") != h.get("trace_sha256"),
            "delta_own": d_own,
            "delta_rival": d_rival,
            "delta_margin": d_margin,
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
        "schema": "titan-v31-h3c-a612-realization/v1",
        "engine_ref": EXPECTED_ENGINE_REF,
        "seeds": control["seeds"],
        "cells": cells,
        "summary": {
            "paired_cells": len(cells),
            "trace_changed_cells": trace_changed,
            "money_changed_cells": money_changed,
            "delta_margin_signs": {"positive": pos, "negative": neg, "zero": tie},
            "mean_delta_own": mean_own,
            "mean_delta_rival": mean_rival,
            "mean_delta_margin": mean_margin,
            "disposition": disposition,
        },
        "truth_boundary": "Trace delta is an activation proxy. Promotion requires opponent-diverse paired own/rival/margin evidence on the then-current canonical stack.",
    }
    Path(args.json_out).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")

    lines = [
        "## H3c goose rescue — a612 exact-current-stack realization",
        "",
        f"Engine `{EXPECTED_ENGINE_REF}` · **{len(cells)}** paired cells · trace deltas **{trace_changed}/{len(cells)}** · money deltas **{money_changed}/{len(cells)}**.",
        "",
        f"ΔM signs **{pos}+ / {neg}- / {tie}=** · mean Δown **{mean_own:+.3f}** · mean Δrival **{mean_rival:+.3f}** · mean ΔM **{mean_margin:+.3f}**.",
        "",
        f"**Disposition: `{disposition}`**",
        "",
        "| seed | seat | trace Δ | Δown | Δrival | ΔM | first daily-bank divergence |",
        "|---:|---:|:---:|---:|---:|---:|:---|",
    ]
    for row in cells:
        div = row["first_daily_bank_divergence"]
        compact = "—" if div is None else json.dumps(div, separators=(",", ":"))
        lines.append(
            f"| {row['seed']} | {row['candidate_seat']} | {'yes' if row['trace_changed'] else 'no'} | "
            f"{row['delta_own']:+.0f} | {row['delta_rival']:+.0f} | {row['delta_margin']:+.0f} | `{compact}` |"
        )
    lines += ["", "This is execution evidence only. Any positive result still requires an opponent-diverse D3-style widen before package/default work."]
    Path(args.markdown_out).write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(result["summary"], sort_keys=True))


if __name__ == "__main__":
    main()
