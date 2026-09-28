#!/usr/bin/env python3
"""Fail closed before a margin-only three-arm result becomes a development lead."""
from __future__ import annotations

import argparse
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping

import evidence
import panel_analysis
import variants as arm_defs

OPERATION = "op:titan-v3-final-pressure-three-arm-20260909-solstice"
DIRECTIONAL_SIGNALS = {
    "final_boundary": "FINAL_BOUNDARY_LEADS_DEVELOPMENT",
    "legacy_in_pipeline": "LEGACY_IN_PIPELINE_LEADS_DEVELOPMENT",
    "pressure_off": "PRESSURE_OFF_LEADS_DEVELOPMENT",
}
# comparison key, +1 when the prospective leader is the stored left arm, -1 otherwise
LEADER_COMPARISONS = {
    "final_boundary": (
        ("final_boundary_minus_pressure_off", 1, "pressure_off"),
        ("final_boundary_minus_legacy_in_pipeline", 1, "legacy_in_pipeline"),
    ),
    "legacy_in_pipeline": (
        ("final_boundary_minus_legacy_in_pipeline", -1, "final_boundary"),
        ("legacy_in_pipeline_minus_pressure_off", 1, "pressure_off"),
    ),
    "pressure_off": (
        ("final_boundary_minus_pressure_off", -1, "final_boundary"),
        ("legacy_in_pipeline_minus_pressure_off", -1, "legacy_in_pipeline"),
    ),
}
CLASSIFICATIONS = frozenset(("identical", "syntactic_only", "state_only", "realized"))


