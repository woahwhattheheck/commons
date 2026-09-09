#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Strict paired-game comparison for TITAN candidate panels."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

Key = tuple[str, int, int]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _sign(value: float) -> int:
    return 1 if value > 0 else -1 if value < 0 else 0


def _label(value: int) -> str:
    return {-1: "L", 0: "T", 1: "W"}[value]


def load_games(path: Path) -> dict[Key, dict[str, Any]]:
    games: dict[Key, dict[str, Any]] = {}
    for line_no, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not raw.strip():
            continue
        try:
            row = json.loads(raw)
            opponent = str(row["opponent"])
            seed = int(row["seed"])
            seat = int(row["candidate_seat"])
            scores = row["scores"]
        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as error:
            raise ValueError(f"{path}:{line_no}: malformed row: {error}") from error
        if seat not in (0, 1):
            raise ValueError(f"{path}:{line_no}: candidate_seat must be 0 or 1")
        if row.get("status") != "complete":
            raise ValueError(f"{path}:{line_no}: incomplete game {(opponent, seed, seat)!r}")
        if not isinstance(scores, list) or len(scores) != 2:
            raise ValueError(f"{path}:{line_no}: scores must contain two values")
        values = [float(value) for value in scores]
        if not all(math.isfinite(value) for value in values):
            raise ValueError(f"{path}:{line_no}: non-finite score")
        key = (opponent, seed, seat)
        if key in games:
            raise ValueError(f"{path}:{line_no}: duplicate key {key!r}")
        row = dict(row)
        row.update(opponent=opponent, seed=seed, candidate_seat=seat, scores=values)
        games[key] = row
    if not games:
        raise ValueError(f"{path}: no game rows")
    return games


def ensure_grid(
    games: dict[Key, dict[str, Any]],
    *,
    opponents: Iterable[str] | None,
    seeds: Iterable[int] | None,
) -> None:
    if opponents is None or seeds is None:
        return
    expected = {
        (str(opponent), int(seed), seat)
        for opponent in opponents for seed in seeds for seat in (0, 1)
    }
    observed = set(games)
    if observed != expected:
        missing = sorted(expected - observed)
        unexpected = sorted(observed - expected)
        raise ValueError(
            f"grid mismatch: missing={missing[:20]!r} ({len(missing)}), "
            f"unexpected={unexpected[:20]!r} ({len(unexpected)})"
        )


def _view(row: dict[str, Any]) -> tuple[float, float, float, int]:
    seat = int(row["candidate_seat"])
    own = float(row["scores"][seat])
    rival = float(row["scores"][1 - seat])
    margin = own - rival
    return own, rival, margin, _sign(margin)


def _aggregate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {
            "cells": 0,
            "changed": 0,
            "mean_margin_delta": None,
            "sum_margin_delta": 0.0,
            "mean_own_delta": None,
            "sum_own_delta": 0.0,
            "mean_rival_delta": None,
            "sum_rival_delta": 0.0,
            "new_losses": 0,
            "recovered_losses": 0,
            "transitions": {},
        }
    transitions = Counter(row["transition"] for row in rows)
    n = len(rows)
    margin_sum = sum(row["margin_delta"] for row in rows)
    own_sum = sum(row["own_delta"] for row in rows)
    rival_sum = sum(row["rival_delta"] for row in rows)
    return {
        "cells": n,
        "changed": sum(row["changed"] for row in rows),
        "mean_margin_delta": round(margin_sum / n, 6),
        "sum_margin_delta": round(margin_sum, 6),
        "mean_own_delta": round(own_sum / n, 6),
        "sum_own_delta": round(own_sum, 6),
        "mean_rival_delta": round(rival_sum / n, 6),
        "sum_rival_delta": round(rival_sum, 6),
        "new_losses": sum(
            row["candidate_result"] < 0 <= row["baseline_result"] for row in rows
        ),
        "recovered_losses": sum(
            row["baseline_result"] < 0 <= row["candidate_result"] for row in rows
        ),
        "transitions": dict(sorted(transitions.items())),
    }


