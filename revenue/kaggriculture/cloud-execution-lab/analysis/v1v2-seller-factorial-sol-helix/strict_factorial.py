# SPDX-License-Identifier: Apache-2.0
"""Fail-closed admission and own-cash ranking for the HELIX V1/V2 factorial.

This module deliberately does not materialize the candidate-action evaluator.
It consumes the SOL-VECTOR action fields and SOL-LATTICE receipt accounting and
rejects reports that predate those producer contracts.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import statistics
from typing import Any, Mapping, Sequence

from strict_common import *  # re-export the public contract used by materializers/tests
from strict_evidence import validate_arm


def _own_margin(game: Mapping[str, Any], seat: int) -> tuple[float, float]:
    own = float(game["scores"][seat])
    rival = float(game["scores"][1 - seat])
    return own, own - rival


def summarize(values: Sequence[float]) -> dict[str, Any]:
    if not values:
        return {"n": 0}
    return {
        "n": len(values),
        "mean": statistics.fmean(values),
        "median": statistics.median(values),
        "min": min(values),
        "max": max(values),
        "positive": sum(value > 0 for value in values),
        "zero": sum(value == 0 for value in values),
        "negative": sum(value < 0 for value in values),
    }


def _effects(values: Mapping[str, float]) -> dict[str, float]:
    control, carry, force, both = (values[arm] for arm in ARMS)
    return {
        "carry_main": ((carry - control) + (both - force)) / 2,
        "force_end_main": ((force - control) + (both - carry)) / 2,
        "interaction": both - carry - force + control,
    }


def _shared_environment(arms: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    control = arms["control"]
    identity_fields = (
        "engine_ref", "evaluator_source_sha256", "evaluator_effective_sha256",
        "loader_sha256", "opponent_entry_sha256", "opponent_bundles",
        "generated_apex_binary",
    )
    shared = {field: control["identity"].get(field) for field in identity_fields}
    for arm, row in arms.items():
        for field in identity_fields:
            if row["identity"].get(field) != shared[field]:
                raise AdmissionError(f"{arm}: cross-arm identity drift in {field}")
    environment = control["environment_rows"][0]
    for arm, row in arms.items():
        for item in row["environment_rows"]:
            if item != environment:
                raise AdmissionError(f"{arm}: cross-shard runtime environment drift")
    entries = [row["materialization"]["entry_sha256"] for row in arms.values()]
    closures = [row["materialization"]["closure_sha256"] for row in arms.values()]
    receipts = [row["materialization"]["receipt_sha256"] for row in arms.values()]
    invocations = [value for row in arms.values() for value in row["invocation_ids"]]
    for label, values, expected in (
        ("entrypoints", entries, 4),
        ("closures", closures, 4),
        ("materialization receipts", receipts, 4),
        ("evaluator invocations", invocations, 8),
    ):
        if len(values) != expected or len(set(values)) != expected:
            raise AdmissionError(f"factorial lacks distinct {label}")
    return {
        "identity": shared,
        "runtime": environment,
        "entry_sha256": dict(zip(ARMS, entries)),
        "closure_sha256": dict(zip(ARMS, closures)),
        "materialization_receipt_sha256": dict(zip(ARMS, receipts)),
        "invocation_ids": invocations,
    }


def build_report(arm_paths: Mapping[str, Path], *, head: str) -> dict[str, Any]:
    if set(arm_paths) != set(ARMS):
        raise AdmissionError("exactly four named arm paths are required")
    arms = {arm: validate_arm(Path(arm_paths[arm]), arm, head) for arm in ARMS}
    shared = _shared_environment(arms)
    keys = expected_keys()
    cells: list[dict[str, Any]] = []
    for opponent, seed, seat in sorted(keys):
        values: dict[str, dict[str, Any]] = {}
        for arm in ARMS:
            game = arms[arm]["games"][(opponent, seed, seat)]
            own, margin = _own_margin(game, seat)
            values[arm] = {
                "own": own,
                "margin": margin,
                "candidate_action_sha256": game["candidate_action_sha256"],
                "trace_sha256": game["trace_sha256"],
            }
        own_effects = _effects({arm: values[arm]["own"] for arm in ARMS})
        margin_effects = _effects({arm: values[arm]["margin"] for arm in ARMS})
        row: dict[str, Any] = {
            "opponent": opponent,
            "seed": seed,
            "candidate_seat": seat,
            "arms": values,
        }
        for arm in NONCONTROL:
            row[f"{arm}_own_delta"] = values[arm]["own"] - values["control"]["own"]
            row[f"{arm}_margin_delta"] = values[arm]["margin"] - values["control"]["margin"]
            row[f"{arm}_candidate_action_changed"] = (
                values[arm]["candidate_action_sha256"] != values["control"]["candidate_action_sha256"]
            )
            row[f"{arm}_trace_changed"] = values[arm]["trace_sha256"] != values["control"]["trace_sha256"]
            row[f"{arm}_new_loss"] = values["control"]["margin"] >= 0 and values[arm]["margin"] < 0
        for name, value in own_effects.items():
            row[f"{name}_own"] = value
        for name, value in margin_effects.items():
            row[f"{name}_margin"] = value
        cells.append(row)

    groups: list[dict[str, Any]] = []
    for opponent in EXPECTED_OPPONENTS:
        for seed in EXPECTED_SEEDS:
            rows = [row for row in cells if row["opponent"] == opponent and row["seed"] == seed]
            if [row["candidate_seat"] for row in rows] != [0, 1]:
                raise AdmissionError(f"missing mirrored seat group {(opponent, seed)}")
            group: dict[str, Any] = {"opponent": opponent, "seed": seed, "seats": [0, 1]}
            for arm in NONCONTROL:
                for kind in ("own_delta", "margin_delta"):
                    field = f"{arm}_{kind}"
                    group[field] = statistics.fmean(float(row[field]) for row in rows)
            for factor in ("carry_main", "force_end_main", "interaction"):
                for kind in ("own", "margin"):
                    field = f"{factor}_{kind}"
                    group[field] = statistics.fmean(float(row[field]) for row in rows)
            groups.append(group)

    arm_results: dict[str, Any] = {}
    candidates: dict[str, Any] = {}
    for arm in NONCONTROL:
        group_own = [float(row[f"{arm}_own_delta"]) for row in groups]
        group_margin = [float(row[f"{arm}_margin_delta"]) for row in groups]
        opponent_means = {
            opponent: statistics.fmean(
                float(row[f"{arm}_own_delta"]) for row in cells if row["opponent"] == opponent
            )
            for opponent in EXPECTED_OPPONENTS
        }
        opponent_seat_means = {
            f"{opponent}/seat{seat}": statistics.fmean(
                float(row[f"{arm}_own_delta"])
                for row in cells
                if row["opponent"] == opponent and row["candidate_seat"] == seat
            )
            for opponent in EXPECTED_OPPONENTS for seat in (0, 1)
        }
        action_changed = sum(bool(row[f"{arm}_candidate_action_changed"]) for row in cells)
        trace_changed = sum(bool(row[f"{arm}_trace_changed"]) for row in cells)
        new_losses = sum(bool(row[f"{arm}_new_loss"]) for row in cells)
        checks = {
            "candidate_actions_activated": action_changed > 0,
            "positive_mean_group_own_cash": statistics.fmean(group_own) > 0,
            "nonnegative_median_group_own_cash": statistics.median(group_own) >= 0,
            "positive_groups_not_outnumbered": sum(v > 0 for v in group_own) >= sum(v < 0 for v in group_own),
            "no_catastrophic_group": min(group_own) >= -1000,
            "every_opponent_nonnegative": all(value >= 0 for value in opponent_means.values()),
            "every_opponent_seat_nonnegative": all(value >= 0 for value in opponent_seat_means.values()),
            "no_new_losses": new_losses == 0,
        }
        result = {
            "group_own_delta": summarize(group_own),
            "group_margin_delta": summarize(group_margin),
            "cell_own_delta": summarize([float(row[f"{arm}_own_delta"]) for row in cells]),
            "cell_margin_delta": summarize([float(row[f"{arm}_margin_delta"]) for row in cells]),
            "per_opponent_mean_own_delta": opponent_means,
            "per_opponent_seat_mean_own_delta": opponent_seat_means,
            "candidate_action_changed_cells": action_changed,
            "whole_trace_changed_cells": trace_changed,
            "new_loss_cells": new_losses,
        }
        arm_results[arm] = result
        candidates[arm] = {
            "eligible": all(checks.values()),
            "checks": checks,
            "rank_metric_mean_group_own_delta": result["group_own_delta"]["mean"],
        }

    eligible = [arm for arm in NONCONTROL if candidates[arm]["eligible"]]
    selected = max(
        eligible,
        key=lambda arm: float(candidates[arm]["rank_metric_mean_group_own_delta"]),
        default="control",
    )
    factor_results: dict[str, Any] = {}
    for factor in ("carry_main", "force_end_main", "interaction"):
        factor_results[factor] = {
            "group_own_effect": summarize([float(row[f"{factor}_own"]) for row in groups]),
            "group_margin_effect": summarize([float(row[f"{factor}_margin"]) for row in groups]),
        }
    return {
        "schema_version": 2,
        "operation": OPERATION,
        "repair": "sol-vernier-factorial-admission-v1",
        "status": "complete",
        "git_head": head,
        "design": {
            "arms": ARMS,
            "seeds": EXPECTED_SEEDS,
            "opponents": EXPECTED_OPPONENTS,
            "cells_per_arm": EXPECTED_CELLS_PER_ARM,
            "total_cells": EXPECTED_CELLS_PER_ARM * len(ARMS),
            "groups": len(groups),
            "unit_of_inference": "opponent/world-seed mirrored across candidate seats",
        },
        "custody": shared,
        "arm_results": arm_results,
        "factor_effects": factor_results,
        "selection": {
            "decision": "SCREEN_CONTROL" if selected == "control" else f"SCREEN_KEEP_{selected.upper()}",
            "selected_arm": selected,
            "candidates": candidates,
            "scope": "causal development screen only; not promotion, leaderboard, or submission authorization",
        },
        "group_rows": groups,
        "cell_rows": cells,
        "source_reports": {
            arm: {"path": str(Path(path)), "sha256": sha256_file(Path(path))}
            for arm, path in arm_paths.items()
        },
    }


def markdown(report: Mapping[str, Any]) -> str:
    lines = [
        "# TITAN V1/V2 seller factorial — strict SOL-VERNIER admission",
        "",
        f"Decision: **{report['selection']['decision']}**",
        f"Selected arm: `{report['selection']['selected_arm']}`",
        f"Exact head: `{report['git_head']}`",
        f"Admitted cells: {report['design']['total_cells']} across {report['design']['groups']} mirrored groups",
        "",
        "| Arm | Mean own Δ | Median | Action-changed | Trace-changed | New losses | Eligible |",
        "|---|---:|---:|---:|---:|---:|:---:|",
    ]
    for arm in NONCONTROL:
        row = report["arm_results"][arm]
        own = row["group_own_delta"]
        eligible = report["selection"]["candidates"][arm]["eligible"]
        lines.append(
            f"| `{arm}` | {own['mean']:.3f} | {own['median']:.3f} | "
            f"{row['candidate_action_changed_cells']} | {row['whole_trace_changed_cells']} | "
            f"{row['new_loss_cells']} | {'YES' if eligible else 'NO'} |"
        )
    lines += ["", "## Admission checks", ""]
    for arm in NONCONTROL:
        lines.append(f"### `{arm}`")
        for name, passed in report["selection"]["candidates"][arm]["checks"].items():
            lines.append(f"- {'PASS' if passed else 'FAIL'} — `{name}`")
        lines.append("")
    lines += [report["selection"]["scope"], ""]
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for arm in ARMS:
        parser.add_argument(f"--{arm.replace('_', '-')}", type=Path, required=True)
    parser.add_argument("--head", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--markdown", type=Path, required=True)
    args = parser.parse_args(argv)
    paths = {arm: getattr(args, arm) for arm in ARMS}
    try:
        report = build_report(paths, head=args.head)
        atomic_json(args.output, report)
        args.markdown.parent.mkdir(parents=True, exist_ok=True)
        args.markdown.write_text(markdown(report), encoding="utf-8", newline="\n")
        print(json.dumps({"status": "complete", **report["selection"]}, sort_keys=True))
        return 0
    except BaseException as exc:
        invalid = {
            "schema_version": 2,
            "operation": OPERATION,
            "repair": "sol-vernier-factorial-admission-v1",
            "status": "invalid",
            "git_head": args.head,
            "error": f"{type(exc).__name__}: {exc}"[:3000],
        }
        try:
            atomic_json(args.output, invalid)
            args.markdown.parent.mkdir(parents=True, exist_ok=True)
            args.markdown.write_text(
                "# TITAN V1/V2 seller factorial — strict SOL-VERNIER admission\n\n"
                "Status: **INVALID**\n\n"
                f"Compact error: {invalid['error']}\n\nNo scoring conclusion is authorized.\n",
                encoding="utf-8",
                newline="\n",
            )
        except Exception:
            pass
        print(json.dumps(invalid, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
