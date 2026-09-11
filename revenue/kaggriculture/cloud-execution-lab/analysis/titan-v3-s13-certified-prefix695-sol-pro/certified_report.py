#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
'''Compare unsafe prefix-695, exact-certified prefix-695, and frozen control.'''
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from statistics import mean, median
from typing import Any, Mapping

SCHEMA = "titan-v3-s13-certified-prefix-report/v2"
CAPTURE_SCHEMA = "titan-v3-s13-activation-capture-receipt/v1"
DIAGNOSTIC_SCHEMA = "titan-v3-s13-certified-activation/v1"


class CertifiedReportError(RuntimeError):
    pass


def _strict_json(path: Path) -> Any:
    def pairs(items):
        out = {}
        for key, value in items:
            if key in out:
                raise CertifiedReportError(f"{path}: duplicate JSON key {key!r}")
            out[key] = value
        return out
    def reject(value):
        raise CertifiedReportError(f"{path}: non-finite JSON constant {value}")
    try:
        return json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=pairs,
            parse_constant=reject,
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise CertifiedReportError(f"{path}: invalid JSON: {exc}") from exc


def _capture_receipt(path: Path) -> dict[str, Any]:
    value = _strict_json(path)
    if not isinstance(value, Mapping) or value.get("schema") != CAPTURE_SCHEMA:
        raise CertifiedReportError("activation capture receipt schema mismatch")
    for key in (
        "candidate_name",
        "candidate_sha256",
        "wrapper_name",
        "wrapper_sha256",
        "marker_name",
        "diagnostic_name",
        "diagnostic_schema",
    ):
        if not isinstance(value.get(key), str) or not value[key]:
            raise CertifiedReportError(f"activation capture receipt missing {key}")
    if value["diagnostic_schema"] != DIAGNOSTIC_SCHEMA:
        raise CertifiedReportError("activation diagnostic schema mismatch")
    return dict(value)


def _activation(
    game: Mapping[str, Any],
    *,
    seat: int,
    source_seat: int,
    capture: Mapping[str, Any],
) -> dict[str, Any]:
    actors = game.get("actors")
    if not isinstance(actors, list) or len(actors) != 2:
        raise CertifiedReportError("certified evaluator game lacks two actor reports")
    actor = actors[seat]
    if not isinstance(actor, Mapping):
        raise CertifiedReportError("candidate actor report is malformed")
    if actor.get("candidate_diagnostics_capture_error") is not None:
        raise CertifiedReportError(
            "candidate diagnostics capture failed: "
            + str(actor["candidate_diagnostics_capture_error"])
        )
    if actor.get("candidate_diagnostics_capture_setup_error") is not None:
        raise CertifiedReportError(
            "candidate diagnostics setup failed: "
            + str(actor["candidate_diagnostics_capture_setup_error"])
        )
    diagnostics = actor.get("candidate_diagnostics")
    if not isinstance(diagnostics, Mapping):
        raise CertifiedReportError("candidate diagnostics are absent")
    if diagnostics.get("schema") != DIAGNOSTIC_SCHEMA:
        raise CertifiedReportError("candidate diagnostics schema mismatch")
    if diagnostics.get("target_sha256") != capture["candidate_sha256"]:
        raise CertifiedReportError("candidate diagnostics target SHA-256 mismatch")
    if diagnostics.get("target_name") != capture["candidate_name"]:
        raise CertifiedReportError("candidate diagnostics target name mismatch")
    if diagnostics.get("source_seat") != source_seat:
        raise CertifiedReportError("candidate diagnostics source seat mismatch")
    arm_id = diagnostics.get("arm_id")
    if not isinstance(arm_id, str) or not arm_id:
        raise CertifiedReportError("candidate diagnostics arm id is absent")
    policy = diagnostics.get("policy")
    if not isinstance(policy, Mapping):
        raise CertifiedReportError("candidate policy diagnostics are absent")
    if policy.get("source_seat") != source_seat:
        raise CertifiedReportError("policy diagnostics source seat mismatch")
    activation_steps = policy.get("activation_steps")
    activation_count = policy.get("activation_count")
    if (
        not isinstance(activation_steps, list)
        or any(type(step) is not int or step < 0 for step in activation_steps)
        or activation_steps != sorted(set(activation_steps))
        or type(activation_count) is not int
        or activation_count != len(activation_steps)
    ):
        raise CertifiedReportError("candidate activation diagnostics are malformed")
    start_step = policy.get("start_step")
    if type(start_step) is not int or start_step < 0:
        raise CertifiedReportError("candidate diagnostics start_step is malformed")
    if any(step < start_step for step in activation_steps):
        raise CertifiedReportError("candidate activation precedes owned route")
    checks = policy.get("certificate_checks")
    matches = policy.get("certificate_matches")
    if (
        type(checks) is not int
        or type(matches) is not int
        or checks < 0
        or matches < 0
        or matches > checks
    ):
        raise CertifiedReportError("candidate certificate counters are malformed")
    if activation_count > matches:
        raise CertifiedReportError("activation count exceeds certificate matches")
    raw_sha = actor.get("candidate_diagnostics_sha256")
    raw_bytes = actor.get("candidate_diagnostics_bytes")
    if (
        not isinstance(raw_sha, str)
        or len(raw_sha) != 64
        or any(ch not in "0123456789abcdef" for ch in raw_sha)
        or type(raw_bytes) is not int
        or raw_bytes <= 0
    ):
        raise CertifiedReportError("candidate diagnostics capture metadata is malformed")
    return {
        "arm_id": arm_id,
        "diagnostics_sha256": raw_sha,
        "diagnostics_bytes": raw_bytes,
        "activation_count": activation_count,
        "activation_steps": list(activation_steps),
        "certificate_checks": checks,
        "certificate_matches": matches,
        "active": policy.get("active"),
        "handoff_step": policy.get("handoff_step"),
        "handoff_reason": policy.get("handoff_reason"),
    }


