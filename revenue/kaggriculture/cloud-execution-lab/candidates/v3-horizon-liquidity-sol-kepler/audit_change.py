# SPDX-License-Identifier: Apache-2.0
"""Fail-closed custody audit for the historical carry seam and V3 target."""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
LAB = HERE.parents[1]
V1_NEEDLE = "carry=.95*self.single(inv,remaining)[0]"
FULL_NEEDLE = "carry=float(self.single(inv,remaining)[0])"
SELECTED_IMPORT = "from selected_sell_core import optimize_lot, joint_plan_metrics, shared_slot_ledger"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


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


def build_report(lab: Path = LAB) -> dict[str, Any]:
    paths = {
        "v1": lab / "runtime/variants/v1/scheduler.py",
        "v2": lab / "runtime/variants/v2/scheduler.py",
        "current_scheduler": lab / "scheduler.py",
        "selected_sell_core": lab / "selected_sell_core.py",
        "frozen_selected": lab / "frozen_selected.py",
        "ablation": HERE / "liquidity_haircut.py",
        "candidate": HERE / "candidate.py",
    }
    missing = [str(path) for path in paths.values() if not path.is_file()]
    if missing:
        raise FileNotFoundError("missing source: " + ", ".join(missing))

    text = {name: path.read_text(encoding="utf-8") for name, path in paths.items()}
    checks = {
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
    }
    report = {
        "schema_version": 2,
        "operation": "titan-v3-horizon-liquidity-20260909-sol-kepler-01",
        "decision": "PASS" if all(checks.values()) else "FAIL",
        "claim": {
            "historical_v1_artificial_horizon_carry_factor": 0.95,
            "historical_v2_artificial_horizon_carry_factor": 1.0,
            "current_selected_optimizer_carry_factor": 1.0,
            "candidate_selected_optimizer_carry_factor": 0.95,
            "target": "selected_sell_core.MarketPath.score",
            "canonical_files_modified": False,
        },
        "checks": checks,
        "sources": {
            name: {
                "path": str(path.relative_to(lab.parent.parent.parent)),
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
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
