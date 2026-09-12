#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Paired current-native field gate for the hardened WF1 wheat-fertilize adapter.

The authenticated runtime is never rewritten in place by policy code.  This
runner expects the test-only entry plus exact donor/adapter files to be copied
beside ``main.py``.  Each seed/seat executes BASE (native vs native) and WF1
(test entry vs native) through the existing process-isolated official-interpreter
runner.  This is native execution evidence, not hosted scoring or activation.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
from pathlib import Path
import statistics
import sys

HERE = Path(__file__).resolve().parent
S8_RUNNER = HERE.parent / "s8-egg-care" / "run_s8_field.py"
DEFAULT_SEEDS = (2026091201, 2026091207, 2026091213, 2026091219)
TELEMETRY_NAME = ".wf1-field-telemetry.json"


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def paired_first_change(base_rows: Path, candidate_rows: Path):
    base = read_json(base_rows)
    cand = read_json(candidate_rows)
    for left, right in zip(base, cand):
        if left["step"] != right["step"]:
            return min(left["step"], right["step"])
        if left["own_action_sha256"] != right["own_action_sha256"]:
            return left["step"]
    if len(base) != len(cand):
        return min(len(base), len(cand))
    return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seeds", default=",".join(map(str, DEFAULT_SEEDS)))
    args = parser.parse_args()
    runtime = args.runtime.resolve()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    seeds = tuple(int(x) for x in args.seeds.split(",") if x.strip())
    runner = load(S8_RUNNER, "wf1_shared_native_runner")
    candidate_entry = runtime / "wf1_native_entry.py"
    telemetry_path = runtime / TELEMETRY_NAME
    required = [runtime / "main.py", runtime / "r04_wheat_fert.py",
                runtime / "wf1_current_adapter.py", candidate_entry]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise FileNotFoundError("missing runtime field files: " + ", ".join(missing))

    # Force the fixture to use its deterministic evaluator-visible fallback,
    # rather than accepting a caller environment that Actor will later strip.
    os.environ.pop("WF1_TELEMETRY_PATH", None)

    cells = []
    for seed in seeds:
        for seat in (0, 1):
            key = f"seed-{seed}-seat-{seat}"
            base_dir = output / key / "base"
            cand_dir = output / key / "wf1"
            telemetry_path.unlink(missing_ok=True)
            base = runner.play(runtime, seed, seat, base_dir,
                               opponent=runtime, passive=False)
            telemetry_path.unlink(missing_ok=True)
            candidate = runner.play(runtime, seed, seat, cand_dir,
                                    opponent=runtime, passive=False,
                                    entry=str(candidate_entry) + "::agent")
            telemetry = read_json(telemetry_path) if telemetry_path.is_file() else None
            telemetry_path.unlink(missing_ok=True)
            complete = base["status"] == "complete" and candidate["status"] == "complete"
            delta = None
            if complete:
                delta = {
                    "own": candidate["scores"][seat] - base["scores"][seat],
                    "rival": candidate["scores"][1-seat] - base["scores"][1-seat],
                    "margin": candidate["margin"] - base["margin"],
                }
            cells.append({
                "seed": seed,
                "seat": seat,
                "complete": complete,
                "base": {k: base.get(k) for k in ("status", "steps", "scores", "margin", "failure",
                                                         "trace_sha256", "action_sha256", "world_sha256")},
                "wf1": {k: candidate.get(k) for k in ("status", "steps", "scores", "margin", "failure",
                                                              "trace_sha256", "action_sha256", "world_sha256")},
                "telemetry": telemetry,
                "paired_first_action_change_step": paired_first_change(base_dir / "rows.json", cand_dir / "rows.json"),
                "delta": delta,
            })

    completed = [cell for cell in cells if cell["complete"]]
    deltas = [cell["delta"]["margin"] for cell in completed]
    own_deltas = [cell["delta"]["own"] for cell in completed]
    rival_deltas = [cell["delta"]["rival"] for cell in completed]
    engaged = [cell for cell in completed if (cell["telemetry"] or {}).get("transformed_actions", 0) > 0]
    result = {
        "schema": "titan.v4.wf1.current-native-field.v1",
        "method": "paired current-native BASE vs hardened WF1, both seats, process-isolated official interpreter; not hosted scoring",
        "seeds": list(seeds),
        "cells": cells,
        "summary": {
            "requested_cells": len(cells),
            "complete_cells": len(completed),
            "engaged_cells": len(engaged),
            "positive_margin_cells": sum(value > 0 for value in deltas),
            "zero_margin_cells": sum(value == 0 for value in deltas),
            "negative_margin_cells": sum(value < 0 for value in deltas),
            "mean_margin_delta": statistics.mean(deltas) if deltas else None,
            "median_margin_delta": statistics.median(deltas) if deltas else None,
            "mean_own_delta": statistics.mean(own_deltas) if own_deltas else None,
            "mean_rival_delta": statistics.mean(rival_deltas) if rival_deltas else None,
            "total_transformed_actions": sum((cell["telemetry"] or {}).get("transformed_actions", 0) for cell in completed),
            "total_changed_unit_rows": sum((cell["telemetry"] or {}).get("changed_unit_rows", 0) for cell in completed),
            "total_changed_market_callbacks": sum((cell["telemetry"] or {}).get("changed_market_callbacks", 0) for cell in completed),
        },
    }
    (output / "WF1-CURRENT-FIELD-RESULT.json").write_text(
        json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps(result["summary"], sort_keys=True, allow_nan=False))
    return int(len(completed) != len(cells))


if __name__ == "__main__":
    raise SystemExit(main())
