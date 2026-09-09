# SPDX-License-Identifier: Apache-2.0
"""Rank complete L02 screen arms without ever emitting a promotion verdict."""
from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Mapping

from ablation import ARMS


_HEX = frozenset("0123456789abcdef")


def _pairs_no_duplicates(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise ValueError(f"duplicate JSON key: {key}")
        out[key] = value
    return out


def _canonical(value: Any) -> str:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"non-canonical receipt value: {exc}") from exc


def _fingerprint(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _sha256(value: Any, name: str) -> str:
    if not (isinstance(value, str) and len(value) == 64 and set(value) <= _HEX):
        raise ValueError(f"invalid SHA-256 for {name}")
    return value


def _integer(value: Any, name: str, *, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ValueError(f"invalid integer for {name}")
    return value


def _finite(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"invalid finite number for {name}")
    return float(value)


def load_report(path: Path) -> dict[str, Any]:
    report = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_pairs_no_duplicates)
    if not isinstance(report, dict) or report.get("status") != "complete":
        raise ValueError(f"incomplete report: {path}")
    summary = report.get("summary")
    identity = report.get("identity")
    if not isinstance(summary, dict) or not isinstance(identity, dict):
        raise ValueError(f"missing summary/identity: {path}")
    arm = identity.get("ablation_arm")
    if arm not in ARMS:
        raise ValueError(f"unknown or missing arm identity: {path}")
    for name in ("mean_own_delta", "mean_margin_delta", "min_own_delta"):
        _finite(summary.get(name), f"{path}:{name}")
    return report


def _grid(report: Mapping[str, Any], arm: str) -> tuple[list[int], list[str], int]:
    seeds = report.get("seeds")
    opponents = report.get("opponents")
    if (not isinstance(seeds, list) or not seeds
            or any(isinstance(seed, bool) or not isinstance(seed, int) for seed in seeds)
            or len(seeds) != len(set(seeds))):
        raise ValueError(f"invalid seed grid for arm {arm}")
    if (not isinstance(opponents, list) or not opponents
            or any(not isinstance(name, str) or not name for name in opponents)
            or len(opponents) != len(set(opponents))):
        raise ValueError(f"invalid opponent grid for arm {arm}")
    expected = _integer(report.get("expected_cells_per_variant"),
                        f"{arm}:expected_cells_per_variant", minimum=1)
    if expected != len(seeds) * len(opponents) * 2:
        raise ValueError(f"grid/cell cardinality mismatch for arm {arm}")
    summary = report["summary"]
    if _integer(summary.get("cells"), f"{arm}:summary.cells", minimum=1) != expected:
        raise ValueError(f"incomplete paired cells for arm {arm}")
    changed = _integer(summary.get("trace_changed_cells", 0),
                       f"{arm}:summary.trace_changed_cells")
    if changed > expected:
        raise ValueError(f"trace-changed count exceeds cells for arm {arm}")
    per_opponent = report.get("per_opponent")
    if not isinstance(per_opponent, dict) or set(per_opponent) != set(opponents):
        raise ValueError(f"opponent coverage mismatch for arm {arm}")
    for opponent, row in per_opponent.items():
        if not isinstance(row, dict):
            raise ValueError(f"invalid opponent summary for {arm}:{opponent}")
        _finite(row.get("mean_own_delta"), f"{arm}:{opponent}:mean_own_delta")
    return list(seeds), list(opponents), expected


def _identity(report: Mapping[str, Any], arm: str) -> tuple[str, str, str]:
    identity = report["identity"]
    sha = identity.get("sha256")
    if not isinstance(sha, dict):
        raise ValueError(f"missing dependency SHA map for arm {arm}")
    candidate = _sha256(sha.get("candidate"), f"{arm}:candidate")
    canonical = _sha256(sha.get("canonical_main"), f"{arm}:canonical_main")
    for required in ("overlay", "candidate_base", "ablation", "titan_runtime",
                     "frozen_selected", "scheduler", "config", "source_manifest",
                     "evaluator", "evaluator_source", "loader"):
        _sha256(sha.get(required), f"{arm}:{required}")
    common = deepcopy(identity)
    common.pop("ablation_arm", None)
    common_sha = dict(common["sha256"])
    common_sha.pop("candidate", None)
    common["sha256"] = common_sha
    return candidate, canonical, _fingerprint(common)


def _execution_context(report: Mapping[str, Any], arm: str, expected: int,
                       candidate_sha256: str, canonical_sha256: str) -> str:
    identity_sha = report["identity"]["sha256"]
    contexts: list[str] = []
    for gate_name, expected_agent in (("baseline_gate", canonical_sha256),
                                      ("candidate_gate", candidate_sha256)):
        gate = report.get(gate_name)
        if not isinstance(gate, dict) or gate.get("valid") is not True:
            raise ValueError(f"invalid {gate_name} for arm {arm}")
        if (_integer(gate.get("expected"), f"{arm}:{gate_name}.expected") != expected
                or _integer(gate.get("accepted"), f"{arm}:{gate_name}.accepted") != expected):
            raise ValueError(f"incomplete {gate_name} for arm {arm}")
        provenance = gate.get("provenance")
        if not isinstance(provenance, list) or not provenance:
            raise ValueError(f"missing {gate_name} provenance for arm {arm}")
        for index, row in enumerate(provenance):
            if not isinstance(row, dict):
                raise ValueError(f"invalid {gate_name} provenance row for arm {arm}")
            observed_agent = (row.get("candidate") or {}).get("sha256")
            if observed_agent != expected_agent:
                raise ValueError(f"agent digest drift in {gate_name} for arm {arm}")
            engine = _sha256(row.get("engine_sha256"), f"{arm}:{gate_name}:{index}:engine")
            loader = _sha256(row.get("loader_sha256"), f"{arm}:{gate_name}:{index}:loader")
            evaluator = _sha256(row.get("evaluator_sha256"),
                                f"{arm}:{gate_name}:{index}:evaluator")
            if loader != identity_sha["loader"] or evaluator != identity_sha["evaluator"]:
                raise ValueError(f"execution/dependency receipt drift for arm {arm}")
            opponents = row.get("opponents")
            limits = row.get("limits")
            if not isinstance(opponents, dict) or not isinstance(limits, dict):
                raise ValueError(f"missing execution context for arm {arm}")
            contexts.append(_fingerprint({
                "engine_sha256": engine,
                "loader_sha256": loader,
                "evaluator_sha256": evaluator,
                "opponents": opponents,
                "limits": limits,
            }))
    if len(set(contexts)) != 1:
        raise ValueError(f"baseline/candidate or shard execution drift for arm {arm}")
    return contexts[0]


def rank(paths: list[Path]) -> dict[str, Any]:
    reports = [load_report(path) for path in paths]
    seen: set[str] = set()
    candidate_digests: dict[str, str] = {}
    rows = []
    common_grid = None
    common_identity = None
    common_execution = None
    for report in reports:
        arm = report["identity"]["ablation_arm"]
        if arm in seen:
            raise ValueError(f"duplicate arm: {arm}")
        seen.add(arm)
        seeds, opponents, expected = _grid(report, arm)
        candidate, canonical, identity_digest = _identity(report, arm)
        execution_digest = _execution_context(report, arm, expected, candidate, canonical)
        candidate_digests[arm] = candidate
        grid = (report["identity"].get("git_head"), tuple(seeds), tuple(opponents), expected)
        if common_grid is None:
            common_grid = grid
            common_identity = identity_digest
            common_execution = execution_digest
        elif grid != common_grid:
            raise ValueError("arm reports do not share one immutable screen grid")
        elif identity_digest != common_identity:
            raise ValueError("arm reports do not share one dependency closure")
        elif execution_digest != common_execution:
            raise ValueError("arm reports do not share one execution context")
        per_opponent = report["per_opponent"]
        own = _finite(report["summary"]["mean_own_delta"], f"{arm}:mean_own_delta")
        margin = _finite(report["summary"]["mean_margin_delta"], f"{arm}:mean_margin_delta")
        worst = min(_finite(item.get("mean_own_delta"), f"{arm}:opponent")
                    for item in per_opponent.values())
        nonnegative = sum(_finite(item.get("mean_own_delta"), f"{arm}:opponent") >= 0
                          for item in per_opponent.values())
        rows.append({
            "arm": arm,
            "mean_own_delta": own,
            "mean_margin_delta": margin,
            "min_cell_own_delta": _finite(report["summary"]["min_own_delta"],
                                           f"{arm}:min_own_delta"),
            "worst_opponent_mean_own_delta": worst,
            "nonnegative_opponents": nonnegative,
            "cells": expected,
            "trace_changed_cells": _integer(report["summary"].get("trace_changed_cells", 0),
                                             f"{arm}:trace_changed_cells"),
        })
    missing = set(ARMS) - seen
    extra = seen - set(ARMS)
    if missing or extra:
        raise ValueError(f"incomplete arm set: missing={sorted(missing)} extra={sorted(extra)}")
    if len(set(candidate_digests.values())) != len(candidate_digests):
        raise ValueError("two ablation arms resolve to the same candidate entry digest")
    rows.sort(key=lambda row: (row["mean_own_delta"], row["mean_margin_delta"]), reverse=True)
    survivor = next((row for row in rows if row["mean_own_delta"] > 0
                     and row["worst_opponent_mean_own_delta"] >= -300
                     and row["trace_changed_cells"] > 0), None)
    return {
        "schema_version": 2,
        "decision": "FULL_PANEL_REQUIRED" if survivor else "NO_ARM_SURVIVES_SCREEN",
        "scope": "development screen only; never a promotion or leaderboard claim",
        "screen_identity": {
            "git_head": common_grid[0],
            "seeds": list(common_grid[1]),
            "opponents": list(common_grid[2]),
            "expected_cells_per_variant": common_grid[3],
            "dependency_closure_digest_sha256": common_identity,
            "execution_context_digest_sha256": common_execution,
            "candidate_entry_sha256": dict(sorted(candidate_digests.items())),
        },
        "recommended_arm": survivor["arm"] if survivor else None,
        "ranking": rows,
    }


def markdown(result: dict[str, Any]) -> str:
    lines = ["# TITAN L02 terminal-window ablation screen", "",
             f"Decision: **{result['decision']}**", "",
             "| Rank | Arm | Mean own Δ | Mean margin Δ | Worst opponent own Δ | Nonnegative opponents | Cells |",
             "|---:|---|---:|---:|---:|---:|---:|"]
    for index, row in enumerate(result["ranking"], 1):
        lines.append(f"| {index} | `{row['arm']}` | {row['mean_own_delta']:.3f} | "
                     f"{row['mean_margin_delta']:.3f} | {row['worst_opponent_mean_own_delta']:.3f} | "
                     f"{row['nonnegative_opponents']} | {row['cells']} |")
    lines += ["", result["scope"], ""]
    return "\n".join(lines)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inputs", nargs="+", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--markdown", required=True, type=Path)
    args = parser.parse_args(argv)
    result = rank(args.inputs)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    args.markdown.write_text(markdown(result), encoding="utf-8")
    print(json.dumps({"decision": result["decision"], "recommended_arm": result["recommended_arm"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
