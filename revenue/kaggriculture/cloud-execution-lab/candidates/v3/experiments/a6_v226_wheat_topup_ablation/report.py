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
EXPECTED_SEEDS = (2611151001, 2611151002, 2611151003, 2611151004)
EXPECTED_RNG_SEED = 20260911
EXPECTED_REGIMES = {
    "selfplay": {"opponent": "a612", "opponent_entry": "baseline.py"},
    "arlene": {"opponent": "arlene", "opponent_entry": "arlene.py"},
}


def load(path: str):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _valid_sha256(value):
    return isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value)


def _strict_score(value, label):
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError(f"{label}: score must be a finite JSON number, got {value!r}")
    return value


def _validate_fingerprint(value, label, expected_entry):
    if not isinstance(value, dict):
        raise ValueError(f"{label}: fingerprint must be an object")
    if value.get("entry") != expected_entry:
        raise ValueError(f"{label}: wrong entry {value.get('entry')!r}")
    if value.get("callable") != "agent":
        raise ValueError(f"{label}: wrong callable {value.get('callable')!r}")
    if not _valid_sha256(value.get("sha256")):
        raise ValueError(f"{label}: invalid sha256 {value.get('sha256')!r}")


def validate_game(game, label, expected_opponent):
    if not isinstance(game, dict):
        raise ValueError(f"{label}: game must be an object")
    opponent = game.get("opponent")
    seed = game.get("seed")
    seat = game.get("candidate_seat")
    if opponent != expected_opponent or not isinstance(opponent, str):
        raise ValueError(f"{label}: wrong opponent {opponent!r}")
    if type(seed) is not int or seed not in EXPECTED_SEEDS:
        raise ValueError(f"{label}: invalid seed {seed!r}")
    if type(seat) is not int or seat not in (0, 1):
        raise ValueError(f"{label}: invalid candidate_seat {seat!r}")
    if game.get("status") != "complete" or not isinstance(game.get("status"), str):
        raise ValueError(f"{label}: incomplete/invalid status {game.get('status')!r}")
    if game.get("failure") is not None:
        raise ValueError(f"{label}: non-null failure {game.get('failure')!r}")
    scores = game.get("scores")
    if not isinstance(scores, list) or len(scores) != 2:
        raise ValueError(f"{label}: scores must be a two-element list")
    _strict_score(scores[0], f"{label}:scores[0]")
    _strict_score(scores[1], f"{label}:scores[1]")
    trace = game.get("trace_sha256")
    if not _valid_sha256(trace):
        raise ValueError(f"{label}: invalid trace_sha256 {trace!r}")
    return (opponent, seed, seat)


def validate_report(report, label, expected_opponent, expected_opponent_entry, expected_candidate_entry):
    if not isinstance(report, dict):
        raise ValueError(f"{label}: report must be an object")
    if report.get("schema_version") != 1 or type(report.get("schema_version")) is not int:
        raise ValueError(f"{label}: wrong schema_version {report.get('schema_version')!r}")
    if report.get("engine_ref") != ENGINE_REF:
        raise ValueError(f"{label}: wrong engine {report.get('engine_ref')!r}")
    if report.get("agent_rng_seed") != EXPECTED_RNG_SEED or type(report.get("agent_rng_seed")) is not int:
        raise ValueError(f"{label}: wrong agent_rng_seed {report.get('agent_rng_seed')!r}")
    if report.get("reproducibility", {}).get("same_trace_and_scores") is not True:
        raise ValueError(f"{label}: first-cell reproducibility failed")

    seeds = report.get("seeds")
    if not isinstance(seeds, list) or len(seeds) != len(EXPECTED_SEEDS):
        raise ValueError(f"{label}: seed panel shape mismatch")
    if any(type(seed) is not int for seed in seeds) or tuple(seeds) != EXPECTED_SEEDS:
        raise ValueError(f"{label}: seed panel mismatch {seeds!r}")

    _validate_fingerprint(report.get("candidate"), f"{label}:candidate", expected_candidate_entry)
    opponents = report.get("opponents")
    if not isinstance(opponents, dict) or set(opponents) != {expected_opponent}:
        raise ValueError(f"{label}: opponent metadata must contain exactly {expected_opponent!r}")
    _validate_fingerprint(opponents[expected_opponent], f"{label}:opponent", expected_opponent_entry)

    games = report.get("games")
    if not isinstance(games, list):
        raise ValueError(f"{label}: games must be a list")
    expected_cells = frozenset((expected_opponent, seed, seat) for seed in EXPECTED_SEEDS for seat in (0, 1))
    indexed = {}
    for index, game in enumerate(games):
        cell = validate_game(game, f"{label}:games[{index}]", expected_opponent)
        if cell in indexed:
            raise ValueError(f"{label}: duplicate paired cell {cell!r}")
        indexed[cell] = game
    if frozenset(indexed) != expected_cells:
        missing = sorted(expected_cells - frozenset(indexed))
        extra = sorted(frozenset(indexed) - expected_cells)
        raise ValueError(f"{label}: exact paired cell set mismatch missing={missing!r} extra={extra!r}")
    return indexed


def pair_scores(game):
    seat = game["candidate_seat"]
    scores = game["scores"]
    return scores[seat], scores[1 - seat]


def reduce_regime(name: str, control_path: str, candidate_path: str):
    expected = EXPECTED_REGIMES[name]
    try:
        before = validate_report(
            load(control_path), f"{name}/control", expected["opponent"], expected["opponent_entry"], "baseline.py"
        )
        after = validate_report(
            load(candidate_path), f"{name}/candidate", expected["opponent"], expected["opponent_entry"], "candidate.py"
        )
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    cells = []
    for key in sorted(before):
        b, a = before[key], after[key]
        b_own, b_rival = pair_scores(b)
        a_own, a_rival = pair_scores(a)
        d_own = a_own - b_own
        d_rival = a_rival - b_rival
        d_margin = (a_own - a_rival) - (b_own - b_rival)
        cells.append({
            "opponent": key[0],
            "seed": key[1],
            "candidate_seat": key[2],
            "trace_changed": b["trace_sha256"] != a["trace_sha256"],
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
        "schema": "titan-v31-a612-a6-v226-topup-ablation/v2",
        "canonical_parent": PARENT,
        "engine_ref": ENGINE_REF,
        "seeds": list(EXPECTED_SEEDS),
        "agent_rng_seed": EXPECTED_RNG_SEED,
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
    print(json.dumps(result["summary"], sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
