# SPDX-License-Identifier: Apache-2.0
"""Fail-closed source audit for the executable receipt-profile factor."""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
LAB = HERE.parents[1]
FROZEN = LAB / "frozen_selected.py"
SCHEDULER = LAB / "scheduler.py"
ENGINE = LAB / "reference" / "engine" / "kaggriculture.py"
EXPECTED_FROZEN = "fc7baf5c179818a55037f6a61d92984d81d1a21c"
EXPECTED_SCHEDULER = "a483b24dd72b580d7d8811636b54d2d44f391575"


def git_blob_sha1(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(f"blob {len(data)}\0".encode("ascii") + data).hexdigest()


def function_source(path: Path, class_name: str, function_name: str) -> str:
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            for child in node.body:
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)) and child.name == function_name:
                    segment = ast.get_source_segment(source, child)
                    if segment is None:
                        raise RuntimeError("could not recover function source")
                    return segment
    raise RuntimeError(f"missing {class_name}.{function_name}")


def audit() -> dict:
    if git_blob_sha1(FROZEN) != EXPECTED_FROZEN:
        raise RuntimeError("frozen_selected.py drift")
    if git_blob_sha1(SCHEDULER) != EXPECTED_SCHEDULER:
        raise RuntimeError("scheduler.py drift")

    profile = function_source(SCHEDULER, "SellScheduler", "receipt_profile")
    if profile.count("for o in orders:") != 1:
        raise RuntimeError("receipt_profile raw market-loop cardinality drift")
    if "orders[:max_orders]" in profile:
        raise RuntimeError("predecessor no longer exposes the claimed suffix seam")

    engine = ENGINE.read_text(encoding="utf-8")
    if engine.count("queues.append(q[:max_orders])") != 1:
        raise RuntimeError("official engine queue-prefix contract drift")
    if engine.count("max_orders = max(1, int(get(env.configuration, \"maxMarketOrdersPerTurn\", 10)))") != 1:
        raise RuntimeError("official engine max-order normalization drift")

    candidate = (HERE / "executable_receipt_profile.py").read_text(encoding="utf-8")
    if candidate.count("market[:max_orders]") != 1:
        raise RuntimeError("candidate prefix transformation cardinality drift")
    return {
        "schema_version": 1,
        "operation": "titan-v3-executable-receipt-profile-20260909-sol-quoin-01",
        "frozen_selected_git_blob": EXPECTED_FROZEN,
        "scheduler_git_blob": EXPECTED_SCHEDULER,
        "canonical_profile_raw_loop_count": 1,
        "official_engine_prefix_slice_count": 1,
        "candidate_prefix_slice_count": 1,
        "factor": "exclude raw rows after maxMarketOrdersPerTurn from receipt_profile only",
        "canonical_files_modified": False,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", type=Path)
    args = parser.parse_args(argv)
    result = audit()
    text = json.dumps(result, sort_keys=True, indent=2) + "\n"
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(text, encoding="utf-8")
    print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
