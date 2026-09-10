#!/usr/bin/env python3
"""Fail-closed 2×2 gameplay admission for strict-dominance × own-value.

Input is a JSON array or JSONL stream.  Every row must bind an arm, opponent,
seat, seed, own/rival terminal cash, outcome, and the tested actor's returned-
action trace hash.  The analyzer requires a complete four-arm grid and reports
main effects in both contexts plus the cellwise interaction term.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import json
import math
import string
from pathlib import Path
from statistics import mean, median
from typing import Iterable

ARMS = ("incumbent", "strict-only", "own-only", "combined")
OUTCOMES = {"win": 1, "tie": 0, "loss": -1}


def load_rows(path: Path) -> list[dict]:
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        raise ValueError("empty gameplay ledger")
    if text.startswith("["):
        rows = json.loads(text)
    else:
        rows = [json.loads(line) for line in text.splitlines() if line.strip()]
    if not isinstance(rows, list) or not rows:
        raise ValueError("gameplay ledger must contain rows")
    return rows


def _number(row: dict, name: str) -> float:
    value = row.get(name)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be numeric")
    value = float(value)
    if not math.isfinite(value):
        raise ValueError(f"{name} must be finite")
    return value


def normalize(rows: Iterable[dict]) -> dict[tuple, dict[str, dict]]:
    grid: dict[tuple, dict[str, dict]] = defaultdict(dict)
    for raw in rows:
        if not isinstance(raw, dict):
            raise ValueError("every gameplay row must be an object")
        arm = raw.get("arm")
        if arm not in ARMS:
            raise ValueError(f"unknown arm {arm!r}")
        opponent = raw.get("opponent")
        seat = raw.get("seat")
        seed = raw.get("seed")
        trace = raw.get("candidate_action_trace_sha256")
        if not isinstance(opponent, str) or not opponent:
            raise ValueError("opponent must be a non-empty string")
        if isinstance(seat, bool) or seat not in (0, 1):
            raise ValueError("seat must be 0 or 1")
        if isinstance(seed, bool) or not isinstance(seed, int):
            raise ValueError("seed must be an integer")
        if (not isinstance(trace, str) or len(trace) != 64
                or any(character not in string.hexdigits for character in trace)):
            raise ValueError(
                "candidate_action_trace_sha256 must be a 64-character hex digest"
            )
        trace = trace.lower()
        outcome = raw.get("outcome")
        if outcome not in OUTCOMES:
            raise ValueError("outcome must be win, tie, or loss")
        row = {
            "arm": arm,
            "opponent": opponent,
            "seat": seat,
            "seed": seed,
            "own_cash": _number(raw, "own_cash"),
            "rival_cash": _number(raw, "rival_cash"),
            "outcome": outcome,
            "outcome_value": OUTCOMES[outcome],
            "candidate_action_trace_sha256": trace,
        }
        row["margin"] = row["own_cash"] - row["rival_cash"]
        key = (opponent, seat, seed)
        if arm in grid[key]:
            raise ValueError(f"duplicate arm {arm} for cell {key}")
        grid[key][arm] = row

    for key, arms in grid.items():
        missing = set(ARMS) - set(arms)
        extra = set(arms) - set(ARMS)
        if missing or extra:
            raise ValueError(
                f"incomplete factorial cell {key}: missing={sorted(missing)} "
                f"extra={sorted(extra)}"
            )
    return dict(grid)


def summarize(values: list[float]) -> dict:
    return {
        "n": len(values),
        "mean": mean(values),
        "median": median(values),
        "positive": sum(v > 0 for v in values),
        "zero": sum(v == 0 for v in values),
        "negative": sum(v < 0 for v in values),
        "minimum": min(values),
        "maximum": max(values),
        "total": sum(values),
    }


def analyze(rows: Iterable[dict]) -> dict:
    grid = normalize(rows)
    cell_reports: list[dict] = []
    metrics = ("own_cash", "margin", "outcome_value")
    effects: dict[str, dict[str, list[float]]] = {
        metric: defaultdict(list) for metric in metrics
    }
    activations = {"strict": 0, "own": 0, "combined": 0}
    new_losses = 0
    lost_wins = 0

    for (opponent, seat, seed), arms in sorted(grid.items()):
        base = arms["incumbent"]
        strict = arms["strict-only"]
        own = arms["own-only"]
        combined = arms["combined"]
        activations["strict"] += strict["candidate_action_trace_sha256"] != base[
            "candidate_action_trace_sha256"
        ]
        activations["own"] += own["candidate_action_trace_sha256"] != base[
            "candidate_action_trace_sha256"
        ]
        activations["combined"] += combined[
            "candidate_action_trace_sha256"
        ] != base["candidate_action_trace_sha256"]
        new_losses += base["outcome"] != "loss" and combined["outcome"] == "loss"
        lost_wins += base["outcome"] == "win" and combined["outcome"] != "win"

        report = {"opponent": opponent, "seat": seat, "seed": seed, "effects": {}}
        for metric in metrics:
            y00 = base[metric]
            y10 = strict[metric]
            y01 = own[metric]
            y11 = combined[metric]
            values = {
                "strict_at_incumbent": y10 - y00,
                "strict_at_own": y11 - y01,
                "own_at_incumbent": y01 - y00,
                "own_at_strict": y11 - y10,
                "combined_vs_incumbent": y11 - y00,
                "interaction": y11 - y10 - y01 + y00,
            }
            report["effects"][metric] = values
            for name, value in values.items():
                effects[metric][name].append(value)
        cell_reports.append(report)

    aggregate = {
        metric: {name: summarize(values) for name, values in metric_effects.items()}
        for metric, metric_effects in effects.items()
    }

    strata: dict[str, dict] = {}
    for opponent, seat in sorted({(key[0], key[1]) for key in grid}):
        selected = [
            cell
            for cell in cell_reports
            if cell["opponent"] == opponent and cell["seat"] == seat
        ]
        name = f"{opponent}|seat={seat}"
        strata[name] = {
            metric: {
                effect: summarize(
                    [cell["effects"][metric][effect] for cell in selected]
                )
                for effect in (
                    "strict_at_incumbent",
                    "strict_at_own",
                    "own_at_incumbent",
                    "own_at_strict",
                    "combined_vs_incumbent",
                )
            }
            for metric in ("own_cash", "margin")
        }

    reasons: list[str] = []
    if activations["strict"] == 0:
        reasons.append("strict factor did not activate returned actions")
    if activations["own"] == 0:
        reasons.append("own-value factor did not activate returned actions")
    if activations["combined"] == 0:
        reasons.append("combined arm did not activate returned actions")
    if new_losses:
        reasons.append(f"combined arm introduced {new_losses} new losses")
    if lost_wins:
        reasons.append(f"combined arm lost {lost_wins} incumbent wins")

    # Require each factor to remain nonnegative both alone and in the presence
    # of the other factor.  This is stricter than accepting a positive total
    # whose interaction masks one harmful main effect.
    for metric in ("own_cash", "margin"):
        for effect in (
            "strict_at_incumbent",
            "strict_at_own",
            "own_at_incumbent",
            "own_at_strict",
            "combined_vs_incumbent",
        ):
            summary = aggregate[metric][effect]
            if summary["mean"] < 0:
                reasons.append(f"negative aggregate {metric} {effect}")
        combined = aggregate[metric]["combined_vs_incumbent"]
        if combined["positive"] < combined["negative"]:
            reasons.append(f"more negative than positive combined {metric} cells")

    for name, report in strata.items():
        for metric in ("own_cash", "margin"):
            for effect in (
                "strict_at_incumbent",
                "strict_at_own",
                "own_at_incumbent",
                "own_at_strict",
                "combined_vs_incumbent",
            ):
                if report[metric][effect]["mean"] < 0:
                    reasons.append(f"negative stratum {name} {metric} {effect}")

    return {
        "schema": "titan-v3-factorial-admission/v1",
        "verdict": "ADMIT" if not reasons else "REJECT",
        "cells": len(grid),
        "rows": len(grid) * len(ARMS),
        "activations": activations,
        "new_losses": new_losses,
        "lost_wins": lost_wins,
        "aggregate": aggregate,
        "strata": strata,
        "reasons": reasons,
        "promotion_authorized": False,
        "cell_effects": cell_reports,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = analyze(load_rows(args.ledger))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["verdict"] == "ADMIT" else 1


if __name__ == "__main__":
    raise SystemExit(main())
