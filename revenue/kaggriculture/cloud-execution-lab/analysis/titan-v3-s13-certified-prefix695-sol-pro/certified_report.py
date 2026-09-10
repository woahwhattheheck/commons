#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Compare unsafe prefix-695, exact-certified prefix-695, and frozen control."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from statistics import mean, median
from typing import Any, Mapping

SCHEMA = "titan-v3-s13-certified-prefix-report/v1"


class CertifiedReportError(RuntimeError):
    pass


def cells(report: Mapping[str, Any]) -> dict[tuple[str, int, int], dict[str, Any]]:
    result: dict[tuple[str, int, int], dict[str, Any]] = {}
    games = report.get("games")
    if not isinstance(games, list):
        raise CertifiedReportError("evaluator report has no games")
    for game in games:
        if (
            not isinstance(game, Mapping)
            or game.get("status") != "complete"
            or game.get("failure") is not None
        ):
            raise CertifiedReportError("evaluator report contains an incomplete game")
        opponent = game.get("opponent")
        seed = game.get("seed")
        seat = game.get("candidate_seat")
        scores = game.get("scores")
        trace = game.get("trace_sha256")
        if not isinstance(opponent, str) or type(seed) is not int or seat not in (0, 1):
            raise CertifiedReportError("evaluator cell key is malformed")
        if not isinstance(scores, list) or len(scores) != 2:
            raise CertifiedReportError("evaluator scores are malformed")
        if not isinstance(trace, str):
            raise CertifiedReportError("evaluator trace digest is absent")
        key = (opponent, seed, seat)
        if key in result:
            raise CertifiedReportError(f"duplicate evaluator cell: {key!r}")
        own = float(scores[seat])
        rival = float(scores[1 - seat])
        result[key] = {
            "opponent": opponent,
            "seed": seed,
            "seat": seat,
            "own_cash": own,
            "rival_cash": rival,
            "margin": own - rival,
            "trace_sha256": trace,
        }
    return result


def paired(
    candidate: Mapping[tuple[str, int, int], Mapping[str, Any]],
    control: Mapping[tuple[str, int, int], Mapping[str, Any]],
) -> dict[str, Any]:
    if not candidate or set(candidate) != set(control):
        raise CertifiedReportError("candidate and control cell banks differ")
    rows: list[dict[str, Any]] = []
    for key in sorted(candidate):
        cand, base = candidate[key], control[key]
        rows.append(
            {
                "opponent": cand["opponent"],
                "seed": cand["seed"],
                "seat": cand["seat"],
                "own_cash": cand["own_cash"],
                "margin": cand["margin"],
                "control_own_cash": base["own_cash"],
                "control_margin": base["margin"],
                "own_cash_delta": cand["own_cash"] - base["own_cash"],
                "margin_delta": cand["margin"] - base["margin"],
                "trace_changed": cand["trace_sha256"] != base["trace_sha256"],
                "new_loss": cand["margin"] < 0 <= base["margin"],
            }
        )
    strata = []
    for opponent, seat in sorted({(row["opponent"], row["seat"]) for row in rows}):
        subset = [row for row in rows if row["opponent"] == opponent and row["seat"] == seat]
        strata.append(
            {
                "opponent": opponent,
                "seat": seat,
                "cells": len(subset),
                "mean_own_cash_delta": mean(row["own_cash_delta"] for row in subset),
                "mean_margin_delta": mean(row["margin_delta"] for row in subset),
                "trace_changed_cells": sum(row["trace_changed"] for row in subset),
                "new_losses": sum(row["new_loss"] for row in subset),
            }
        )
    return {
        "rows": rows,
        "pair_rows": len(rows),
        "mean_own_cash_delta": mean(row["own_cash_delta"] for row in rows),
        "median_own_cash_delta": median(row["own_cash_delta"] for row in rows),
        "min_own_cash_delta": min(row["own_cash_delta"] for row in rows),
        "max_own_cash_delta": max(row["own_cash_delta"] for row in rows),
        "mean_margin_delta": mean(row["margin_delta"] for row in rows),
        "negative_own_cells": sum(row["own_cash_delta"] < 0 for row in rows),
        "new_losses": sum(row["new_loss"] for row in rows),
        "trace_changed_cells": sum(row["trace_changed"] for row in rows),
        "strata": strata,
    }


