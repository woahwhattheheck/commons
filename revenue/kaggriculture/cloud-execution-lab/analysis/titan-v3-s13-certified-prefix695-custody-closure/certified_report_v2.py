#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Exact-cell report using retained runtime activation diagnostics, not trace drift."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from statistics import mean, median
from typing import Any, Mapping

SCHEMA = "titan-v3-s13-certified-prefix-report/v2"
DONOR_HEAD = "cbfff2bec813e2c2609ce9c5819b74669e98c566"
DONOR_BLOB = "89a3325eb541ae0e8a81e1e0a426292820f10d98"


class CertifiedReportError(RuntimeError):
    pass


def canonical(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode()
    except (TypeError, ValueError) as exc:
        raise CertifiedReportError(f"value is not canonical JSON: {exc}") from exc


def strict_load(path: Path) -> Any:
    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for key, value in items:
            if key in out:
                raise CertifiedReportError(f"{path}: duplicate JSON key {key!r}")
            out[key] = value
        return out

    def reject(value: str) -> Any:
        raise CertifiedReportError(f"{path}: non-finite JSON constant {value}")

    try:
        return json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=pairs,
            parse_constant=reject,
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise CertifiedReportError(f"{path}: invalid evaluator JSON: {exc}") from exc


def finite_number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise CertifiedReportError(f"{label} is not numeric")
    result = float(value)
    if not math.isfinite(result):
        raise CertifiedReportError(f"{label} is non-finite")
    return result


def runtime_diagnostics(game: Mapping[str, Any], seat: int) -> dict[str, Any]:
    actors = game.get("actors")
    if not isinstance(actors, list) or len(actors) != 2:
        raise CertifiedReportError("certified evaluator row has no exact two-actor diagnostics")
    actor = actors[seat]
    if not isinstance(actor, Mapping):
        raise CertifiedReportError("certified candidate actor diagnostics are malformed")
    diag = actor.get("agent_diagnostics")
    if not isinstance(diag, Mapping):
        raise CertifiedReportError("certified candidate runtime diagnostics are absent")

    source_seat = diag.get("source_seat")
    if source_seat not in (0, 1):
        raise CertifiedReportError("runtime source_seat is malformed")
    steps = diag.get("activation_steps")
    if (
        not isinstance(steps, list)
        or any(type(step) is not int or step < 0 for step in steps)
        or steps != sorted(set(steps))
    ):
        raise CertifiedReportError("runtime activation_steps are noncanonical")
    count = diag.get("activation_count")
    checks = diag.get("certificate_checks")
    matches = diag.get("certificate_matches")
    if type(count) is not int or count != len(steps):
        raise CertifiedReportError("runtime activation_count disagrees with activation_steps")
    if type(checks) is not int or type(matches) is not int:
        raise CertifiedReportError("runtime certificate counters are malformed")
    if checks < 0 or matches < 0 or matches > checks or count > matches:
        raise CertifiedReportError("runtime certificate counters are inconsistent")
    if diag.get("certificate_donor_head") != DONOR_HEAD:
        raise CertifiedReportError("runtime certificate donor head drift")
    if diag.get("certificate_donor_blob") != DONOR_BLOB:
        raise CertifiedReportError("runtime certificate donor blob drift")
    handoff_step = diag.get("handoff_step")
    if handoff_step is not None and (type(handoff_step) is not int or handoff_step < 0):
        raise CertifiedReportError("runtime handoff_step is malformed")
    handoff_reason = diag.get("handoff_reason")
    if handoff_reason is not None and not isinstance(handoff_reason, str):
        raise CertifiedReportError("runtime handoff_reason is malformed")
    return {
        "source_seat": source_seat,
        "activation_steps": list(steps),
        "activation_count": count,
        "certificate_checks": checks,
        "certificate_matches": matches,
        "handoff_step": handoff_step,
        "handoff_reason": handoff_reason,
        "certificate_donor_head": DONOR_HEAD,
        "certificate_donor_blob": DONOR_BLOB,
    }


def cells(
    report: Mapping[str, Any],
    *,
    require_runtime_diagnostics: bool = False,
) -> dict[tuple[str, int, int], dict[str, Any]]:
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
        if not isinstance(opponent, str) or not opponent or type(seed) is not int or seat not in (0, 1):
            raise CertifiedReportError("evaluator cell key is malformed")
        if not isinstance(scores, list) or len(scores) != 2:
            raise CertifiedReportError("evaluator scores are malformed")
        if not isinstance(trace, str) or not trace:
            raise CertifiedReportError("evaluator trace digest is absent")
        key = (opponent, seed, seat)
        if key in result:
            raise CertifiedReportError(f"duplicate evaluator cell: {key!r}")
        own = finite_number(scores[seat], f"{key!r} own score")
        rival = finite_number(scores[1 - seat], f"{key!r} rival score")
        row = {
            "opponent": opponent,
            "seed": seed,
            "seat": seat,
            "own_cash": own,
            "rival_cash": rival,
            "margin": own - rival,
            "trace_sha256": trace,
        }
        if require_runtime_diagnostics:
            row["runtime_diagnostics"] = runtime_diagnostics(game, seat)
        result[key] = row
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
        row = {
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
        if "runtime_diagnostics" in cand:
            row["runtime_diagnostics"] = cand["runtime_diagnostics"]
            row["activation_steps"] = cand["runtime_diagnostics"]["activation_steps"]
            row["activation_count"] = cand["runtime_diagnostics"]["activation_count"]
        rows.append(row)
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
                "activation_cells": sum(row.get("activation_count", 0) > 0 for row in subset),
                "activation_events": sum(row.get("activation_count", 0) for row in subset),
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
        "activation_cells": sum(row.get("activation_count", 0) > 0 for row in rows),
        "activation_events": sum(row.get("activation_count", 0) for row in rows),
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
    control = cells(strict_load(control_path))
    unsafe = cells(strict_load(unsafe_path))
    certified = cells(
        strict_load(certified_path),
        require_runtime_diagnostics=True,
    )
    if set(control) != set(unsafe) or set(control) != set(certified):
        raise CertifiedReportError("the three evaluator banks differ")
    for key, row in certified.items():
        if row["runtime_diagnostics"]["source_seat"] != source_seat:
            raise CertifiedReportError(f"runtime source-seat binding drift at {key!r}")

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
        row["activation_count"] == 0
        and not row["trace_changed"]
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
    source_activated = any(row["activation_count"] > 0 for row in source_rows)

    if off_seat_exact_fallback and source_safe and source_activated:
        verdict = "CERTIFIED_SURVIVOR"
    elif off_seat_exact_fallback and not source_activated:
        verdict = "CERTIFICATE_REJECTS_TRANSPLANT"
    else:
        verdict = "CERTIFIED_HOLD"

    diagnostic_rows = [
        {
            "opponent": row["opponent"],
            "seed": row["seed"],
            "seat": row["seat"],
            "runtime_diagnostics": row["runtime_diagnostics"],
        }
        for row in certified_summary["rows"]
    ]
    diagnostic_sha = hashlib.sha256(canonical(diagnostic_rows)).hexdigest()
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
        "runtime_diagnostics_sha256": diagnostic_sha,
        "off_seat_exact_fallback": off_seat_exact_fallback,
        "source_seat_activated": source_activated,
        "source_seat_activation_cells": sum(
            row["activation_count"] > 0 for row in source_rows
        ),
        "source_seat_activation_events": sum(
            row["activation_count"] for row in source_rows
        ),
        "source_seat_safe": source_safe,
        "verdict": verdict,
        "scope": "reused frozen seeds only; activation derives only from retained runtime emissions; no promotion, provider, Kaggle, or submission mutation",
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
            f"**Source-seat runtime activation:** `{report['source_seat_activated']}`",
            f"**Source-seat activation cells/events:** `{report['source_seat_activation_cells']}` / `{report['source_seat_activation_events']}`",
            f"**Runtime diagnostics SHA-256:** `{report['runtime_diagnostics_sha256']}`",
            "",
            "| arm | mean own Δ vs control | median own Δ | mean margin Δ | min own Δ | new losses | changed traces | runtime activation cells |",
            "|---|---:|---:|---:|---:|---:|---:|---:|",
            f"| unsafe prefix-695 | {unsafe['mean_own_cash_delta']:.3f} | {unsafe['median_own_cash_delta']:.3f} | {unsafe['mean_margin_delta']:.3f} | {unsafe['min_own_cash_delta']:.3f} | {unsafe['new_losses']} | {unsafe['trace_changed_cells']} | n/a |",
            f"| exact-certified prefix-695 | {certified['mean_own_cash_delta']:.3f} | {certified['median_own_cash_delta']:.3f} | {certified['mean_margin_delta']:.3f} | {certified['min_own_cash_delta']:.3f} | {certified['new_losses']} | {certified['trace_changed_cells']} | {certified['activation_cells']} |",
            "",
            "Activation is established only by the certified runtime's retained activation_steps, never by trace divergence.",
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
