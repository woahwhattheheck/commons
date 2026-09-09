#!/usr/bin/env python3
"""Faithful S24 champion-freeze sharder over the pinned official evaluator.

The evaluator itself is never edited. Each shard launches an independent evaluator
process on disjoint seeds; candidate/opponent paths are supplied by the caller.
S24 is fail-closed: every scheduled game must complete for exit status 0.
Exact scheduled identity (opponent, seed, candidate_seat) is enforced, not only
aggregate cardinality.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path


def split_seeds(seeds: list[int], workers: int) -> list[list[int]]:
    buckets = [[] for _ in range(max(1, min(workers, len(seeds))))]
    for index, seed in enumerate(seeds):
        buckets[index % len(buckets)].append(seed)
    return [bucket for bucket in buckets if bucket]


def expected_keys(seeds: list[int], opponents: list[str]) -> set[tuple[str, int, int]]:
    keys: set[tuple[str, int, int]] = set()
    for opponent in opponents:
        for seed in seeds:
            for seat in (0, 1):
                keys.add((opponent, seed, seat))
    return keys


def run_shard(
    index: int,
    seeds: list[int],
    opponents: list[tuple[str, str]],
    output_dir: Path,
    python: str,
    evaluator: str,
    engine_dir: str,
    loader: str,
    candidate: str,
    action_timeout: float,
    startup_timeout: float,
    game_timeout: float,
) -> dict:
    output_path = output_dir / f"shard-{index:02d}.json"
    command = [
        python,
        "-B",
        evaluator,
        "--engine-dir",
        engine_dir,
        "--loader",
        loader,
        "--candidate",
        candidate,
        "--seeds",
        ",".join(str(seed) for seed in seeds),
        "--action-timeout",
        str(action_timeout),
        "--startup-timeout",
        str(startup_timeout),
        "--game-timeout",
        str(game_timeout),
        "--output",
        str(output_path),
    ]
    for name, spec in opponents:
        command.extend(["--opponent", f"{name}={spec}"])

    started = time.monotonic()
    process = subprocess.run(command, capture_output=True, text=True)
    elapsed = time.monotonic() - started
    games: list[dict] = []
    parse_errors: list[str] = []
    for line in process.stdout.splitlines():
        if not line.startswith('{"opponent"'):
            continue
        try:
            games.append(json.loads(line))
        except json.JSONDecodeError as error:
            parse_errors.append(f"{error}: {line[:500]}")
    return {
        "shard": index,
        "seeds": seeds,
        "seconds": round(elapsed, 3),
        "returncode": process.returncode,
        "games": games,
        "parse_errors": parse_errors,
        "stderr_tail": process.stderr[-8000:],
        "stdout_tail": process.stdout[-8000:],
    }


def aggregate(games: list[dict], opponents: list[str]) -> dict:
    by_opponent: dict[str, dict] = {}
    all_margins: list[float] = []
    for opponent in opponents:
        rows = [g for g in games if g.get("opponent") == opponent and g.get("status") == "complete"]
        margins: list[float] = []
        seats = {"0": 0, "1": 0}
        for game in rows:
            seat = int(game["candidate_seat"])
            scores = game["scores"]
            margin = float(scores[seat]) - float(scores[1 - seat])
            margins.append(margin)
            all_margins.append(margin)
            seats[str(seat)] += 1
        by_opponent[opponent] = {
            "games": len(rows),
            "W": sum(m > 0 for m in margins),
            "T": sum(m == 0 for m in margins),
            "L": sum(m < 0 for m in margins),
            "seat_games": seats,
            "mean_margin": round(sum(margins) / len(margins), 6) if margins else None,
            "min_margin": min(margins) if margins else None,
            "max_margin": max(margins) if margins else None,
        }
    return {
        "per_opponent": by_opponent,
        "overall": {
            "games": len(all_margins),
            "W": sum(m > 0 for m in all_margins),
            "T": sum(m == 0 for m in all_margins),
            "L": sum(m < 0 for m in all_margins),
            "mean_margin": round(sum(all_margins) / len(all_margins), 6) if all_margins else None,
            "min_margin": min(all_margins) if all_margins else None,
            "max_margin": max(all_margins) if all_margins else None,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--python", required=True)
    parser.add_argument("--evaluator", required=True)
    parser.add_argument("--engine-dir", required=True)
    parser.add_argument("--loader", required=True)
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--seeds", required=True)
    parser.add_argument("--opponent", action="append", required=True, help="name=module.py::agent")
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--action-timeout", type=float, default=15.0)
    parser.add_argument("--startup-timeout", type=float, default=60.0)
    parser.add_argument("--game-timeout", type=float, default=1800.0)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    seeds = [int(value) for value in args.seeds.split(",") if value]
    opponents: list[tuple[str, str]] = []
    for raw in args.opponent:
        if "=" not in raw:
            parser.error(f"invalid --opponent {raw!r}")
        name, spec = raw.split("=", 1)
        opponents.append((name, spec))
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    groups = split_seeds(seeds, args.workers)
    started = time.monotonic()
    shard_results: list[dict] = []
    with ThreadPoolExecutor(max_workers=len(groups)) as executor:
        futures = [
            executor.submit(
                run_shard,
                index,
                group,
                opponents,
                output_dir,
                args.python,
                args.evaluator,
                args.engine_dir,
                args.loader,
                args.candidate,
                args.action_timeout,
                args.startup_timeout,
                args.game_timeout,
            )
            for index, group in enumerate(groups)
        ]
        for future in as_completed(futures):
            shard_results.append(future.result())
    wall_seconds = time.monotonic() - started
    shard_results.sort(key=lambda row: row["shard"])
    games = [game for shard in shard_results for game in shard["games"]]
    games.sort(key=lambda g: (str(g.get("opponent")), int(g.get("seed", -1)), int(g.get("candidate_seat", -1))))

    opponent_names = [name for name, _ in opponents]
    expected = len(seeds) * len(opponents) * 2
    expected_key_set = expected_keys(seeds, opponent_names)

    # Exact scheduled identity: reject duplicates, unexpected, missing keys.
    observed_keys: list[tuple[str, int, int]] = []
    key_errors: list[str] = []
    for game in games:
        try:
            key = (str(game["opponent"]), int(game["seed"]), int(game["candidate_seat"]))
        except (KeyError, TypeError, ValueError) as err:
            key_errors.append(f"malformed game record: {err}")
            continue
        observed_keys.append(key)
    observed_key_set = set(observed_keys)
    if len(observed_keys) != len(observed_key_set):
        key_errors.append(
            f"duplicate keys: observed {len(observed_keys)} rows but {len(observed_key_set)} unique "
            f"(opponent, seed, candidate_seat)"
        )
    missing = sorted(expected_key_set - observed_key_set)
    unexpected = sorted(observed_key_set - expected_key_set)
    if missing:
        key_errors.append(f"missing scheduled keys ({len(missing)}): {missing[:20]}")
    if unexpected:
        key_errors.append(f"unexpected keys ({len(unexpected)}): {unexpected[:20]}")

    # Per-shard seed bucket: each shard's observed seeds must be subset of its assigned seeds.
    for shard in shard_results:
        assigned = set(shard["seeds"])
        observed_seeds = {int(g.get("seed", -1)) for g in shard["games"] if "seed" in g}
        extra = sorted(observed_seeds - assigned)
        if extra:
            key_errors.append(f"shard {shard['shard']} observed seeds outside assigned bucket: {extra}")

    complete = [game for game in games if game.get("status") == "complete"]
    incomplete = [game for game in games if game.get("status") != "complete"]
    shard_failures = [
        {
            "shard": shard["shard"],
            "returncode": shard["returncode"],
            "parse_errors": shard["parse_errors"],
            "stderr_tail": shard["stderr_tail"],
        }
        for shard in shard_results
        if shard["returncode"] != 0 or shard["parse_errors"]
    ]
    summary = {
        "schema": "titan-s24-champion-freeze-h-v1",
        "scheduled": expected,
        "observed_records": len(games),
        "completed": len(complete),
        "incomplete": len(incomplete),
        "missing": max(0, expected - len(games)),
        "workers": len(groups),
        "wall_seconds": round(wall_seconds, 3),
        "throughput_games_per_min": round(len(games) / (wall_seconds / 60.0), 3) if wall_seconds else None,
        "seeds": seeds,
        "opponents": opponent_names,
        "shard_seconds": [row["seconds"] for row in shard_results],
        "shard_failures": shard_failures,
        "incomplete_games": incomplete,
        "key_errors": key_errors,
        **aggregate(games, opponent_names),
    }
    (output_dir / "GAMES.jsonl").write_text("".join(json.dumps(game, sort_keys=True) + "\n" for game in games), encoding="utf-8")
    (output_dir / "SUMMARY.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (output_dir / "SHARDS.json").write_text(json.dumps(shard_results, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("S24_SUMMARY=" + json.dumps(summary, sort_keys=True), flush=True)

    success = (
        len(complete) == expected
        and len(games) == expected
        and not incomplete
        and not shard_failures
        and not key_errors
        and observed_key_set == expected_key_set
        and all(
            row["games"] == len(seeds) * 2
            and row["seat_games"] == {"0": len(seeds), "1": len(seeds)}
            for row in summary["per_opponent"].values()
        )
    )
    if not success:
        sys.stderr.write(
            f"S24 FAIL-CLOSED: expected={expected} observed={len(games)} complete={len(complete)} "
            f"incomplete={len(incomplete)} shard_failures={len(shard_failures)} key_errors={len(key_errors)}\n"
        )
        for err in key_errors[:10]:
            sys.stderr.write(f"  {err}\n")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
