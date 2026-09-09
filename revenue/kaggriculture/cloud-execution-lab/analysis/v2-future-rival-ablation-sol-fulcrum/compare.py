# SPDX-License-Identifier: Apache-2.0
"""Compare closure-bound frozen V2 control and future-rival ablation reports."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from compare_common import (
    ACTION_CAPTURE_BOUNDARY,
    ACTION_DIGEST_SCHEMA,
    CORE_EVALUATOR_GIT_BLOB,
    CompareError,
    ENGINE_REF,
    EXPECTED_CELLS,
    EXPECTED_LIMITS,
    EXPECTED_OPPONENTS,
    EXPECTED_SEEDS,
    ENTRYPOINT_SHA256,
    FREEZE_GIT_BLOB,
    OPERATION,
    SCHEDULER_GIT_BLOB,
    SCHEDULER_SHA256,
    closure_digest,
    finite_number,
    require_hex,
    strict_json,
    validate_inventory,
)
from compare_receipts import validate_receipt
from compare_reports import _paired_identity, _score, validate_games, validate_top_level
from compare_analysis import analyze

def markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# TITAN V2 future-rival ablation",
        "",
        f"**Verdict: `{report['verdict']}`**",
        "",
        "This is a closure-bound development causal screen, not a promotion or hosted leaderboard claim.",
        "",
        "## Summary",
        "",
        f"- paired cells: {report['grid']['paired_cells']}",
        f"- candidate-action changed cells: {summary['candidate_action_changed_cells']}",
        f"- mean own-cash delta: {summary['mean_own_delta']:.6f}",
        f"- median own-cash delta: {summary['median_own_delta']:.6f}",
        f"- mean margin delta: {summary['mean_margin_delta']:.6f}",
        f"- positive / zero / negative own cells: {summary['positive_own_cells']} / {summary['zero_own_cells']} / {summary['negative_own_cells']}",
        "",
        "## Admission criteria",
        "",
    ]
    for name, value in report["criteria"].items():
        lines.append(f"- `{name}`: **{'PASS' if value else 'FAIL'}**")
    lines.extend(
        [
            "",
            "## Opponent × seat strata",
            "",
            "| Opponent | Seat | Cells | Changed | Mean own Δ | Mean margin Δ |",
            "|---|---:|---:|---:|---:|---:|",
        ]
    )
    for row in report["strata"]:
        lines.append(
            f"| {row['opponent']} | {row['candidate_seat']} | {row['cells']} | "
            f"{row['changed_actions']} | {row['mean_own_delta']:.6f} | {row['mean_margin_delta']:.6f} |"
        )
    lines.extend(
        [
            "",
            "## Executable identities",
            "",
            f"- source closure: `{report['identities']['source_runtime_closure_sha256']}`",
            f"- control closure: `{report['identities']['control_runtime_closure_sha256']}`",
            f"- ablation closure: `{report['identities']['ablation_runtime_closure_sha256']}`",
            f"- control entry: `{report['identities']['control_entry_sha256']}`",
            f"- ablation entry: `{report['identities']['ablation_entry_sha256']}`",
            "",
        ]
    )
    return "\n".join(lines)


def _write(path: Path, payload: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload, encoding="utf-8", newline="\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--control", type=Path, required=True)
    parser.add_argument("--ablation", type=Path, required=True)
    parser.add_argument("--control-receipt", type=Path, required=True)
    parser.add_argument("--ablation-receipt", type=Path, required=True)
    parser.add_argument("--head", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--markdown", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        report = analyze(
            strict_json(args.control),
            strict_json(args.ablation),
            strict_json(args.control_receipt),
            strict_json(args.ablation_receipt),
            args.head,
        )
    except CompareError as exc:
        invalid = {
            "schema_version": 1,
            "operation": OPERATION,
            "checkout_head": args.head,
            "verdict": "INVALID",
            "error": str(exc),
        }
        _write(args.output, json.dumps(invalid, indent=2, sort_keys=True) + "\n")
        _write(args.markdown, f"# TITAN V2 future-rival ablation\n\n**Verdict: `INVALID`**\n\n{exc}\n")
        print(f"INVALID: {exc}")
        return 2
    _write(args.output, json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n")
    _write(args.markdown, markdown(report))
    print(json.dumps({"verdict": report["verdict"], **report["summary"]}, sort_keys=True))
    return 0 if report["verdict"] == "UPSIDE_SCREEN" else 3


if __name__ == "__main__":
    raise SystemExit(main())
