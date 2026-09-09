#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Source-bound paired smoke for the exact-prefix seller-ledger candidate."""
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
from typing import Any

ENGINE_REF = "28b6d8af3ce73926b3d0fda1410c1ddd8384ab8c"
OPERATION = "op:titan-v3-frozen-seller-phantom-tail-ledger-20260909-01"
DEVELOPMENT_SEEDS = {2609099901, 2609099902}
HEX40 = re.compile(r"^[0-9a-f]{40}$")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def tree_digest(root: Path) -> dict[str, Any]:
    rows = []
    digest = hashlib.sha256()
    for path in sorted(p for p in root.rglob("*")
                       if p.is_file() and not p.is_symlink()
                       and "__pycache__" not in p.parts and p.suffix != ".pyc"):
        relative = path.relative_to(root).as_posix()
        file_sha = sha256_file(path)
        rows.append({"path": relative, "sha256": file_sha, "bytes": path.stat().st_size})
        digest.update(relative.encode())
        digest.update(b"\0")
        digest.update(file_sha.encode())
        digest.update(b"\n")
    return {"sha256": digest.hexdigest(), "files": rows}


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def import_file(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def finite_scores(row: dict[str, Any]) -> tuple[int, int]:
    scores = row.get("scores")
    if not isinstance(scores, list) or len(scores) != 2:
        raise ValueError(f"invalid scores: {scores!r}")
    result = []
    for score in scores:
        if isinstance(score, bool) or not isinstance(score, (int, float)):
            raise ValueError(f"invalid score: {score!r}")
        if not math.isfinite(score) or int(score) != score:
            raise ValueError(f"nonfinite/nonintegral score: {score!r}")
        result.append(int(score))
    return result[0], result[1]


def outcome(margin: int) -> str:
    return "W" if margin > 0 else ("T" if margin == 0 else "L")


def summarize(games: list[dict[str, Any]], seeds: list[int]) -> dict[str, Any]:
    expected = {(arm, seed, seat) for arm in ("control", "candidate")
                for seed in seeds for seat in (0, 1)}
    keys = [(row["arm"], int(row["seed"]), int(row["candidate_seat"])) for row in games]
    if set(keys) != expected or len(keys) != len(set(keys)):
        raise ValueError("incomplete, duplicate, or extra result cells")
    lookup = {(row["arm"], int(row["seed"]), int(row["candidate_seat"])): row
              for row in games}
    pairs = []
    for seed in seeds:
        for seat in (0, 1):
            values = {}
            for arm in ("control", "candidate"):
                row = lookup[(arm, seed, seat)]
                left, right = finite_scores(row)
                own, rival = (left, right) if seat == 0 else (right, left)
                margin = own - rival
                values[arm] = {
                    "own": own,
                    "rival": rival,
                    "margin": margin,
                    "outcome": outcome(margin),
                    "trace_sha256": row.get("trace_sha256"),
                }
            pairs.append({
                "seed": seed,
                "seat": seat,
                "control": values["control"],
                "candidate": values["candidate"],
                "own_delta": values["candidate"]["own"] - values["control"]["own"],
                "margin_delta": values["candidate"]["margin"] - values["control"]["margin"],
                "trace_changed": (values["candidate"]["trace_sha256"]
                                  != values["control"]["trace_sha256"]),
                "outcome_flip": values["control"]["outcome"] + "->" + values["candidate"]["outcome"],
            })
    own = [row["own_delta"] for row in pairs]
    margin = [row["margin_delta"] for row in pairs]
    regressive_wins = [row for row in pairs
                       if row["control"]["outcome"] == "W"
                       and row["candidate"]["outcome"] != "W"]
    changed = sum(row["trace_changed"] for row in pairs)
    if changed == 0:
        decision = "NO_SIGNAL"
    elif sum(own) > 0 and sum(margin) > 0 and not regressive_wins:
        decision = "DEVELOPMENT_SIGNAL"
    elif sum(own) < 0 or regressive_wins:
        decision = "REGRESSION_SIGNAL"
    else:
        decision = "MIXED"
    return {
        "pairs": pairs,
        "paired": {
            "cells": len(pairs),
            "mean_own_delta": sum(own) / len(own),
            "mean_margin_delta": sum(margin) / len(margin),
            "min_own_delta": min(own),
            "max_own_delta": max(own),
            "changed_trace_cells": changed,
            "regressive_win_flips": len(regressive_wins),
            "decision": decision,
            "scope": "tiny public development smoke; not promotion or leaderboard evidence",
        },
    }


def markdown(report: dict[str, Any]) -> str:
    lines = [
        "# TITAN V3 exact-prefix seller-ledger smoke",
        "",
        f"- Status: `{report.get('status')}`",
        f"- Head: `{report.get('runner_head')}`",
        f"- Complete: `{len(report.get('games', []))}/{report.get('expected_games')}`",
    ]
    paired = (report.get("summary") or {}).get("paired")
    if paired:
        lines.extend([
            f"- Decision: `{paired['decision']}`",
            f"- Mean own delta: `{paired['mean_own_delta']}`",
            f"- Mean margin delta: `{paired['mean_margin_delta']}`",
            f"- Changed trace cells: `{paired['changed_trace_cells']}`",
            f"- Regressive W→non-W flips: `{paired['regressive_win_flips']}`",
            "",
            "| seed | seat | own Δ | margin Δ | trace | flip |",
            "|---:|---:|---:|---:|:---:|:---|",
        ])
        for row in report["summary"]["pairs"]:
            lines.append(
                f"| {row['seed']} | {row['seat']} | {row['own_delta']} | "
                f"{row['margin_delta']} | {row['trace_changed']} | {row['outcome_flip']} |"
            )
    lines.extend(["", "This smoke is not a V1/V2/V3 strength or Kaggle claim.", ""])
    return "\n".join(lines)


def run(args: argparse.Namespace) -> dict[str, Any]:
    started = time.time()
    report: dict[str, Any] = {
        "schema_version": 1,
        "operation": OPERATION,
        "status": "initializing",
        "runner_head": args.runner_head,
        "games": [],
        "completed_keys": [],
    }
    atomic_json(args.output, report)
    try:
        if not HEX40.fullmatch(args.runner_head):
            raise ValueError("runner head must be lowercase 40-hex")
        repo = args.repo_root.resolve(strict=True)
        lab = repo / "revenue/kaggriculture/cloud-execution-lab"
        candidate_dir = lab / "candidates/v3-frozen-seller-prefix-ledger"
        control = lab / "main.py"
        candidate = candidate_dir / "main.py"
        opponent = lab / "reference/next-panel/vendor/arlene.py"
        evaluator_path = lab / "reference/evaluator/evaluate.py"
        loader = lab / "reference/evaluator/loader.py"
        engine_dir = lab / "reference/engine"
        config = lab / "TITAN-CONFIG.json"
        archive = lab / "exports/titan-current.tar.gz"
        source_manifest = lab / "runtime/integrated-selected/CURRENT-SOURCE.json"
        closure_files = [
            control, lab / "titan_runtime.py", lab / "frozen_selected.py",
            lab / "scheduler.py", lab / "mechanics.py", config, source_manifest,
            evaluator_path, loader, candidate, candidate_dir / "prefix_ledger.py",
            archive, opponent,
            *(engine_dir / name for name in ("kaggriculture.py", "kaggriculture.json", "utils.py")),
        ]
        missing = [str(path.relative_to(repo)) for path in closure_files if not path.is_file()]
        if missing:
            raise FileNotFoundError(f"missing inputs: {missing}")
        seeds = [int(value) for value in args.seeds.split(",") if value.strip()]
        if not seeds or len(seeds) != len(set(seeds)):
            raise ValueError("seeds must be distinct")
        unexpected = sorted(set(seeds) - DEVELOPMENT_SEEDS)
        if unexpected:
            raise ValueError(f"non-development seeds: {unexpected}")

        evaluator = import_file("_prefix_ledger_evaluator", evaluator_path)
        if evaluator.ENGINE_REF != ENGINE_REF:
            raise ValueError(f"engine ref drift: {evaluator.ENGINE_REF}")
        engine, engine_hashes = evaluator.get_engine(engine_dir, loader)
        source_evidence = {
            "canonical_closure": {
                str(path.relative_to(lab)): {
                    "sha256": sha256_file(path), "bytes": path.stat().st_size
                }
                for path in closure_files if path.is_file() and path != archive
            },
            "archive": {"sha256": sha256_file(archive), "bytes": archive.stat().st_size},
            "candidate_tree": tree_digest(candidate_dir),
            "opponent_tree": tree_digest(opponent.parent),
            "engine": engine_hashes,
        }
        expected = [[arm, seed, seat] for seed in seeds for seat in (0, 1)
                    for arm in ("control", "candidate")]
        report.update({
            "status": "running",
            "seeds": seeds,
            "expected_keys": expected,
            "expected_games": len(expected),
            "source_evidence": source_evidence,
            "limits": {
                "action_timeout_seconds": args.action_timeout,
                "startup_timeout_seconds": args.startup_timeout,
                "game_timeout_seconds": args.game_timeout,
            },
        })
        atomic_json(args.output, report)

        specs = {"control": str(control.resolve()) + "::agent",
                 "candidate": str(candidate.resolve()) + "::agent"}
        opponent_spec = str(opponent.resolve()) + "::agent"
        for seed in seeds:
            for seat in (0, 1):
                for arm in ("control", "candidate"):
                    key = [arm, seed, seat]
                    pair = ([specs[arm], opponent_spec] if seat == 0
                            else [opponent_spec, specs[arm]])
                    game = evaluator.play(
                        engine, pair, engine_dir, loader, seed, seat,
                        args.agent_rng_seed, args.action_timeout,
                        args.startup_timeout, args.game_timeout, None,
                    )
                    row = {"arm": arm, "opponent": "exact_public_arlene", **game}
                    report["games"].append(row)
                    report["wall_seconds"] = time.time() - started
                    if game.get("status") != "complete" or game.get("failure") is not None:
                        report.update(status="failed", failed_cell=row)
                        atomic_json(args.output, report)
                        raise RuntimeError(f"failed cell: {key}")
                    finite_scores(game)
                    report["completed_keys"].append(key)
                    atomic_json(args.output, report)
                    print(json.dumps({"key": key, "scores": game["scores"],
                                      "trace_sha256": game.get("trace_sha256")},
                                     sort_keys=True), flush=True)

        report["summary"] = summarize(report["games"], seeds)
        report.update(status="complete", all_complete=True,
                      wall_seconds=time.time() - started)
        atomic_json(args.output, report)
        args.markdown.parent.mkdir(parents=True, exist_ok=True)
        args.markdown.write_text(markdown(report), encoding="utf-8")
        return report
    except BaseException as exc:
        if report.get("status") != "failed":
            report.update(status="failed", error=f"{type(exc).__name__}: {exc}"[:2000],
                          wall_seconds=time.time() - started)
            atomic_json(args.output, report)
        raise


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser()
    result.add_argument("--repo-root", type=Path, required=True)
    result.add_argument("--runner-head", required=True)
    result.add_argument("--seeds", default="2609099901,2609099902")
    result.add_argument("--agent-rng-seed", type=int, default=0)
    result.add_argument("--action-timeout", type=float, default=1.0)
    result.add_argument("--startup-timeout", type=float, default=10.0)
    result.add_argument("--game-timeout", type=float, default=180.0)
    result.add_argument("--output", type=Path, required=True)
    result.add_argument("--markdown", type=Path, required=True)
    return result


if __name__ == "__main__":
    args = parser().parse_args()
    completed = run(args)
    print(json.dumps({"status": completed["status"],
                      "decision": completed["summary"]["paired"]["decision"]},
                     sort_keys=True))
