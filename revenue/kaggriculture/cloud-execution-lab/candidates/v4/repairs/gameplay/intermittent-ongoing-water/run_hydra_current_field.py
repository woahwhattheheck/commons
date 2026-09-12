#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Three-arm current-native field gate for source-bound HYDRA watering.

For every seed/seat this runner executes BASE, HYDRA-OFF, and HYDRA-ON through
the existing process-isolated official-interpreter runner. OFF must reproduce
BASE exactly. ON is measured for natural engagement, safety, and economics.
This is execution evidence only; it does not promote production defaults.
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


def compact(result):
    keys = ("status", "steps", "scores", "margin", "failure", "trace_sha256",
            "action_sha256", "world_sha256", "actors", "wall_seconds")
    return {key: result.get(key) for key in keys}


def exact_identity(base, off) -> bool:
    if base.get("status") != "complete" or off.get("status") != "complete":
        return False
    keys = ("steps", "scores", "margin", "trace_sha256", "action_sha256", "world_sha256")
    return all(base.get(key) == off.get(key) for key in keys)


def _run_arm(runner, runtime, seat, seed, out_dir, entry, *, enabled, telemetry_path=None):
    old_enabled = os.environ.get("HYDRA_ENABLED")
    old_telemetry = os.environ.get("HYDRA_TELEMETRY_PATH")
    try:
        if enabled is None:
            os.environ.pop("HYDRA_ENABLED", None)
        else:
            os.environ["HYDRA_ENABLED"] = "1" if enabled else "0"
        if telemetry_path is None:
            os.environ.pop("HYDRA_TELEMETRY_PATH", None)
        else:
            os.environ["HYDRA_TELEMETRY_PATH"] = str(telemetry_path)
        return runner.play(runtime, seed, seat, out_dir,
                           opponent=runtime, passive=False, entry=entry)
    finally:
        if old_enabled is None:
            os.environ.pop("HYDRA_ENABLED", None)
        else:
            os.environ["HYDRA_ENABLED"] = old_enabled
        if old_telemetry is None:
            os.environ.pop("HYDRA_TELEMETRY_PATH", None)
        else:
            os.environ["HYDRA_TELEMETRY_PATH"] = old_telemetry


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
    if not seeds:
        raise ValueError("at least one seed is required")

    runner = load(S8_RUNNER, "hydra_shared_native_runner")
    candidate_entry = runtime / "hydra_native_entry.py"
    required = [runtime / "main.py", runtime / "ongoing_water_skip.py", candidate_entry]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise FileNotFoundError("missing runtime field files: " + ", ".join(missing))

    cells = []
    for seed in seeds:
        for seat in (0, 1):
            key = f"seed-{seed}-seat-{seat}"
            base_dir = output / key / "base"
            off_dir = output / key / "off"
            on_dir = output / key / "on"
            entry = str(candidate_entry) + "::agent"

            base = _run_arm(runner, runtime, seat, seed, base_dir, None,
                            enabled=None, telemetry_path=None)
            off_telemetry_path = off_dir / "hydra-telemetry.json"
            off = _run_arm(runner, runtime, seat, seed, off_dir, entry,
                           enabled=False, telemetry_path=off_telemetry_path)
            on_telemetry_path = on_dir / "hydra-telemetry.json"
            on = _run_arm(runner, runtime, seat, seed, on_dir, entry,
                          enabled=True, telemetry_path=on_telemetry_path)

            off_telemetry = read_json(off_telemetry_path) if off_telemetry_path.is_file() else None
            on_telemetry = read_json(on_telemetry_path) if on_telemetry_path.is_file() else None
            complete = all(result.get("status") == "complete" for result in (base, off, on))
            delta = None
            if base.get("status") == "complete" and on.get("status") == "complete":
                delta = {
                    "own": on["scores"][seat] - base["scores"][seat],
                    "rival": on["scores"][1-seat] - base["scores"][1-seat],
                    "margin": on["margin"] - base["margin"],
                }
            cells.append({
                "seed": seed,
                "seat": seat,
                "complete": complete,
                "off_exact_identity": exact_identity(base, off),
                "base": compact(base),
                "off": compact(off),
                "on": compact(on),
                "off_telemetry": off_telemetry,
                "on_telemetry": on_telemetry,
                "paired_first_on_action_change_step": (
                    paired_first_change(base_dir / "rows.json", on_dir / "rows.json")
                    if base.get("status") == "complete" and on.get("status") == "complete" else None),
                "delta": delta,
            })

    completed = [cell for cell in cells if cell["complete"]]
    deltas = [cell["delta"]["margin"] for cell in cells if cell["delta"] is not None]
    own_deltas = [cell["delta"]["own"] for cell in cells if cell["delta"] is not None]
    rival_deltas = [cell["delta"]["rival"] for cell in cells if cell["delta"] is not None]
    engaged = [cell for cell in completed if (cell["on_telemetry"] or {}).get("rewritten_rows", 0) > 0]

    def tsum(key):
        return sum((cell["on_telemetry"] or {}).get(key, 0) for cell in completed)

    safety_violations = sum(
        int((cell["on_telemetry"] or {}).get("weed_after_rewrite", 0) > 0)
        for cell in completed)
    summary = {
        "requested_cells": len(cells),
        "complete_cells": len(completed),
        "off_exact_identity_cells": sum(cell["off_exact_identity"] for cell in cells),
        "engaged_cells": len(engaged),
        "classification": "COLD" if len(completed) == len(cells) and not engaged else "ENGAGED",
        "positive_margin_cells": sum(value > 0 for value in deltas),
        "zero_margin_cells": sum(value == 0 for value in deltas),
        "negative_margin_cells": sum(value < 0 for value in deltas),
        "mean_margin_delta": statistics.mean(deltas) if deltas else None,
        "median_margin_delta": statistics.median(deltas) if deltas else None,
        "mean_own_delta": statistics.mean(own_deltas) if own_deltas else None,
        "mean_rival_delta": statistics.mean(rival_deltas) if rival_deltas else None,
        "authored_water_rows": tsum("authored_water_rows"),
        "eligible_rows": tsum("eligible_rows"),
        "rewritten_rows": tsum("rewritten_rows"),
        "followup_next_day_water": tsum("followup_next_day_water"),
        "weed_after_rewrite": tsum("weed_after_rewrite"),
        "missing_or_replaced_after_rewrite": tsum("missing_or_replaced_after_rewrite"),
        "fertilizer_bonus_blocks": tsum("fertilizer_bonus_blocks"),
        "prior_streak_blocks": tsum("prior_streak_blocks"),
        "safety_violation_cells": safety_violations,
    }
    result = {
        "schema": "titan.v4.hydra.current-native-field.v1",
        "method": "three-arm paired current-native BASE/OFF/ON, both seats, process-isolated official interpreter; not hosted scoring",
        "seeds": list(seeds),
        "cells": cells,
        "summary": summary,
    }
    (output / "HYDRA-CURRENT-FIELD-RESULT.json").write_text(
        json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps(summary, sort_keys=True, allow_nan=False))

    all_complete = len(completed) == len(cells)
    all_off_exact = summary["off_exact_identity_cells"] == len(cells)
    safe = summary["weed_after_rewrite"] == 0
    return int(not (all_complete and all_off_exact and safe))


if __name__ == "__main__":
    raise SystemExit(main())
