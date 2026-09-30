#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Run telemetry-only current-native market-budget census against native self-play."""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
S8_RUNNER = HERE.parents[1] / "repairs" / "gameplay" / "s8-egg-care" / "run_s8_field.py"


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=2026091223)
    args = parser.parse_args()
    runtime = args.runtime.resolve()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    runner = load(S8_RUNNER, "orderbudget_shared_native_runner")
    entry = runtime / "market_budget_native_entry.py"
    helper = runtime / "market_order_budget.py"
    for path in (runtime / "main.py", entry, helper):
        if not path.is_file():
            raise FileNotFoundError(path)

    cells = []
    for seat in (0, 1):
        cell_dir = output / f"seat-{seat}"
        telemetry_path = cell_dir / "telemetry.json"
        os.environ["ORDERBUDGET_TELEMETRY_PATH"] = str(telemetry_path)
        result = runner.play(runtime, args.seed, seat, cell_dir,
                             opponent=runtime, passive=False,
                             entry=str(entry) + "::agent")
        os.environ.pop("ORDERBUDGET_TELEMETRY_PATH", None)
        telemetry = json.loads(telemetry_path.read_text()) if telemetry_path.is_file() else None
        cells.append({
            "seat": seat,
            "status": result.get("status"),
            "steps": result.get("steps"),
            "scores": result.get("scores"),
            "margin": result.get("margin"),
            "failure": result.get("failure"),
            "action_sha256": result.get("action_sha256"),
            "trace_sha256": result.get("trace_sha256"),
            "world_sha256": result.get("world_sha256"),
            "telemetry": telemetry,
        })

    if any(cell["status"] != "complete" or not isinstance(cell["telemetry"], dict) for cell in cells):
        raise RuntimeError("current-native census did not complete in both seats")
    report = {
        "schema": "titan.v4.market-order-budget.current-native-census.v1",
        "method": "telemetry-only wrapper returns native parent action unchanged; native self-play, both seats",
        "seed": args.seed,
        "cells": cells,
        "summary": {
            "complete_cells": len(cells),
            "callbacks": sum(cell["telemetry"]["callbacks"] for cell in cells),
            "max_raw_rows": max(cell["telemetry"]["max_raw_rows"] for cell in cells),
            "max_active_slot": max((cell["telemetry"]["max_active_slot"] for cell in cells if cell["telemetry"]["max_active_slot"] is not None), default=None),
            "structural_overflow_callbacks": sum(cell["telemetry"]["structural_overflow_callbacks"] for cell in cells),
            "dropped_nonempty_callbacks": sum(cell["telemetry"]["dropped_nonempty_callbacks"] for cell in cells),
            "dropped_nonempty_rows": sum(cell["telemetry"]["dropped_nonempty_rows"] for cell in cells),
            "no_admission_slot_callbacks": sum(cell["telemetry"]["no_admission_slot_callbacks"] for cell in cells),
        },
    }
    target = output / "current-native-census.json"
    target.write_text(json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps(report["summary"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
