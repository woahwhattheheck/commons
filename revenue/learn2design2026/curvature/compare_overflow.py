"""Source-pinned analytic comparison of the numerical repair, not physics evidence.

Example: python compare_overflow.py --reference /tmp/old-submission.py --out /tmp/new-report.json
Obtain the historical reference from commit de7288df468251c69c9efdc342ee0ed7c4d35749.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import platform

import jax
import jax.numpy as jnp
import numpy as np

from benchmark import identity, trace_hash, verify_sources
from synthetic import SyntheticObjective, load_candidate, problem

ROOT = Path(__file__).resolve().parent
REFERENCE_BLOB = "2bd09e07a24070a210c08d760899b539cb69ca61"


def execute(cls, loss, dimension, seed, batches, initial_scale=2.0):
    finite_gradients = []

    def record_gradient(batch, values, gradients):
        finite_gradients.append(bool(np.isfinite(np.asarray(gradients)).all()))
        return values, gradients

    obj = SyntheticObjective(loss, dimension, batches, initial_scale,
                             dtype=np.float32, injected=record_gradient)
    cls().optimize(obj, random_seed=seed, population_size=8)
    count = sum(a.shape[0] for a in obj.history)
    if count != batches * 8:
        raise ValueError("wrong evaluation count")
    return obj, {"evaluations": count, "best_loss": obj.best_loss,
                 "parameter_trace_sha256": trace_hash(obj.history),
                 "loss_trace_sha256": trace_hash(obj.loss_history),
                 "all_parameters_finite": all(np.isfinite(a).all().item() for a in obj.history),
                 "all_losses_finite": all(np.isfinite(a).all().item() for a in obj.loss_history),
                 "all_gradients_finite": all(finite_gradients)}


def compare(reference):
    before = verify_sources()
    reference_before = identity(reference)
    if reference_before["git_blob"] != REFERENCE_BLOB:
        raise ValueError("reference is not the historical frozen candidate")
    harness_before = {name: identity(ROOT / name) for name in
                      ("synthetic.py", "benchmark.py", "compare_overflow.py")}
    old = load_candidate(reference, "_overflow_old").BatchedCurvaturePortfolio
    new = load_candidate(ROOT / "submission.py", "_overflow_new").BatchedCurvaturePortfolio
    rows = []
    for name in ("sphere", "rotated_ellipsoid", "rosenbrock", "double_well"):
        for dimension in (8, 32, 200):
            loss = problem(name, dimension)
            for seed in (11, 53, 97):
                left, old_result = execute(old, loss, dimension, seed, 128)
                right, new_result = execute(new, loss, dimension, seed, 128)
                same_params = np.array_equal(np.asarray(left.history), np.asarray(right.history))
                same_losses = np.array_equal(np.asarray(left.loss_history), np.asarray(right.loss_history))
                rows.append({"problem": name, "dimension": dimension, "seed": seed,
                             "reference": old_result, "repaired": new_result,
                             "parameter_trace_equal": bool(same_params),
                             "loss_trace_equal": bool(same_losses)})
                print(f"{name}/{dimension}/{seed}: parameters={same_params} losses={same_losses}", flush=True)
    extreme = lambda x: jnp.asarray(1e38, x.dtype) * jnp.exp(jnp.sum(x))
    _, old_extreme = execute(old, extreme, 64, 7, 12, 0.0)
    _, new_extreme = execute(new, extreme, 64, 7, 12, 0.0)
    after = verify_sources()
    harness_after = {name: identity(ROOT / name) for name in harness_before}
    if before != after or reference_before != identity(reference) or harness_before != harness_after:
        raise ValueError("source changed during execution")
    return {"schema": "learn2design-curvature-overflow-comparison/v1",
            "evidence_class": "LOCAL_ANALYTIC_FAKE_DFBENCH_REAL_JAX",
            "observed_at": datetime.now(timezone.utc).isoformat(),
            "environment": {"python": platform.python_version(), "jax": jax.__version__,
                            "numpy": np.__version__, "backend": jax.default_backend(),
                            "x64_enabled": jax.config.x64_enabled},
            "reference_identity": reference_before, "sources_before": before, "sources_after": after,
            "harness": harness_before, "ordinary_cells": rows,
            "ordinary_equal_parameter_and_loss_traces": sum(
                r["parameter_trace_equal"] and r["loss_trace_equal"] for r in rows),
            "finite_extreme_exponential": {"dimension": 64, "seed": 7,
                                           "reference": old_extreme, "repaired": new_extreme},
            "authority": {"organizer_physics": False, "official_score": False,
                          "promotion": False, "prize": False, "revenue": False},
            "status": "COMPLETE"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    if args.out.exists():
        parser.error("output exists; choose a new path")
    report = compare(args.reference)
    with args.out.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, sort_keys=True, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps({"ordinary_equal": report["ordinary_equal_parameter_and_loss_traces"],
                      "extreme": report["finite_extreme_exponential"]}, sort_keys=True))


if __name__ == "__main__":
    main()
