#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Paired current-package cattle OFF vs ON economics receipt.

The reducer accepts only the exact native evaluator schema emitted by the pinned
driver for the workflow-requested 8-seed x 2-seat cattle_on panel. Receipt
normalization rejects coercible aliases, duplicate/substituted cells, non-finite
scores, malformed fingerprints/traces, and incomplete/failed games before any
economics are computed.
"""
from __future__ import annotations

import argparse
import json
import math
import statistics
from pathlib import Path

ENGINE_REF = "28b6d8af3ce73926b3d0fda1410c1ddd8384ab8c"
EXPECTED_RNG_SEED = 20260911
EXPECTED_SEEDS = (
    2611152001,
    2611152002,
    2611152003,
    2611152004,
    2611152005,
    2611152006,
    2611152007,
    2611152008,
)
EXPECTED_OPPONENT = "cattle_on"
EXPECTED_KEYS = frozenset(
    (EXPECTED_OPPONENT, seed, seat)
    for seed in EXPECTED_SEEDS
    for seat in (0, 1)
)


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
    if type(value) not in (int, float) or not math.isfinite(value):
        raise SystemExit(f"{label}: expected finite number")
    return value


def strict_trace(value, label):
    if not isinstance(value, str) or len(value) != 64:
        raise SystemExit(f"{label}: expected sha256 trace")
    try:
        int(value, 16)
    except ValueError as exc:
        raise SystemExit(f"{label}: expected sha256 trace") from exc
    return value


def strict_fingerprint(value, label):
    if not isinstance(value, dict):
        raise SystemExit(f"{label}: fingerprint must be an object")
    if value.get("entry") != "main.py":
        raise SystemExit(f"{label}: expected main.py entry")
    if value.get("callable") != "agent":
        raise SystemExit(f"{label}: expected agent callable")
    strict_trace(value.get("sha256"), f"{label}.sha256")
    return value


def normalized_games(report, label):
    if not isinstance(report, dict):
        raise SystemExit(f"{label}: receipt must be an object")
    if report.get("schema_version") != 1 or type(report.get("schema_version")) is not int:
        raise SystemExit(f"{label}: wrong schema_version {report.get('schema_version')!r}")
    if report.get("engine_ref") != ENGINE_REF:
        raise SystemExit(f"{label}: wrong engine ref {report.get('engine_ref')!r}")
    if report.get("agent_rng_seed") != EXPECTED_RNG_SEED or type(report.get("agent_rng_seed")) is not int:
        raise SystemExit(f"{label}: wrong agent_rng_seed {report.get('agent_rng_seed')!r}")

    seeds = report.get("seeds")
    opponents = report.get("opponents")
    games = report.get("games")
    if not isinstance(seeds, list):
        raise SystemExit(f"{label}: missing seeds metadata")
    if not isinstance(opponents, dict):
        raise SystemExit(f"{label}: opponents metadata must use native evaluator mapping")
    if not isinstance(games, list) or not games:
        raise SystemExit(f"{label}: missing games")

    if len(seeds) != len(EXPECTED_SEEDS):
        raise SystemExit(f"{label}: requested seed panel length mismatch")
    seen_seed_metadata = set()
    for index, (seed, expected) in enumerate(zip(seeds, EXPECTED_SEEDS)):
        strict_int(seed, f"{label}.seeds[{index}]")
        if seed in seen_seed_metadata:
            raise SystemExit(f"{label}: duplicate seed metadata {seed!r}")
        seen_seed_metadata.add(seed)
        if seed != expected:
            raise SystemExit(
                f"{label}.seeds[{index}]: unexpected seed {seed!r}; requested {expected!r}"
            )

    if set(opponents) != {EXPECTED_OPPONENT}:
        raise SystemExit(
            f"{label}: opponent metadata must contain exactly {EXPECTED_OPPONENT!r}"
        )
    strict_fingerprint(opponents[EXPECTED_OPPONENT], f"{label}.opponents[{EXPECTED_OPPONENT!r}]")
    strict_fingerprint(report.get("candidate"), f"{label}.candidate")

    reproducibility = report.get("reproducibility")
    if not isinstance(reproducibility, dict) or reproducibility.get("same_trace_and_scores") is not True:
        raise SystemExit(f"{label}: reproducibility recheck failed")

    result = {}
    for index, game in enumerate(games):
        if not isinstance(game, dict):
            raise SystemExit(f"{label}.games[{index}]: expected object")
        if game.get("status") != "complete" or not isinstance(game.get("status"), str):
            raise SystemExit(f"{label}.games[{index}]: incomplete status {game.get('status')!r}")
        if game.get("failure") is not None:
            raise SystemExit(f"{label}.games[{index}]: non-null failure {game.get('failure')!r}")

        opponent = game.get("opponent")
        if opponent != EXPECTED_OPPONENT or not isinstance(opponent, str):
            raise SystemExit(f"{label}.games[{index}]: undeclared opponent {opponent!r}")
        seed = strict_int(game.get("seed"), f"{label}.games[{index}].seed")
        if seed not in EXPECTED_SEEDS:
            raise SystemExit(f"{label}.games[{index}]: undeclared seed {seed!r}")
        seat = strict_int(game.get("candidate_seat"), f"{label}.games[{index}].candidate_seat")
        if seat not in (0, 1):
            raise SystemExit(f"{label}.games[{index}]: seat must be 0/1")

        values = game.get("scores")
        if not isinstance(values, list) or len(values) != 2:
            raise SystemExit(f"{label}.games[{index}]: scores must be [seat0, seat1]")
        normalized_scores = [
            finite_number(values[0], f"{label}.games[{index}].scores[0]"),
            finite_number(values[1], f"{label}.games[{index}].scores[1]"),
        ]
        trace = strict_trace(game.get("trace_sha256"), f"{label}.games[{index}].trace_sha256")

        key = (opponent, seed, seat)
        if key in result:
            raise SystemExit(f"{label}: duplicate paired cell {key!r}")
        normalized = dict(game)
        normalized["scores"] = normalized_scores
        normalized["trace_sha256"] = trace
        result[key] = normalized

    actual_keys = frozenset(result)
    if actual_keys != EXPECTED_KEYS:
        missing = sorted(EXPECTED_KEYS - actual_keys)
        extra = sorted(actual_keys - EXPECTED_KEYS)
        raise SystemExit(
            f"{label}: exact requested coverage mismatch: missing={missing!r} extra={extra!r}"
        )
    return result


def scores(game, key):
    seat = key[2]
    values = game["scores"]
    return values[seat], values[1 - seat]


def outcome(margin):
    return "W" if margin > 0 else "L" if margin < 0 else "T"


def validate_materialization(materialization):
    if not isinstance(materialization, dict):
        raise SystemExit("materialization receipt must be an object")
    on_package_sha256 = strict_trace(
        materialization.get("on_package_sha256"), "materialization.on_package_sha256"
    )
    off_package_sha256 = strict_trace(
        materialization.get("off_package_sha256"), "materialization.off_package_sha256"
    )
    if on_package_sha256 == off_package_sha256:
        raise SystemExit("materialization package digests are identical; cattle A/B did not materialize")
    if materialization.get("on_to_off_changed_members") != ["TITAN-CONFIG.json"]:
        raise SystemExit("materialization is not one-member cattle A/B")
    if materialization.get("on_to_off_changed_config_keys") != ["r04_cattle_early"]:
        raise SystemExit("materialization is not cattle-only config A/B")
    control_config = materialization.get("control_config")
    candidate_config = materialization.get("candidate_config")
    if not isinstance(control_config, dict) or not isinstance(candidate_config, dict):
        raise SystemExit("materialization configs must be objects")
    if control_config.get("r04_cattle_early") is not True:
        raise SystemExit("control is not cattle ON")
    if candidate_config.get("r04_cattle_early") is not False:
        raise SystemExit("candidate is not cattle OFF")
    for key in (
        "r04_sale_window",
        "r04_sale_fertilizer",
        "r04_strawberry_topup",
        "r04_no_late_sale_advance",
    ):
        if control_config.get(key) is not True or candidate_config.get(key) is not True:
            raise SystemExit(f"required held-constant factor not ON: {key}")
    if type(control_config.get("r04_sale_horizon")) is not int or control_config["r04_sale_horizon"] != 8:
        raise SystemExit("control horizon is not literal int 8")
    if type(candidate_config.get("r04_sale_horizon")) is not int or candidate_config["r04_sale_horizon"] != 8:
        raise SystemExit("candidate horizon is not literal int 8")
    if type(control_config.get("r04_no_late_sale_advance_step")) is not int or control_config["r04_no_late_sale_advance_step"] != 648:
        raise SystemExit("control L3 threshold is not literal int 648")
    if type(candidate_config.get("r04_no_late_sale_advance_step")) is not int or candidate_config["r04_no_late_sale_advance_step"] != 648:
        raise SystemExit("candidate L3 threshold is not literal int 648")


def validate_receipt_pair(control_raw, candidate_raw):
    if control_raw["opponents"] != candidate_raw["opponents"]:
        raise SystemExit("fixed cattle_on opponent fingerprint drifted across arms")
    if control_raw["candidate"] != candidate_raw["candidate"]:
        raise SystemExit("shared candidate entry fingerprint drifted across cattle A/B arms")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("materialization")
    parser.add_argument("control")
    parser.add_argument("candidate")
    parser.add_argument("--json-out", required=True)
    parser.add_argument("--markdown-out", required=True)
    args = parser.parse_args()

    materialization = load(args.materialization)
    control_raw, candidate_raw = load(args.control), load(args.candidate)
    validate_materialization(materialization)
    control = normalized_games(control_raw, "control")
    candidate = normalized_games(candidate_raw, "candidate")
    if control.keys() != candidate.keys():
        raise SystemExit("paired cell key mismatch")
    validate_receipt_pair(control_raw, candidate_raw)

    rows = []
    transitions = {}
    for key in sorted(EXPECTED_KEYS):
        c, o = control[key], candidate[key]
        c_own, c_rival = scores(c, key)
        o_own, o_rival = scores(o, key)
        c_margin = c_own - c_rival
        o_margin = o_own - o_rival
        transition = f"{outcome(c_margin)}->{outcome(o_margin)}"
        transitions[transition] = transitions.get(transition, 0) + 1
        rows.append({
            "opponent": key[0],
            "seed": key[1],
            "candidate_seat": key[2],
            "control_scores": c["scores"],
            "candidate_scores": o["scores"],
            "control_margin": c_margin,
            "candidate_margin": o_margin,
            "delta_own": o_own - c_own,
            "delta_rival": o_rival - c_rival,
            "delta_margin": o_margin - c_margin,
            "outcome_transition": transition,
            "trace_changed": c["trace_sha256"] != o["trace_sha256"],
        })

    pos = sum(row["delta_margin"] > 0 for row in rows)
    neg = sum(row["delta_margin"] < 0 for row in rows)
    zero = len(rows) - pos - neg
    trace = sum(row["trace_changed"] for row in rows)
    money = sum(bool(row["delta_own"] or row["delta_rival"]) for row in rows)
    mean_own = statistics.mean(row["delta_own"] for row in rows)
    mean_rival = statistics.mean(row["delta_rival"] for row in rows)
    mean_margin = statistics.mean(row["delta_margin"] for row in rows)
    median_margin = statistics.median(row["delta_margin"] for row in rows)
    control_wtl = {
        "wins": sum(row["control_margin"] > 0 for row in rows),
        "ties": sum(row["control_margin"] == 0 for row in rows),
        "losses": sum(row["control_margin"] < 0 for row in rows),
    }
    candidate_wtl = {
        "wins": sum(row["candidate_margin"] > 0 for row in rows),
        "ties": sum(row["candidate_margin"] == 0 for row in rows),
        "losses": sum(row["candidate_margin"] < 0 for row in rows),
    }

    if trace == 0:
        disposition = "HOLD_ZERO_POLICY_DELTA"
    elif money == 0:
        disposition = "HOLD_POLICY_DELTA_NO_MONEY_REALIZATION"
    elif neg:
        disposition = "HOLD_NEGATIVE_CURRENT_STACK_CELL"
    elif pos:
        disposition = "PASS_CHEAP_SELFPLAY_WIDEN_OPPONENT_DIVERSITY"
    else:
        disposition = "HOLD_MARGIN_NEUTRAL"

    result = {
        "schema": "titan-v31-a612-cattle-off-ab/v2",
        "engine_ref": ENGINE_REF,
        "materialization": materialization,
        "seeds": list(EXPECTED_SEEDS),
        "opponents": [EXPECTED_OPPONENT],
        "cells": rows,
        "summary": {
            "paired_cells": len(rows),
            "trace_changed_cells": trace,
            "money_changed_cells": money,
            "delta_margin_signs": {"positive": pos, "negative": neg, "zero": zero},
            "mean_delta_own": mean_own,
            "mean_delta_rival": mean_rival,
            "mean_delta_margin": mean_margin,
            "median_delta_margin": median_margin,
            "control_wtl": control_wtl,
            "candidate_wtl": candidate_wtl,
            "outcome_transitions": transitions,
            "disposition": disposition,
        },
        "truth_boundary": "Current-package self-play interaction gate only; opponent-diverse widening is still required before submission authority.",
    }
    Path(args.json_out).write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")

    lines = [
        "## Cattle OFF vs ON — exact a612 score-facing package A/B",
        "",
        f"Packages differ only in `TITAN-CONFIG.json:r04_cattle_early` (`true -> false`). Engine `{ENGINE_REF}`.",
        "",
        f"Paired cells **{len(rows)}** · trace deltas **{trace}/{len(rows)}** · money deltas **{money}/{len(rows)}**.",
        "",
        f"ΔM signs **{pos}+ / {neg}- / {zero}=** · mean Δown **{mean_own:+.3f}** · mean Δrival **{mean_rival:+.3f}** · mean ΔM **{mean_margin:+.3f}** · median ΔM **{median_margin:+.3f}**.",
        "",
        f"Control W/T/L **{control_wtl['wins']}/{control_wtl['ties']}/{control_wtl['losses']}** → cattle-OFF **{candidate_wtl['wins']}/{candidate_wtl['ties']}/{candidate_wtl['losses']}**.",
        "",
        f"Transitions: `{json.dumps(transitions, sort_keys=True)}`",
        "",
        f"**Disposition: `{disposition}`**",
        "",
        "| seed | seat | control | off | Δown | Δrival | ΔM | transition | trace Δ |",
        "|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|",
    ]
    for row in rows:
        lines.append(
            f"| {row['seed']} | {row['candidate_seat']} | {row['control_margin']:+.0f} | {row['candidate_margin']:+.0f} | "
            f"{row['delta_own']:+.0f} | {row['delta_rival']:+.0f} | {row['delta_margin']:+.0f} | {row['outcome_transition']} | {'yes' if row['trace_changed'] else 'no'} |"
        )
    lines += [
        "",
        "Self-play is an interaction-safety screen, not final leaderboard authority. Any widening must hold the same package pair fixed against representative published opponents.",
    ]
    Path(args.markdown_out).write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(result["summary"], sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
