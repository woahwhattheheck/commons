#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Reduce exact live-a612 control/JIT receipts into a paired interaction verdict."""
from __future__ import annotations

import argparse
import json
import math
import statistics
from pathlib import Path

ENGINE_REF = "28b6d8af3ce73926b3d0fda1410c1ddd8384ab8c"


def load(path: str):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def key(game):
    return (game["opponent"], int(game["seed"]), int(game["candidate_seat"]))


def scores(game):
    seat = int(game["candidate_seat"])
    pair = game.get("scores")
    if (not isinstance(pair, list) or len(pair) != 2
            or not all(type(v) in (int, float) and not isinstance(v, bool) and math.isfinite(v) for v in pair)):
        raise ValueError(f"invalid terminal scores for {key(game)}: {pair!r}")
    return float(pair[seat]), float(pair[1 - seat])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("control")
    parser.add_argument("candidate")
    parser.add_argument("--json-out", required=True)
    parser.add_argument("--markdown-out", required=True)
    args = parser.parse_args()

    control = load(args.control)
    candidate = load(args.candidate)
    for label, report in (("control", control), ("candidate", candidate)):
        if report.get("engine_ref") != ENGINE_REF:
            raise SystemExit(f"{label}: wrong engine {report.get('engine_ref')!r}")
        if report.get("reproducibility", {}).get("same_trace_and_scores") is not True:
            raise SystemExit(f"{label}: first-cell reproducibility failed")
    if control.get("seeds") != candidate.get("seeds"):
        raise SystemExit("seed panel mismatch")
    if control.get("opponents") != candidate.get("opponents"):
        raise SystemExit("opponent fingerprint mismatch")

    cg = {key(g): g for g in control.get("games", [])}
    jg = {key(g): g for g in candidate.get("games", [])}
    if not cg or cg.keys() != jg.keys():
        raise SystemExit("paired cell set mismatch or empty panel")

    cells = []
    for cell_key in sorted(cg):
        before, after = cg[cell_key], jg[cell_key]
        if before.get("status") != "complete" or after.get("status") != "complete":
            raise SystemExit(f"incomplete cell {cell_key}")
        b_own, b_rival = scores(before)
        a_own, a_rival = scores(after)
        d_own = a_own - b_own
        d_rival = a_rival - b_rival
        d_margin = (a_own - a_rival) - (b_own - b_rival)
        cells.append({
            "opponent": cell_key[0],
            "seed": cell_key[1],
            "candidate_seat": cell_key[2],
            "trace_changed": before.get("trace_sha256") != after.get("trace_sha256"),
            "control_scores": before["scores"],
            "jit_scores": after["scores"],
            "delta_own": d_own,
            "delta_rival": d_rival,
            "delta_margin": d_margin,
        })

    changed = sum(c["trace_changed"] for c in cells)
    positive = sum(c["delta_margin"] > 0 for c in cells)
    negative = sum(c["delta_margin"] < 0 for c in cells)
    zero = len(cells) - positive - negative
    mean_own = statistics.mean(c["delta_own"] for c in cells)
    mean_rival = statistics.mean(c["delta_rival"] for c in cells)
    mean_margin = statistics.mean(c["delta_margin"] for c in cells)

    if changed == 0:
        disposition = "REJECT_ZERO_LIVE_TRACE_ACTIVATION"
    elif negative:
        disposition = "HOLD_LIVE_INTERACTION_REGRESSION"
    elif mean_margin <= 0:
        disposition = "HOLD_NO_POSITIVE_LIVE_MARGIN"
    else:
        disposition = "PROMISING_LIVE_INTERACTION_PACKAGE_GATE_NEXT"

    result = {
        "schema": "titan-v31-a612-jit-live-interaction/v1",
        "engine_ref": ENGINE_REF,
        "canonical_parent": "a6120d0ea1bdb75eb0da2239220efce551f624a6",
        "cells": cells,
        "summary": {
            "paired_cells": len(cells),
            "trace_changed_cells": changed,
            "delta_margin_signs": {"positive": positive, "negative": negative, "zero": zero},
            "mean_delta_own": mean_own,
            "mean_delta_rival": mean_rival,
            "mean_delta_margin": mean_margin,
            "disposition": disposition,
        },
        "truth_boundary": (
            "A trace delta is an activation proxy for the exact reviewed JIT-only wrapper, not a production-package receipt. "
            "Positive live-a612 economics only authorizes the next default-OFF materialized package gate; it does not authorize merge/default/Kaggle promotion."
        ),
    }
    Path(args.json_out).write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")

    lines = [
        "## a612 JIT live-interaction screen",
        "",
        f"Paired cells **{len(cells)}**; trace deltas **{changed}/{len(cells)}**; ΔM signs **{positive}+ / {negative}- / {zero}=**.",
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
        "Truth boundary: this is an evidence-only composition on exact shipped `a612`; no package/default bytes are changed. "
        "Trace deltas are activation proxies. A positive result advances JIT only to a materialized default-OFF package gate.",
    ]
    Path(args.markdown_out).write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(result["summary"], sort_keys=True))


if __name__ == "__main__":
    main()
