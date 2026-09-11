#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Reduce exact a612 V219-ablation receipts across self-play and Arlene.

This evidence reducer binds the literal workflow-requested engine, seeds,
opponent and both seats for each regime. Duplicate, missing, substituted,
type-confused or non-finite cells fail closed before economics are summarized.
"""
from __future__ import annotations

import argparse
import json
import math
import statistics
from pathlib import Path

ENGINE_REF = "28b6d8af3ce73926b3d0fda1410c1ddd8384ab8c"
PARENT = "a6120d0ea1bdb75eb0da2239220efce551f624a6"
EXPECTED_SEEDS = (2611151001, 2611151002, 2611151003, 2611151004)
EXPECTED_OPPONENT = {"selfplay": "a612", "arlene": "arlene"}


def load(path: str):
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
        raise SystemExit(f"{label}: expected finite non-bool number")
    return float(value)


def normalized_games(report, label: str, opponent: str):
    if report.get("engine_ref") != ENGINE_REF:
        raise SystemExit(f"{label}: wrong engine {report.get('engine_ref')!r}")
    if report.get("reproducibility", {}).get("same_trace_and_scores") is not True:
        raise SystemExit(f"{label}: first-cell reproducibility failed")
    seeds, opponents, games = report.get("seeds"), report.get("opponents"), report.get("games")
    if not isinstance(seeds, list) or not isinstance(opponents, list):
        raise SystemExit(f"{label}: missing seeds/opponents metadata")
    if not isinstance(games, list) or not games:
        raise SystemExit(f"{label}: missing games")
    if len(seeds) != len(EXPECTED_SEEDS):
        raise SystemExit(f"{label}: requested seed panel length mismatch")
    for index, (seed, expected) in enumerate(zip(seeds, EXPECTED_SEEDS)):
        strict_int(seed, f"{label}.seeds[{index}]")
        if seed != expected:
            raise SystemExit(f"{label}.seeds[{index}]: unexpected seed {seed!r}; requested {expected!r}")
    if len(opponents) != 1 or not isinstance(opponents[0], str) or opponents[0] != opponent:
        raise SystemExit(f"{label}: unexpected opponent metadata {opponents!r}; requested {[opponent]!r}")

    expected_keys = frozenset((opponent, seed, seat) for seed in EXPECTED_SEEDS for seat in (0, 1))
    result = {}
    for index, game in enumerate(games):
        if not isinstance(game, dict):
            raise SystemExit(f"{label}.games[{index}]: expected object")
        if game.get("status") != "complete":
            raise SystemExit(f"{label}.games[{index}]: incomplete status {game.get('status')!r}")
        game_opponent = game.get("opponent")
        if not isinstance(game_opponent, str) or game_opponent != opponent:
            raise SystemExit(f"{label}.games[{index}]: undeclared opponent {game_opponent!r}")
        seed = strict_int(game.get("seed"), f"{label}.games[{index}].seed")
        if seed not in EXPECTED_SEEDS:
            raise SystemExit(f"{label}.games[{index}]: undeclared seed {seed!r}")
        seat = strict_int(game.get("candidate_seat"), f"{label}.games[{index}].candidate_seat")
        if seat not in (0, 1):
            raise SystemExit(f"{label}.games[{index}]: seat must be 0/1")
        scores = game.get("scores")
        if not isinstance(scores, list) or len(scores) != 2:
            raise SystemExit(f"{label}.games[{index}]: scores must be [seat0, seat1]")
        normalized_scores = [
            finite_number(scores[0], f"{label}.games[{index}].scores[0]"),
            finite_number(scores[1], f"{label}.games[{index}].scores[1]"),
        ]
        trace = game.get("trace_sha256")
        if not isinstance(trace, str) or not trace:
            raise SystemExit(f"{label}.games[{index}]: missing trace sha")
        key = (game_opponent, seed, seat)
        if key in result:
            raise SystemExit(f"{label}: duplicate paired cell {key!r}")
        row = dict(game)
        row["scores"] = normalized_scores
        result[key] = row
    actual_keys = frozenset(result)
    if actual_keys != expected_keys:
        raise SystemExit(
            f"{label}: exact requested coverage mismatch: "
            f"missing={sorted(expected_keys-actual_keys)!r} extra={sorted(actual_keys-expected_keys)!r}"
        )
    return result


def reduce_regime(name: str, control_path: str, candidate_path: str):
    if name not in EXPECTED_OPPONENT:
        raise SystemExit(f"unknown regime {name!r}")
    opponent = EXPECTED_OPPONENT[name]
    before = normalized_games(load(control_path), f"{name}/control", opponent)
    after = normalized_games(load(candidate_path), f"{name}/candidate", opponent)
    if before.keys() != after.keys():
        raise SystemExit(f"{name}: paired cell key mismatch")
    cells = []
    for key in sorted((opponent, seed, seat) for seed in EXPECTED_SEEDS for seat in (0, 1)):
        b, a = before[key], after[key]
        seat = key[2]
        b_own, b_rival = b["scores"][seat], b["scores"][1-seat]
        a_own, a_rival = a["scores"][seat], a["scores"][1-seat]
        d_own, d_rival = a_own-b_own, a_rival-b_rival
        cells.append({
            "opponent": key[0], "seed": key[1], "candidate_seat": seat,
            "trace_changed": b["trace_sha256"] != a["trace_sha256"],
            "control_scores": b["scores"], "ablation_scores": a["scores"],
            "delta_own": d_own, "delta_rival": d_rival, "delta_margin": d_own-d_rival,
        })
    return {"cells": cells, "summary": {
        "paired_cells": len(cells),
        "trace_changed_cells": sum(c["trace_changed"] for c in cells),
        "positive": sum(c["delta_margin"] > 0 for c in cells),
        "zero": sum(c["delta_margin"] == 0 for c in cells),
        "negative": sum(c["delta_margin"] < 0 for c in cells),
        "mean_delta_own": statistics.mean(c["delta_own"] for c in cells),
        "mean_delta_rival": statistics.mean(c["delta_rival"] for c in cells),
        "mean_delta_margin": statistics.mean(c["delta_margin"] for c in cells),
    }}


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
    zero = len(all_cells)-positive-negative
    mean_own = statistics.mean(c["delta_own"] for c in all_cells)
    mean_rival = statistics.mean(c["delta_rival"] for c in all_cells)
    mean_margin = statistics.mean(c["delta_margin"] for c in all_cells)
    if changed == 0:
        disposition = "REJECT_ZERO_V219_ABLATION_ACTIVATION"
    elif negative:
        disposition = "HOLD_V219_ABLATION_NEGATIVE_CELL"
    elif any(regime["summary"]["mean_delta_margin"] <= 0 for regime in regimes.values()):
        disposition = "HOLD_V219_ABLATION_REGIME_NOT_POSITIVE"
    else:
        disposition = "PROMISING_V219_DELETION_PRODUCTION_GATE_NEXT"
    result = {
        "schema": "titan-v31-a612-a1-kill-v219/v1", "canonical_parent": PARENT,
        "engine_ref": ENGINE_REF, "seeds": list(EXPECTED_SEEDS), "opponents": dict(EXPECTED_OPPONENT),
        "regimes": regimes,
        "summary": {"paired_cells": len(all_cells), "trace_changed_cells": changed,
                    "delta_margin_signs": {"positive": positive, "zero": zero, "negative": negative},
                    "mean_delta_own": mean_own, "mean_delta_rival": mean_rival,
                    "mean_delta_margin": mean_margin, "disposition": disposition},
        "truth_boundary": "Evidence-only V219 qualification ablation on exact shipped a612; positive evidence advances only to a reviewed default-OFF seam plus materialized identity/reachability and wider D3 economics.",
    }
    Path(args.json_out).write_text(json.dumps(result, indent=2, allow_nan=False)+"\n", encoding="utf-8")
    lines = ["## A1 V219 late-TOMATO ablation — current a612 screen", "",
             f"Cells **{len(all_cells)}**; trace deltas **{changed}/{len(all_cells)}**; ΔM signs **{positive}+ / {negative}- / {zero}=**.",
             f"Aggregate mean Δown **{mean_own:+.3f}**, Δrival **{mean_rival:+.3f}**, ΔM **{mean_margin:+.3f}**.", "",
             f"**Disposition: `{disposition}`**", ""]
    for name, regime in regimes.items():
        summary = regime["summary"]
        lines += [f"### {name}",
                  f"Trace Δ {summary['trace_changed_cells']}/{summary['paired_cells']}; ΔM signs {summary['positive']}+ / {summary['negative']}- / {summary['zero']}=; mean Δown {summary['mean_delta_own']:+.3f}, Δrival {summary['mean_delta_rival']:+.3f}, ΔM {summary['mean_delta_margin']:+.3f}.", "",
                  "| seed | seat | trace Δ | Δown | Δrival | ΔM |", "|---:|---:|:---:|---:|---:|---:|"]
        for cell in regime["cells"]:
            lines.append(f"| {cell['seed']} | {cell['candidate_seat']} | {'yes' if cell['trace_changed'] else 'no'} | {cell['delta_own']:+.0f} | {cell['delta_rival']:+.0f} | {cell['delta_margin']:+.0f} |")
        lines.append("")
    lines.append("Truth boundary: positive evidence advances only to a default-OFF production/package gate; it is not merge/default/Kaggle authority.")
    Path(args.markdown_out).write_text("\n".join(lines)+"\n", encoding="utf-8")
    print(json.dumps(result["summary"], sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
