#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Fail-closed selector for paired leader-route experiment reports."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import statistics
from typing import Any, Iterable, Mapping


class SelectionError(RuntimeError):
    pass


def _number(value: Any) -> float | None:
    if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value)):
        return float(value)
    return None


def _walk(value: Any) -> Iterable[Mapping[str, Any]]:
    if isinstance(value, Mapping):
        yield value
        for child in value.values():
            yield from _walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk(child)


def _pick(mapping: Mapping[str, Any], *names: str) -> float | None:
    for name in names:
        value = _number(mapping.get(name))
        if value is not None:
            return value
    return None


def _pair_rows(report: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    best: list[Mapping[str, Any]] = []
    stack: list[Any] = [report]
    while stack:
        value = stack.pop()
        if isinstance(value, Mapping):
            stack.extend(value.values())
        elif isinstance(value, list):
            rows = [row for row in value if isinstance(row, Mapping)]
            score = sum(
                1
                for row in rows
                if any(
                    name in row
                    for name in (
                        "own_cash_delta",
                        "candidate_own_cash",
                        "control_own_cash",
                        "margin_delta",
                    )
                )
            )
            if score > len(best):
                best = rows
            stack.extend(value)
    return best


def metrics(report: Mapping[str, Any]) -> dict[str, Any]:
    overall = report.get("overall") if isinstance(report.get("overall"), Mapping) else {}
    mean_own = _pick(overall, "mean_own_cash_delta", "mean_candidate_own_cash_delta")
    median_own = _pick(overall, "median_own_cash_delta", "median_candidate_own_cash_delta")
    mean_margin = _pick(overall, "mean_margin_delta", "mean_score_margin_delta")
    changed = _pick(overall, "trace_changed_cells", "action_changed_cells", "changed_action_cells")
    new_losses = _pick(overall, "new_losses", "new_loss_cells", "wins_lost")

    rows = _pair_rows(report)
    own_values: list[float] = []
    margin_values: list[float] = []
    stratum: dict[tuple[str, str], dict[str, list[float]]] = {}
    inferred_new_losses = 0
    for row in rows:
        own = _pick(row, "own_cash_delta", "candidate_own_cash_delta")
        if own is None:
            candidate = _pick(row, "candidate_own_cash", "candidate_cash")
            control = _pick(row, "control_own_cash", "control_cash")
            if candidate is not None and control is not None:
                own = candidate - control
        margin = _pick(row, "margin_delta", "score_margin_delta")
        if margin is None:
            cand_own = _pick(row, "candidate_own_cash", "candidate_cash")
            cand_other = _pick(row, "candidate_opponent_cash", "candidate_rival_cash")
            ctrl_own = _pick(row, "control_own_cash", "control_cash")
            ctrl_other = _pick(row, "control_opponent_cash", "control_rival_cash")
            if None not in (cand_own, cand_other, ctrl_own, ctrl_other):
                margin = (cand_own - cand_other) - (ctrl_own - ctrl_other)
        if own is not None:
            own_values.append(own)
        if margin is not None:
            margin_values.append(margin)
        opponent = str(row.get("opponent", row.get("opponent_name", "unknown")))
        seat = str(row.get("candidate_seat", row.get("seat", row.get("candidate_position", "unknown"))))
        bucket = stratum.setdefault((opponent, seat), {"own": [], "margin": []})
        if own is not None:
            bucket["own"].append(own)
        if margin is not None:
            bucket["margin"].append(margin)
        control_outcome = str(row.get("control_outcome", row.get("baseline_outcome", ""))).lower()
        candidate_outcome = str(row.get("candidate_outcome", "")).lower()
        control_margin = _pick(row, "control_margin")
        candidate_margin = _pick(row, "candidate_margin")
        if (
            candidate_outcome == "loss"
            and control_outcome in {"win", "tie", "draw"}
        ) or (
            candidate_margin is not None
            and control_margin is not None
            and candidate_margin < 0 <= control_margin
        ):
            inferred_new_losses += 1

    if mean_own is None and own_values:
        mean_own = statistics.fmean(own_values)
    if median_own is None and own_values:
        median_own = statistics.median(own_values)
    if mean_margin is None and margin_values:
        mean_margin = statistics.fmean(margin_values)
    if new_losses is None and rows:
        new_losses = float(inferred_new_losses)
    if changed is None:
        for node in _walk(report):
            changed = _pick(node, "trace_changed_cells", "action_changed_cells", "changed_action_cells")
            if changed is not None:
                break

    strata = []
    for (opponent, seat), values in sorted(stratum.items()):
        strata.append({
            "opponent": opponent,
            "seat": seat,
            "mean_own_cash_delta": statistics.fmean(values["own"]) if values["own"] else None,
            "mean_margin_delta": statistics.fmean(values["margin"]) if values["margin"] else None,
        })
    return {
        "parent_verdict": report.get("verdict"),
        "mean_own_cash_delta": mean_own,
        "median_own_cash_delta": median_own,
        "mean_margin_delta": mean_margin,
        "trace_changed_cells": changed,
        "new_losses": new_losses,
        "strata": strata,
        "pair_rows": len(rows),
    }


def classify(value: Mapping[str, Any]) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    required = (
        "mean_own_cash_delta",
        "median_own_cash_delta",
        "mean_margin_delta",
        "trace_changed_cells",
        "new_losses",
    )
    for key in required:
        if _number(value.get(key)) is None:
            reasons.append(f"missing_{key}")
    if reasons:
        return False, reasons
    if float(value["trace_changed_cells"]) <= 0:
        reasons.append("zero_action_activation")
    if float(value["mean_own_cash_delta"]) <= 0:
        reasons.append("nonpositive_mean_own_cash")
    if float(value["median_own_cash_delta"]) < 0:
        reasons.append("negative_median_own_cash")
    if float(value["mean_margin_delta"]) < 0:
        reasons.append("negative_global_margin")
    if float(value["new_losses"]) > 0:
        reasons.append("new_losses")
    strata = value.get("strata")
    if not isinstance(strata, list) or not strata:
        reasons.append("missing_opponent_seat_strata")
    else:
        for row in strata:
            if not isinstance(row, Mapping):
                reasons.append("malformed_stratum")
                continue
            own = _number(row.get("mean_own_cash_delta"))
            margin = _number(row.get("mean_margin_delta"))
            if own is None or margin is None:
                reasons.append("incomplete_stratum")
            elif own < 0 or margin < 0:
                reasons.append(f"negative_stratum:{row.get('opponent')}:{row.get('seat')}")
    return not reasons, reasons


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reports-dir", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--selected", type=Path, required=True)
    parser.add_argument("--top", type=int, default=2)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    arms = {row["arm_id"]: row for row in manifest.get("arms", [])}
    results = []
    for path in sorted(args.reports_dir.glob("*.json")):
        arm_id = path.stem
        if arm_id not in arms:
            continue
        report = json.loads(path.read_text(encoding="utf-8"))
        value = metrics(report)
        advance, reasons = classify(value)
        results.append({"arm_id": arm_id, "advance": advance, "reasons": reasons, "metrics": value, "source": arms[arm_id]})
    if len(results) != len(arms):
        missing = sorted(set(arms) - {row["arm_id"] for row in results})
        raise SelectionError(f"missing pair reports: {missing}")
    ranked = sorted(
        results,
        key=lambda row: (
            not row["advance"],
            -float(row["metrics"].get("mean_own_cash_delta") or -10**18),
            -float(row["metrics"].get("mean_margin_delta") or -10**18),
            row["arm_id"],
        ),
    )
    selected = [row["arm_id"] for row in ranked if row["advance"]][: args.top]
    payload = {"schema": "titan-v3-s13-route-selection/v1", "selected": selected, "arms": ranked}
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    args.selected.write_text("\n".join(selected) + ("\n" if selected else ""), encoding="utf-8")
    print(json.dumps({"arms": len(ranked), "advanced": sum(row["advance"] for row in ranked), "selected": selected}, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SelectionError as exc:
        print(f"ERROR: {exc}")
        raise SystemExit(2)
