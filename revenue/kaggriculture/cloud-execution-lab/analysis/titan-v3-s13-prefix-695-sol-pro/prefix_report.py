#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Compare an S13 prefix route with control and its full-route parent."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from statistics import mean, median
from typing import Any, Mapping

SCHEMA = "titan-v3-s13-prefix-report/v1"


class PrefixReportError(RuntimeError):
    pass


def _cells(report: Mapping[str, Any]) -> dict[tuple[str, int, int], dict[str, Any]]:
    rows: dict[tuple[str, int, int], dict[str, Any]] = {}
    games = report.get("games")
    if not isinstance(games, list):
        raise PrefixReportError("evaluator report has no games")
    for game in games:
        if not isinstance(game, Mapping) or game.get("status") != "complete" or game.get("failure") is not None:
            raise PrefixReportError("evaluator report contains an incomplete game")
        opponent = game.get("opponent")
        seed = game.get("seed")
        seat = game.get("candidate_seat")
        scores = game.get("scores")
        if not isinstance(opponent, str) or type(seed) is not int or seat not in (0, 1):
            raise PrefixReportError("evaluator cell key is malformed")
        if not isinstance(scores, list) or len(scores) != 2:
            raise PrefixReportError("evaluator scores are malformed")
        key = (opponent, seed, seat)
        if key in rows:
            raise PrefixReportError(f"duplicate evaluator cell: {key!r}")
        own = float(scores[seat])
        rival = float(scores[1 - seat])
        rows[key] = {
            "opponent": opponent,
            "seed": seed,
            "seat": seat,
            "own_cash": own,
            "rival_cash": rival,
            "margin": own - rival,
            "trace_sha256": game.get("trace_sha256"),
        }
    return rows


def _summary(candidate: Mapping[tuple[str, int, int], Mapping[str, Any]], control: Mapping[tuple[str, int, int], Mapping[str, Any]]) -> dict[str, Any]:
    if set(candidate) != set(control) or not candidate:
        raise PrefixReportError("candidate and control cell banks differ")
    rows = []
    for key in sorted(candidate):
        cand = candidate[key]
        base = control[key]
        rows.append({
            **{name: cand[name] for name in ("opponent", "seed", "seat", "own_cash", "rival_cash", "margin", "trace_sha256")},
            "control_own_cash": base["own_cash"],
            "control_margin": base["margin"],
            "own_cash_delta": cand["own_cash"] - base["own_cash"],
            "margin_delta": cand["margin"] - base["margin"],
            "new_loss": cand["margin"] < 0 <= base["margin"],
            "trace_changed": cand["trace_sha256"] != base["trace_sha256"],
        })
    strata = []
    for opponent, seat in sorted({(row["opponent"], row["seat"]) for row in rows}):
        subset = [row for row in rows if row["opponent"] == opponent and row["seat"] == seat]
        strata.append({
            "opponent": opponent,
            "seat": seat,
            "cells": len(subset),
            "mean_own_cash_delta": mean(row["own_cash_delta"] for row in subset),
            "mean_margin_delta": mean(row["margin_delta"] for row in subset),
        })
    result = {
        "cells": rows,
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
    result["strict_survivor"] = bool(
        result["mean_own_cash_delta"] > 0
        and result["median_own_cash_delta"] >= 0
        and result["mean_margin_delta"] >= 0
        and result["new_losses"] == 0
        and result["trace_changed_cells"] == result["pair_rows"]
        and all(row["mean_margin_delta"] >= 0 for row in strata)
    )
    return result


def build_report(control_path: Path, full_path: Path, prefix_path: Path) -> dict[str, Any]:
    control = _cells(json.loads(control_path.read_text(encoding="utf-8")))
    full = _cells(json.loads(full_path.read_text(encoding="utf-8")))
    prefix = _cells(json.loads(prefix_path.read_text(encoding="utf-8")))
    full_summary = _summary(full, control)
    prefix_summary = _summary(prefix, control)
    if set(full) != set(prefix):
        raise PrefixReportError("full and prefix banks differ")
    retention = []
    for key in sorted(full):
        f = full[key]
        p = prefix[key]
        retention.append({
            "opponent": p["opponent"],
            "seed": p["seed"],
            "seat": p["seat"],
            "own_cash_delta_prefix_minus_full": p["own_cash"] - f["own_cash"],
            "margin_delta_prefix_minus_full": p["margin"] - f["margin"],
            "prefix_margin": p["margin"],
            "full_margin": f["margin"],
        })
    mean_full = full_summary["mean_own_cash_delta"]
    return {
        "schema": SCHEMA,
        "control": str(control_path),
        "full": full_summary,
        "prefix": prefix_summary,
        "prefix_vs_full": {
            "cells": retention,
            "mean_own_cash_delta": mean(row["own_cash_delta_prefix_minus_full"] for row in retention),
            "mean_margin_delta": mean(row["margin_delta_prefix_minus_full"] for row in retention),
            "min_prefix_margin": min(row["prefix_margin"] for row in retention),
            "retained_mean_own_uplift_fraction": (
                prefix_summary["mean_own_cash_delta"] / mean_full if mean_full > 0 else None
            ),
        },
        "verdict": "PREFIX_SURVIVOR" if prefix_summary["strict_survivor"] else "PREFIX_HOLD",
        "scope": "frozen-seed research only; not a promotion or submission receipt",
    }


def markdown(report: Mapping[str, Any]) -> str:
    full = report["full"]
    prefix = report["prefix"]
    retention = report["prefix_vs_full"]
    return "\n".join([
        "# TITAN V3 S13 prefix-695 report",
        "",
        f"**Verdict:** `{report['verdict']}`",
        "",
        "| candidate | mean own Δ vs control | median own Δ | mean margin Δ | min own Δ | negative own cells | new losses |",
        "|---|---:|---:|---:|---:|---:|---:|",
        f"| full route | {full['mean_own_cash_delta']:.3f} | {full['median_own_cash_delta']:.3f} | {full['mean_margin_delta']:.3f} | {full['min_own_cash_delta']:.3f} | {full['negative_own_cells']} | {full['new_losses']} |",
        f"| prefix-695 | {prefix['mean_own_cash_delta']:.3f} | {prefix['median_own_cash_delta']:.3f} | {prefix['mean_margin_delta']:.3f} | {prefix['min_own_cash_delta']:.3f} | {prefix['negative_own_cells']} | {prefix['new_losses']} |",
        "",
        f"Prefix minus full mean own cash: `{retention['mean_own_cash_delta']:.3f}`.",
        f"Prefix minus full mean margin: `{retention['mean_margin_delta']:.3f}`.",
        f"Retained full-route mean uplift: `{retention['retained_mean_own_uplift_fraction']}`.",
        "",
        "Frozen-seed research only. No promotion, provider, Kaggle, or submission mutation.",
        "",
    ])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--control", type=Path, required=True)
    parser.add_argument("--full", type=Path, required=True)
    parser.add_argument("--prefix", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--markdown", type=Path, required=True)
    args = parser.parse_args(argv)
    report = build_report(args.control, args.full, args.prefix)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    args.markdown.write_text(markdown(report), encoding="utf-8")
    print(json.dumps({"verdict": report["verdict"], "prefix": report["prefix"], "prefix_vs_full": report["prefix_vs_full"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
