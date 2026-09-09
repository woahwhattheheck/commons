# SPDX-License-Identifier: Apache-2.0
"""Run paired exact-engine P01 development cells and preserve raw evidence."""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import statistics
import sys
import time

ROOT = Path("/tmp/p01-runtime")
TRACE_DIR = Path(os.environ.get("P01_TRACE_DIR", "/tmp/p01-traces"))
MODE = os.environ.get("P01_MODE", "annual").strip().lower()
DISPATCH = "de4121fcadf365c4ce22c9f5a3a136bc7a075a3d"
ARCHIVE_SHA256 = "385022ff9d5c153b09086f261197de9ae502ca57731e00ffd9391c5a6cf39492"
SOURCE_SHA256 = "9abd5b96091816428780172c6b0b8f69cfebddcd61de65a3a438f26435da674f"
DEFAULT_SEEDS = tuple(range(2909010001, 2909010009))

EVALUATOR = ROOT / "checks/reference/evaluator/evaluate.py"
ENGINE = ROOT / "checks/reference/engine"
LOADER = ROOT / "checks/reference/evaluator/loader.py"
CONTROL = str(ROOT / "main.py") + "::agent"
CANDIDATE = str(ROOT / "p01_agent.py") + "::agent"
OPPONENT = str(ROOT / "reference/next-panel/vendor/arlene.py") + "::agent"


def _seeds() -> tuple[int, ...]:
    raw = os.environ.get("P01_SEEDS", "").strip()
    if not raw:
        return DEFAULT_SEEDS
    values = tuple(int(part.strip()) for part in raw.split(",") if part.strip())
    if not values or len(values) > 64 or len(set(values)) != len(values):
        raise ValueError("P01_SEEDS must contain 1..64 distinct integers")
    return values


def _load_evaluator():
    spec = importlib.util.spec_from_file_location("p01_host_eval", EVALUATOR)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load evaluator from {EVALUATOR}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _outcome(own: float, rival: float) -> str:
    return "W" if own > rival else "L" if own < rival else "T"


def _mean(values: list[float]) -> float:
    return float(statistics.fmean(values)) if values else 0.0


def _read_traces() -> list[dict]:
    rows: list[dict] = []
    for path in sorted(TRACE_DIR.glob(f"p01-{MODE}-*.jsonl")):
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            row = json.loads(line)
            row["trace_file"] = path.name
            row["trace_line"] = number
            rows.append(row)
    rows.sort(key=lambda row: (int(row.get("step", 10**9)), row["trace_file"], row["trace_line"]))
    return rows


