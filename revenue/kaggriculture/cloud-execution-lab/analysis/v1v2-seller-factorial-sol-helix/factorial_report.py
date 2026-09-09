# SPDX-License-Identifier: Apache-2.0
"""Validate and analyze the closure-bound 2x2 V1/V2 seller factorial."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import random
import statistics
import tempfile
from typing import Any, Mapping, Sequence

OPERATION = "titan-v3-v1v2-seller-factorial-20260909-01"
ARMS = ("control", "carry_095", "force_end", "both")
NONCONTROL = ARMS[1:]
BOOTSTRAP_SEED = 20260909
BOOTSTRAP_DRAWS = 5000
IDENTITY_FIELDS = (
    "git_head", "engine_ref", "evaluator_source_sha256",
    "evaluator_effective_sha256", "loader_sha256", "opponent_entry_sha256",
    "opponent_bundles", "generated_apex_binary",
)


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", newline="\n", dir=path.parent, delete=False
    ) as handle:
        temporary = Path(handle.name)
        handle.write(payload); handle.flush(); os.fsync(handle.fileno())
    os.replace(temporary, path)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def summarize(values: Sequence[float]) -> dict[str, Any]:
    if not values:
        return {"n": 0}
    return {
        "n": len(values), "mean": statistics.fmean(values),
        "median": statistics.median(values), "min": min(values), "max": max(values),
        "positive": sum(x > 0 for x in values), "zero": sum(x == 0 for x in values),
        "negative": sum(x < 0 for x in values),
    }


def _quantile(values: Sequence[float], p: float) -> float:
    if not values or not 0 <= p <= 1:
        raise ValueError("invalid quantile")
    position = p * (len(values) - 1); low = math.floor(position); high = math.ceil(position)
    if low == high:
        return float(values[low])
    return float(values[low] * (high - position) + values[high] * (position - low))


def bootstrap_mean_ci(
    values: Sequence[float], *, draws: int = BOOTSTRAP_DRAWS, seed: int = BOOTSTRAP_SEED
) -> dict[str, float | int]:
    if not values or draws <= 0:
        raise ValueError("bootstrap requires values and positive draws")
    rng = random.Random(seed); n = len(values)
    means = sorted(sum(values[rng.randrange(n)] for _ in range(n)) / n for _ in range(draws))
    return {
        "draws": draws, "seed": seed, "lower_90": _quantile(means, .05),
        "median": _quantile(means, .5), "upper_90": _quantile(means, .95),
    }


def _load_arm(path: Path, arm: str, head: str) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(path)
    report = json.loads(path.read_text(encoding="utf-8")); gate = report.get("gate") or {}
    if report.get("schema_version") != 1 or report.get("operation") != OPERATION:
        raise RuntimeError(f"{arm}: report schema/operation mismatch")
    if report.get("arm") != arm or report.get("status") != "complete":
        raise RuntimeError(f"{arm}: report identity/status mismatch")
    if gate.get("valid") is not True or gate.get("errors"):
        raise RuntimeError(f"{arm}: invalid arm gate: {gate.get('errors')}")
    identity = report.get("identity") or {}
    if identity.get("git_head") != head or identity.get("arm") != arm:
        raise RuntimeError(f"{arm}: identity/head mismatch")
    return report


def _game_map(report: Mapping[str, Any]) -> dict[tuple[str, int, int], dict[str, Any]]:
    arm = str(report["arm"]); games: dict[tuple[str, int, int], dict[str, Any]] = {}
    for raw in report.get("games") or []:
        try:
            key = (str(raw["opponent"]), int(raw["seed"]), int(raw["candidate_seat"]))
        except (KeyError, TypeError, ValueError) as exc:
            raise RuntimeError(f"{arm}: malformed game") from exc
        scores = raw.get("scores"); trace = raw.get("trace_sha256")
        valid_scores = (
            isinstance(scores, list) and len(scores) == 2 and
            all(isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)
                for x in scores)
        )
        if key in games or raw.get("status") != "complete" or raw.get("failure") is not None:
            raise RuntimeError(f"{arm}: duplicate/incomplete game {key}")
        if not valid_scores or not isinstance(trace, str) or len(trace) != 64:
            raise RuntimeError(f"{arm}: invalid scores/trace {key}")
        games[key] = dict(raw)
    expected = int(report.get("expected_cells", -1))
    if len(games) != expected:
        raise RuntimeError(f"{arm}: expected {expected} accepted games, found {len(games)}")
    return games


def _identity(reports: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    control = reports["control"]["identity"]; mismatches = {}
    for arm, report in reports.items():
        identity = report["identity"]
        for field in IDENTITY_FIELDS:
            if identity.get(field) != control.get(field):
                mismatches.setdefault(arm, {})[field] = True
        for field in ("seeds", "opponents"):
            if report.get(field) != reports["control"].get(field):
                mismatches.setdefault(arm, {})[field] = True
    if mismatches:
        raise RuntimeError(f"cross-arm provenance mismatch: {mismatches}")
    entries = {
        arm: {
            "entry_sha256": report["identity"]["entry_sha256"],
            "closure_sha256": report["identity"]["closure"]["sha256"],
            "materialization_receipt_sha256": report["identity"]["materialization_receipt_sha256"],
        } for arm, report in reports.items()
    }
    if len({row["entry_sha256"] for row in entries.values()}) != 4:
        raise RuntimeError("factorial arms lack four distinct entrypoints")
    return {
        "shared": {field: control.get(field) for field in IDENTITY_FIELDS},
        "seeds": reports["control"]["seeds"],
        "opponents": reports["control"]["opponents"], "arms": entries,
    }


def _own_margin(game: Mapping[str, Any], seat: int) -> tuple[float, float]:
    own = float(game["scores"][seat]); rival = float(game["scores"][1 - seat])
    return own, own - rival


def _effects(values: Mapping[str, float]) -> dict[str, float]:
    c, a, b, ab = (values[name] for name in ARMS)
    return {
        "carry_main": ((a - c) + (ab - b)) / 2,
        "force_end_main": ((b - c) + (ab - a)) / 2,
        "interaction": ab - a - b + c,
    }


def _per_opponent(rows: Sequence[Mapping[str, Any]], field: str) -> dict[str, Any]:
    names = sorted({str(row["opponent"]) for row in rows})
    return {name: summarize([float(row[field]) for row in rows if row["opponent"] == name])
            for name in names}


def build_report(
    arm_paths: Mapping[str, Path], *, head: str, draws: int = BOOTSTRAP_DRAWS
) -> dict[str, Any]:
    reports = {arm: _load_arm(arm_paths[arm], arm, head) for arm in ARMS}
    identity = _identity(reports); maps = {arm: _game_map(report) for arm, report in reports.items()}
    keys = set(maps["control"])
    for arm in NONCONTROL:
        if set(maps[arm]) != keys:
            raise RuntimeError(f"{arm}: unmatched cell grid")

    cells = []
    for opponent, seed, seat in sorted(keys):
        arm_values = {}
        for arm in ARMS:
            own, margin = _own_margin(maps[arm][(opponent, seed, seat)], seat)
            arm_values[arm] = {
                "own": own, "margin": margin,
                "trace_sha256": maps[arm][(opponent, seed, seat)]["trace_sha256"],
            }
        own_effects = _effects({arm: arm_values[arm]["own"] for arm in ARMS})
        margin_effects = _effects({arm: arm_values[arm]["margin"] for arm in ARMS})
        row: dict[str, Any] = {
            "opponent": opponent, "seed": seed, "candidate_seat": seat,
            "arms": arm_values,
        }
        for arm in NONCONTROL:
            row[f"{arm}_own_delta"] = arm_values[arm]["own"] - arm_values["control"]["own"]
            row[f"{arm}_margin_delta"] = arm_values[arm]["margin"] - arm_values["control"]["margin"]
            row[f"{arm}_trace_changed"] = arm_values[arm]["trace_sha256"] != arm_values["control"]["trace_sha256"]
        for name, value in own_effects.items(): row[f"{name}_own"] = value
        for name, value in margin_effects.items(): row[f"{name}_margin"] = value
        cells.append(row)

    metrics = [
        *(f"{arm}_{kind}_delta" for arm in NONCONTROL for kind in ("own", "margin")),
        *(f"{factor}_{kind}" for factor in ("carry_main", "force_end_main", "interaction")
          for kind in ("own", "margin")),
    ]
    grouped: dict[tuple[str, int], list[dict[str, Any]]] = {}
    for row in cells: grouped.setdefault((row["opponent"], row["seed"]), []).append(row)
    groups = []
    for (opponent, seed), rows in sorted(grouped.items()):
        if sorted(row["candidate_seat"] for row in rows) != [0, 1]:
            raise RuntimeError(f"group {(opponent, seed)} lacks exact seat pair")
        group = {"opponent": opponent, "seed": seed, "seats": [0, 1]}
        group.update({field: statistics.fmean(row[field] for row in rows) for field in metrics})
        groups.append(group)

    arm_results = {}
    for index, arm in enumerate(NONCONTROL):
        own = [row[f"{arm}_own_delta"] for row in groups]
        margin = [row[f"{arm}_margin_delta"] for row in groups]
        own_summary = summarize(own)
        own_summary["bootstrap_mean_90"] = bootstrap_mean_ci(
            own, draws=draws, seed=BOOTSTRAP_SEED + index
        )
        arm_results[arm] = {
            "group_own_delta": own_summary, "group_margin_delta": summarize(margin),
            "cell_own_delta": summarize([row[f"{arm}_own_delta"] for row in cells]),
            "cell_margin_delta": summarize([row[f"{arm}_margin_delta"] for row in cells]),
            "per_opponent_group_own_delta": _per_opponent(groups, f"{arm}_own_delta"),
            "trace_changed_cells": sum(row[f"{arm}_trace_changed"] for row in cells),
        }

    factor_results = {}
    for index, factor in enumerate(("carry_main", "force_end_main", "interaction")):
        own = [row[f"{factor}_own"] for row in groups]
        own_summary = summarize(own)
        own_summary["bootstrap_mean_90"] = bootstrap_mean_ci(
            own, draws=draws, seed=BOOTSTRAP_SEED + 100 + index
        )
        factor_results[factor] = {
            "group_own_effect": own_summary,
            "group_margin_effect": summarize([row[f"{factor}_margin"] for row in groups]),
            "per_opponent_group_own_effect": _per_opponent(groups, f"{factor}_own"),
        }

    candidates = {}
    for arm, result in arm_results.items():
        own = result["group_own_delta"]; margin = result["group_margin_delta"]
        checks = {
            "behavior_activated": result["trace_changed_cells"] > 0,
            "positive_mean_group_own_cash": own["mean"] > 0,
            "nonnegative_median_group_own_cash": own["median"] >= 0,
            "positive_mean_group_margin": margin["mean"] > 0,
            "positive_groups_not_outnumbered": own["positive"] >= own["negative"],
            "no_catastrophic_group": own["min"] >= -1000,
            "no_large_opponent_regression": all(
                row["mean"] >= -500 for row in result["per_opponent_group_own_delta"].values()
            ),
        }
        candidates[arm] = {
            "eligible": all(checks.values()), "checks": checks,
            "rank_metric_mean_group_own_delta": own["mean"],
        }
    eligible = [arm for arm in NONCONTROL if candidates[arm]["eligible"]]
    selected = max(eligible, key=lambda arm: candidates[arm]["rank_metric_mean_group_own_delta"],
                   default="control")
    selection = {
        "decision": "SCREEN_CONTROL" if selected == "control" else f"SCREEN_KEEP_{selected.upper()}",
        "selected_arm": selected, "candidates": candidates,
        "scope": "causal development screen only; not promotion authorization or a leaderboard claim",
    }
    return {
        "schema_version": 1, "operation": OPERATION, "status": "complete", "git_head": head,
        "identity": identity,
        "design": {
            "factors": {"A": "carry 1.00 -> 0.95", "B": "residual reference -> horizon end"},
            "arms": {"control": {"A": 0, "B": 0}, "carry_095": {"A": 1, "B": 0},
                     "force_end": {"A": 0, "B": 1}, "both": {"A": 1, "B": 1}},
            "unit_of_inference": "opponent/seed averaged across both candidate seats",
            "cells": len(cells), "groups": len(groups),
        },
        "arm_results": arm_results, "factor_effects": factor_results,
        "selection": selection, "group_rows": groups, "cell_rows": cells,
        "source_reports": {arm: {"path": str(path), "sha256": sha256_file(path)}
                           for arm, path in arm_paths.items()},
    }


def markdown(report: Mapping[str, Any]) -> str:
    lines = [
        "# TITAN V1/V2 seller-policy factorial — SOL-HELIX", "",
        f"Decision: **{report['selection']['decision']}**",
        f"Selected arm: `{report['selection']['selected_arm']}`",
        f"Head: `{report['git_head']}`",
        f"Cells / groups: {report['design']['cells']} / {report['design']['groups']}", "",
        "| Arm | Mean own Δ | Median | Mean margin Δ | Trace-changed | 90% CI | Eligible |",
        "|---|---:|---:|---:|---:|---:|:---:|",
    ]
    for arm in NONCONTROL:
        row = report["arm_results"][arm]; own = row["group_own_delta"]
        ci = own["bootstrap_mean_90"]; eligible = report["selection"]["candidates"][arm]["eligible"]
        lines.append(
            f"| `{arm}` | {own['mean']:.3f} | {own['median']:.3f} | "
            f"{row['group_margin_delta']['mean']:.3f} | {row['trace_changed_cells']} | "
            f"[{ci['lower_90']:.3f}, {ci['upper_90']:.3f}] | {'YES' if eligible else 'NO'} |"
        )
    lines += ["", "| Factor | Mean own effect | Median | Mean margin effect |",
              "|---|---:|---:|---:|"]
    for factor in ("carry_main", "force_end_main", "interaction"):
        row = report["factor_effects"][factor]; own = row["group_own_effect"]
        lines.append(f"| `{factor}` | {own['mean']:.3f} | {own['median']:.3f} | "
                     f"{row['group_margin_effect']['mean']:.3f} |")
    lines += ["", "## Gate", ""]
    for arm in NONCONTROL:
        lines.append(f"### `{arm}`")
        for name, passed in report["selection"]["candidates"][arm]["checks"].items():
            lines.append(f"- {'PASS' if passed else 'FAIL'} — `{name}`")
        lines.append("")
    lines += [report["selection"]["scope"], ""]
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for arm in ARMS: parser.add_argument(f"--{arm.replace('_', '-')}", type=Path, required=True)
    parser.add_argument("--head", required=True); parser.add_argument("--bootstrap-draws", type=int, default=BOOTSTRAP_DRAWS)
    parser.add_argument("--output", type=Path, required=True); parser.add_argument("--markdown", type=Path, required=True)
    args = parser.parse_args(argv)
    paths = {arm: getattr(args, arm) for arm in ARMS}
    try:
        report = build_report(paths, head=args.head, draws=args.bootstrap_draws)
        atomic_json(args.output, report); args.markdown.parent.mkdir(parents=True, exist_ok=True)
        args.markdown.write_text(markdown(report), encoding="utf-8", newline="\n")
        print(json.dumps({"status": "complete", **report["selection"]}, sort_keys=True)); return 0
    except BaseException as exc:
        invalid = {
            "schema_version": 1, "operation": OPERATION, "status": "invalid",
            "git_head": args.head, "error": f"{type(exc).__name__}: {exc}"[:3000],
        }
        try:
            atomic_json(args.output, invalid); args.markdown.parent.mkdir(parents=True, exist_ok=True)
            args.markdown.write_text(
                "# TITAN V1/V2 seller-policy factorial — SOL-HELIX\n\nStatus: **INVALID**\n\n"
                f"Compact error: {invalid['error']}\n\nNo scoring conclusion is authorized.\n",
                encoding="utf-8", newline="\n",
            )
        except Exception: pass
        print(json.dumps(invalid, sort_keys=True)); return 2


if __name__ == "__main__":
    raise SystemExit(main())
