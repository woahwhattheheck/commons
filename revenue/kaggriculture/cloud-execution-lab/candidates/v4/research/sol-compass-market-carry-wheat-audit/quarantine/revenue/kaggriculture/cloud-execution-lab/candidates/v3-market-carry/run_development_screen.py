#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Run a source-bound matched development screen for V3 market carry."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import re
import sys
import time
import traceback
from typing import Any


ENGINE_REF = "28b6d8af3ce73926b3d0fda1410c1ddd8384ab8c"
OPERATION = "op:titan-v3-market-carry-20260909-01"
DEVELOPMENT_SEEDS = {2609099701, 2609099702}
HEX40 = re.compile(r"^[0-9a-f]{40}$")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def tree_digest(root: Path) -> dict[str, Any]:
    files = sorted(
        path for path in root.rglob("*") if path.is_file() and not path.is_symlink()
    )
    digest = hashlib.sha256()
    rows = []
    for path in files:
        relative = path.relative_to(root).as_posix()
        file_sha = sha256_file(path)
        rows.append({"path": relative, "sha256": file_sha, "bytes": path.stat().st_size})
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(file_sha.encode("ascii"))
        digest.update(b"\n")
    return {"sha256": digest.hexdigest(), "files": rows}


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    temporary.replace(path)


