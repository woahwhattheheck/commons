#!/usr/bin/env python3
"""Run a source-pinned public-development matrix for Learn2Design v1/v2/v3.

This is deliberately not official/hidden/H100 evidence. It measures only the
organizer's public ConstrainedVoyagerProblem under identical Objective budgets.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import platform
from pathlib import Path
import statistics
import sys
import time

ORGANIZER_COMMIT = "84a4b0a4c7e0f3b702459ffc8ba6a1d84d34cefa"
EXPECTED = {
    "v1": {
        "gitBlobSha1": "0e5b0141138c471c9b47163aca4f1a01336dfdf1",
        "algorithm": "tjlabs_staged_trust_portfolio_v1",
    },
    "v2": {
        "gitBlobSha1": "ac814d1f543529a823f7c3afa2a9c4f54c0bfe12",
        "algorithm": "tjlabs_vectorized_trust_portfolio_v2",
    },
    "v3": {
        "gitBlobSha1": "78ce195e1779441f2a0c53feef67c8dafd87f240",
        "algorithm": "tjlabs_depth_throughput_portfolio_v3",
    },
}
AUTHORITY = {
    "organizerPublicDevelopmentOnly": True,
    "hiddenTopology": False,
    "officialH100": False,
    "officialScore": False,
    "officialRank": False,
    "submission": False,
    "prize": False,
    "payment": False,
    "revenue": False,
}


def git_blob_sha1(raw: bytes) -> str:
    header = f"blob {len(raw)}\0".encode()
    return hashlib.sha1(header + raw).hexdigest()


def canonical_sha256(value: dict) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def load_candidate(label: str, path: Path):
    raw = path.read_bytes()
    blob = git_blob_sha1(raw)
    expected = EXPECTED[label]
    if blob != expected["gitBlobSha1"]:
        raise RuntimeError(f"{label} source drift: {blob} != {expected['gitBlobSha1']}")
    name = f"learn2design_matrix_{label}"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    cls = getattr(module, "StagedTrustPortfolio", None)
    if cls is None or getattr(cls, "algorithm_str", None) != expected["algorithm"]:
        raise RuntimeError(f"{label} optimizer identity mismatch")
    return cls, hashlib.sha256(raw).hexdigest(), blob


def instantiate_candidate(cls):
    abstract = set(getattr(cls, "__abstractmethods__", ()))
    if not abstract:
        return cls()
    if abstract != {"__init__"}:
        raise RuntimeError(f"unsupported abstract methods: {sorted(abstract)}")

    def _matrix_init(self):
        pass

    adapter = type(
        f"{cls.__name__}MatrixInitAdapter",
        (cls,),
        {"__init__": _matrix_init, "__module__": cls.__module__},
    )
    obj = adapter()
    if adapter.optimize is not cls.optimize or adapter.algorithm_str != cls.algorithm_str:
        raise RuntimeError("init adapter changed optimizer identity")
    return obj


def one_measurement(label: str, cls, seed: int, seconds: int, source_sha256: str, blob: str):
    from dfbench import Objective
    from dfbench.problems import ConstrainedVoyagerProblem

    objective = Objective(ConstrainedVoyagerProblem(), max_time=seconds, verbose=0)
    optimizer = instantiate_candidate(cls)
    started = time.monotonic()
    optimizer.optimize(objective, random_seed=seed)
    elapsed = time.monotonic() - started
    loss = float(objective.best_loss)
    eval_count = int(objective.eval_count)
    if not math.isfinite(loss) or eval_count <= 0:
        raise RuntimeError(f"invalid {label} measurement: loss={loss!r}, evals={eval_count}")
    row = {
        "candidate": label,
        "algorithm": EXPECTED[label]["algorithm"],
        "seed": seed,
        "maxTimeSeconds": seconds,
        "bestLoss": loss,
        "evalCount": eval_count,
        "budgetExceeded": bool(objective.budget_exceeded),
        "elapsedSeconds": round(elapsed, 6),
        "sourceSha256": source_sha256,
        "gitBlobSha1": blob,
    }
    row["receiptSha256"] = canonical_sha256(row)
    return row


def summarize(rows: list[dict]) -> dict:
    by = {label: [row for row in rows if row["candidate"] == label] for label in EXPECTED}
    summary = {}
    for label, values in by.items():
        losses = [r["bestLoss"] for r in values]
        evals = [r["evalCount"] for r in values]
        summary[label] = {
            "meanBestLoss": statistics.fmean(losses),
            "medianBestLoss": statistics.median(losses),
            "meanEvalCount": statistics.fmean(evals),
            "losses": losses,
            "evalCounts": evals,
        }
    seeds = sorted({row["seed"] for row in rows})
    pairwise = {}
    for other in ("v1", "v2"):
        wins = 0
        losses = 0
        ties = 0
        for seed in seeds:
            v3 = next(r["bestLoss"] for r in by["v3"] if r["seed"] == seed)
            baseline = next(r["bestLoss"] for r in by[other] if r["seed"] == seed)
            if v3 < baseline:
                wins += 1
            elif v3 > baseline:
                losses += 1
            else:
                ties += 1
        pairwise[f"v3_vs_{other}"] = {"wins": wins, "losses": losses, "ties": ties}
    promote = (
        summary["v3"]["meanBestLoss"] < summary["v1"]["meanBestLoss"]
        and summary["v3"]["meanBestLoss"] < summary["v2"]["meanBestLoss"]
        and pairwise["v3_vs_v1"]["wins"] >= 2
        and pairwise["v3_vs_v2"]["wins"] >= 2
    )
    return {"candidates": summary, "pairwise": pairwise, "publicPromotionCriterionMet": promote}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--v1", type=Path, required=True)
    parser.add_argument("--v2", type=Path, required=True)
    parser.add_argument("--v3", type=Path, required=True)
    parser.add_argument("--seed", type=int, action="append", dest="seeds", required=True)
    parser.add_argument("--seconds", type=int, default=30)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.seconds < 10 or len(set(args.seeds)) < 3:
        parser.error("matrix requires >=3 distinct seeds and >=10 seconds per cell")

    loaded = {}
    for label, path in (("v1", args.v1), ("v2", args.v2), ("v3", args.v3)):
        loaded[label] = (*load_candidate(label, path), path.as_posix())

    rows = []
    labels = ("v1", "v2", "v3")
    for seed_index, seed in enumerate(args.seeds):
        order = labels[seed_index % 3 :] + labels[: seed_index % 3]
        for label in order:
            cls, source_sha256, blob, _ = loaded[label]
            row = one_measurement(label, cls, seed, args.seconds, source_sha256, blob)
            rows.append(row)
            print(json.dumps(row, sort_keys=True), flush=True)

    result = {
        "schema": "tjlabs.learn2design.public-matrix.v1",
        "evidenceClass": "ORGANIZER_PUBLIC_DEVELOPMENT",
        "organizerRepository": "artificial-scientist-lab/Learn2Design-2026",
        "organizerCommit": ORGANIZER_COMMIT,
        "problem": "ConstrainedVoyagerProblem",
        "python": platform.python_version(),
        "platform": platform.platform(),
        "authority": AUTHORITY,
        "seeds": args.seeds,
        "maxTimeSecondsPerCell": args.seconds,
        "candidateSources": {
            label: {
                "path": loaded[label][3],
                "sourceSha256": loaded[label][1],
                "gitBlobSha1": loaded[label][2],
                "algorithm": EXPECTED[label]["algorithm"],
            }
            for label in labels
        },
        "measurements": sorted(rows, key=lambda r: (r["seed"], r["candidate"])),
    }
    result["summary"] = summarize(result["measurements"])
    unsigned = dict(result)
    result["receiptSha256"] = canonical_sha256(unsigned)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result["summary"], indent=2, sort_keys=True))
    print("receipt", result["receiptSha256"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
