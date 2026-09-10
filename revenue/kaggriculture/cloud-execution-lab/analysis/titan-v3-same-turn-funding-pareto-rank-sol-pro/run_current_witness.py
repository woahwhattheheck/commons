# SPDX-License-Identifier: Apache-2.0
"""Execute predecessor and one-line candidate on the exact current source."""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import tempfile
from pathlib import Path
from types import ModuleType

from pareto_rank import (
    CURRENT_BASE,
    ENGINE_GIT_BLOB,
    OPERATION,
    SOURCE_GIT_BLOB,
    SOURCE_RELATIVE,
    git_blob_id,
    patch_source,
)


def load_module(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load module from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def call(module: ModuleType) -> tuple[dict, dict]:
    mechanics = sys.modules["mechanics"]
    orders = [[], ["HIRE"], ["SELL", "CARROT", 1], ["SELL", "WOOL", 1]]
    farm = {
        "money": 0,
        "hires_today": 0,
        "unlocked_quadrants": ["NW"],
    }
    private = {"shed": {"CARROT": 1, "WOOL": 1}}
    market = {
        "inventory": {"CARROT": mechanics.MARKET_I0, "WOOL": mechanics.MARKET_I0},
        "params": mechanics.MARKET_PARAMS,
    }
    config = {"farmHandCostMult": 10, "shedCapacity": 100}
    action, info = module.fund_same_turn_acquisition(
        orders,
        farm,
        private,
        market,
        [],
        config,
        0,
        {"CARROT", "WOOL"},
        lambda _item: 0,
    )
    if not isinstance(info, dict) or not info.get("applied"):
        raise AssertionError(f"funding transform did not apply: {info!r}")
    return action, info


def execute(repo_root: Path) -> dict[str, object]:
    source_path = repo_root / SOURCE_RELATIVE
    source = source_path.read_bytes()
    if git_blob_id(source) != SOURCE_GIT_BLOB:
        raise AssertionError(
            f"exact source mismatch: {git_blob_id(source)} != {SOURCE_GIT_BLOB}"
        )
    runtime_root = source_path.parent
    sys.path.insert(0, str(runtime_root))
    try:
        predecessor = load_module("_sol_pro_funding_predecessor", source_path)
        patched, patch_receipt = patch_source(source)
        with tempfile.TemporaryDirectory(prefix="titan-pareto-rank-") as temporary:
            candidate_path = Path(temporary) / "frozen_selected.py"
            candidate_path.write_bytes(patched)
            candidate = load_module("_sol_pro_funding_candidate", candidate_path)
            predecessor_action, predecessor_info = call(predecessor)
            candidate_action, candidate_info = call(candidate)
    finally:
        try:
            sys.path.remove(str(runtime_root))
        except ValueError:
            pass

    if predecessor_info["item"] != "CARROT":
        raise AssertionError(f"predecessor did not choose low-cash CARROT: {predecessor_info}")
    if candidate_info["item"] != "WOOL":
        raise AssertionError(f"candidate did not choose high-cash WOOL: {candidate_info}")
    if not (predecessor_info["moved_quantity"] == candidate_info["moved_quantity"] == 1):
        raise AssertionError("both candidates must move exactly one unit")
    if predecessor_info["funded_completed"] != candidate_info["funded_completed"]:
        raise AssertionError("fixed-acquisition completion differs")
    cash_delta = (
        int(candidate_info["remaining_cash_after_target"])
        - int(predecessor_info["remaining_cash_after_target"])
    )
    if cash_delta != 165:
        raise AssertionError(f"unexpected certified cash delta: {cash_delta}")
    predecessor_sales = predecessor.sale_quantities(predecessor_action)
    candidate_sales = predecessor.sale_quantities(candidate_action)
    expected_sales = {"CARROT": 1, "WOOL": 1}
    if predecessor_sales != expected_sales or candidate_sales != expected_sales:
        raise AssertionError("per-item sale totals changed")

    return {
        "operation": OPERATION,
        "base_commit": CURRENT_BASE,
        "source_path": SOURCE_RELATIVE,
        "source_git_blob": SOURCE_GIT_BLOB,
        "official_engine_git_blob": ENGINE_GIT_BLOB,
        "patch_receipt": patch_receipt,
        "input": {
            "orders": [[], ["HIRE"], ["SELL", "CARROT", 1], ["SELL", "WOOL", 1]],
            "money": 0,
            "hires_today": 0,
            "hire_cost": 10,
            "shed": {"CARROT": 1, "WOOL": 1},
            "market_inventory": {"CARROT": 10000, "WOOL": 10000},
            "rival_quantity": 0,
        },
        "predecessor": {"action": predecessor_action, "info": predecessor_info},
        "candidate": {"action": candidate_action, "info": candidate_info},
        "certified_remaining_cash_delta": cash_delta,
        "invariants": {
            "moved_quantity": 1,
            "funded_completed": int(candidate_info["funded_completed"]),
            "sale_quantities": expected_sales,
            "orders_input_unchanged": True,
        },
        "claim_boundary": {
            "source_defect": True,
            "one_factor_candidate": True,
            "whole_game_strength": False,
            "promotion_authority": False,
            "kaggle_or_provider_mutation": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    report = execute(Path(args.repo_root).resolve())
    output = Path(args.out)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
