# SPDX-License-Identifier: Apache-2.0
"""Bind the hardened paired official-engine collector to this candidate."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import math
from pathlib import Path
from typing import Any, Mapping, Sequence

HERE = Path(__file__).resolve().parent
LAB = HERE.parents[1]
SHARED = LAB / "candidates" / "v3-l02-ledger-tranche" / "run_panel.py"
EXPECTED_SHARED_GIT_BLOB = "ce4309319c6a0fc93a81e425a0d01a5f0e7393ed"


def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


def load_shared():
    data = SHARED.read_bytes()
    actual = git_blob_sha(data)
    if actual != EXPECTED_SHARED_GIT_BLOB:
        raise RuntimeError(
            f"shared paired-panel collector drift: expected {EXPECTED_SHARED_GIT_BLOB}, got {actual}"
        )
    spec = importlib.util.spec_from_file_location("multi_lot_shared_panel", SHARED)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load shared paired-panel collector")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def install_overrides(panel):
    panel.HERE = HERE

    def dependency_receipt(head: str, *, evaluator: Path | None = None) -> dict[str, Any]:
        evaluator_path = Path(evaluator) if evaluator is not None else panel.EVALUATOR
        paths = {
            "candidate": HERE / "candidate.py",
            "overlay": HERE / "multi_lot_portfolio.py",
            "patch": HERE / "candidate_patch.py",
            "canonical_main": panel.LAB / "main.py",
            "titan_runtime": panel.LAB / "titan_runtime.py",
            "frozen_selected": panel.LAB / "frozen_selected.py",
            "scheduler": panel.LAB / "scheduler.py",
            "config": panel.LAB / "TITAN-CONFIG.json",
            "source_manifest": panel.LAB / "runtime/integrated-selected/CURRENT-SOURCE.json",
            "evaluator": evaluator_path,
            "evaluator_source": panel.EVALUATOR,
            "loader": panel.LOADER,
            "shared_panel": SHARED,
        }
        missing = [str(path) for path in paths.values() if not path.is_file()]
        if missing:
            raise FileNotFoundError("missing dependency paths: " + ", ".join(missing))
        bundles = {
            "arlene": panel.OPPONENTS["arlene"],
            "apex": panel.OPPONENTS["apex"].parent,
            "kaito_v43": panel.OPPONENTS["kaito_v43"],
            "cok_v10": panel.OPPONENTS["cok_v10"],
            "public_bt12": panel.OPPONENTS["public_bt12"].parent,
            "v1": panel.OPPONENTS["v1"].parent,
        }
        receipt = {
            "git_head": head,
            "sha256": {name: panel.sha256_file(path) for name, path in paths.items()},
            "opponent_entries": {
                name: panel.sha256_file(path) for name, path in panel.OPPONENTS.items()
            },
            "opponent_bundles": {
                name: panel.tree_sha256(root) for name, root in bundles.items()
            },
        }
        apex_binary = panel.OPPONENTS["apex"].parent / "agent.so"
        if apex_binary.is_file():
            receipt["generated_apex_binary"] = {
                "sha256": panel.sha256_file(apex_binary),
                "bytes": apex_binary.stat().st_size,
            }
        return receipt

    def verdict(global_summary: Mapping[str, Any], per_opponent: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
        checks = {
            "behavior_activated": int(global_summary.get("trace_changed_cells", 0)) > 0,
            "positive_global_own_cash": float(global_summary.get("mean_own_delta", 0.0)) > 0,
            "nonnegative_global_margin": float(global_summary.get("mean_margin_delta", 0.0)) >= 0,
            "all_opponent_strata_nonnegative": bool(per_opponent) and all(
                float(row.get("mean_own_delta", -math.inf)) >= 0
                for row in per_opponent.values()
            ),
            "no_large_cell_regression": float(global_summary.get("min_own_delta", -math.inf)) >= -500,
        }
        return {
            "decision": "ADVANCE" if all(checks.values()) else "REJECT",
            "checks": checks,
            "scope": "development panel only; not a Kaggle or leaderboard claim",
        }

    def markdown(report: Mapping[str, Any]) -> str:
        summary = report["summary"]
        lines = [
            "# TITAN V3 multi-lot portfolio — development panel",
            "",
            f"Verdict: **{report['verdict']['decision']}**",
            "",
            f"Cells: {summary['cells']}; trace-changed: {summary['trace_changed_cells']}",
            f"Mean own-cash delta: {summary['mean_own_delta']:.3f}",
            f"Mean margin delta: {summary['mean_margin_delta']:.3f}",
            "",
            "| Opponent | Cells | Mean own Δ | Mean margin Δ | + / 0 / - |",
            "|---|---:|---:|---:|---:|",
        ]
        for name, row in report["per_opponent"].items():
            lines.append(
                f"| {name} | {row['cells']} | {row['mean_own_delta']:.3f} | "
                f"{row['mean_margin_delta']:.3f} | {row['positive_own_cells']} / "
                f"{row['zero_own_cells']} / {row['negative_own_cells']} |"
            )
        lines += ["", "## Gate", ""]
        for name, passed in report["verdict"]["checks"].items():
            lines.append(f"- {'PASS' if passed else 'FAIL'} — `{name}`")
        lines += ["", report["verdict"]["scope"], ""]
        return "\n".join(lines)

    original_failure = panel.failure_markdown

    def failure_markdown(payload: Mapping[str, Any]) -> str:
        return original_failure(payload).replace(
            "TITAN L02 ledger-coherent tranche", "TITAN V3 multi-lot portfolio"
        )

    panel.dependency_receipt = dependency_receipt
    panel.verdict = verdict
    panel.markdown = markdown
    panel.failure_markdown = failure_markdown


def main(argv: Sequence[str] | None = None) -> int:
    panel = load_shared()
    install_overrides(panel)
    return int(panel.main(argv))


if __name__ == "__main__":
    raise SystemExit(main())
