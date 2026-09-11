#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Reduce exact a612 V226-topup ablation receipts across self-play and Arlene."""
from __future__ import annotations

import argparse
import json
import math
import statistics
from pathlib import Path

ENGINE_REF = "28b6d8af3ce73926b3d0fda1410c1ddd8384ab8c"
PARENT = "a6120d0ea1bdb75eb0da2239220efce551f624a6"


def load(path: str):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def cell_key(game):
    return (game["opponent"], int(game["seed"]), int(game["candidate_seat"]))


def pair_scores(game):
    seat = int(game["candidate_seat"])
    scores = game.get("scores")
    if (not isinstance(scores, list) or len(scores) != 2
            or not all(type(v) in (int, float) and not isinstance(v, bool) and math.isfinite(v) for v in scores)):
        raise ValueError(f"invalid scores for {cell_key(game)}: {scores!r}")
    return float(scores[seat]), float(scores[1 - seat])


def reduce_regime(name: str, control_path: str, candidate_path: str):
    control, candidate = load(control_path), load(candidate_path)
    for label, report in (("control", control), ("candidate", candidate)):
        if report.get("engine_ref") != ENGINE_REF:
            raise SystemExit(f"{name}/{label}: wrong engine {report.get('engine_ref')!r}")
        if report.get("reproducibility", {}).get("same_trace_and_scores") is not True:
            raise SystemExit(f"{name}/{label}: first-cell reproducibility failed")
    if control.get("seeds") != candidate.get("seeds"):
        raise SystemExit(f"{name}: seed panel mismatch")
    if control.get("opponents") != candidate.get("opponents"):
        raise SystemExit(f"{name}: opponent fingerprint mismatch")

    before = {cell_key(g): g for g in control.get("games", [])}
    after = {cell_key(g): g for g in candidate.get("games", [])}
    if not before or before.keys() != after.keys():
        raise SystemExit(f"{name}: empty or mismatched paired cells")

    cells = []
    for key in sorted(before):
        b, a = before[key], after[key]
        if b.get("status") != "complete" or a.get("status") != "complete":
            raise SystemExit(f"{name}: incomplete cell {key}")
        b_own, b_rival = pair_scores(b)
        a_own, a_rival = pair_scores(a)
        d_own = a_own - b_own
        d_rival = a_rival - b_rival
        d_margin = (a_own - a_rival) - (b_own - b_rival)
        cells.append({
            "opponent": key[0],
            "seed": key[1],
            "candidate_seat": key[2],
            "trace_changed": b.get("trace_sha256") != a.get("trace_sha256"),
            "control_scores": b["scores"],
            "ablation_scores": a["scores"],
            "delta_own": d_own,
            "delta_rival": d_rival,
            "delta_margin": d_margin,
        })

    return {
        "cells": cells,
        "summary": {
            "paired_cells": len(cells),
            "trace_changed_cells": sum(c["trace_changed"] for c in cells),
            "positive": sum(c["delta_margin"] > 0 for c in cells),
            "zero": sum(c["delta_margin"] == 0 for c in cells),
            "negative": sum(c["delta_margin"] < 0 for c in cells),
            "mean_delta_own": statistics.mean(c["delta_own"] for c in cells),
            "mean_delta_rival": statistics.mean(c["delta_rival"] for c in cells),
            "mean_delta_margin": statistics.mean(c["delta_margin"] for c in cells),
        },
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--control-selfplay", required=True)
    parser.add_argument("--candidate-selfplay", required=True)
    parser.add_argument("--control-arlene", required=True)
    parser.add_argument("--candidate-arlene", required=True)
    parser.add_argument("--json-out", required=True)
    parser.add_argument("--markdown-out", required=True)
    args = parser.parse_args()

    regimes = {
        "selfplay": reduce_regime("selfplay", args.control_selfplay, args.candidate_selfplay),
        "arlene": reduce_regime("arlene", args.control_arlene, args.candidate_arlene),
    }
    all_cells = [cell for regime in regimes.values() for cell in regime["cells"]]
    changed = sum(c["trace_changed"] for c in all_cells)
    positive = sum(c["delta_margin"] > 0 for c in all_cells)
    negative = sum(c["delta_margin"] < 0 for c in all_cells)
    zero = len(all_cells) - positive - negative
    mean_own = statistics.mean(c["delta_own"] for c in all_cells)
    mean_rival = statistics.mean(c["delta_rival"] for c in all_cells)
    mean_margin = statistics.mean(c["delta_margin"] for c in all_cells)

    if changed == 0:
        disposition = "REJECT_ZERO_V226_TOPUP_ACTIVATION"
    elif negative:
        disposition = "HOLD_V226_ABLATION_NEGATIVE_CELL"
    elif any(regime["summary"]["mean_delta_margin"] <= 0 for regime in regimes.values()):
        disposition = "HOLD_V226_ABLATION_REGIME_NOT_POSITIVE"
    else:
        disposition = "PROMISING_V226_TOPUP_REDUCTION_GATE_NEXT"

    result = {
        "schema": "titan-v31-a612-a6-v226-topup-ablation/v1",
        "canonical_parent": PARENT,
        "engine_ref": ENGINE_REF,
        "regimes": regimes,
        "summary": {
            "paired_cells": len(all_cells),
            "trace_changed_cells": changed,
            "delta_margin_signs": {"positive": positive, "zero": zero, "negative": negative},
            "mean_delta_own": mean_own,
            "mean_delta_rival": mean_rival,
            "mean_delta_margin": mean_margin,
            "disposition": disposition,
        },
        "truth_boundary": (
            "This isolates only V226 dynamic wheat top-ups. Native tape buys, V233 initial/daily sheep-feed buys, and V234 rescue buys remain live. "
            "A positive ablation therefore supports narrowing/removing V226 only; it does not prove all observed wheat purchases are waste or authorize package/default/submission changes."
        ),
    }
    Path(args.json_out).write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")

    lines = [
        "## A6 V226 dynamic-WHEAT-topup ablation — current a612 screen",
        "",
        f"Cells **{len(all_cells)}**; trace deltas **{changed}/{len(all_cells)}**; ΔM signs **{positive}+ / {negative}- / {zero}=**.",
        f"Aggregate mean Δown **{mean_own:+.3f}**, Δrival **{mean_rival:+.3f}**, ΔM **{mean_margin:+.3f}**.",
        "",
        f"**Disposition: `{disposition}`**",
        "",
    ]
    for name, regime in regimes.items():
        summary = regime["summary"]
        lines += [
            f"### {name}",
            f"Trace Δ {summary['trace_changed_cells']}/{summary['paired_cells']}; "
            f"ΔM signs {summary['positive']}+ / {summary['negative']}- / {summary['zero']}=; "
            f"mean Δown {summary['mean_delta_own']:+.3f}, Δrival {summary['mean_delta_rival']:+.3f}, ΔM {summary['mean_delta_margin']:+.3f}.",
            "",
            "| seed | seat | trace Δ | Δown | Δrival | ΔM |",
            "|---:|---:|:---:|---:|---:|---:|",
        ]
        for cell in regime["cells"]:
            lines.append(
                f"| {cell['seed']} | {cell['candidate_seat']} | {'yes' if cell['trace_changed'] else 'no'} | "
                f"{cell['delta_own']:+.0f} | {cell['delta_rival']:+.0f} | {cell['delta_margin']:+.0f} |"
            )
        lines.append("")
    lines.append("Truth boundary: this screen isolates V226 only; positive evidence advances only to a reviewed V226 reduction/production gate.")
    Path(args.markdown_out).write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(result["summary"], sort_keys=True))


if __name__ == "__main__":
    main()
