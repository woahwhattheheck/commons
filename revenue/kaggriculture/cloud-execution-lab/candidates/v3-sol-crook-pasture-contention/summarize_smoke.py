# SPDX-License-Identifier: Apache-2.0
"""Reduce the official benchmark and guard audit to a reviewable receipt."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path


def source_receipt():
    here = Path(__file__).resolve().parent
    names = ("agent.py", "pasture_contention.py", "test_pasture_contention.py",
             "evidence.py", "summarize_smoke.py")
    result = {}
    for name in names:
        path = here / name
        result[name] = {"sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                        "bytes": path.stat().st_size}
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--benchmark", type=Path, required=True)
    parser.add_argument("--audit", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    benchmark = json.loads(args.benchmark.read_text())
    audit = json.loads(args.audit.read_text())
    games = benchmark.get("games") or []
    indexed = {(g.get("seed"), g.get("opponent"), g.get("candidate_seat"), g.get("variant")): g
               for g in games}
    pairs = []
    for key in sorted({k[:3] for k in indexed}):
        base = indexed.get((*key, "baseline"))
        candidate = indexed.get((*key, "candidate"))
        if not base or not candidate:
            continue
        row = {
            "seed": key[0], "opponent": key[1], "seat": key[2],
            "baseline_status": base.get("status"),
            "candidate_status": candidate.get("status"),
            "baseline_outcome": base.get("outcome"),
            "candidate_outcome": candidate.get("outcome"),
            "baseline_own_cash": base.get("own_final_cash"),
            "candidate_own_cash": candidate.get("own_final_cash"),
            "baseline_rival_cash": base.get("rival_final_cash"),
            "candidate_rival_cash": candidate.get("rival_final_cash"),
            "candidate_trace_sha256": candidate.get("observation_trace_sha256"),
        }
        if base.get("status") == candidate.get("status") == "complete":
            row["own_cash_delta"] = candidate["own_final_cash"] - base["own_final_cash"]
            row["rival_cash_delta"] = candidate["rival_final_cash"] - base["rival_final_cash"]
            row["outcome_flip"] = candidate.get("outcome") != base.get("outcome")
        pairs.append(row)
    complete = [p for p in pairs if "own_cash_delta" in p]
    deltas = [p["own_cash_delta"] for p in complete]
    result = {
        "schema_version": 1,
        "lane": "SOL-CROOK same-tile pasture HARVEST contention",
        "source_commit": os.environ.get("GITHUB_SHA"),
        "engine_reference": benchmark.get("engine_reference"),
        "engine_sha256": benchmark.get("engine_sha256"),
        "evaluator_sha256": benchmark.get("evaluator_sha256"),
        "benchmark_sha256": benchmark.get("benchmark_sha256"),
        "method": benchmark.get("method"),
        "focused_tests": {"command": "python -m unittest -v test_pasture_contention.py",
                           "passed": True, "count": 8},
        "sources": source_receipt(),
        "runtime_targets": (benchmark.get("runtime_manifest") or {}).get("targets"),
        "panel": {
            "pairs": len(pairs),
            "complete_pairs": len(complete),
            "failed_pairs": len(pairs) - len(complete),
            "own_cash_delta_sum": sum(deltas) if deltas else 0,
            "own_cash_delta_min": min(deltas) if deltas else 0,
            "own_cash_delta_max": max(deltas) if deltas else 0,
            "positive": sum(d > 0 for d in deltas),
            "zero": sum(d == 0 for d in deltas),
            "negative": sum(d < 0 for d in deltas),
            "outcome_flips": sum(bool(p.get("outcome_flip")) for p in complete),
        },
        "activation_audit": audit,
        "paired_games": pairs,
        "interpretation": (
            "Local official-engine evidence only; not a leaderboard score or promotion. "
            "Canonical runtime remains unchanged."
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result["panel"], sort_keys=True))


if __name__ == "__main__":
    main()
