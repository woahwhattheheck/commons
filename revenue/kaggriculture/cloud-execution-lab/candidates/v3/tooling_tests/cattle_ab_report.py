#!/usr/bin/env python3
"""Reduce exact cattle-ON control vs cattle-OFF candidate evaluator receipts."""
from __future__ import annotations

import argparse
import json
import math
import statistics
from pathlib import Path

ENGINE_REF = "28b6d8af3ce73926b3d0fda1410c1ddd8384ab8c"
EXPECTED_SEEDS = [2611151001, 2611151002]
EXPECTED_OPPONENT = "cattle_on"


def load(path: Path):
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: top level must be an object")
    return value


def strict_int(value, label: str) -> int:
    if type(value) is not int:
        raise ValueError(f"{label} must be an exact integer")
    return value


def strict_number(value, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{label} must be a JSON number")
    out = float(value)
    if not math.isfinite(out):
        raise ValueError(f"{label} must be finite")
    return out


def game_key(game, label: str):
    if not isinstance(game, dict):
        raise ValueError(f"{label} game must be an object")
    opponent = game.get("opponent")
    seed = strict_int(game.get("seed"), f"{label}.seed")
    seat = strict_int(game.get("candidate_seat"), f"{label}.candidate_seat")
    if opponent != EXPECTED_OPPONENT:
        raise ValueError(f"{label}.opponent must be {EXPECTED_OPPONENT!r}")
    if seed not in EXPECTED_SEEDS or seat not in (0, 1):
        raise ValueError(f"{label} cell outside frozen panel: {(opponent, seed, seat)!r}")
    return opponent, seed, seat


def score_pair(game, label: str) -> tuple[float, float]:
    seat = strict_int(game.get("candidate_seat"), f"{label}.candidate_seat")
    scores = game.get("scores")
    if not isinstance(scores, list) or len(scores) != 2:
        raise ValueError(f"{label}.scores must be [seat0, seat1]")
    values = [strict_number(value, f"{label}.scores[{idx}]") for idx, value in enumerate(scores)]
    return values[seat], values[1 - seat]


def validate_report(report, label: str):
    if report.get("engine_ref") != ENGINE_REF:
        raise ValueError(f"{label}: wrong engine_ref {report.get('engine_ref')!r}")
    if report.get("seeds") != EXPECTED_SEEDS:
        raise ValueError(f"{label}: wrong seeds {report.get('seeds')!r}")
    opponents = report.get("opponents")
    if not isinstance(opponents, dict) or set(opponents) != {EXPECTED_OPPONENT}:
        raise ValueError(f"{label}: opponent set must be exactly {EXPECTED_OPPONENT!r}")
    reproducibility = report.get("reproducibility")
    if not isinstance(reproducibility, dict) or reproducibility.get("checked") is not True or reproducibility.get("same_trace_and_scores") is not True:
        raise ValueError(f"{label}: first-cell reproducibility did not pass")

    rows = report.get("games")
    if not isinstance(rows, list):
        raise ValueError(f"{label}: games must be a list")
    expected = {(EXPECTED_OPPONENT, seed, seat) for seed in EXPECTED_SEEDS for seat in (0, 1)}
    mapped = {}
    for index, game in enumerate(rows):
        key = game_key(game, f"{label}.games[{index}]")
        if key in mapped:
            raise ValueError(f"{label}: duplicate cell {key!r}")
        if game.get("status") != "complete" or game.get("failure") is not None:
            raise ValueError(f"{label}: incomplete cell {key!r}: {game.get('status')!r} / {game.get('failure')!r}")
        trace = game.get("trace_sha256")
        if not isinstance(trace, str) or len(trace) != 64 or any(c not in "0123456789abcdef" for c in trace):
            raise ValueError(f"{label}: malformed trace hash for {key!r}")
        score_pair(game, f"{label}.games[{index}]")
        mapped[key] = game
    if set(mapped) != expected:
        raise ValueError(f"{label}: frozen cell set mismatch")
    return mapped


def validate_materialization(receipt):
    if receipt.get("schema") != "titan-v31-cattle-conditional-ab-materialization/v1":
        raise ValueError("wrong materialization schema")
    if receipt.get("base_to_off_changed_members") != ["TITAN-CONFIG.json"]:
        raise ValueError("score-facing transform changed more than TITAN-CONFIG.json")
    if receipt.get("on_to_off_changed_members") != ["TITAN-CONFIG.json"]:
        raise ValueError("cattle A/B trees differ outside TITAN-CONFIG.json")
    on = receipt.get("control_cattle_on_config")
    off = receipt.get("candidate_cattle_off_config")
    if not isinstance(on, dict) or not isinstance(off, dict):
        raise ValueError("materialization configs missing")
    expected_common = {
        "r04_sale_window": True,
        "r04_sale_horizon": 8,
        "r04_sale_fertilizer": True,
    }
    for key, expected in expected_common.items():
        if type(on.get(key)) is not type(expected) or on.get(key) != expected:
            raise ValueError(f"control config mismatch {key}")
        if type(off.get(key)) is not type(expected) or off.get(key) != expected:
            raise ValueError(f"candidate config mismatch {key}")
    if on.get("r04_cattle_early") is not True or off.get("r04_cattle_early") is not False:
        raise ValueError("cattle boolean split is not exact")
    for key in on:
        if key == "r04_cattle_early":
            continue
        if key not in off or type(on[key]) is not type(off[key]) or on[key] != off[key]:
            raise ValueError(f"config drift outside cattle flag: {key}")
    if set(on) != set(off):
        raise ValueError("config key set drift")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("control", type=Path)
    parser.add_argument("candidate", type=Path)
    parser.add_argument("materialization", type=Path)
    parser.add_argument("--json-out", type=Path, required=True)
    parser.add_argument("--markdown-out", type=Path, required=True)
    args = parser.parse_args(argv)

    control = load(args.control)
    candidate = load(args.candidate)
    materialization = load(args.materialization)
    validate_materialization(materialization)
    control_games = validate_report(control, "control")
    candidate_games = validate_report(candidate, "candidate")

    cells = []
    for key in sorted(control_games):
        base = control_games[key]
        arm = candidate_games[key]
        base_own, base_rival = score_pair(base, f"control[{key!r}]")
        arm_own, arm_rival = score_pair(arm, f"candidate[{key!r}]")
        delta_own = arm_own - base_own
        delta_rival = arm_rival - base_rival
        delta_margin = delta_own - delta_rival
        cells.append({
            "opponent": key[0],
            "seed": key[1],
            "candidate_seat": key[2],
            "control_scores": base["scores"],
            "candidate_scores": arm["scores"],
            "control_trace_sha256": base["trace_sha256"],
            "candidate_trace_sha256": arm["trace_sha256"],
            "trace_changed": base["trace_sha256"] != arm["trace_sha256"],
            "delta_own": delta_own,
            "delta_rival": delta_rival,
            "delta_margin": delta_margin,
        })

    positives = sum(cell["delta_margin"] > 0 for cell in cells)
    negatives = sum(cell["delta_margin"] < 0 for cell in cells)
    zeros = len(cells) - positives - negatives
    trace_changed = sum(bool(cell["trace_changed"]) for cell in cells)
    mean_own = statistics.mean(cell["delta_own"] for cell in cells)
    mean_rival = statistics.mean(cell["delta_rival"] for cell in cells)
    mean_margin = statistics.mean(cell["delta_margin"] for cell in cells)

    if trace_changed == 0:
        disposition = "NO_OBSERVED_CATTLE_INTERACTION_ON_CHEAP_PANEL"
    elif mean_margin > 0 and negatives == 0:
        disposition = "SUPPORT_CATTLE_OFF_ON_EXACT_CURRENT_STACK"
    elif mean_margin > 0:
        disposition = "MIXED_BUT_POSITIVE_CATTLE_OFF_WIDEN_BEFORE_UPLOAD"
    elif mean_margin < 0:
        disposition = "SIGN_REVERSAL_HOLD_CATTLE_OFF_UPLOAD"
    else:
        disposition = "NEUTRAL_OR_MIXED_HOLD_FOR_WIDER_PANEL"

    result = {
        "schema": "titan-v31-cattle-conditional-ab/v1",
        "engine_ref": ENGINE_REF,
        "materialization": {
            "control_tree_sha256": materialization.get("control_tree_sha256"),
            "candidate_tree_sha256": materialization.get("candidate_tree_sha256"),
            "control_archive_sha256": materialization.get("control_archive_sha256"),
            "candidate_archive_sha256": materialization.get("candidate_archive_sha256"),
            "only_tree_difference": materialization.get("on_to_off_changed_members"),
        },
        "seeds": EXPECTED_SEEDS,
        "cells": cells,
        "summary": {
            "paired_cells": len(cells),
            "trace_changed_cells": trace_changed,
            "delta_margin_signs": {"positive": positives, "negative": negatives, "zero": zeros},
            "mean_delta_own": mean_own,
            "mean_delta_rival": mean_rival,
            "mean_delta_margin": mean_margin,
            "disposition": disposition,
        },
        "truth_boundary": (
            "This is a cheap exact-current-stack unilateral cattle ON/OFF interaction screen against the exact cattle-ON stack. "
            "It complements but does not replace the 1,984-game/arm opponent-diverse field result. A positive screen supports "
            "the score-facing risk-reduction decision; a sign reversal must stop the upload until widened."
        ),
    }
    args.json_out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    lines = [
        "## V3.1 cattle-off conditional A/B — exact current-stack cheap screen",
        "",
        f"Cells: **{len(cells)}**. Trace-changed: **{trace_changed}/{len(cells)}**. ",
        f"ΔM signs: **{positives}+ / {negatives}- / {zeros}=**. ",
        f"Mean Δown **{mean_own:+.3f}**, Δrival **{mean_rival:+.3f}**, ΔM **{mean_margin:+.3f}**.",
        "",
        f"**Disposition: `{disposition}`**",
        "",
        "| seed | seat | trace Δ | control ON scores | candidate OFF scores | Δown | Δrival | ΔM |",
        "|---:|---:|:---:|:---:|:---:|---:|---:|---:|",
    ]
    for cell in cells:
        lines.append(
            f"| {cell['seed']} | {cell['candidate_seat']} | {'yes' if cell['trace_changed'] else 'no'} | "
            f"`{cell['control_scores']}` | `{cell['candidate_scores']}` | {cell['delta_own']:+.0f} | "
            f"{cell['delta_rival']:+.0f} | {cell['delta_margin']:+.0f} |"
        )
    lines += [
        "",
        "Package custody: the two materialized trees differ only in `TITAN-CONFIG.json`; sale-window=true, horizon=8, "
        "sale-fertilizer=true are identical, and only cattle-early is ON vs OFF.",
        "",
        "Truth boundary: this is the conditional interaction check missing from the broader field result, not a replacement for "
        "that opponent-diverse 1,984-game/arm evidence. A sign reversal here is a stop signal; otherwise combine both receipts.",
    ]
    args.markdown_out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(result["summary"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
