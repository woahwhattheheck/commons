#!/usr/bin/env python3
"""Reproduce the H3/L3 Arlene factor gate from an exact V3.1 package tree."""
from __future__ import annotations
import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SEEDS = [2611151001,2611151002,2611151003,2611151004,2611151005,2611151006,2611151007,2611151008]
EXPECTED = {
    "main.py": "c4c22d0f2b1071cadf6a9f74effccc8cb20ea9f4d10ca1cf9f1fe57351709dc1",
    "r04_full_router.py": "281117d7460d57c71a8caa9f30ed81cd918b714ad88638d47cb06d071bc12239",
    "checks/reference/evaluator/evaluate.py": "e30b3108e0027477ab7ddbc057892a241c41a1f2b38f72caf267477877c4333c",
    "checks/reference/evaluator/loader.py": "cd113a94ae99b03492502e425bdcf09c3db17a2aa2a8fd866f0d78caec9e311e",
    "reference/next-panel/vendor/arlene.py": "1dc166ae2bf0c56a44fac4482f469b8812968c4cb32459cb9860f5077897a7d4",
}
WRAPPERS = {
    "l3_control.py": "2f3ed65894e2c41398dccaf42738c6604e7e0c5ebf0d705bc4db1a16e258137e",
    "l3_candidate.py": "0802b0d4f827c9b427a3a8431264035d9ff2b0eb47b3c4b7372b9ac1f3ef2867",
}
IDENTITY = {
    0: {"scores": [76863.0, 70554.0], "trace_sha256": "1f4beb9497a365d244373b3da1e5d31bc2b7a490b661b7461ffc658b8e7638bc"},
    1: {"scores": [70554.0, 76863.0], "trace_sha256": "bb4adfce8b9786cc0567561f1c81fc755328536dc9b7c7a795f62dac5da2d02e"},
}
EXPECTED_SUMMARY = {
    "delta_own_mean": 205.0,
    "delta_rival_mean": 0.25,
    "delta_margin_mean": 204.75,
    "positive": 16,
    "zero": 0,
    "negative": 0,
}

def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def require_hash(root: Path, rel: str, expected: str) -> None:
    got = sha(root / rel)
    if got != expected:
        raise SystemExit(f"SHA mismatch {rel}: {got} != {expected}")

def run_eval(root: Path, candidate: Path, seeds: list[int], output: Path) -> dict:
    evaluator = root / "checks/reference/evaluator/evaluate.py"
    cmd = [sys.executable, str(evaluator),
           "--engine-dir", str(root / "checks/reference/engine"),
           "--loader", str(root / "checks/reference/evaluator/loader.py"),
           "--candidate", str(candidate),
           "--opponent", f"arlene={root / 'reference/next-panel/vendor/arlene.py'}::agent",
           "--seeds", ",".join(map(str, seeds)),
           "--output", str(output)]
    subprocess.run(cmd, check=True)
    return json.loads(output.read_text(encoding="utf-8"))

def keyed(report: dict) -> dict:
    return {(int(g["seed"]), int(g["candidate_seat"])): g for g in report["games"]}

def identity_check(main: dict, control: dict) -> None:
    a, b = keyed(main), keyed(control)
    if set(a) != set(b) or set(a) != {(2027,0),(2027,1)}:
        raise SystemExit("control identity cell set mismatch")
    for key in sorted(a):
        if a[key]["status"] != "complete" or b[key]["status"] != "complete":
            raise SystemExit(f"identity cell failed: {key}")
        exp = IDENTITY[key[1]]
        for report in (a[key], b[key]):
            if report["scores"] != exp["scores"] or report["trace_sha256"] != exp["trace_sha256"]:
                raise SystemExit(f"identity receipt drift: {key}")
        if a[key]["scores"] != b[key]["scores"] or a[key]["trace_sha256"] != b[key]["trace_sha256"]:
            raise SystemExit(f"control wrapper is not exact-main identical: {key}")

def compare(control: dict, candidate: dict) -> dict:
    a, b = keyed(control), keyed(candidate)
    if set(a) != set(b):
        raise SystemExit("panel cell sets differ")
    rows = []
    for key in sorted(a):
        cg, hg = a[key], b[key]
        if cg["status"] != "complete" or hg["status"] != "complete":
            raise SystemExit(f"incomplete panel cell: {key}")
        seat = key[1]
        co, cr = cg["scores"][seat], cg["scores"][1-seat]
        ho, hr = hg["scores"][seat], hg["scores"][1-seat]
        rows.append({"seed": key[0], "seat": seat,
                     "delta_own": ho-co, "delta_rival": hr-cr,
                     "delta_margin": (ho-hr)-(co-cr)})
    n = len(rows)
    summary = {
        "delta_own_mean": sum(r["delta_own"] for r in rows)/n,
        "delta_rival_mean": sum(r["delta_rival"] for r in rows)/n,
        "delta_margin_mean": sum(r["delta_margin"] for r in rows)/n,
        "positive": sum(r["delta_margin"] > 0 for r in rows),
        "zero": sum(r["delta_margin"] == 0 for r in rows),
        "negative": sum(r["delta_margin"] < 0 for r in rows),
    }
    if summary != EXPECTED_SUMMARY:
        raise SystemExit(f"summary drift: {summary} != {EXPECTED_SUMMARY}")
    return {"summary": summary, "cells": rows}

def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--package-tree", required=True, type=Path)
    p.add_argument("--out", type=Path, default=Path("h3-replay"))
    p.add_argument("--identity-only", action="store_true")
    args = p.parse_args()
    src = args.package_tree.resolve()
    for rel, expected in EXPECTED.items():
        require_hash(src, rel, expected)
    here = Path(__file__).resolve().parent
    for name, expected in WRAPPERS.items():
        require_hash(here, name, expected)
    args.out.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="h3-replay-") as td:
        root = Path(td) / "package"
        shutil.copytree(src, root)
        for name in WRAPPERS:
            shutil.copy2(here / name, root / name)
        main_report = run_eval(root, root / "main.py", [2027], args.out / "identity-main-2027.json")
        control_id = run_eval(root, root / "l3_control.py", [2027], args.out / "identity-control-2027.json")
        identity_check(main_report, control_id)
        print("CONTROL IDENTITY PASS: seed 2027, both seats, scores + trace SHA exact")
        if args.identity_only:
            return 0
        control = run_eval(root, root / "l3_control.py", SEEDS, args.out / "control-panel.json")
        candidate = run_eval(root, root / "l3_candidate.py", SEEDS, args.out / "candidate-panel.json")
        receipt = compare(control, candidate)
        (args.out / "paired-summary.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
        print("H3 GATE PASS", json.dumps(receipt["summary"], sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