def _leaderboard_admission(
    *,
    changed: list[dict[str, Any]],
    overall: dict[str, Any],
    by_opponent: dict[str, dict[str, Any]],
    by_seat: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Apply the leaderboard-own-score-first promotion boundary.

    The evaluator records the candidate's terminal reward at
    ``scores[candidate_seat]``. Margin remains useful secondary evidence, but a
    candidate cannot be promoted by lowering both players' scores and merely
    lowering the rival more.
    """
    negative_own_opponents = sorted(
        opponent
        for opponent, metrics in by_opponent.items()
        if metrics["mean_own_delta"] is not None
        and metrics["mean_own_delta"] < 0
    )
    negative_own_seats = sorted(
        seat
        for seat, metrics in by_seat.items()
        if metrics["mean_own_delta"] is not None
        and metrics["mean_own_delta"] < 0
    )
    checks = {
        "changed_cells": bool(changed),
        "no_new_losses": overall["new_losses"] == 0,
        "positive_mean_candidate_score": (
            overall["mean_own_delta"] is not None
            and overall["mean_own_delta"] > 0
        ),
        "nonnegative_candidate_score_by_opponent": not negative_own_opponents,
        "nonnegative_candidate_score_by_seat": not negative_own_seats,
        "positive_mean_margin": (
            overall["mean_margin_delta"] is not None
            and overall["mean_margin_delta"] > 0
        ),
    }

    if not checks["no_new_losses"]:
        decision = "reject"
        reason = "candidate introduces new head-to-head losses"
    elif not checks["changed_cells"]:
        decision = "null"
        reason = "no score- or state-changing paired cells"
    elif overall["mean_own_delta"] < 0:
        decision = "reject"
        reason = "candidate terminal score regresses overall"
    elif negative_own_opponents:
        decision = "reject"
        reason = (
            "candidate terminal score regresses for opponent strata: "
            + ", ".join(negative_own_opponents)
        )
    elif negative_own_seats:
        decision = "reject"
        reason = (
            "candidate terminal score regresses for seat strata: "
            + ", ".join(negative_own_seats)
        )
    elif all(checks.values()):
        decision = "advance"
        reason = (
            "positive candidate terminal score, nonnegative opponent and seat "
            "strata, positive margin, and no new losses"
        )
    else:
        decision = "hold"
        reason = "leaderboard-own-score-first admission checks not all cleared"

    return {
        "rule": "leaderboard-own-score-first-v1",
        "primary_metric": "scores[candidate_seat] terminal reward",
        "secondary_metric": "candidate score minus rival score",
        "decision": decision,
        "reason": reason,
        "checks": checks,
        "negative_own_score_opponents": negative_own_opponents,
        "negative_own_score_seats": negative_own_seats,
    }


def compare(
    baseline: dict[Key, dict[str, Any]],
    candidate: dict[Key, dict[str, Any]],
) -> dict[str, Any]:
    if set(baseline) != set(candidate):
        missing = sorted(set(baseline) - set(candidate))
        extra = sorted(set(candidate) - set(baseline))
        raise ValueError(
            f"paired keys differ: missing={missing[:20]!r}, "
            f"candidate_only={extra[:20]!r}"
        )

    rows: list[dict[str, Any]] = []
    baseline_results = Counter()
    candidate_results = Counter()
    for opponent, seed, seat in sorted(baseline):
        bo, br, bm, bresult = _view(baseline[(opponent, seed, seat)])
        co, cr, cm, cresult = _view(candidate[(opponent, seed, seat)])
        baseline_results[bresult] += 1
        candidate_results[cresult] += 1
        rows.append({
            "opponent": opponent,
            "seed": seed,
            "candidate_seat": seat,
            "baseline_own": bo,
            "baseline_rival": br,
            "baseline_margin": bm,
            "candidate_own": co,
            "candidate_rival": cr,
            "candidate_margin": cm,
            "own_delta": co - bo,
            "rival_delta": cr - br,
            "margin_delta": cm - bm,
            "baseline_result": bresult,
            "candidate_result": cresult,
            "transition": f"{_label(bresult)}->{_label(cresult)}",
            "changed": bool(co != bo or cr != br),
        })

    changed = [row for row in rows if row["changed"]]
    opponents = sorted({row["opponent"] for row in rows})
    by_opponent = {
        opponent: _aggregate([row for row in rows if row["opponent"] == opponent])
        for opponent in opponents
    }
    by_seat = {
        str(seat): _aggregate(
            [row for row in rows if row["candidate_seat"] == seat]
        )
        for seat in (0, 1)
    }

    normalization_sites = []
    for row in changed:
        counterpart = baseline.get(
            (row["opponent"], row["seed"], 1 - row["candidate_seat"])
        )
        if counterpart is None:
            continue
        own, rival, _, _ = _view(counterpart)
        if own == row["candidate_own"] and rival == row["candidate_rival"]:
            normalization_sites.append({
                "opponent": row["opponent"],
                "seed": row["seed"],
                "candidate_seat": row["candidate_seat"],
            })

    overall = _aggregate(rows)
    changed_only = _aggregate(changed)
    admission = _leaderboard_admission(
        changed=changed,
        overall=overall,
        by_opponent=by_opponent,
        by_seat=by_seat,
    )

    labels = {-1: "L", 0: "T", 1: "W"}
    return {
        "schema": "titan-v3-paired-panel-delta-v1",
        "admission_rule": admission["rule"],
        "cells": len(rows),
        "baseline_record": {
            labels[key]: baseline_results[key] for key in (-1, 0, 1)
        },
        "candidate_record": {
            labels[key]: candidate_results[key] for key in (-1, 0, 1)
        },
        "overall": overall,
        "changed_only": changed_only,
        "changed_cells": changed,
        "unchanged_cells": len(rows) - len(changed),
        "by_opponent": by_opponent,
        "by_seat": by_seat,
        "seat_normalization": {
            "matches": len(normalization_sites),
            "changed_cells": len(changed),
            "fraction": (
                round(len(normalization_sites) / len(changed), 6)
                if changed else 0.0
            ),
            "sites": normalization_sites,
        },
        "leaderboard_admission": admission,
        "verdict": admission["decision"],
        "verdict_reason": admission["reason"],
    }


def assert_historical_l01(report: dict[str, Any]) -> None:
    expected = {
        ("arlene", seed, 0) for seed in range(2611061001, 2611061009)
    }
    actual = {
        (row["opponent"], int(row["seed"]), int(row["candidate_seat"]))
        for row in report["changed_cells"]
    }
    checks = {
        "cells": report["cells"] == 192,
        "changed_keys": actual == expected,
        "loss_to_win": report["changed_only"]["transitions"] == {"L->W": 8},
        "new_losses": report["overall"]["new_losses"] == 0,
        "sum_margin_delta": report["overall"]["sum_margin_delta"] == 129576.0,
        "mean_margin_delta": report["overall"]["mean_margin_delta"] == 674.875,
        "arlene_mean_delta": (
            report["by_opponent"]["arlene"]["mean_margin_delta"] == 4049.25
        ),
        "changed_own_mean": (
            report["changed_only"]["mean_own_delta"] == -8505.0
        ),
        "changed_own_sum": (
            report["changed_only"]["sum_own_delta"] == -68040.0
        ),
        "overall_own_mean": report["overall"]["mean_own_delta"] == -354.375,
        "arlene_own_mean": (
            report["by_opponent"]["arlene"]["mean_own_delta"] == -2126.25
        ),
        "changed_rival_mean": (
            report["changed_only"]["mean_rival_delta"] == -24702.0
        ),
        "seat_normalization_matches": (
            report["seat_normalization"]["matches"] == 7
        ),
        "leaderboard_verdict": report["verdict"] == "reject",
        "seat_zero_own_mean": (
            report["by_seat"]["0"]["mean_own_delta"] == -708.75
        ),
        "negative_own_score_seats": (
            report["leaderboard_admission"]["negative_own_score_seats"] == ["0"]
        ),
        "leaderboard_rule": (
            report["admission_rule"] == "leaderboard-own-score-first-v1"
        ),
    }
    failed = sorted(name for name, passed in checks.items() if not passed)
    report["historical_l01_profile"] = {
        "passed": not failed,
        "checks": checks,
        "failed": failed,
    }
    if failed:
        raise ValueError(f"historical L01 signature mismatch: {failed}")


def markdown(report: dict[str, Any]) -> str:
    overall = report["overall"]
    changed = report["changed_only"]
    admission = report["leaderboard_admission"]
    negative_opponents = admission["negative_own_score_opponents"]
    negative_seats = admission["negative_own_score_seats"]
    lines = [
        "# TITAN paired-panel delta",
        "",
        f"- Verdict: **{report['verdict'].upper()}**",
        f"- Admission rule: `{admission['rule']}`",
        f"- Decision reason: {admission['reason']}",
        f"- Cells: {report['cells']} ({len(report['changed_cells'])} changed)",
        f"- Record: {report['baseline_record']} → {report['candidate_record']}",
        f"- Mean candidate-score Δ: {overall['mean_own_delta']:+.3f}",
        f"- Sum candidate-score Δ: {overall['sum_own_delta']:+.3f}",
        f"- Mean margin Δ: {overall['mean_margin_delta']:+.3f}",
        f"- Sum margin Δ: {overall['sum_margin_delta']:+.3f}",
        f"- New losses: {overall['new_losses']}",
        f"- Recovered losses: {overall['recovered_losses']}",
        (
            "- Opponent strata with negative candidate-score Δ: "
            + (", ".join(negative_opponents) if negative_opponents else "none")
        ),
        (
            "- Seat strata with negative candidate-score Δ: "
            + (", ".join(negative_seats) if negative_seats else "none")
        ),
        (
            f"- Changed-cell economics: own {changed['mean_own_delta']:+.3f} "
            f"(sum {changed['sum_own_delta']:+.3f}), "
            f"rival {changed['mean_rival_delta']:+.3f}, "
            f"margin {changed['mean_margin_delta']:+.3f}"
            if changed["cells"]
            else "- Changed-cell economics: no changed cells"
        ),
        (
            "- Opposite-seat baseline matches: "
            f"{report['seat_normalization']['matches']}/"
            f"{len(report['changed_cells'])}"
        ),
        "",
        "## Opponents",
        "",
        (
            "| opponent | cells | changed | mean candidate-score Δ | "
            "mean margin Δ | new losses | recovered losses |"
        ),
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for opponent, metrics in report["by_opponent"].items():
        lines.append(
            f"| {opponent} | {metrics['cells']} | {metrics['changed']} | "
            f"{metrics['mean_own_delta']:+.3f} | "
            f"{metrics['mean_margin_delta']:+.3f} | "
            f"{metrics['new_losses']} | {metrics['recovered_losses']} |"
        )
    lines.extend([
        "",
        "## Seats",
        "",
        "| candidate seat | cells | changed | mean candidate-score Δ | mean margin Δ |",
        "|---:|---:|---:|---:|---:|",
    ])
    for seat, metrics in report["by_seat"].items():
        own_delta = metrics["mean_own_delta"]
        margin_delta = metrics["mean_margin_delta"]
        own_text = "n/a" if own_delta is None else f"{own_delta:+.3f}"
        margin_text = "n/a" if margin_delta is None else f"{margin_delta:+.3f}"
        lines.append(
            f"| {seat} | {metrics['cells']} | {metrics['changed']} | "
            f"{own_text} | {margin_text} |"
        )
    lines.extend(["", "## Changed cells", ""])
    if not report["changed_cells"]:
        lines.append("None.")
    else:
        lines.extend([
            (
                "| opponent | seed | seat | transition | own Δ | rival Δ | "
                "margin Δ |"
            ),
            "|---|---:|---:|---|---:|---:|---:|",
        ])
        for row in report["changed_cells"]:
            lines.append(
                f"| {row['opponent']} | {row['seed']} | "
                f"{row['candidate_seat']} | {row['transition']} | "
                f"{row['own_delta']:+.0f} | {row['rival_delta']:+.0f} | "
                f"{row['margin_delta']:+.0f} |"
            )
    return "\n".join(lines) + "\n"


def _csv(raw: str | None) -> list[str] | None:
    return (
        None
        if raw is None
        else [part.strip() for part in raw.split(",") if part.strip()]
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", required=True, type=Path)
    parser.add_argument("--candidate", required=True, type=Path)
    parser.add_argument("--opponents")
    parser.add_argument("--seed-start", type=int)
    parser.add_argument("--seed-count", type=int)
    parser.add_argument("--expect-historical-l01", action="store_true")
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--markdown-out", type=Path)
    args = parser.parse_args()
    if (args.seed_start is None) != (args.seed_count is None):
        parser.error("--seed-start and --seed-count must be supplied together")
    seeds = (
        range(args.seed_start, args.seed_start + args.seed_count)
        if args.seed_start is not None
        else None
    )
    opponents = _csv(args.opponents)
    baseline = load_games(args.baseline)
    candidate = load_games(args.candidate)
    ensure_grid(baseline, opponents=opponents, seeds=seeds)
    ensure_grid(candidate, opponents=opponents, seeds=seeds)
    report = compare(baseline, candidate)
    report["inputs"] = {
        "baseline": str(args.baseline),
        "baseline_sha256": sha256(args.baseline),
        "candidate": str(args.candidate),
        "candidate_sha256": sha256(args.candidate),
    }
    if args.expect_historical_l01:
        assert_historical_l01(report)
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    if args.markdown_out:
        args.markdown_out.parent.mkdir(parents=True, exist_ok=True)
        args.markdown_out.write_text(markdown(report), encoding="utf-8")
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
