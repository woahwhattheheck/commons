# SPDX-License-Identifier: Apache-2.0
"""Fail-closed source and execution-custody audit for SOL-AMPLIFIER."""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
LAB = HERE.parents[1]
OPERATION = "titan-v3-full-queue-same-product-sell-growth-20260909-sol-amplifier-01"
EXPECTED_BLOBS = {
    "v1": "cbc502a92fe9d790cfaf763f6990d1057bc9b82d",
    "v2": "7c068b7078c3d7c09bb3836590ad42b0af934cdf",
    "frozen_selected": "fc7baf5c179818a55037f6a61d92984d81d1a21c",
    "main": "4a8cf7bcda1f0fea231a144692cb84a779a9e73e",
    "titan_runtime": "b952c9c228ecbde592bf3d2df01638677abb0d24",
}
QUEUE_NEEDLE = "if q>offered:return False"
CAP_NEEDLE = "q=min(max(0,int(o[2])),remaining.get(item,0),max(0,available.get(item,0)))"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git_blob_sha1(data: bytes) -> str:
    header = f"blob {len(data)}\0".encode("ascii")
    return hashlib.sha1(header + data).hexdigest()


def _nested_feasible_has_exact_gate(text: str, class_name: str) -> bool:
    tree = ast.parse(text)
    functions = [
        node
        for top in tree.body
        if isinstance(top, ast.ClassDef) and top.name == class_name
        for method in top.body
        if isinstance(method, (ast.FunctionDef, ast.AsyncFunctionDef))
        and method.name in ("act", "transform")
        for node in ast.walk(method)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == "feasible"
    ]
    if len(functions) != 1:
        return False
    gates = []
    for node in ast.walk(functions[0]):
        if not isinstance(node, ast.If):
            continue
        test = node.test
        if not (
            isinstance(test, ast.Compare)
            and isinstance(test.left, ast.Name)
            and test.left.id == "q"
            and len(test.ops) == 1
            and isinstance(test.ops[0], ast.Gt)
            and len(test.comparators) == 1
            and isinstance(test.comparators[0], ast.Name)
            and test.comparators[0].id == "offered"
        ):
            continue
        if len(node.body) == 1 and isinstance(node.body[0], ast.Return):
            value = node.body[0].value
            if isinstance(value, ast.Constant) and value.value is False:
                gates.append(node)
    return len(gates) == 1


def _one_function(text: str, name: str) -> bool:
    tree = ast.parse(text)
    return sum(
        isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name
        for node in ast.walk(tree)
    ) == 1


def build_report(lab: Path = LAB) -> dict[str, Any]:
    paths = {
        "v1": lab / "runtime/variants/v1/scheduler.py",
        "v2": lab / "runtime/variants/v2/scheduler.py",
        "frozen_selected": lab / "frozen_selected.py",
        "main": lab / "main.py",
        "titan_runtime": lab / "titan_runtime.py",
        "growth_patch": HERE / "growth_patch.py",
        "candidate": HERE / "candidate.py",
    }
    missing = [str(path) for path in paths.values() if not path.is_file()]
    if missing:
        raise FileNotFoundError("missing source: " + ", ".join(missing))
    blobs = {name: path.read_bytes() for name, path in paths.items()}
    text = {name: data.decode("utf-8") for name, data in blobs.items()}
    checks = {
        "exact_historical_and_current_blobs": all(
            git_blob_sha1(blobs[name]) == expected
            for name, expected in EXPECTED_BLOBS.items()
        ),
        "v1_has_no_saturated_offered_gate": QUEUE_NEEDLE not in text["v1"],
        "v1_grows_first_inherited_same_product_row": (
            text["v1"].count("if item not in used:") == 1
            and text["v1"].count("q=current[item]") == 1
        ),
        "v2_has_exact_saturated_offered_gate": (
            text["v2"].count(QUEUE_NEEDLE) == 1
            and _nested_feasible_has_exact_gate(text["v2"], "SellScheduler")
        ),
        "v2_caps_inherited_sell_to_original_quantity": (
            text["v2"].count(CAP_NEEDLE) == 1
        ),
        "current_selected_has_exact_saturated_offered_gate": (
            text["frozen_selected"].count(QUEUE_NEEDLE) == 1
            and _nested_feasible_has_exact_gate(text["frozen_selected"], "FrozenSelected")
        ),
        "current_selected_has_one_materializer_with_quantity_cap": (
            _one_function(text["frozen_selected"], "materialize_sales")
            and text["frozen_selected"].count(CAP_NEEDLE) == 1
        ),
        "actual_runtime_imports_frozen_selected_at_lazy_init": (
            text["titan_runtime"].count("from frozen_selected import FrozenSelected") == 1
            and text["titan_runtime"].count("self.consumer = FrozenSelected()") == 1
        ),
        "candidate_delegates_canonical_outer_agent": (
            text["candidate"].count("return _CANONICAL.agent(observation, configuration)") == 1
            and "instance.act(observation" not in text["candidate"]
        ),
        "candidate_attaches_inside_canonical_new_instance": (
            text["candidate"].count("instance = _ORIGINAL_NEW_INSTANCE(root, feature_data)") == 1
            and text["candidate"].count("_LAST_INSTALL_RECEIPT = attach(instance, frozen_selected)") == 1
        ),
        "patch_reuses_exact_transform_code_with_private_globals": (
            text["growth_patch"].count("base_transform.__code__") >= 2
            and text["growth_patch"].count('"optimize_lot": _build_optimizer') == 1
            and text["growth_patch"].count('"materialize_sales": _build_materializer') == 1
        ),
        "patch_is_exact_length_and_existing_positive_row_only": (
            text["growth_patch"].count("len(orders) != limit") >= 2
            and text["growth_patch"].count("offered <= 0") == 1
            and text["growth_patch"].count("if not matches or desired <= inherited") == 1
        ),
        "initializer_uses_private_import_without_global_mutation": (
            text["growth_patch"].count('if level == 0 and name == "frozen_selected"') == 1
            and text["growth_patch"].count('{"__builtins__": private_builtins}') == 1
            and "frozen_selected_module.FrozenSelected =" not in text["growth_patch"]
            and "sys.modules[" not in text["growth_patch"]
            and "sys.modules." not in text["growth_patch"]
        ),
        "canonical_sources_are_read_only_targets": all(
            path.parent != HERE for name, path in paths.items()
            if name in EXPECTED_BLOBS
        ),
    }
    root = lab.parents[2]
    return {
        "schema_version": 1,
        "operation": OPERATION,
        "decision": "PASS" if all(checks.values()) else "FAIL",
        "claim": {
            "historical_v1_saturated_growth": True,
            "historical_v2_saturated_growth": False,
            "current_selected_saturated_growth": False,
            "candidate_changes": [
                "capacity admission for exact-limit queues with a positive inherited same-product SELL row",
                "in-place quantity expansion of that inherited row",
            ],
            "new_slot_created": False,
            "order_index_changed": False,
            "canonical_files_modified": False,
        },
        "checks": checks,
        "sources": {
            name: {
                "path": path.relative_to(root).as_posix(),
                "bytes": len(blobs[name]),
                "git_blob_sha1": git_blob_sha1(blobs[name]),
                "sha256": sha256_bytes(blobs[name]),
            }
            for name, path in paths.items()
        },
    }


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