def cells(
    report: Mapping[str, Any],
    *,
    source_seat: int | None = None,
    capture: Mapping[str, Any] | None = None,
) -> dict[tuple[str, int, int], dict[str, Any]]:
    if (source_seat is None) != (capture is None):
        raise CertifiedReportError("source_seat and capture receipt must be supplied together")
    if capture is not None:
        candidate = report.get("candidate")
        if not isinstance(candidate, Mapping) or candidate.get("sha256") != capture["wrapper_sha256"]:
            raise CertifiedReportError("certified evaluator candidate wrapper SHA-256 mismatch")
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
        row = {
            "opponent": opponent,
            "seed": seed,
            "seat": seat,
            "own_cash": own,
            "rival_cash": rival,
            "margin": own - rival,
            "trace_sha256": trace,
        }
        if capture is not None:
            assert source_seat is not None
            row["activation"] = _activation(
                game, seat=seat, source_seat=source_seat, capture=capture
            )
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
        if "activation" in cand:
            row["activation"] = cand["activation"]
            row["activation_count"] = cand["activation"]["activation_count"]
            row["activation_steps"] = cand["activation"]["activation_steps"]
        rows.append(row)
    strata = []
    for opponent, seat in sorted({(row["opponent"], row["seat"]) for row in rows}):
        subset = [
            row for row in rows
            if row["opponent"] == opponent and row["seat"] == seat
        ]
        strata.append(
            {
                "opponent": opponent,
                "seat": seat,
                "cells": len(subset),
                "mean_own_cash_delta": mean(row["own_cash_delta"] for row in subset),
                "mean_margin_delta": mean(row["margin_delta"] for row in subset),
                "trace_changed_cells": sum(row["trace_changed"] for row in subset),
                "new_losses": sum(row["new_loss"] for row in subset),
                "activated_cells": sum(row.get("activation_count", 0) > 0 for row in subset),
                "activation_count": sum(row.get("activation_count", 0) for row in subset),
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
        "activated_cells": sum(row.get("activation_count", 0) > 0 for row in rows),
        "activation_count": sum(row.get("activation_count", 0) for row in rows),
        "strata": strata,
    }


def build_report(
    control_path: Path,
    unsafe_path: Path,
    certified_path: Path,
    *,
    source_seat: int,
    capture_receipt_path: Path,
) -> dict[str, Any]:
    if source_seat not in (0, 1):
        raise CertifiedReportError("source_seat must be 0 or 1")
    capture = _capture_receipt(capture_receipt_path)
    control = cells(_strict_json(control_path))
    unsafe = cells(_strict_json(unsafe_path))
    certified = cells(
        _strict_json(certified_path),
        source_seat=source_seat,
        capture=capture,
    )
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
    source_rows = [
        row for row in certified_summary["rows"] if row["seat"] == source_seat
    ]
    off_rows = [
        row for row in certified_summary["rows"] if row["seat"] != source_seat
    ]
    if not source_rows or not off_rows:
        raise CertifiedReportError("both candidate seats are required")

    def exact_fallback(row: Mapping[str, Any]) -> bool:
        return (
            row.get("activation_count") == 0
            and not row["trace_changed"]
            and row["own_cash_delta"] == 0
            and row["margin_delta"] == 0
        )

    off_seat_exact_fallback = all(exact_fallback(row) for row in off_rows)
    inactive_source_exact_fallback = all(
        exact_fallback(row)
        for row in source_rows
        if row.get("activation_count") == 0
    )
    activation_trace_consistent = all(
        (row.get("activation_count", 0) > 0) == bool(row["trace_changed"])
        for row in source_rows
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
    source_activated = any(row.get("activation_count", 0) > 0 for row in source_rows)
    source_activation_count = sum(row.get("activation_count", 0) for row in source_rows)

    if (
        off_seat_exact_fallback
        and inactive_source_exact_fallback
        and activation_trace_consistent
        and source_safe
        and source_activated
    ):
        verdict = "CERTIFIED_SURVIVOR"
    elif (
        off_seat_exact_fallback
        and inactive_source_exact_fallback
        and activation_trace_consistent
        and not source_activated
    ):
        verdict = "CERTIFICATE_REJECTS_TRANSPLANT"
    else:
        verdict = "CERTIFIED_HOLD"

    capture_bytes = capture_receipt_path.read_bytes()
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
        "activation_evidence": {
            "basis": "candidate-process policy diagnostics captured from the exact certified wrapper; trace hashes are consistency checks only",
            "capture_receipt": str(capture_receipt_path),
            "capture_receipt_sha256": hashlib.sha256(capture_bytes).hexdigest(),
            "candidate_sha256": capture["candidate_sha256"],
            "wrapper_sha256": capture["wrapper_sha256"],
            "source_activation_count": source_activation_count,
            "activation_trace_consistent": activation_trace_consistent,
            "inactive_source_exact_fallback": inactive_source_exact_fallback,
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
    activation = report["activation_evidence"]
    return "\n".join(
        [
            "# TITAN V3 S13 exact-certified prefix-695 report",
            "",
            f"**Verdict:** `{report['verdict']}`",
            f"**Source seat:** `{report['source_seat']}`",
            f"**Off-seat exact fallback:** `{report['off_seat_exact_fallback']}`",
            f"**Source-seat activation:** `{report['source_seat_activated']}`",
            f"**Authenticated activation count:** `{activation['source_activation_count']}`",
            f"**Activation/trace consistency:** `{activation['activation_trace_consistent']}`",
            "",
            "| arm | mean own Δ vs control | median own Δ | mean margin Δ | min own Δ | new losses | changed traces | activated cells | activations |",
            "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
            f"| unsafe prefix-695 | {unsafe['mean_own_cash_delta']:.3f} | {unsafe['median_own_cash_delta']:.3f} | {unsafe['mean_margin_delta']:.3f} | {unsafe['min_own_cash_delta']:.3f} | {unsafe['new_losses']} | {unsafe['trace_changed_cells']} | {unsafe['activated_cells']} | {unsafe['activation_count']} |",
            f"| exact-certified prefix-695 | {certified['mean_own_cash_delta']:.3f} | {certified['median_own_cash_delta']:.3f} | {certified['mean_margin_delta']:.3f} | {certified['min_own_cash_delta']:.3f} | {certified['new_losses']} | {certified['trace_changed_cells']} | {certified['activated_cells']} | {certified['activation_count']} |",
            "",
            "Source-seat activation is derived from exact candidate-process policy diagnostics. Trace changes are used only as a consistency check.",
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
    parser.add_argument("--capture-receipt", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--markdown", type=Path, required=True)
    args = parser.parse_args(argv)
    report = build_report(
        args.control,
        args.unsafe_prefix,
        args.certified_prefix,
        source_seat=args.source_seat,
        capture_receipt_path=args.capture_receipt,
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