def import_file(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def outcome(margin: int) -> str:
    return "W" if margin > 0 else ("T" if margin == 0 else "L")


def finite_scores(game: dict[str, Any]) -> list[int]:
    scores = game.get("scores")
    if not isinstance(scores, list) or len(scores) != 2:
        raise ValueError(f"invalid scores: {scores!r}")
    if any(
        isinstance(score, bool)
        or not isinstance(score, (int, float))
        or not math.isfinite(score)
        or int(score) != score
        for score in scores
    ):
        raise ValueError(f"non-integral/nonfinite scores: {scores!r}")
    return [int(score) for score in scores]


def summarize(games: list[dict[str, Any]], seeds: list[int]) -> dict[str, Any]:
    expected = {
        (arm, seed, seat)
        for arm in ("control", "candidate")
        for seed in seeds
        for seat in (0, 1)
    }
    actual = {
        (row["arm"], int(row["seed"]), int(row["candidate_seat"])) for row in games
    }
    if actual != expected or len(actual) != len(games):
        raise AssertionError(
            f"incomplete/duplicate matrix: missing={sorted(expected-actual)} "
            f"extra={sorted(actual-expected)}"
        )
    lookup = {
        (row["arm"], int(row["seed"]), int(row["candidate_seat"])): row
        for row in games
    }
    pairs = []
    arm_stats = {
        arm: {"games": 0, "W": 0, "T": 0, "L": 0, "own_scores": [], "margins": []}
        for arm in ("control", "candidate")
    }
    for seed in seeds:
        for seat in (0, 1):
            rows = {
                arm: lookup[(arm, seed, seat)] for arm in ("control", "candidate")
            }
            values = {}
            for arm, row in rows.items():
                scores = finite_scores(row)
                own, rival = scores[seat], scores[1 - seat]
                margin = own - rival
                values[arm] = {
                    "own_score": own,
                    "rival_score": rival,
                    "margin": margin,
                    "outcome": outcome(margin),
                    "trace_sha256": row.get("trace_sha256"),
                }
                stats = arm_stats[arm]
                stats["games"] += 1
                stats[values[arm]["outcome"]] += 1
                stats["own_scores"].append(own)
                stats["margins"].append(margin)
            pairs.append(
                {
                    "seed": seed,
                    "seat": seat,
                    **values,
                    "own_score_delta": (
                        values["candidate"]["own_score"]
                        - values["control"]["own_score"]
                    ),
                    "rival_score_delta": (
                        values["candidate"]["rival_score"]
                        - values["control"]["rival_score"]
                    ),
                    "margin_delta": (
                        values["candidate"]["margin"] - values["control"]["margin"]
                    ),
                    "outcome_flip": (
                        values["control"]["outcome"]
                        + "->"
                        + values["candidate"]["outcome"]
                    ),
                }
            )
    for stats in arm_stats.values():
        own = stats.pop("own_scores")
        margins = stats.pop("margins")
        stats["mean_own_score"] = sum(own) / len(own)
        stats["mean_margin"] = sum(margins) / len(margins)

    own_deltas = [row["own_score_delta"] for row in pairs]
    margin_deltas = [row["margin_delta"] for row in pairs]
    regressive_flips = [
        row for row in pairs
        if row["control"]["outcome"] == "W"
        and row["candidate"]["outcome"] != "W"
    ]
    return {
        "pairs": pairs,
        "arms": arm_stats,
        "paired": {
            "cells": len(pairs),
            "mean_own_score_delta": sum(own_deltas) / len(own_deltas),
            "mean_margin_delta": sum(margin_deltas) / len(margin_deltas),
            "min_own_score_delta": min(own_deltas),
            "max_own_score_delta": max(own_deltas),
            "min_margin_delta": min(margin_deltas),
            "max_margin_delta": max(margin_deltas),
            "positive_own_cells": sum(delta > 0 for delta in own_deltas),
            "negative_own_cells": sum(delta < 0 for delta in own_deltas),
            "changed_trace_cells": sum(
                row["control"]["trace_sha256"]
                != row["candidate"]["trace_sha256"]
                for row in pairs
            ),
            "regressive_win_flips": len(regressive_flips),
            "development_signal": (
                sum(own_deltas) > 0
                and sum(margin_deltas) > 0
                and not regressive_flips
            ),
        },
    }


def markdown(receipt: dict[str, Any]) -> str:
    summary = receipt.get("summary") or {}
    paired = summary.get("paired") or {}
    lines = [
        "# TITAN V3 market-carry development screen",
        "",
        f"- Status: `{receipt.get('status')}`",
        f"- Runner head: `{receipt.get('runner_head')}`",
        f"- Seeds: `{','.join(map(str, receipt.get('seeds', [])))}`",
        f"- Complete games: `{len(receipt.get('games', []))}/{receipt.get('expected_games')}`",
    ]
    if paired:
        lines += [
            f"- Mean own-score delta: `{paired.get('mean_own_score_delta')}`",
            f"- Mean margin delta: `{paired.get('mean_margin_delta')}`",
            f"- Changed-trace cells: `{paired.get('changed_trace_cells')}`",
            f"- Regressive W→non-W flips: `{paired.get('regressive_win_flips')}`",
            f"- Development signal: `{paired.get('development_signal')}`",
            "",
            "| seed | seat | control own | candidate own | own Δ | margin Δ | flip |",
            "|---:|---:|---:|---:|---:|---:|:---|",
        ]
        for row in summary["pairs"]:
            lines.append(
                f"| {row['seed']} | {row['seat']} | "
                f"{row['control']['own_score']} | {row['candidate']['own_score']} | "
                f"{row['own_score_delta']} | {row['margin_delta']} | "
                f"{row['outcome_flip']} |"
            )
    lines += [
        "",
        "This is a tiny public development screen, not held evidence, a "
        "generalized strength estimate, or a Kaggle/leaderboard claim.",
        "",
    ]
    return "\n".join(lines)


def run(args: argparse.Namespace) -> dict[str, Any]:
    started = time.time()
    receipt: dict[str, Any] = {
        "schema_version": 1,
        "operation": OPERATION,
        "status": "initializing",
        "runner_head": args.runner_head,
        "seeds": [],
        "expected_games": 0,
        "completed_keys": [],
        "games": [],
    }
    try:
        if not HEX40.fullmatch(args.runner_head):
            raise ValueError("--runner-head must be a lowercase 40-hex commit")
        repo = args.repo_root.resolve(strict=True)
        lab = repo / "revenue/kaggriculture/cloud-execution-lab"
        candidate_dir = lab / "candidates/v3-market-carry"
        candidate = candidate_dir / "main.py"
        control = lab / "main.py"
        opponent = lab / "reference/next-panel/vendor/arlene.py"
        evaluator_path = lab / "reference/evaluator/evaluate.py"
        loader = lab / "reference/evaluator/loader.py"
        engine_dir = lab / "reference/engine"
        archive = lab / "exports/titan-current.tar.gz"
        source_manifest = lab / "runtime/integrated-selected/CURRENT-SOURCE.json"
        config = lab / "TITAN-CONFIG.json"
        required = [
            candidate,
            candidate_dir / "market_carry.py",
            control,
            opponent,
            evaluator_path,
            loader,
            archive,
            source_manifest,
            config,
            *(engine_dir / name for name in (
                "kaggriculture.py", "kaggriculture.json", "utils.py"
            )),
        ]
        missing = [str(path.relative_to(repo)) for path in required if not path.is_file()]
        if missing:
            raise FileNotFoundError(f"missing source-bound inputs: {missing}")

        seeds = [int(value.strip()) for value in args.seeds.split(",") if value.strip()]
        if not seeds or len(seeds) != len(set(seeds)):
            raise ValueError("--seeds must contain distinct integers")
        bad = [seed for seed in seeds if seed not in DEVELOPMENT_SEEDS]
        if bad:
            raise ValueError(f"non-development seed(s): {bad}")

        evaluator = import_file("_titan_market_carry_evaluator", evaluator_path)
        if evaluator.ENGINE_REF != ENGINE_REF:
            raise AssertionError(f"engine ref drift: {evaluator.ENGINE_REF}")
        engine, engine_hashes = evaluator.get_engine(engine_dir, loader)
        specs = {
            "control": str(control.resolve()) + "::agent",
            "candidate": str(candidate.resolve()) + "::agent",
        }
        opponent_spec = str(opponent.resolve()) + "::agent"
        source_evidence = {
            "candidate_main": sha256_file(candidate),
            "market_carry": sha256_file(candidate_dir / "market_carry.py"),
            "control_main": sha256_file(control),
            "config": sha256_file(config),
            "archive": {
                "sha256": sha256_file(archive),
                "bytes": archive.stat().st_size,
            },
            "source_manifest": sha256_file(source_manifest),
            "evaluator": sha256_file(evaluator_path),
            "loader": sha256_file(loader),
            "engine": engine_hashes,
            "opponent_bundle": tree_digest(opponent.parent),
        }
        expected = [
            [arm, seed, seat]
            for seed in seeds
            for seat in (0, 1)
            for arm in ("control", "candidate")
        ]
        receipt.update(
            {
                "status": "running",
                "repo_root": str(repo),
                "lab_root": str(lab),
                "engine_ref": ENGINE_REF,
                "source_evidence": source_evidence,
                "seeds": seeds,
                "opponent": "exact_public_arlene",
                "agent_rng_seed": args.agent_rng_seed,
                "limits": {
                    "action_timeout_seconds": args.action_timeout,
                    "startup_timeout_seconds": args.startup_timeout,
                    "game_timeout_seconds": args.game_timeout,
                },
                "expected_keys": expected,
                "expected_games": len(expected),
                "method": (
                    "Pinned official interpreter; process-isolated agents; "
                    "same public opponent/seed/seat for current control and "
                    "append-only candidate."
                ),
            }
        )
        write_json(args.output, receipt)

        for seed in seeds:
            for seat in (0, 1):
                for arm in ("control", "candidate"):
                    key = [arm, seed, seat]
                    receipt["running_key"] = key
                    write_json(args.output, receipt)
                    pair = (
                        [specs[arm], opponent_spec]
                        if seat == 0
                        else [opponent_spec, specs[arm]]
                    )
                    game = evaluator.play(
                        engine,
                        pair,
                        engine_dir,
                        loader,
                        seed,
                        seat,
                        args.agent_rng_seed,
                        args.action_timeout,
                        args.startup_timeout,
                        args.game_timeout,
                        None,
                    )
                    row = {"arm": arm, "opponent": "exact_public_arlene", **game}
                    receipt["games"].append(row)
                    receipt["wall_seconds"] = time.time() - started
                    if (
                        game.get("status") != "complete"
                        or game.get("failure") is not None
                    ):
                        receipt["status"] = "failed"
                        receipt["failed_cell"] = row
                        write_json(args.output, receipt)
                        raise RuntimeError(f"game failed closed: {key}")
                    finite_scores(game)
                    receipt["completed_keys"].append(key)
                    receipt.pop("running_key", None)
                    write_json(args.output, receipt)
                    print(
                        json.dumps(
                            {
                                "arm": arm,
                                "seed": seed,
                                "seat": seat,
                                "scores": game["scores"],
                                "trace_sha256": game.get("trace_sha256"),
                            },
                            sort_keys=True,
                        ),
                        flush=True,
                    )

        receipt["summary"] = summarize(receipt["games"], seeds)
        receipt["status"] = "complete"
        receipt["all_complete"] = True
        receipt["wall_seconds"] = time.time() - started
        write_json(args.output, receipt)
        args.markdown.parent.mkdir(parents=True, exist_ok=True)
        args.markdown.write_text(markdown(receipt), encoding="utf-8")
        print(
            "MARKET_CARRY_SUMMARY "
            + json.dumps(receipt["summary"]["paired"], sort_keys=True),
            flush=True,
        )
        return receipt
    except BaseException as exc:
        receipt["status"] = "failed"
        receipt["failure"] = {
            "type": type(exc).__name__,
            "message": str(exc)[:2000],
            "traceback": traceback.format_exc()[-4000:],
        }
        receipt["wall_seconds"] = time.time() - started
        try:
            write_json(args.output, receipt)
        finally:
            raise


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description=__doc__)
    value.add_argument("--repo-root", type=Path, required=True)
    value.add_argument("--runner-head", required=True)
    value.add_argument("--seeds", default="2609099701,2609099702")
    value.add_argument("--agent-rng-seed", type=int, default=20260909)
    value.add_argument("--action-timeout", type=float, default=1.0)
    value.add_argument("--startup-timeout", type=float, default=10.0)
    value.add_argument("--game-timeout", type=float, default=180.0)
    value.add_argument("--output", type=Path, required=True)
    value.add_argument("--markdown", type=Path, required=True)
    return value


def main() -> None:
    args = parser().parse_args()
    if any(
        not math.isfinite(value) or value <= 0
        for value in (
            args.action_timeout,
            args.startup_timeout,
            args.game_timeout,
        )
    ):
        raise SystemExit("timeouts must be finite and positive")
    run(args)


if __name__ == "__main__":
    main()
