# SPDX-License-Identifier: Apache-2.0
"""Fail-closed custody audit for the carry seam, V3 target, and activation gate."""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
LAB = HERE.parents[1]
REPO = HERE.parents[4]
V1_NEEDLE = "carry=.95*self.single(inv,remaining)[0]"
FULL_NEEDLE = "carry=float(self.single(inv,remaining)[0])"
SELECTED_IMPORT = "from selected_sell_core import optimize_lot, joint_plan_metrics, shared_slot_ledger"
WHOLE_TRACE_NEEDLE = 'trace.update(encoded({"step": step, "actions": actions, "bank": bank}))'
EXPECTED_GIT_BLOBS = {
    "v1": "cbc502a92fe9d790cfaf763f6990d1057bc9b82d",
    "v2": "7c068b7078c3d7c09bb3836590ad42b0af934cdf",
    "current_scheduler": "a483b24dd72b580d7d8811636b54d2d44f391575",
    "selected_sell_core": "f23d3a8b5ee5e82029026e7f8f44eb36c143a5a3",
    "frozen_selected": "fc7baf5c179818a55037f6a61d92984d81d1a21c",
    "canonical_main": "4a8cf7bcda1f0fea231a144692cb84a779a9e73e",
    "evaluator": "077feb2208b6e0c1727835eb4f8089709bf67f3b",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def _method_ast(path: Path, class_name: str, method_name: str) -> str:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    matches = [
        item
        for node in ast.walk(tree)
        if isinstance(node, ast.ClassDef) and node.name == class_name
        for item in node.body
        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
        and item.name == method_name
    ]
    if len(matches) != 1:
        raise RuntimeError(
            f"expected one {class_name}.{method_name} in {path}; found {len(matches)}"
        )
    return ast.dump(matches[0], include_attributes=False)


def _function_ast(path: Path, function_name: str) -> str:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    matches = [
        node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == function_name
    ]
    if len(matches) != 1:
        raise RuntimeError(
            f"expected one {function_name} in {path}; found {len(matches)}"
        )
    return ast.dump(matches[0], include_attributes=False)


def build_report(lab: Path = LAB, *, enforce_source_pins: bool = True) -> dict[str, Any]:
    repo = lab.parents[2]
    paths = {
        "v1": lab / "runtime/variants/v1/scheduler.py",
        "v2": lab / "runtime/variants/v2/scheduler.py",
        "current_scheduler": lab / "scheduler.py",
        "selected_sell_core": lab / "selected_sell_core.py",
        "frozen_selected": lab / "frozen_selected.py",
        "canonical_main": lab / "main.py",
        "evaluator": lab.parent / "cloud-eval/evaluate.py",
        "ablation": HERE / "liquidity_haircut.py",
        "candidate": HERE / "candidate.py",
        "panel": HERE / "run_panel.py",
        "panel_tests": HERE / "test_panel_activation.py",
        "workflow": repo / ".github/workflows/titan-v3-horizon-liquidity-sol-kepler.yml",
    }
    missing = [str(path) for path in paths.values() if not path.is_file()]
    if missing:
        raise FileNotFoundError("missing source: " + ", ".join(missing))

    text = {name: path.read_text(encoding="utf-8") for name, path in paths.items()}
    panel_verdict_ast = _function_ast(paths["panel"], "verdict_with_candidate_actions")
    semantic_checks = {
        "v1_has_one_095_carry": text["v1"].count(V1_NEEDLE) == 1,
        "v1_has_no_full_carry": FULL_NEEDLE not in text["v1"],
        "v2_has_one_full_carry": text["v2"].count(FULL_NEEDLE) == 1,
        "v2_has_no_095_carry": V1_NEEDLE not in text["v2"],
        "current_scheduler_has_one_full_carry": (
            text["current_scheduler"].count(FULL_NEEDLE) == 1
        ),
        "selected_core_has_one_full_carry": (
            text["selected_sell_core"].count(FULL_NEEDLE) == 1
        ),
        "selected_core_has_no_095_carry": V1_NEEDLE not in text["selected_sell_core"],
        "frozen_selector_imports_selected_optimizer_once": (
            text["frozen_selected"].count(SELECTED_IMPORT) == 1
        ),
        "frozen_selector_calls_selected_optimizer_once": (
            text["frozen_selected"].count("plan,info=optimize_lot(") == 1
        ),
        "ablation_wraps_base_score_without_reimplementing_loop": (
            "super().score(" in text["ablation"]
            and "for step in range(" not in text["ablation"]
            and "DEFAULT_CARRY_DISCOUNT = 0.95" in text["ablation"]
        ),
        "candidate_targets_selected_core_not_scheduler": (
            "import selected_sell_core" in text["candidate"]
            and "install(selected_sell_core)" in text["candidate"]
            and "install(scheduler)" not in text["candidate"]
        ),
        "candidate_delegates_canonical_agent": (
            "return _CANONICAL.agent(observation, configuration)" in text["candidate"]
            and "instance.act(observation" not in text["candidate"]
        ),
        "selected_score_ast_is_present": bool(
            _method_ast(paths["selected_sell_core"], "MarketPath", "score")
        ),
        "evaluator_whole_trace_includes_both_actions_and_bank": (
            text["evaluator"].count(WHOLE_TRACE_NEEDLE) == 1
        ),
        "evaluator_has_one_preinterpreter_action_append_seam": (
            text["evaluator"].count('actions.append(response["action"])') == 1
        ),
        "panel_adds_length_delimited_candidate_action_digest": (
            text["panel"].count("candidate_action_trace.update(candidate_action_payload)") == 1
            and 'to_bytes(8, "big")' in text["panel"]
            and 'if seat == candidate_seat:' in text["panel"]
        ),
        "panel_retains_whole_trace_as_diagnostic_only": (
            '"whole_trace_is_diagnostic_only": True' in text["panel"]
            and 'whole_trace_role="diagnostic only"' in text["panel"]
        ),
        "panel_verdict_uses_candidate_action_not_whole_trace": (
            "candidate_action_changed_cells" in panel_verdict_ast
            and "trace_changed_cells" not in panel_verdict_ast
            and "candidate_returned_action_activated" in text["panel"]
        ),
        "panel_requires_exact_719_actions_720_states": (
            "EXPECTED_EPISODE_STEPS = 720" in text["panel"]
            and "EXPECTED_ACTION_COUNT = 719" in text["panel"]
            and "candidate action/step mismatch" in text["panel"]
        ),
        "workflow_executes_candidate_action_contracts": (
            "test_panel_activation.py" in text["workflow"]
            and "test_liquidity_haircut.py test_panel_activation.py" in text["workflow"]
        ),
        "workflow_has_no_duplicate_push_trigger": "\n  push:\n" not in text["workflow"],
    }
    source_pin_checks = {
        f"{name}_git_blob_pinned": git_blob_sha(paths[name]) == expected
        for name, expected in EXPECTED_GIT_BLOBS.items()
    }
    checks = {**semantic_checks, **source_pin_checks}
    decision_checks = checks if enforce_source_pins else semantic_checks
    report = {
        "schema_version": 3,
        "operation": "titan-v3-horizon-liquidity-20260909-sol-kepler-01",
        "decision": "PASS" if all(decision_checks.values()) else "FAIL",
        "source_pins_enforced": enforce_source_pins,
        "claim": {
            "historical_v1_artificial_horizon_carry_factor": 0.95,
            "historical_v2_artificial_horizon_carry_factor": 1.0,
            "current_selected_optimizer_carry_factor": 1.0,
            "candidate_selected_optimizer_carry_factor": 0.95,
            "target": "selected_sell_core.MarketPath.score",
            "activation_measure": "candidate-seat pre-interpreter returned-action digest",
            "whole_game_trace_role": "diagnostic only",
            "expected_actions_states": [719, 720],
            "canonical_files_modified": False,
        },
        "checks": checks,
        "expected_git_blobs": EXPECTED_GIT_BLOBS,
        "observed_git_blobs": {
            name: git_blob_sha(paths[name]) for name in EXPECTED_GIT_BLOBS
        },
        "sources": {
            name: {
                "path": str(path.relative_to(repo)),
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
                "git_blob": git_blob_sha(path),
            }
            for name, path in paths.items()
        },
    }
    return report


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", type=Path)
    args = parser.parse_args(argv)
    report = build_report()
    payload = json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n"
    if args.json is not None:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(payload, encoding="utf-8")
    print(json.dumps({"decision": report["decision"], "checks": report["checks"]}, sort_keys=True))
    return 0 if report["decision"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