def build_report(
    control_path: Path,
    unsafe_path: Path,
    certified_path: Path,
    *,
    source_seat: int,
) -> dict[str, Any]:
    if source_seat not in (0, 1):
        raise CertifiedReportError("source_seat must be 0 or 1")
    control = cells(json.loads(control_path.read_text(encoding="utf-8")))
    unsafe = cells(json.loads(unsafe_path.read_text(encoding="utf-8")))
    certified = cells(json.loads(certified_path.read_text(encoding="utf-8")))
    if set(control) != set(unsafe) or set(control) != set(certified):
        raise CertifiedReportError("the three evaluator banks differ")
    unsafe_summary = paired(unsafe, control)
    certified_summary = paired(certified, control)
    retention_rows = []
    for key in sorted(control):
        raw, guarded = unsafe[key], certified[key]
        retention_rows.append(
            {
                "opponent": guarded["opponent"],
                "seed": guarded["seed"],
                "seat": guarded["seat"],
                "own_cash_delta_certified_minus_unsafe": guarded["own_cash"] - raw["own_cash"],
                "margin_delta_certified_minus_unsafe": guarded["margin"] - raw["margin"],
            }
        )
    source_rows = [row for row in certified_summary["rows"] if row["seat"] == source_seat]
    off_rows = [row for row in certified_summary["rows"] if row["seat"] != source_seat]
    if not source_rows or not off_rows:
        raise CertifiedReportError("both candidate seats are required")
    off_seat_exact_fallback = all(
        not row["trace_changed"]
        and row["own_cash_delta"] == 0
        and row["margin_delta"] == 0
        for row in off_rows
    )
    source_strata = [
        row for row in certified_summary["strata"] if row["seat"] == source_seat
    ]
    source_safe = bool(
        sum(row["new_loss"] for row in source_rows) == 0
        and mean(row["own_cash_delta"] for row in source_rows) >= 0
        and mean(row["margin_delta"] for row in source_rows) >= 0
        and all(row["mean_margin_delta"] >= 0 for row in source_strata)
    )
    source_activated = any(row["trace_changed"] for row in source_rows)
    if off_seat_exact_fallback and source_safe and source_activated:
        verdict = "CERTIFIED_SURVIVOR"
    elif off_seat_exact_fallback and not source_activated:
        verdict = "CERTIFICATE_REJECTS_TRANSPLANT"
    else:
        verdict = "CERTIFIED_HOLD"
    return {
        "schema": SCHEMA,
        "source_seat": source_seat,
        "control": str(control_path),
        "unsafe_prefix": unsafe_summary,
        "certified_prefix": certified_summary,
        "certified_vs_unsafe": {
            "rows": retention_rows,
            "mean_own_cash_delta": mean(
                row["own_cash_delta_certified_minus_unsafe"] for row in retention_rows
            ),
            "mean_margin_delta": mean(
                row["margin_delta_certified_minus_unsafe"] for row in retention_rows
            ),
        },
        "off_seat_exact_fallback": off_seat_exact_fallback,
        "source_seat_activated": source_activated,
        "source_seat_safe": source_safe,
        "verdict": verdict,
        "scope": "reused frozen seeds only; no promotion, provider, Kaggle, or submission mutation",
    }


def markdown(report: Mapping[str, Any]) -> str:
    unsafe = report["unsafe_prefix"]
    certified = report["certified_prefix"]
    return "\n".join(
        [
            "# TITAN V3 S13 exact-certified prefix-695 report",
            "",
            f"**Verdict:** `{report['verdict']}`",
            f"**Source seat:** `{report['source_seat']}`",
            f"**Off-seat exact fallback:** `{report['off_seat_exact_fallback']}`",
            f"**Source-seat activation:** `{report['source_seat_activated']}`",
            "",
            "| arm | mean own Δ vs control | median own Δ | mean margin Δ | min own Δ | new losses | changed traces |",
            "|---|---:|---:|---:|---:|---:|---:|",
            f"| unsafe prefix-695 | {unsafe['mean_own_cash_delta']:.3f} | {unsafe['median_own_cash_delta']:.3f} | {unsafe['mean_margin_delta']:.3f} | {unsafe['min_own_cash_delta']:.3f} | {unsafe['new_losses']} | {unsafe['trace_changed_cells']} |",
            f"| exact-certified prefix-695 | {certified['mean_own_cash_delta']:.3f} | {certified['median_own_cash_delta']:.3f} | {certified['mean_margin_delta']:.3f} | {certified['min_own_cash_delta']:.3f} | {certified['new_losses']} | {certified['trace_changed_cells']} |",
            "",
            "The certificate is an own/public prestate certificate. It does not certify the rival's hidden simultaneous market queue or exact market outcome.",
            "",
            "Reused frozen-seed research only. No promotion, provider, Kaggle, or submission mutation.",
            "",
        ]
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--control", type=Path, required=True)
    parser.add_argument("--unsafe-prefix", type=Path, required=True)
    parser.add_argument("--certified-prefix", type=Path, required=True)
    parser.add_argument("--source-seat", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--markdown", type=Path, required=True)
    args = parser.parse_args(argv)
    report = build_report(
        args.control,
        args.unsafe_prefix,
        args.certified_prefix,
        source_seat=args.source_seat,
    )
    args.output.write_text(
        json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    args.markdown.write_text(markdown(report), encoding="utf-8")
    print(json.dumps(report, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