def _integer(value: Any, *, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise evidence.EvidenceError(f"{label} must be a nonnegative integer")
    return value


def _number(value: Any, *, label: str) -> float:
    if not panel_analysis.finite_number(value):
        raise evidence.EvidenceError(f"{label} must be a finite number")
    return float(value)


def _directed(comparison: Mapping[str, Any], direction: int, *, label: str) -> dict[str, Any]:
    if direction not in (-1, 1):
        raise evidence.EvidenceError(f"Invalid comparison direction for {label}")
    paired = comparison.get("paired_cells")
    if not isinstance(paired, list) or not paired:
        raise evidence.EvidenceError(f"{label}.paired_cells must be a nonempty list")
    counts = {name: 0 for name in CLASSIFICATIONS}
    state_precedes_action = 0
    for index, row in enumerate(paired):
        if not isinstance(row, dict) or row.get("classification") not in counts:
            raise evidence.EvidenceError(f"Invalid classification at {label}/{index}")
        classification = row["classification"]
        action_step = row.get("first_candidate_action_divergence")
        state_step = row.get("first_post_state_divergence")
        for field, value in (("action", action_step), ("state", state_step)):
            if value is not None and (
                isinstance(value, bool) or not isinstance(value, int) or value < 0
            ):
                raise evidence.EvidenceError(
                    f"Invalid first {field} divergence at {label}/{index}"
                )
        expected_presence = {
            "identical": (False, False),
            "syntactic_only": (True, False),
            "state_only": (False, True),
            "realized": (True, True),
        }[classification]
        if (action_step is not None, state_step is not None) != expected_presence:
            raise evidence.EvidenceError(
                f"Classification/divergence mismatch at {label}/{index}"
            )
        if (
            classification == "realized"
            and state_step is not None
            and action_step is not None
            and state_step < action_step
        ):
            state_precedes_action += 1
        counts[classification] += 1
    cells = _integer(comparison.get("cells"), label=f"{label}.cells")
    if cells != len(paired) or sum(counts.values()) != cells:
        raise evidence.EvidenceError(f"{label} classification/cardinality mismatch")
    action_changed = _integer(
        comparison.get("candidate_action_changed_cells"),
        label=f"{label}.candidate_action_changed_cells",
    )
    state_changed = _integer(
        comparison.get("post_state_changed_cells"),
        label=f"{label}.post_state_changed_cells",
    )
    if action_changed != counts["syntactic_only"] + counts["realized"]:
        raise evidence.EvidenceError(f"{label} action classification mismatch")
    if state_changed != counts["state_only"] + counts["realized"]:
        raise evidence.EvidenceError(f"{label} state classification mismatch")
    forward_new_losses = _integer(
        comparison.get("new_losses"), label=f"{label}.new_losses"
    )
    forward_resolved_losses = _integer(
        comparison.get("resolved_losses"), label=f"{label}.resolved_losses"
    )
    return {
        "direction": direction,
        "cells": cells,
        "realized_cells": counts["realized"],
        "state_only_cells": counts["state_only"],
        "state_precedes_action_cells": state_precedes_action,
        "syntactic_only_cells": counts["syntactic_only"],
        "identical_cells": counts["identical"],
        "mean_margin_delta": direction
        * _number(comparison.get("mean_margin_delta"), label=f"{label}.mean_margin_delta"),
        "mean_candidate_score_delta": direction
        * _number(
            comparison.get("mean_candidate_score_delta"),
            label=f"{label}.mean_candidate_score_delta",
        ),
        "mean_opponent_score_delta": direction
        * _number(
            comparison.get("mean_opponent_score_delta"),
            label=f"{label}.mean_opponent_score_delta",
        ),
        "new_losses": (
            forward_new_losses if direction == 1 else forward_resolved_losses
        ),
        "resolved_losses": (
            forward_resolved_losses if direction == 1 else forward_new_losses
        ),
    }


def classify_summary(summary: Mapping[str, Any]) -> dict[str, Any]:
    """Return a directional signal only with realized, own-score-positive evidence."""
    if not isinstance(summary, Mapping):
        raise evidence.EvidenceError("summary must be an object")
    comparisons = summary.get("comparisons")
    if not isinstance(comparisons, Mapping):
        raise evidence.EvidenceError("summary.comparisons must be an object")
    required = {
        "final_boundary_minus_pressure_off",
        "final_boundary_minus_legacy_in_pipeline",
        "legacy_in_pipeline_minus_pressure_off",
    }
    if set(comparisons) != required:
        raise evidence.EvidenceError("summary comparison identity mismatch")
    leaders = summary.get("leaders_by_mean_margin")
    if (
        not isinstance(leaders, list)
        or not leaders
        or len(leaders) != len(set(leaders))
        or any(name not in arm_defs.VARIANTS for name in leaders)
    ):
        raise evidence.EvidenceError("Invalid leaders_by_mean_margin")

    normalized: dict[str, dict[str, Any]] = {}
    total_state_only = 0
    total_state_precedes_action = 0
    for key in sorted(required):
        value = comparisons[key]
        if not isinstance(value, Mapping):
            raise evidence.EvidenceError(f"Comparison {key} must be an object")
        directed = _directed(value, 1, label=key)
        normalized[key] = directed
        total_state_only += directed["state_only_cells"]
        total_state_precedes_action += directed["state_precedes_action_cells"]

    raw_signal = summary.get("development_signal")
    if not isinstance(raw_signal, str) or not raw_signal:
        raise evidence.EvidenceError("Missing raw development_signal")

    decision: dict[str, Any] = {
        "schema_version": 1,
        "operation": OPERATION,
        "raw_margin_signal": raw_signal,
        "leaders_by_mean_margin": list(leaders),
        "state_only_cells_across_pairings": total_state_only,
        "state_precedes_action_cells_across_pairings": total_state_precedes_action,
        "qualified_directional_leader": False,
        "automatic_promotion": False,
        "comparisons": {},
    }
    if total_state_precedes_action:
        decision.update(
            development_signal="CAUSAL_ORDER_HOLD",
            reason=(
                "At least one arm pair changed post-engine state before its first "
                "candidate-action divergence; the later action cannot cause the earlier state."
            ),
        )
        return decision
    if total_state_only:
        decision.update(
            development_signal="STATE_ONLY_HOLD",
            reason=(
                "At least one arm pair changed post-engine state without any "
                "candidate-action divergence; causal attribution is ambiguous."
            ),
        )
        return decision
    if len(leaders) != 1:
        decision.update(
            development_signal="DEVELOPMENT_TIE",
            reason="No unique mean-margin leader exists on the complete development grid.",
        )
        return decision

    leader = leaders[0]
    leader_rows: dict[str, Any] = {}
    failures: list[str] = []
    for key, direction, comparator in LEADER_COMPARISONS[leader]:
        row = _directed(comparisons[key], direction, label=key)
        checks = {
            "realized_activation": row["realized_cells"] > 0,
            "positive_mean_margin": row["mean_margin_delta"] > 0,
            "positive_mean_candidate_score": row["mean_candidate_score_delta"] > 0,
            "no_new_losses": row["new_losses"] == 0,
        }
        leader_rows[comparator] = {**row, "checks": checks}
        failures.extend(
            f"{leader}_vs_{comparator}:{name}"
            for name, passed in checks.items()
            if not passed
        )
    decision["leader"] = leader
    decision["comparisons"] = leader_rows
    if not failures:
        decision.update(
            development_signal=DIRECTIONAL_SIGNALS[leader],
            qualified_directional_leader=True,
            reason=(
                "Unique mean-margin leader also has realized activation, positive "
                "own-score and margin deltas, and no new losses against both arms."
            ),
        )
        return decision

    if any(item.endswith(":realized_activation") for item in failures):
        signal = "UNREALIZED_LEADER_HOLD"
    elif any(item.endswith(":positive_mean_candidate_score") for item in failures):
        signal = "MARGIN_ONLY_LEADER_HOLD"
    elif any(item.endswith(":no_new_losses") for item in failures):
        signal = "NEW_LOSS_HOLD"
    else:
        signal = "MIXED_DEVELOPMENT_HOLD"
    decision.update(
        development_signal=signal,
        failed_checks=failures,
        reason="The unique margin leader did not satisfy the causal/own-score safety gate.",
    )
    return decision


def gate_report(report: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    if not isinstance(report, Mapping):
        raise evidence.EvidenceError("Report must be a JSON object")
    if report.get("schema_version") != 1 or report.get("operation") != OPERATION:
        raise evidence.EvidenceError("Report schema/operation mismatch")
    if report.get("status") != "complete" or report.get("all_complete") is not True:
        raise evidence.EvidenceError("Decision gate requires a complete report")
    games = report.get("games")
    variant_rows = report.get("variants")
    opponents = report.get("opponents")
    seeds = report.get("seeds")
    if not isinstance(games, list) or not isinstance(variant_rows, list):
        raise evidence.EvidenceError("Report games/variants must be lists")
    if not isinstance(opponents, list) or not isinstance(seeds, list):
        raise evidence.EvidenceError("Report opponents/seeds must be lists")
    recomputed = panel_analysis.summarize(games, variant_rows, opponents, seeds)
    if report.get("summary") != recomputed:
        raise evidence.EvidenceError("Stored summary differs from exact game re-derivation")
    scheduled = report.get("scheduled_games")
    if isinstance(scheduled, bool) or not isinstance(scheduled, int) or scheduled != len(games):
        raise evidence.EvidenceError("scheduled_games does not bind the game ledger")
    decision = classify_summary(recomputed)
    patched = deepcopy(dict(report))
    patched_summary = deepcopy(recomputed)
    patched_summary["raw_margin_signal"] = recomputed["development_signal"]
    patched_summary["development_signal"] = decision["development_signal"]
    patched_summary["decision_gate"] = decision
    patched["summary"] = patched_summary
    patched["decision_gate"] = decision
    patched["automatic_promotion"] = False
    return patched, decision


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--decision", type=Path, required=True)
    parser.add_argument("--markdown", type=Path, required=True)
    args = parser.parse_args()
    value, source = evidence.read_json(args.report, max_bytes=256 << 20)
    patched, decision = gate_report(value)
    decision = dict(decision)
    decision["input_report_sha256"] = source.sha256
    patched["decision_gate"] = decision
    patched["summary"]["decision_gate"] = decision
    evidence.write_json(args.report, patched)
    args.markdown.parent.mkdir(parents=True, exist_ok=True)
    temporary_markdown = args.markdown.with_name(args.markdown.name + ".tmp")
    temporary_markdown.write_text(panel_analysis.markdown(patched), encoding="utf-8")
    temporary_markdown.replace(args.markdown)
    decision["gated_report_sha256"] = evidence.snapshot(args.report).sha256
    decision["gated_markdown_sha256"] = evidence.snapshot(args.markdown).sha256
    evidence.write_json(args.decision, decision)
    print(
        f"FINAL_PRESSURE_DECISION {decision['development_signal']} "
        f"qualified={decision['qualified_directional_leader']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
