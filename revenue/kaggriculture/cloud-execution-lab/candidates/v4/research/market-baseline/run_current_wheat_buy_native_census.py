#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Run a returned-action WHEAT-buy census through the official native harness."""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
LAB = HERE.parents[3]
S8_RUNNER = HERE.parents[1] / "repairs" / "gameplay" / "s8-egg-care" / "run_s8_field.py"
ENTRY = HERE / "current_wheat_buy_native_entry.py"


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--seeds", default="17,101,2026091201")
    args = ap.parse_args(argv)
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    seeds = [int(part) for part in args.seeds.split(",") if part]
    runner = load(S8_RUNNER, "townprocure_shared_native_runner")

    cells = []
    for seed in seeds:
        for seat in (0, 1):
            cell_dir = output / f"seed-{seed}-seat-{seat}"
            telemetry_path = cell_dir / "townprocure-telemetry.json"
            os.environ["TOWNPROCURE_TELEMETRY_PATH"] = str(telemetry_path)
            result = runner.play(
                LAB,
                seed,
                seat,
                cell_dir,
                opponent=LAB,
                passive=False,
                entry=str(ENTRY) + "::agent",
            )
            os.environ.pop("TOWNPROCURE_TELEMETRY_PATH", None)
            telemetry = (
                json.loads(telemetry_path.read_text(encoding="utf-8"))
                if telemetry_path.is_file()
                else None
            )
            cell = {
                "seed": seed,
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
            }
            cells.append(cell)

    for cell in cells:
        telemetry = cell["telemetry"]
        if cell["status"] != "complete" or not isinstance(telemetry, dict):
            raise RuntimeError(f"current-native cell incomplete: {cell}")
        if telemetry.get("telemetry_errors") != 0:
            raise RuntimeError(f"telemetry error in cell: {cell}")
        if telemetry.get("callback_attempts") != cell["steps"]:
            raise RuntimeError(f"callback attempt mismatch in cell: {cell}")
        if telemetry.get("callbacks") != cell["steps"]:
            raise RuntimeError(f"callback record mismatch in cell: {cell}")

    wheat_rows = sum(cell["telemetry"]["wheat_buy_rows"] for cell in cells)
    wheat_units = sum(cell["telemetry"]["wheat_buy_units"] for cell in cells)
    report = {
        "schema": "titan.v4.market-baseline.current-wheat-buy-native-census.v1",
        "method": "transparent parent-action wrapper; official interpreter; current main self-play; both seats",
        "seeds": seeds,
        "cells": cells,
        "summary": {
            "complete_cells": len(cells),
            "callbacks": sum(cell["steps"] for cell in cells),
            "wheat_buy_rows": wheat_rows,
            "wheat_buy_units": wheat_units,
            "cells_with_wheat_buys": sum(
                cell["telemetry"]["wheat_buy_rows"] > 0 for cell in cells
            ),
            "decision": "RETURNED_WHEAT_BUYS_PRESENT" if wheat_rows else "NO_RETURNED_WHEAT_BUYS_IN_PANEL",
        },
        "limits": [
            "finite current-native panel; zero observations do not prove impossibility outside sampled seeds",
            "wrapper returns parent action object unchanged",
            "no speculative purchase authorization or runtime mutation",
        ],
    }
    target = output / "current-wheat-buy-native-census.json"
    target.write_text(
        json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report["summary"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
