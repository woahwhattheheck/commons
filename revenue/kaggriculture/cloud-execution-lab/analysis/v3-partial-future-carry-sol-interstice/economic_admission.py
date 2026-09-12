# SPDX-License-Identifier: Apache-2.0
"""Fail-closed economic admission for the exact three-arm carry panel."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import statistics
from typing import Any, Mapping

import bind_execution as binding
import compare_three_arm as predecessor
import materialize as lane

OUTCOME_RANK = {"loss": 0, "tie": 1, "win": 2}
MIN_POSITIVE_OPPONENT_SEED_BLOCKS = 5
MIN_POSITIVE_SEEDS = 3


class AdmissionError(predecessor.ClassificationError):
    """The evidence cannot support a causal economic admission decision."""


def outcome(margin: float) -> str:
    if margin > 0:
        return "win"
    if margin < 0:
        return "loss"
    return "tie"


def paired_summary(
    before_cells: Mapping[tuple[str, int, int], Mapping[str, Any]],
    after_cells: Mapping[tuple[str, int, int], Mapping[str, Any]],
) -> dict[str, Any]:
    if set(before_cells) != set(after_cells):
        raise AdmissionError("paired comparison cell sets differ")

    rows: list[dict[str, Any]] = []
    transitions: dict[str, int] = {}
    for key in sorted(before_cells):
        opponent, seed, seat = key
        before = before_cells[key]
        after = after_cells[key]
        own_delta = after["own"] - before["own"]
        rival_delta = after["rival"] - before["rival"]
        margin_delta = own_delta - rival_delta
        action_changed = before["action_sha256"] != after["action_sha256"]
        trace_changed = before["trace_sha256"] != after["trace_sha256"]
        first_divergence = predecessor.first_bank_divergence(
            before["daily_bank"], after["daily_bank"]
        )
        terminal_changed = (
            own_delta != 0 or rival_delta != 0 or first_divergence is not None
        )
        if not action_changed and (trace_changed or terminal_changed):
            raise AdmissionError(
                f"action-identical cell {key} changed trace or terminal evidence"
            )
        if not trace_changed and terminal_changed:
            raise AdmissionError(
                f"trace-identical cell {key} changed terminal evidence"
            )

        before_outcome = outcome(before["margin"])
        after_outcome = outcome(after["margin"])
        transition = f"{before_outcome}->{after_outcome}"
        transitions[transition] = transitions.get(transition, 0) + 1
        rows.append(
            {
                "opponent": opponent,
                "seed": seed,
                "candidate_seat": seat,
                "own_delta": own_delta,
                "rival_delta": rival_delta,
                "margin_delta": margin_delta,
                "action_changed": action_changed,
                "trace_changed": trace_changed,
                "realized_action_change": action_changed and trace_changed,
                "terminal_changed": terminal_changed,
                "before_outcome": before_outcome,
                "after_outcome": after_outcome,
                "new_loss": after_outcome == "loss" and before_outcome != "loss",
                "lost_win": before_outcome == "win" and after_outcome != "win",
                "outcome_regression": (
                    OUTCOME_RANK[after_outcome] < OUTCOME_RANK[before_outcome]
                ),
                "first_daily_bank_divergence": first_divergence,
            }
        )

    own = [row["own_delta"] for row in rows]
    rival = [row["rival_delta"] for row in rows]
    margin = [row["margin_delta"] for row in rows]
    subgroup_own: dict[str, list[float]] = {}
    subgroup_margin: dict[str, list[float]] = {}
    blocks: dict[tuple[str, int], list[dict[str, Any]]] = {}
    for row in rows:
        subgroup = f"{row['opponent']}/seat-{row['candidate_seat']}"
        subgroup_own.setdefault(subgroup, []).append(row["own_delta"])
        subgroup_margin.setdefault(subgroup, []).append(row["margin_delta"])
        blocks.setdefault((row["opponent"], row["seed"]), []).append(row)

    block_rows: list[dict[str, Any]] = []
    for (opponent, seed), block in sorted(blocks.items()):
        block_rows.append(
            {
                "opponent": opponent,
                "seed": seed,
                "mean_own_delta": statistics.fmean(
                    row["own_delta"] for row in block
                ),
                "mean_margin_delta": statistics.fmean(
                    row["margin_delta"] for row in block
                ),
                "realized_action_cells": sum(
                    row["realized_action_change"] for row in block
                ),
            }
        )
    positive_blocks = [row for row in block_rows if row["mean_own_delta"] > 0]
    negative_blocks = [row for row in block_rows if row["mean_own_delta"] < 0]
    sign_tail = (
        1.0 / (2 ** len(positive_blocks))
        if positive_blocks and not negative_blocks
        else 1.0
    )

    summary: dict[str, Any] = {
        "cells": len(rows),
        "changed_action_cells": sum(row["action_changed"] for row in rows),
        "changed_trace_cells": sum(row["trace_changed"] for row in rows),
        "realized_action_cells": sum(
            row["realized_action_change"] for row in rows
        ),
        "inert_action_cells": sum(
            row["action_changed"] and not row["trace_changed"] for row in rows
        ),
        "terminal_changed_cells": sum(row["terminal_changed"] for row in rows),
        "mean_own_delta": statistics.fmean(own),
        "median_own_delta": statistics.median(own),
        "min_own_delta": min(own),
        "max_own_delta": max(own),
        "positive_own_cells": sum(value > 0 for value in own),
        "zero_own_cells": sum(value == 0 for value in own),
        "negative_own_cells": sum(value < 0 for value in own),
        "mean_rival_delta": statistics.fmean(rival),
        "mean_margin_delta": statistics.fmean(margin),
        "subgroup_mean_own_delta": {
            name: statistics.fmean(values)
            for name, values in sorted(subgroup_own.items())
        },
        "subgroup_mean_margin_delta": {
            name: statistics.fmean(values)
            for name, values in sorted(subgroup_margin.items())
        },
        "new_losses": sum(row["new_loss"] for row in rows),
        "lost_wins": sum(row["lost_win"] for row in rows),
        "outcome_regressions": sum(row["outcome_regression"] for row in rows),
        "outcome_transitions": dict(sorted(transitions.items())),
        "positive_opponent_seed_blocks": len(positive_blocks),
        "negative_opponent_seed_blocks": len(negative_blocks),
        "opponent_seed_sign_tail": sign_tail,
        "positive_block_opponents": sorted(
            {row["opponent"] for row in positive_blocks}
        ),
        "positive_block_seeds": sorted({row["seed"] for row in positive_blocks}),
        "opponent_seed_block_rows": block_rows,
        "first_divergence_steps": sorted(
            {
                row["first_daily_bank_divergence"]
                for row in rows
                if row["first_daily_bank_divergence"] is not None
            }
        ),
        "rows": rows,
    }
    checks = {
        "realized_action_signal": summary["realized_action_cells"] > 0,
        "mean_own_positive": summary["mean_own_delta"] > 0,
        "median_own_nonnegative": summary["median_own_delta"] >= 0,
        "no_negative_own_cells": summary["negative_own_cells"] == 0,
        "global_margin_nonnegative": summary["mean_margin_delta"] >= 0,
        "all_opponent_seat_own_nonnegative": all(
            value >= 0 for value in summary["subgroup_mean_own_delta"].values()
        ),
        "all_opponent_seat_margin_nonnegative": all(
            value >= 0 for value in summary["subgroup_mean_margin_delta"].values()
        ),
        "no_new_losses": summary["new_losses"] == 0,
        "no_lost_wins": summary["lost_wins"] == 0,
        "no_outcome_regressions": summary["outcome_regressions"] == 0,
        "clustered_sign_tail_at_most_0_05": (
            summary["negative_opponent_seed_blocks"] == 0
            and summary["positive_opponent_seed_blocks"]
            >= MIN_POSITIVE_OPPONENT_SEED_BLOCKS
            and summary["opponent_seed_sign_tail"] <= 0.05
        ),
        "positive_blocks_span_all_opponents": set(
            summary["positive_block_opponents"]
        )
        == set(predecessor.expected_opponents()),
        "positive_blocks_span_three_seeds": len(summary["positive_block_seeds"])
        >= MIN_POSITIVE_SEEDS,
    }
    summary["admission_checks"] = checks
    summary["passes_economic_admission_gate"] = all(checks.values())
    return summary


def verdict_for(summary: Mapping[str, Any]) -> str:
    checks = summary["admission_checks"]
    if summary["changed_action_cells"] == 0:
        return "NO_REPAIR_ACTION_CHANGE"
    if summary["realized_action_cells"] == 0:
        return "NO_REPAIR_REALIZED_CHANGE"
    if summary["mean_own_delta"] <= 0:
        return "REPAIR_NO_MEAN_UPSIDE"
    if summary["negative_own_cells"]:
        return "REPAIR_MIXED_UPSIDE"
    if not (
        checks["global_margin_nonnegative"]
        and checks["all_opponent_seat_own_nonnegative"]
        and checks["all_opponent_seat_margin_nonnegative"]
    ):
        return "REPAIR_MARGIN_REGRESSION"
    if not (
        checks["no_new_losses"]
        and checks["no_lost_wins"]
        and checks["no_outcome_regressions"]
    ):
        return "REPAIR_OUTCOME_REGRESSION"
    if not (
        checks["clustered_sign_tail_at_most_0_05"]
        and checks["positive_blocks_span_all_opponents"]
        and checks["positive_blocks_span_three_seeds"]
    ):
        return "REPAIR_INSUFFICIENT_CLUSTERED_SUPPORT"
    if not summary["passes_economic_admission_gate"]:
        return "REPAIR_ROBUSTNESS_GATE_FAILED"
    return "REPAIR_BEATS_CONTROL"


def classify(
    control: Mapping[str, Any],
    strict: Mapping[str, Any],
    repair: Mapping[str, Any],
    binding_arms: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    control_cells, control_invocation = predecessor.validate_panel(
        control, arm="control", binding_arm=binding_arms["control"]
    )
    strict_cells, strict_invocation = predecessor.validate_panel(
        strict, arm="strict", binding_arm=binding_arms["strict"]
    )
    repair_cells, repair_invocation = predecessor.validate_panel(
        repair, arm="repair", binding_arm=binding_arms["repair"]
    )
    if len({control_invocation, strict_invocation, repair_invocation}) != 3:
        raise AdmissionError("the three arm invocations are not distinct")
    for field in predecessor.COMMON_RUNTIME_FIELDS:
        if strict.get(field) != control.get(field) or repair.get(field) != control.get(field):
            raise AdmissionError(f"panel common runtime mismatch at {field}")

    strict_vs_control = paired_summary(control_cells, strict_cells)
    repair_vs_control = paired_summary(control_cells, repair_cells)
    repair_vs_strict = paired_summary(strict_cells, repair_cells)
    repair_passes = repair_vs_control["passes_economic_admission_gate"]
    strict_passes = strict_vs_control["passes_economic_admission_gate"]
    dominates_strict = repair_vs_strict["passes_economic_admission_gate"]

    verdict = verdict_for(repair_vs_control)
    if repair_passes and dominates_strict:
        verdict = "REPAIR_DOMINATES_CONTROL_AND_STRICT"
    preferred = "strict" if strict_passes else "control"
    if repair_passes and (not strict_passes or dominates_strict):
        preferred = "repair"
    return {
        "verdict": verdict,
        "passes_economic_admission_gate": repair_passes,
        "passes_no_negative_control_screen": repair_passes,
        "preferred_arm_under_economic_admission_gate": preferred,
        "preferred_arm_under_no_negative_guard": preferred,
        "invocations": {
            "control": control_invocation,
            "strict": strict_invocation,
            "repair": repair_invocation,
        },
        "strict_vs_control": strict_vs_control,
        "repair_vs_control": repair_vs_control,
        "repair_vs_strict": repair_vs_strict,
    }


def markdown(report: Mapping[str, Any]) -> str:
    comparisons = report["comparisons"]
    lines = [
        "# Titan V3 partial-future carry economic admission",
        "",
        f"**Verdict:** `{comparisons['verdict']}`",
        "**Preferred arm:** "
        f"`{comparisons['preferred_arm_under_economic_admission_gate']}`",
        "",
        "This is a closure-bound causal panel, not leaderboard or release authority.",
        "",
        "| comparison | mean own | mean margin | + / 0 / - | realized | new losses | sign tail | pass |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for label in ("strict_vs_control", "repair_vs_control", "repair_vs_strict"):
        row = comparisons[label]
        lines.append(
            f"| {label} | {row['mean_own_delta']:.3f} | "
            f"{row['mean_margin_delta']:.3f} | {row['positive_own_cells']} / "
            f"{row['zero_own_cells']} / {row['negative_own_cells']} | "
            f"{row['realized_action_cells']} | {row['new_losses']} | "
            f"{row['opponent_seed_sign_tail']:.6f} | "
            f"{row['passes_economic_admission_gate']} |"
        )
    failed = [
        name
        for name, passed in comparisons["repair_vs_control"][
            "admission_checks"
        ].items()
        if not passed
    ]
    lines.extend(
        [
            "",
            f"Failed repair-vs-control gates: `{failed}`",
            "",
            "Repair can displace strict only after the same complete gate passes "
            "on repair-versus-strict evidence.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--control", type=Path, required=True)
    parser.add_argument("--strict", type=Path, required=True)
    parser.add_argument("--repair", type=Path, required=True)
    parser.add_argument("--binding-receipt", type=Path, required=True)
    parser.add_argument("--strict-receipt", type=Path, required=True)
    parser.add_argument("--repair-receipt", type=Path, required=True)
    parser.add_argument("--evaluator-receipt", type=Path, required=True)
    parser.add_argument("--arms-root", type=Path, required=True)
    parser.add_argument("--patched-evaluator", type=Path, required=True)
    parser.add_argument("--head", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--markdown", type=Path, required=True)
    args = parser.parse_args()

    predecessor.validate_live_source_bank()
    strict_receipt = binding.strict_object(args.strict_receipt)
    repair_receipt = binding.strict_object(args.repair_receipt)
    binding.validate_strict_receipt(strict_receipt)
    binding.validate_repair_receipt(repair_receipt)
    evaluator_receipt = binding.strict_object(args.evaluator_receipt)
    predecessor.validate_evaluator_receipt(evaluator_receipt, args.patched_evaluator)
    binding_receipt = binding.strict_object(args.binding_receipt)
    binding_arms = predecessor.validate_binding(
        binding_receipt,
        args.arms_root,
        args.strict_receipt,
        args.repair_receipt,
    )
    comparisons = classify(
        binding.strict_object(args.control),
        binding.strict_object(args.strict),
        binding.strict_object(args.repair),
        binding_arms,
    )
    report = {
        "schema_version": 2,
        "operation": predecessor.OPERATION,
        "head": args.head,
        "identities": {
            "control_sha256": predecessor.digest_file(args.control),
            "strict_sha256": predecessor.digest_file(args.strict),
            "repair_sha256": predecessor.digest_file(args.repair),
            "binding_sha256": predecessor.digest_file(args.binding_receipt),
            "strict_materialization_sha256": predecessor.digest_file(
                args.strict_receipt
            ),
            "repair_materialization_sha256": predecessor.digest_file(
                args.repair_receipt
            ),
            "evaluator_materialization_sha256": predecessor.digest_file(
                args.evaluator_receipt
            ),
            "patched_evaluator_sha256": predecessor.digest_file(
                args.patched_evaluator
            ),
        },
        "comparisons": comparisons,
    }
    lane.atomic_write(
        args.output,
        (json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n").encode(
            "utf-8"
        ),
    )
    lane.atomic_write(args.markdown, markdown(report).encode("utf-8"))
    print(
        json.dumps(
            {
                "verdict": comparisons["verdict"],
                "preferred": comparisons[
                    "preferred_arm_under_economic_admission_gate"
                ],
                "passes": comparisons["passes_economic_admission_gate"],
            },
            sort_keys=True,
        )
    )
    return 0 if comparisons["passes_economic_admission_gate"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