def main() -> None:
    seeds = _seeds()
    TRACE_DIR.mkdir(parents=True, exist_ok=True)
    evaluator = _load_evaluator()
    engine, _ = evaluator.get_engine(ENGINE, LOADER)
    started = time.time()
    games: list[dict] = []
    paired: list[dict] = []
    for seed in seeds:
        for seat in (0, 1):
            cell = {}
            for label, entrypoint in (("control", CONTROL), (MODE, CANDIDATE)):
                agents = [entrypoint, OPPONENT] if seat == 0 else [OPPONENT, entrypoint]
                result = evaluator.play(
                    engine, agents, ENGINE, LOADER, seed, seat, 20260909,
                    1.0, 10.0, 120.0, None,
                )
                row = {"label": label, "seed": seed, "candidate_seat": seat, **result}
                games.append(row)
                cell[label] = row
                print(json.dumps({
                    "mode": MODE, "label": label, "seed": seed, "seat": seat,
                    "status": result.get("status"), "scores": result.get("scores"),
                }, sort_keys=True), flush=True)
            control = cell["control"]
            candidate = cell[MODE]
            pair = {"seed": seed, "candidate_seat": seat,
                    "control_status": control.get("status"),
                    "candidate_status": candidate.get("status")}
            if (control.get("status") == "complete" and candidate.get("status") == "complete"
                    and isinstance(control.get("scores"), list)
                    and isinstance(candidate.get("scores"), list)
                    and len(control["scores"]) == 2 and len(candidate["scores"]) == 2):
                c_own = float(control["scores"][seat])
                c_rival = float(control["scores"][1 - seat])
                p_own = float(candidate["scores"][seat])
                p_rival = float(candidate["scores"][1 - seat])
                pair.update(
                    complete=True,
                    control_own=c_own,
                    control_rival=c_rival,
                    candidate_own=p_own,
                    candidate_rival=p_rival,
                    control_outcome=_outcome(c_own, c_rival),
                    candidate_outcome=_outcome(p_own, p_rival),
                    own_cash_delta=p_own - c_own,
                    rival_cash_delta=p_rival - c_rival,
                    margin_delta=(p_own - p_rival) - (c_own - c_rival),
                )
            else:
                pair["complete"] = False
            paired.append(pair)

    traces = _read_traces()
    activations = [row for row in traces if bool(row.get("report", {}).get("changed"))]
    reason_counts: dict[str, int] = {}
    for row in traces:
        reason = str(row.get("report", {}).get("reason", "missing_reason"))
        reason_counts[reason] = reason_counts.get(reason, 0) + 1
    complete = [row for row in paired if row.get("complete")]
    own_deltas = [float(row["own_cash_delta"]) for row in complete]
    margin_deltas = [float(row["margin_delta"]) for row in complete]
    control_wtl = {key: sum(row["control_outcome"] == key for row in complete) for key in "WTL"}
    candidate_wtl = {key: sum(row["candidate_outcome"] == key for row in complete) for key in "WTL"}
    regressive_flips = sum(
        row["control_outcome"] in ("W", "T") and row["candidate_outcome"] == "L"
        for row in complete
    )
    positive_flips = sum(
        row["control_outcome"] in ("L", "T") and row["candidate_outcome"] == "W"
        for row in complete
    )
    summary = {
        "scheduled_pairs": len(paired),
        "complete_pairs": len(complete),
        "failed_pairs": len(paired) - len(complete),
        "control_wtl": control_wtl,
        "candidate_wtl": candidate_wtl,
        "mean_own_cash_delta": _mean(own_deltas),
        "mean_margin_delta": _mean(margin_deltas),
        "worst_own_cash_delta": min(own_deltas) if own_deltas else None,
        "best_own_cash_delta": max(own_deltas) if own_deltas else None,
        "nonzero_own_delta_pairs": sum(delta != 0 for delta in own_deltas),
        "regressive_flips": regressive_flips,
        "positive_flips": positive_flips,
        "frontier_rows": len(traces),
        "frontier_reason_counts": dict(sorted(reason_counts.items())),
        "activation_rows": len(activations),
        "activation_processes": len({row.get("trace_file") for row in activations}),
        "first_frontier": traces[0] if traces else None,
        "first_activation": activations[0] if activations else None,
    }
    summary["development_signal"] = bool(
        len(complete) == len(paired)
        and activations
        and positive_flips >= regressive_flips
        and summary["mean_own_cash_delta"] > 0
        and summary["mean_margin_delta"] >= 0
    )
    payload = {
        "schema": 1,
        "operation": "op:titan-v25-orders-20260909-P01-sol-forge-01",
        "mode": MODE,
        "dispatch": DISPATCH,
        "archive_sha256": ARCHIVE_SHA256,
        "source_manifest_sha256": SOURCE_SHA256,
        "engine": "kaggle-environments==1.32.7 / commit 28b6d8af3ce73926b3d0fda1410c1ddd8384ab8c",
        "opponent": "intact Arlene from exact archive",
        "seeds": list(seeds),
        "both_seats": True,
        "summary": summary,
        "paired": paired,
        "games": games,
        "traces": traces,
        "wall_seconds": time.time() - started,
        "scope": "development screen only; no canonical enablement or Kaggle submission",
    }
    output = Path(f"/tmp/P01-{MODE}-SCREEN.json")
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"mode": MODE, **summary}, sort_keys=True), flush=True)
    if len(complete) != len(paired):
        raise SystemExit("incomplete P01 paired screen")


if __name__ == "__main__":
    main()
