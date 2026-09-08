#!/usr/bin/env python3
"""Run resumable wide-field shards through the existing official evaluator."""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def valid_report(path: Path, expected: int) -> bool:
    if not path.is_file():
        return False
    try:
        report = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return False
    games = report.get("games", [])
    return len(games) == expected and all(g.get("status") == "complete" for g in games)


def run_job(job: dict, evaluator: Path, engine: Path, opponents: list[str], out: Path) -> dict:
    seeds = job["seeds"]
    target = out / "raw" / job["arm"] / (f"{seeds[0]}-{seeds[-1]}.json")
    log = out / "logs" / job["arm"] / (f"{seeds[0]}-{seeds[-1]}.log")
    target.parent.mkdir(parents=True, exist_ok=True)
    log.parent.mkdir(parents=True, exist_ok=True)
    expected = len(seeds) * len(opponents) * 2
    if valid_report(target, expected):
        return {**job, "status": "reused-complete", "report": str(target), "sha256": sha256(target)}
    cmd = [sys.executable, "-B", str(evaluator), "--engine-dir", str(engine),
           "--candidate", job["candidate"]]
    for opponent in opponents:
        cmd += ["--opponent", opponent]
    cmd += ["--seeds", ",".join(map(str, seeds)), "--output", str(target)]
    started = time.time()
    proc = subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    log.write_text(proc.stdout)
    complete = valid_report(target, expected)
    return {**job, "status": "complete" if complete and proc.returncode == 0 else "failed",
            "returncode": proc.returncode, "elapsed_seconds": time.time() - started,
            "report": str(target), "log": str(log),
            "sha256": sha256(target) if target.is_file() else None}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--jobs", type=int, default=4)
    args = ap.parse_args()
    cfg = json.loads(args.config.read_text())
    args.output.mkdir(parents=True, exist_ok=True)
    seeds = list(range(cfg["seeds"]["first"], cfg["seeds"]["last"] + 1))
    size = int(cfg["seeds"]["shard_size"])
    jobs = []
    for arm, candidate in cfg["arms"].items():
        for i in range(0, len(seeds), size):
            jobs.append({"arm": arm, "candidate": candidate, "seeds": seeds[i:i + size]})
    records = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.jobs) as pool:
        futures = [pool.submit(run_job, j, Path(cfg["evaluator"]), Path(cfg["engine"]),
                               cfg["opponents"], args.output) for j in jobs]
        for future in concurrent.futures.as_completed(futures):
            rec = future.result()
            records.append(rec)
            print(json.dumps(rec, sort_keys=True), flush=True)
            (args.output / "run-state.json").write_text(json.dumps(records, indent=2) + "\n")
    failed = [r for r in records if r["status"] == "failed"]
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
