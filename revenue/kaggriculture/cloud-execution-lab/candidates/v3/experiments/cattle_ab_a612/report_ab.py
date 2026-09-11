#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Paired current-package cattle OFF vs ON economics receipt."""
from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path

ENGINE_REF = "28b6d8af3ce73926b3d0fda1410c1ddd8384ab8c"


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def cell_key(game):
    return (game["opponent"], int(game["seed"]), int(game["candidate_seat"]))


def scores(game):
    seat = int(game["candidate_seat"])
    values = game["scores"]
    return float(values[seat]), float(values[1 - seat])


def outcome(margin):
    return "W" if margin > 0 else "L" if margin < 0 else "T"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("materialization")
    p.add_argument("control")
    p.add_argument("candidate")
    p.add_argument("--json-out", required=True)
    p.add_argument("--markdown-out", required=True)
    args = p.parse_args()

    materialization = load(args.materialization)
    control, candidate = load(args.control), load(args.candidate)
    if materialization.get("on_to_off_changed_members") != ["TITAN-CONFIG.json"]:
        raise SystemExit("materialization is not one-member cattle A/B")
    if materialization.get("on_to_off_changed_config_keys") != ["r04_cattle_early"]:
        raise SystemExit("materialization is not cattle-only config A/B")
    if materialization["control_config"]["r04_cattle_early"] is not True:
        raise SystemExit("control is not cattle ON")
    if materialization["candidate_config"]["r04_cattle_early"] is not False:
        raise SystemExit("candidate is not cattle OFF")
    for key in ("r04_sale_window", "r04_sale_fertilizer", "r04_strawberry_topup", "r04_no_late_sale_advance"):
        if materialization["control_config"][key] is not True or materialization["candidate_config"][key] is not True:
            raise SystemExit(f"required held-constant factor not ON: {key}")
    if materialization["control_config"]["r04_sale_horizon"] != 8 or materialization["candidate_config"]["r04_sale_horizon"] != 8:
        raise SystemExit("horizon is not fixed at 8")
    if materialization["control_config"]["r04_no_late_sale_advance_step"] != 648 or materialization["candidate_config"]["r04_no_late_sale_advance_step"] != 648:
        raise SystemExit("L3 threshold is not fixed at 648")

    for label, report in (("control", control), ("candidate", candidate)):
        if report.get("engine_ref") != ENGINE_REF:
            raise SystemExit(f"{label}: wrong engine ref")
        if report.get("seeds") != control.get("seeds"):
            raise SystemExit(f"{label}: seed mismatch")
        if report.get("opponents") != control.get("opponents"):
            raise SystemExit(f"{label}: opponent fingerprint mismatch")
        if not report.get("reproducibility", {}).get("same_trace_and_scores"):
            raise SystemExit(f"{label}: reproducibility recheck failed")

    cg = {cell_key(game): game for game in control.get("games", [])}
    og = {cell_key(game): game for game in candidate.get("games", [])}
    if not cg or cg.keys() != og.keys():
        raise SystemExit("paired cell set mismatch or empty")

    rows = []
    transitions = {}
    for key in sorted(cg):
        c, o = cg[key], og[key]
        if c.get("status") != "complete" or o.get("status") != "complete":
            raise SystemExit(f"incomplete cell {key}")
        c_own, c_rival = scores(c)
        o_own, o_rival = scores(o)
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
            "trace_changed": c.get("trace_sha256") != o.get("trace_sha256"),
        })

    pos = sum(r["delta_margin"] > 0 for r in rows)
    neg = sum(r["delta_margin"] < 0 for r in rows)
    zero = len(rows) - pos - neg
    trace = sum(r["trace_changed"] for r in rows)
    money = sum(bool(r["delta_own"] or r["delta_rival"]) for r in rows)
    mean_own = statistics.mean(r["delta_own"] for r in rows)
    mean_rival = statistics.mean(r["delta_rival"] for r in rows)
    mean_margin = statistics.mean(r["delta_margin"] for r in rows)
    median_margin = statistics.median(r["delta_margin"] for r in rows)
    control_wtl = {
        "wins": sum(r["control_margin"] > 0 for r in rows),
        "ties": sum(r["control_margin"] == 0 for r in rows),
        "losses": sum(r["control_margin"] < 0 for r in rows),
    }
    candidate_wtl = {
        "wins": sum(r["candidate_margin"] > 0 for r in rows),
        "ties": sum(r["candidate_margin"] == 0 for r in rows),
        "losses": sum(r["candidate_margin"] < 0 for r in rows),
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
        "schema": "titan-v31-a612-cattle-off-ab/v1",
        "engine_ref": ENGINE_REF,
        "materialization": materialization,
        "seeds": control["seeds"],
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
    Path(args.json_out).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")

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
    lines += ["", "Self-play is an interaction-safety screen, not final leaderboard authority. Any widening must hold the same package pair fixed against representative published opponents."]
    Path(args.markdown_out).write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(result["summary"], sort_keys=True))


if __name__ == "__main__":
    main()
