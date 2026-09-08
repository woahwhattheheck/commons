#!/usr/bin/env python3
"""Run resumable wide-field shards through the existing official evaluator."""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
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



def write_run_state(path: Path, records: list[dict]) -> None:
    """Replace one complete UTF-8 checkpoint; never truncate the prior file.

    Staging and replacement share a directory. This is a single-file guarantee,
    not a transaction with raw reports or a power-loss durability guarantee.
    """
    payload = (json.dumps(records, indent=2) + "\n").encode("utf-8")
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="wb", dir=path.parent,
                                         prefix=f".{path.name}.", suffix=".tmp",
                                         delete=False) as stream:
            temporary = Path(stream.name)
            if stream.write(payload) != len(payload):
                raise OSError("Short run-state checkpoint write")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            try:
                temporary.unlink()
            except OSError:
                # Cleanup must not replace the original publication exception.
                # A hard exit or failed cleanup can leave an unreferenced stage.
                pass


def validate_panel_config(cfg: object, workers: int) -> None:
    """Require runnable panel dimensions before creating output or starting work.

    Additional configuration fields and all nonempty actor references pass through
    unchanged. This validates the requested job grid, not source or result identity.
    """
    if not isinstance(cfg, dict):
        raise ValueError("panel configuration must be a JSON object")
    seeds = cfg.get("seeds")
    if not isinstance(seeds, dict):
        raise ValueError("seeds must be an object with first, last and shard_size")
    first, last = seeds.get("first"), seeds.get("last")
    if type(first) is not int or type(last) is not int:
        raise ValueError("seeds.first and seeds.last must be integers")
    if first > last:
        raise ValueError("seeds.first must not exceed seeds.last")
    try:
        # Preserve the existing int-conversion behavior for nonempty shards.
        size = int(seeds["shard_size"])
    except (KeyError, TypeError, ValueError, OverflowError):
        raise ValueError("seeds.shard_size must convert to a positive integer") from None
    if size <= 0:
        raise ValueError("seeds.shard_size must convert to a positive integer")
    arms = cfg.get("arms")
    if not isinstance(arms, dict) or not arms:
        raise ValueError("arms must contain at least one candidate")
    if any(not isinstance(value, str) or not value.strip() for value in arms.values()):
        raise ValueError("each candidate reference must be a nonempty string")
    opponents = cfg.get("opponents")
    if not isinstance(opponents, list) or not opponents:
        raise ValueError("opponents must contain at least one opponent")
    if any(not isinstance(value, str) or not value.strip() for value in opponents):
        raise ValueError("each opponent reference must be a nonempty string")
    for field in ("evaluator", "engine"):
        if not isinstance(cfg.get(field), str) or not cfg[field].strip():
            raise ValueError(f"{field} must be a nonempty string")
    if type(workers) is not int or workers <= 0:
        raise ValueError("--jobs must be a positive integer")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--jobs", type=int, default=4)
    args = ap.parse_args()
    try:
        cfg = json.loads(args.config.read_text())
        validate_panel_config(cfg, args.jobs)
    except (OSError, UnicodeError, ValueError) as error:
        ap.error(f"invalid panel configuration: {error}")
    args.output.mkdir(parents=True, exist_ok=True)
    seeds = list(range(cfg["seeds"]["first"], cfg["seeds"]["last"] + 1))
    size = int(cfg["seeds"]["shard_size"])
    jobs = []
    for arm, candidate in cfg["arms"].items():
        for i in range(0, len(seeds), size):
            jobs.append({"arm": arm, "candidate": candidate, "seeds": seeds[i:i + size]})
    records = []
    first_failure = None
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.jobs) as pool:
        futures = {pool.submit(run_job, j, Path(cfg["evaluator"]), Path(cfg["engine"]),
                               cfg["opponents"], args.output): j for j in jobs}
        for future in concurrent.futures.as_completed(futures):
            try:
                rec = future.result()
            except Exception as exc:
                # All jobs were already submitted. Retain their results before
                # re-raising the first ordinary failure; do not retry any job.
                # BaseException cancellation is deliberately not converted.
                if first_failure is None:
                    first_failure = (exc, exc.__traceback__)
                rec = {**futures[future], "status": "failed",
                       "failure": {"kind": "runner_exception",
                                   "type": type(exc).__name__, "message": str(exc)}}
            records.append(rec)
            try:
                write_run_state(args.output / "run-state.json", records)
            except Exception as output_error:
                if first_failure is not None:
                    error, traceback = first_failure
                    raise error.with_traceback(traceback) from output_error
                raise
            print(json.dumps(rec, sort_keys=True), flush=True)
    if first_failure is not None:
        error, traceback = first_failure
        raise error.with_traceback(traceback)
    failed = [r for r in records if r["status"] == "failed"]
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
