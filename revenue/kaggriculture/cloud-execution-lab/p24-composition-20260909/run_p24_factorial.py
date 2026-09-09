#!/usr/bin/env python3
"""Run a fail-closed 2^4 configuration factorial from one immutable TITAN archive."""
from __future__ import annotations

import argparse
import importlib.util
import json
import math
from pathlib import Path
import sys
import tempfile
import time

import p24_factorial as p24

ENGINE_REF = "28b6d8af3ce73926b3d0fda1410c1ddd8384ab8c"
OPERATION = "op:titan-v25-orders-20260909-P24"


def import_file(path: Path):
    spec = importlib.util.spec_from_file_location("titan_p24_evaluator", path)
    if spec is None or spec.loader is None:
        raise ValueError(f"Cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def opponent_specs(items, runtime: Path):
    output = {}
    for item in items:
        label, separator, value = item.partition("=")
        if not separator or not label or label in output:
            raise ValueError("Each opponent must be a unique LABEL=SPEC")
        if value.startswith("runtime:"):
            relative = value.removeprefix("runtime:")
            path, call_separator, callable_name = relative.partition("::")
            value = str((runtime / path).resolve(strict=True)) + ("::" + callable_name if call_separator else "")
        elif value != "official_starter":
            path, call_separator, callable_name = value.partition("::")
            value = str(Path(path).resolve(strict=True)) + ("::" + callable_name if call_separator else "")
        output[label] = value
    if not output:
        raise ValueError("At least one --opponent is required")
    return output


def run(args):
    archive = args.archive.resolve(strict=True)
    archive_sha, archive_bytes = p24.sha256_file(archive), archive.stat().st_size
    if args.expected_archive_sha256 and archive_sha != args.expected_archive_sha256:
        raise AssertionError(f"Archive SHA mismatch: {archive_sha}")
    if args.expected_archive_bytes is not None and archive_bytes != args.expected_archive_bytes:
        raise AssertionError(f"Archive size mismatch: {archive_bytes}")
    seeds = [int(value.strip()) for value in args.seeds.split(",") if value.strip()]
    if not seeds or len(seeds) != len(set(seeds)):
        raise ValueError("--seeds requires distinct integers")
    started = time.time()
    with tempfile.TemporaryDirectory(prefix="titan-p24-") as directory:
        work = Path(directory); runtime = work / "runtime"
        members = p24.safe_extract(archive, runtime)
        if args.expected_member_count is not None and len(members) != args.expected_member_count:
            raise AssertionError(f"Archive member count mismatch: {len(members)}")
        source = runtime / "SOURCE.json"
        source_sha = p24.sha256_file(source)
        if args.expected_source_sha256 and source_sha != args.expected_source_sha256:
            raise AssertionError(f"SOURCE.json SHA mismatch: {source_sha}")
        matrix, config = p24.prepare_variants(runtime, work / "variants")
        opponents = opponent_specs(args.opponent, runtime)
        evaluator_path = runtime / "checks/reference/evaluator/evaluate.py"
        loader = runtime / "checks/reference/evaluator/loader.py"
        engine_dir = runtime / "checks/reference/engine"
        required = [evaluator_path, loader, *(engine_dir / name for name in ("kaggriculture.py", "kaggriculture.json", "utils.py"))]
        for path in required:
            if not path.exists():
                raise FileNotFoundError(f"Missing evaluator input: {path.relative_to(runtime)}")
        evaluator = import_file(evaluator_path)
        if evaluator.ENGINE_REF != ENGINE_REF:
            raise AssertionError(f"Engine ref drift: {evaluator.ENGINE_REF}")
        engine, engine_hashes = evaluator.get_engine(engine_dir, loader)
        games = []
        for variant in matrix:
            for opponent, rival in opponents.items():
                for seed in seeds:
                    for seat in (0, 1):
                        pair = [variant["candidate"], rival] if seat == 0 else [rival, variant["candidate"]]
                        game = evaluator.play(engine, pair, engine_dir, loader, seed, seat, args.agent_rng_seed,
                                              args.action_timeout, args.startup_timeout, args.game_timeout, None)
                        row = {"variant": variant["name"], "opponent": opponent, **game}; games.append(row)
                        print(json.dumps({key: row.get(key) for key in
                                         ("variant", "opponent", "seed", "candidate_seat", "status", "scores", "failure")},
                                         sort_keys=True), flush=True)
                        if game.get("status") != "complete" or game.get("failure") is not None:
                            p24.write_json(args.output, {"schema_version": 1, "operation": OPERATION,
                                                       "dispatch_commit": args.dispatch_commit,
                                                       "archive_sha256": archive_sha, "status": "failed",
                                                       "failed_cell": row, "completed_or_failed_rows": games})
                            raise RuntimeError(f"Fail-closed game failure: {variant['name']}/{opponent}/{seed}/seat{seat}")
        p24.validate_games(games, matrix, list(opponents), seeds)
        summary = p24.summarize(games, matrix)
        report = {"schema_version": 1, "operation": OPERATION, "dispatch_commit": args.dispatch_commit,
                  "archive": {"path": str(archive), "sha256": archive_sha, "bytes": archive_bytes,
                              "member_count": len(members), "source_manifest_sha256": source_sha},
                  "engine": {"ref": ENGINE_REF, "sha256": engine_hashes,
                             "evaluator_sha256": p24.sha256_file(evaluator_path),
                             "loader_sha256": p24.sha256_file(loader)},
                  "method": "Pinned official interpreter; process-isolated agents; one archive; configuration-only 2^4 matched cells; offline; not hosted scoring.",
                  "factors": list(p24.FACTORS), "base_config": config,
                  "variants": [{key: value for key, value in row.items() if key != "candidate"} for row in matrix],
                  "opponents": list(opponents), "opponent_specs": opponents, "seeds": seeds,
                  "agent_rng_seed": args.agent_rng_seed,
                  "limits": {"action_timeout_seconds": args.action_timeout, "startup_timeout_seconds": args.startup_timeout,
                             "game_timeout_seconds": args.game_timeout},
                  "scheduled_games": len(games), "all_complete": True, "summary": summary, "games": games,
                  "wall_seconds": time.time() - started, "python": sys.version, "platform": sys.platform}
        p24.write_json(args.output, report)
        args.markdown.parent.mkdir(parents=True, exist_ok=True)
        args.markdown.write_text(p24.markdown(report), encoding="utf-8")
        print("P24_SUMMARY " + json.dumps(summary["joint_vs_baseline"], sort_keys=True), flush=True)
        return report


def parser():
    value = argparse.ArgumentParser(description=__doc__)
    value.add_argument("--archive", type=Path, required=True)
    value.add_argument("--expected-archive-sha256")
    value.add_argument("--expected-archive-bytes", type=int)
    value.add_argument("--expected-member-count", type=int)
    value.add_argument("--expected-source-sha256")
    value.add_argument("--dispatch-commit", required=True)
    value.add_argument("--seeds", required=True)
    value.add_argument("--opponent", action="append", default=[])
    value.add_argument("--agent-rng-seed", type=int, default=20260909)
    value.add_argument("--action-timeout", type=float, default=1.0)
    value.add_argument("--startup-timeout", type=float, default=10.0)
    value.add_argument("--game-timeout", type=float, default=120.0)
    value.add_argument("--output", type=Path, required=True)
    value.add_argument("--markdown", type=Path, required=True)
    return value


def main():
    args = parser().parse_args()
    if any(not math.isfinite(value) or value <= 0 for value in
           (args.action_timeout, args.startup_timeout, args.game_timeout)):
        raise SystemExit("Timeouts must be finite and positive")
    run(args)


if __name__ == "__main__":
    main()
