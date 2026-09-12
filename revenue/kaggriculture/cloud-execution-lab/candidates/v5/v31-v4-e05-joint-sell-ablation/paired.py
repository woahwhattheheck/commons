#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Matched exact-V4 control vs E05 joint-SELL ablation evidence runner.

The treatment changes only the E05 two-product composition admission inside the
exact submitted-V4 archive. It retains V4's per-product optimizer and all later
V4 mechanisms. This is evidence tooling; it does not modify production V5.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import platform
import statistics
import sys
import tempfile
import time
import types

import ablation

HELPER = "cloud-execution-lab/candidates/v5/joint-liquidity-bench/paired.py"
HELPER_GIT_BLOB = "fbc5e320b8a2ee63af11dc9856c956a679823409"
SCHEMA = "astra.v5.v31-v4-e05-joint-sell-paired.v1"
ARMS = ("control", "no_joint_sell")


def git_blob_bytes(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def capture_git_blob(path: Path, expected: str) -> bytes:
    path = Path(path)
    if not path.is_file() or path.is_symlink():
        raise ValueError(f"Authenticated helper must be an ordinary file: {path}")
    raw = path.read_bytes()
    actual = git_blob_bytes(raw)
    if actual != expected:
        raise ValueError(f"Helper Git blob mismatch; expected {expected}, got {actual}")
    return raw


def load_captured(raw: bytes, origin: Path, name: str):
    """Compile/execute exactly an already-authenticated source buffer."""
    if type(raw) is not bytes:
        raise TypeError("captured source must be bytes")
    module = types.ModuleType(name)
    module.__file__ = str(origin)
    module.__package__ = ""
    sys.modules[name] = module
    exec(compile(raw, str(origin), "exec", dont_inherit=True), module.__dict__)
    return module


def load_snapshot_path(path: Path, name: str):
    """Load a path that is already inside the authenticated immutable snapshot."""
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(str(path))
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def margin(game: dict, seat: int):
    if game.get("status") != "complete" or game.get("steps") != 719:
        return None
    scores = game.get("scores")
    if not isinstance(scores, list) or len(scores) != 2:
        return None
    return scores[seat] - scores[1 - seat]


def summarize(cells: list[dict]) -> dict:
    by_opponent = {}
    for opponent in sorted({cell["opponent"] for cell in cells}):
        rows = [cell for cell in cells if cell["opponent"] == opponent]
        values = [cell["margin_delta"] for cell in rows if cell["margin_delta"] is not None]
        by_opponent[opponent] = {
            "pairs": len(rows),
            "complete_pairs": len(values),
            "improved": sum(value > 0 for value in values),
            "unchanged": sum(value == 0 for value in values),
            "regressed": sum(value < 0 for value in values),
            "mean_margin_delta": statistics.mean(values) if values else None,
            "min_margin_delta": min(values) if values else None,
            "max_margin_delta": max(values) if values else None,
        }
    values = [cell["margin_delta"] for cell in cells if cell["margin_delta"] is not None]
    return {
        "opponents": by_opponent,
        "complete_pairs": len(values),
        "improved": sum(value > 0 for value in values),
        "unchanged": sum(value == 0 for value in values),
        "regressed": sum(value < 0 for value in values),
        "mean_margin_delta": statistics.mean(values) if values else None,
        "stdev_margin_delta": statistics.stdev(values) if len(values) > 1 else 0.0 if values else None,
    }


def parse_csv_ints(value: str) -> list[int]:
    values = [int(item) for item in value.split(",") if item]
    if not values or len(values) != len(set(values)):
        raise ValueError("Expected a non-empty distinct integer list")
    return values


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kg-root", type=Path, required=True)
    parser.add_argument("--engine-dir", type=Path, required=True)
    parser.add_argument("--baseline", type=Path, required=True, help="Exact submitted V4 archive")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seeds", default="2051966578,1378040481")
    parser.add_argument("--seats", default="0,1")
    parser.add_argument("--opponents", default="apex_v7,arlene_v14")
    parser.add_argument("--rng-seed", type=int, default=20260912)
    parser.add_argument("--action-timeout", type=float, default=1.25)
    parser.add_argument("--startup-timeout", type=float, default=10.0)
    parser.add_argument("--game-timeout", type=float, default=900.0)
    args = parser.parse_args()

    if sys.platform != "linux":
        parser.error("Run games on a Linux fleet VM")
    try:
        seeds = parse_csv_ints(args.seeds)
        seats = parse_csv_ints(args.seats)
    except ValueError as exc:
        parser.error(str(exc))
    opponents = [item for item in args.opponents.split(",") if item]
    if (not set(seats) <= {0, 1} or not opponents or len(opponents) != len(set(opponents))
            or not set(opponents) <= {"apex_v7", "arlene_v14"}):
        parser.error("Use distinct seats 0/1 and opponents apex_v7,arlene_v14")
    if any(not math.isfinite(value) or value <= 0
           for value in (args.action_timeout, args.startup_timeout, args.game_timeout)):
        parser.error("Timeouts must be finite and positive")

    root = args.kg_root.resolve(strict=True)
    engine_dir = args.engine_dir.resolve(strict=True)
    baseline_path = args.baseline.resolve(strict=True)
    output = args.output.resolve()
    if output.exists():
        raise FileExistsError(output)
    output_parent = output.parent.resolve(strict=True)

    # Seal both external authorities before creating caller-visible output.
    baseline_raw = ablation.capture_exact_archive(baseline_path)
    helper_path = root / HELPER
    helper_raw = capture_git_blob(helper_path, HELPER_GIT_BLOB)
    helper = load_captured(helper_raw, helper_path, "e05_authenticated_joint_liquidity_helper")
    if helper.BASELINE_SHA256 != ablation.BASELINE_SHA256:
        raise ValueError("Shared helper baseline authority disagrees with E05 runner")

    with tempfile.TemporaryDirectory(prefix="e05-baseline-", dir=output_parent) as td:
        sealed_baseline = Path(td) / "submitted-v4.tar.gz"
        sealed_baseline.write_bytes(baseline_raw)
        baseline_members = helper.archive_members(sealed_baseline)
    treatment_members, treatment_receipt = ablation.ablate_joint_sell(baseline_members)
    arm_payloads = {"control": baseline_members, "no_joint_sell": treatment_members}

    # Snapshot+authenticate every evaluator/opponent executable before output exists.
    with tempfile.TemporaryDirectory(prefix="e05-harness-", dir=output_parent) as temp:
        staged = Path(temp) / "kg"
        harness = helper.snapshot_harness(root, staged, opponents)
        output.mkdir(parents=False, exist_ok=False)
        snapshot_root = output / ".harness-snapshot"
        os.replace(staged, snapshot_root)

    evaluator = load_snapshot_path(snapshot_root / helper.EVALUATOR, "e05_evaluator")
    pack = load_snapshot_path(snapshot_root / "cloud-pack/pack.py", "e05_pack")
    bridge = load_snapshot_path(snapshot_root / helper.BANK / "reference_policies.py", "e05_reference_bank")
    loader = snapshot_root / "20260907-offline-agent/evaluate.py"
    engine_hashes = evaluator.verify_sources(engine_dir)

    runtime = {}
    opponent_receipts = {}
    expected_bridge = harness["repository_files"][helper.BANK + "/reference_policies.py"]["sha256"]
    expected_registry = harness["repository_files"][helper.BANK + "/REFERENCE-POLICIES.json"]["sha256"]
    for opponent in opponents:
        runtime[opponent] = output / "opponents" / opponent
        receipt = bridge.prepare(opponent, snapshot_root, runtime[opponent])
        if (receipt.get("bridge_sha256") != expected_bridge
                or receipt.get("source_registry_sha256") != expected_registry
                or receipt.get("support_files") != harness["opponent_support_sha256"]):
            raise ValueError(f"Opponent escaped authenticated harness: {opponent}")
        if Path(receipt.get("support_root", "")).resolve(strict=True) != snapshot_root:
            raise ValueError(f"Opponent did not bind snapshot root: {opponent}")
        opponent_receipts[opponent] = receipt

    run = {
        "schema": SCHEMA,
        "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "baseline_archive_sha256": ablation.BASELINE_SHA256,
        "v31_source": ablation.V31_SOURCE,
        "v4_source": ablation.V4_SOURCE,
        "historical_mechanism_pr": ablation.E05_PR,
        "arms": list(ARMS),
        "treatment_receipt": treatment_receipt,
        "seeds": seeds,
        "seats": seats,
        "opponents": opponents,
        "engine": engine_hashes,
        "helper_git_blob": HELPER_GIT_BLOB,
        "helper_sha256": hashlib.sha256(helper_raw).hexdigest(),
        "helper_execution": "single-read Git-blob-authenticated captured bytes",
        "baseline_execution": "single-read SHA256-authenticated private snapshot",
        "harness": harness,
        "opponent_receipts": opponent_receipts,
        "python": sys.version,
        "platform": platform.platform(),
        "method": (
            "Control is exact submitted V4. Treatment changes only frozen_selected.py by "
            "forcing the E05 joint-plan metrics variable to None at the existing pair-admission "
            "callsite; the incumbent guard then declines every two-product pair while retaining "
            "the exact V4 single-product optimizer and all other submitted-V4 bytes."
        ),
    }
    helper.write_json(output / "run.json", run)

    cells = []
    for opponent in opponents:
        for seed in seeds:
            for seat in seats:
                order = list(ARMS)
                if len(cells) % 2:
                    order.reverse()
                cell_id = f"{opponent}-seed{seed}-seat{seat}"
                cell = {
                    "opponent": opponent,
                    "seed": seed,
                    "seat": seat,
                    "execution_order": order,
                    "games": {},
                    "margins": {},
                    "margin_delta": None,
                }
                for arm in order:
                    with tempfile.TemporaryDirectory(prefix=f"{cell_id}-{arm}-", dir=output) as temp:
                        directory = Path(temp)
                        payload = directory / "payload"
                        helper.extract_members(arm_payloads[arm], payload)
                        adapter = directory / "adapter.py"
                        pack.write_adapter(adapter, payload / "main.py")
                        rival = str(runtime[opponent] / "adapter.py")
                        specs = [str(adapter), rival] if seat == 0 else [rival, str(adapter)]
                        engine, _ = evaluator.get_engine(engine_dir, loader)
                        game = evaluator.play(
                            engine, specs, engine_dir, loader, seed, seat,
                            args.rng_seed, args.action_timeout,
                            args.startup_timeout, args.game_timeout,
                        )
                    cell["games"][arm] = game
                    cell["margins"][arm] = margin(game, seat)
                    print(json.dumps({
                        "cell": cell_id,
                        "arm": arm,
                        "status": game.get("status"),
                        "margin": cell["margins"][arm],
                    }), flush=True)
                control = cell["margins"]["control"]
                treatment = cell["margins"]["no_joint_sell"]
                if control is not None and treatment is not None:
                    cell["margin_delta"] = treatment - control
                    cell["status"] = "complete_cell"
                else:
                    cell["status"] = "incomplete_cell"
                helper.write_json(output / f"cell-{len(cells):03d}.json", cell)
                cells.append(cell)

    summary = summarize(cells)
    final = {
        "schema": SCHEMA,
        "run": run,
        "cells": cells,
        "summary": summary,
        "authorizing": False,
        "verdict": (
            "CAUSAL_SCREEN_COMPLETE" if summary["complete_pairs"] == len(cells)
            else "INCOMPLETE_NONAUTHORIZING"
        ),
    }
    helper.write_json(output / "RESULTS.json", final)
    print(json.dumps({"summary": summary, "verdict": final["verdict"]}, sort_keys=True))
    return 0 if final["verdict"] == "CAUSAL_SCREEN_COMPLETE" else 3


if __name__ == "__main__":
    raise SystemExit(main())
