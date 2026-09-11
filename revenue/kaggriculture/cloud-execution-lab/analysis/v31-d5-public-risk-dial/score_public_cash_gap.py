#!/usr/bin/env python3
"""D5 diagnostic: measure whether the public cash gap predicts terminal tightness.

Diagnostic only.  Live features are restricted to the public farm-money pair at
predeclared checkpoints.  Terminal scores are labels, never live inputs.  Unknown
fields fail closed so hidden rival state/future observations cannot silently enter.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

INPUT_SCHEMA = "titan-v31-d5-public-cash-gap-input/v1"
OUTPUT_SCHEMA = "titan-v31-d5-public-cash-gap-report/v1"
GAME_KEYS = {"game_id", "opponent", "candidate_seat", "terminal_scores", "observations"}
OBS_KEYS = {"step", "farms_money"}


def _number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{label} must be a finite JSON number")
    value = float(value)
    if not math.isfinite(value):
        raise ValueError(f"{label} must be a finite JSON number")
    return value


def _integer(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{label} must be a JSON integer")
    return value


def _pair(value: Any, label: str) -> tuple[float, float]:
    if not isinstance(value, list) or len(value) != 2:
        raise ValueError(f"{label} must be a two-element array")
    return _number(value[0], f"{label}[0]"), _number(value[1], f"{label}[1]")


def _margin(pair: tuple[float, float], seat: int) -> float:
    return pair[seat] - pair[1 - seat]


def _sign(value: float) -> int:
    return 1 if value > 0 else (-1 if value < 0 else 0)


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _quantile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    xs = sorted(values)
    if len(xs) == 1:
        return xs[0]
    pos = (len(xs) - 1) * q
    lo, hi = int(math.floor(pos)), int(math.ceil(pos))
    if lo == hi:
        return xs[lo]
    frac = pos - lo
    return xs[lo] * (1.0 - frac) + xs[hi] * frac


def validate_input(payload: Any) -> tuple[list[int], float, list[dict[str, Any]]]:
    if not isinstance(payload, dict):
        raise ValueError("input must be a JSON object")
    if set(payload) != {"schema", "checkpoints", "tight_threshold", "games"}:
        raise ValueError("input keys must be exactly schema/checkpoints/tight_threshold/games")
    if payload["schema"] != INPUT_SCHEMA:
        raise ValueError(f"schema must be {INPUT_SCHEMA!r}")

    checkpoints = payload["checkpoints"]
    if not isinstance(checkpoints, list) or not checkpoints:
        raise ValueError("checkpoints must be a non-empty array")
    checkpoints = [_integer(v, f"checkpoints[{i}]") for i, v in enumerate(checkpoints)]
    if any(step < 0 or step >= 719 for step in checkpoints):
        raise ValueError("checkpoint steps must be in [0, 718]")
    if checkpoints != sorted(set(checkpoints)):
        raise ValueError("checkpoints must be strictly increasing and unique")

    threshold = _number(payload["tight_threshold"], "tight_threshold")
    if threshold <= 0:
        raise ValueError("tight_threshold must be > 0")

    games = payload["games"]
    if not isinstance(games, list) or not games:
        raise ValueError("games must be a non-empty array")
    seen_games: set[str] = set()
    normalized = []
    for gi, game in enumerate(games):
        if not isinstance(game, dict) or set(game) != GAME_KEYS:
            raise ValueError(f"games[{gi}] keys must be exactly {sorted(GAME_KEYS)}")
        game_id, opponent = game["game_id"], game["opponent"]
        if not isinstance(game_id, str) or not game_id.strip():
            raise ValueError(f"games[{gi}].game_id must be a non-empty string")
        if game_id in seen_games:
            raise ValueError(f"duplicate game_id {game_id!r}")
        seen_games.add(game_id)
        if not isinstance(opponent, str) or not opponent.strip():
            raise ValueError(f"games[{gi}].opponent must be a non-empty string")
        seat = _integer(game["candidate_seat"], f"games[{gi}].candidate_seat")
        if seat not in (0, 1):
            raise ValueError(f"games[{gi}].candidate_seat must be 0 or 1")
        terminal = _pair(game["terminal_scores"], f"games[{gi}].terminal_scores")

        observations = game["observations"]
        if not isinstance(observations, list):
            raise ValueError(f"games[{gi}].observations must be an array")
        by_step: dict[int, tuple[float, float]] = {}
        for oi, obs in enumerate(observations):
            if not isinstance(obs, dict) or set(obs) != OBS_KEYS:
                raise ValueError(
                    f"games[{gi}].observations[{oi}] keys must be exactly {sorted(OBS_KEYS)}"
                )
            step = _integer(obs["step"], f"games[{gi}].observations[{oi}].step")
            if step in by_step:
                raise ValueError(f"games[{gi}] has duplicate observation step {step}")
            by_step[step] = _pair(
                obs["farms_money"], f"games[{gi}].observations[{oi}].farms_money"
            )
        missing = [step for step in checkpoints if step not in by_step]
        extra = [step for step in by_step if step not in checkpoints]
        if missing or extra:
            raise ValueError(
                f"games[{gi}] observation steps must equal checkpoints; "
                f"missing={missing} extra={extra}"
            )
        normalized.append(
            {
                "game_id": game_id,
                "opponent": opponent,
                "candidate_seat": seat,
                "terminal_margin": _margin(terminal, seat),
                "checkpoint_margins": {step: _margin(by_step[step], seat) for step in checkpoints},
            }
        )
    return checkpoints, threshold, normalized


def analyze(payload: Any) -> dict[str, Any]:
    checkpoints, threshold, games = validate_input(payload)
    terminal_tight = [abs(g["terminal_margin"]) <= threshold for g in games]
    opponents = [g["opponent"] for g in games]
    rows = []
    for step in checkpoints:
        cp = [g["checkpoint_margins"][step] for g in games]
        terminal = [g["terminal_margin"] for g in games]
        cp_tight = [abs(v) <= threshold for v in cp]
        tp = sum(a and b for a, b in zip(cp_tight, terminal_tight))
        fp = sum(a and not b for a, b in zip(cp_tight, terminal_tight))
        fn = sum((not a) and b for a, b in zip(cp_tight, terminal_tight))
        tn = len(games) - tp - fp - fn
        sign_same = sum(_sign(a) == _sign(b) for a, b in zip(cp, terminal))
        reversals = sum(
            _sign(a) != 0 and _sign(b) != 0 and _sign(a) != _sign(b)
            for a, b in zip(cp, terminal)
        )
        swings = [b - a for a, b in zip(cp, terminal)]
        abs_errors = [abs(v) for v in swings]
        rows.append(
            {
                "step": step,
                "n": len(games),
                "checkpoint_tight_n": sum(cp_tight),
                "terminal_tight_n": sum(terminal_tight),
                "tight_confusion": {"tp": tp, "fp": fp, "fn": fn, "tn": tn},
                "tight_precision": (tp / (tp + fp)) if (tp + fp) else None,
                "tight_recall": (tp / (tp + fn)) if (tp + fn) else None,
                "sign_agreement_rate": sign_same / len(games),
                "strict_sign_reversals": reversals,
                "mean_abs_terminal_swing": _mean(abs_errors),
                "median_abs_terminal_swing": _quantile(abs_errors, 0.5),
                "p90_abs_terminal_swing": _quantile(abs_errors, 0.9),
                "max_abs_terminal_swing": max(abs_errors),
                "checkpoint_margin_mean": _mean(cp),
                "terminal_margin_mean": _mean(terminal),
            }
        )

    return {
        "schema": OUTPUT_SCHEMA,
        "truth_boundary": (
            "diagnostic only: public farm money is the sole live feature; terminal scores are labels"
        ),
        "games": len(games),
        "unique_opponents": len(set(opponents)),
        "all_opponents_unique": len(set(opponents)) == len(opponents),
        "tight_threshold": threshold,
        "checkpoints": rows,
        "policy_authorized": False,
        "required_next": (
            "Choose any gameplay threshold/policy before a new holdout; validate on opponent-disjoint "
            "games with paired competitive economics and D3 externality screening."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input_json", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    payload = json.loads(args.input_json.read_text(encoding="utf-8"))
    report = analyze(payload)
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
