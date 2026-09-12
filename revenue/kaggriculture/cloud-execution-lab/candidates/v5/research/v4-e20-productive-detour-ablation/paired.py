#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Matched exact submitted-V4 control vs E20 productive-detour-OFF games."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import io
import json
import math
import os
from pathlib import Path, PurePosixPath
import shutil
import statistics
import subprocess
import sys
import tarfile
import tempfile
import time
import types

import ablate_e20_productive_detour as ablation
import build_submitted_v4_treatment as builder
import trace_capture as trace

HELPER = "cloud-execution-lab/candidates/v5/joint-liquidity-bench/paired.py"
HELPER_GIT_BLOB = "fbc5e320b8a2ee63af11dc9856c956a679823409"
SCHEMA = "astra.v5.v31-v4-e20-productive-detour-ablation.v1"
ARMS = ("control", "e20_detour_off")
DEFAULT_SEEDS = (
    2051966578,
    5501, 5502, 5503, 5504, 5505, 5506, 5507, 5508,
    5509, 5510, 5511, 5512, 5513, 5514, 5515,
)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git_blob_bytes(data: bytes) -> str:
    return hashlib.sha1(
        b"blob " + str(len(data)).encode("ascii") + b"\0" + data
    ).hexdigest()


def capture_regular(path: Path) -> bytes:
    path = Path(path)
    if not path.is_file() or path.is_symlink():
        raise ValueError(f"authority must be an ordinary file: {path}")
    return path.read_bytes()


def load_captured(raw: bytes, origin: Path, name: str):
    module = types.ModuleType(name)
    module.__file__ = str(origin)
    module.__package__ = ""
    sys.modules[name] = module
    exec(compile(raw, str(origin), "exec", dont_inherit=True), module.__dict__)
    return module


def load_path(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(str(path))
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def write_json(path: Path, value) -> None:
    path = Path(path)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def git_show(repo_root: Path, commit: str, path: str) -> bytes:
    proc = subprocess.run(
        ["git", "-C", str(repo_root), "show", f"{commit}:{path}"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if proc.returncode:
        raise ValueError(f"cannot resolve source authority {commit}:{path}")
    return bytes(proc.stdout)


def git_head(repo_root: Path) -> str:
    proc = subprocess.run(
        ["git", "-C", str(repo_root), "rev-parse", "HEAD"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if proc.returncode:
        raise ValueError("cannot resolve runner Git HEAD")
    value = proc.stdout.decode("ascii").strip()
    if len(value) != 40:
        raise ValueError("runner Git HEAD is not a full SHA")
    return value


def archive_members(raw: bytes) -> dict[str, bytes]:
    out: dict[str, bytes] = {}
    with tarfile.open(fileobj=io.BytesIO(raw), mode="r:gz") as archive:
        for info in archive.getmembers():
            path = PurePosixPath(info.name)
            if (not info.name or "\\" in info.name or path.is_absolute()
                    or ".." in path.parts or str(path) != info.name
                    or not info.isfile() or info.name in out):
                raise ValueError(f"unsafe or duplicate archive member: {info.name}")
            stream = archive.extractfile(info)
            if stream is None:
                raise ValueError(f"unreadable archive member: {info.name}")
            data = stream.read()
            if len(data) != info.size:
                raise ValueError(f"truncated archive member: {info.name}")
            out[info.name] = data
    if "main.py" not in out or "SOURCE.json" not in out:
        raise ValueError("submitted V4 archive missing required package members")
    return out


def extract_members(members: dict[str, bytes], destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=False)
    for name, data in members.items():
        rel = PurePosixPath(name)
        if rel.is_absolute() or ".." in rel.parts or "\\" in name or str(rel) != name:
            raise ValueError(f"unsafe archive member path: {name}")
        path = destination.joinpath(*rel.parts)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)


def summarize(cells: list[dict]) -> dict:
    summary = {}
    groups = ["all"] + sorted({cell["opponent"] for cell in cells})
    for group in groups:
        rows = cells if group == "all" else [
            cell for cell in cells if cell["opponent"] == group
        ]
        complete = [cell for cell in rows if cell["status"] == "complete_pair"]
        engaged = [cell for cell in complete if cell["engaged"] is True]
        own = [cell["score_delta"]["own"] for cell in complete]
        rival = [cell["score_delta"]["rival"] for cell in complete]
        margin = [cell["score_delta"]["margin"] for cell in complete]
        summary[group] = {
            "pairs": len(rows),
            "complete_pairs": len(complete),
            "engaged_pairs": len(engaged),
            "cold_pairs": sum(cell.get("engaged") is False for cell in complete),
            "mean_own_score_delta": statistics.mean(own) if own else None,
            "mean_rival_score_delta": statistics.mean(rival) if rival else None,
            "mean_margin_delta": statistics.mean(margin) if margin else None,
            "engaged_mean_margin_delta": (
                statistics.mean(cell["score_delta"]["margin"] for cell in engaged)
                if engaged else None
            ),
            "margin_improved": sum(value > 0 for value in margin),
            "margin_unchanged": sum(value == 0 for value in margin),
            "margin_regressed": sum(value < 0 for value in margin),
        }
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kg-root", type=Path, required=True)
    parser.add_argument("--engine-dir", type=Path, required=True)
    parser.add_argument("--baseline", type=Path, required=True,
                        help="Exact retained submitted-V4 archive 4d960155...")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--seeds",
        default=",".join(str(seed) for seed in DEFAULT_SEEDS),
    )
    parser.add_argument("--seats", default="0,1")
    parser.add_argument("--opponents", default="apex_v7,arlene_v14")
    parser.add_argument("--rng-seed", type=int, default=20260912)
    parser.add_argument("--action-timeout", type=float, default=1.25)
    parser.add_argument("--startup-timeout", type=float, default=10.0)
    parser.add_argument("--game-timeout", type=float, default=900.0)
    args = parser.parse_args()

    if sys.platform != "linux":
        parser.error("Run games on a Linux fleet VM")
    seeds = [int(value) for value in args.seeds.split(",") if value]
    seats = [int(value) for value in args.seats.split(",") if value]
    opponents = [value for value in args.opponents.split(",") if value]
    if (not seeds or len(seeds) != len(set(seeds))
            or not seats or len(seats) != len(set(seats)) or not set(seats) <= {0, 1}
            or not opponents or len(opponents) != len(set(opponents))
            or not set(opponents) <= {"apex_v7", "arlene_v14"}):
        parser.error("Use distinct seeds, seats 0/1, opponents apex_v7/arlene_v14")
    if any(not math.isfinite(value) or value <= 0
           for value in (args.action_timeout, args.startup_timeout, args.game_timeout)):
        parser.error("Timeouts must be finite and positive")

    root = args.kg_root.resolve(strict=True)
    engine_dir = args.engine_dir.resolve(strict=True)
    output = args.output.resolve()
    if output.exists():
        raise FileExistsError(output)
    output_parent = output.parent.resolve(strict=True)
    repo_proc = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "--show-toplevel"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if repo_proc.returncode:
        raise ValueError("kg-root is not inside the authenticated repository")
    repo_root = Path(repo_proc.stdout.decode("utf-8").strip()).resolve(strict=True)

    baseline_raw = capture_regular(args.baseline)
    if sha256_bytes(baseline_raw) != builder.SUBMITTED_V4_ARCHIVE_SHA256:
        raise ValueError("baseline is not exact retained submitted V4")
    v31_helper = git_show(repo_root, ablation.V31_COMMIT, ablation.HELPER_PATH)
    treatment_raw, treatment_receipt = builder.build_treatment_archive(
        baseline_raw, v31_helper
    )
    control_members = archive_members(baseline_raw)
    treatment_members = archive_members(treatment_raw)
    helper_path = root / HELPER
    helper_raw = capture_regular(helper_path)
    if git_blob_bytes(helper_raw) != HELPER_GIT_BLOB:
        raise ValueError("joint-liquidity paired helper source drift")
    helper = load_captured(helper_raw, helper_path, "e20_authenticated_paired_helper")

    # The entire candidate/opponent execution leaf lives in one private sibling
    # for the full panel lifetime.  Public output receives evidence copies only;
    # no Actor path is ever sourced from the public evidence directory.
    private_runtime = tempfile.TemporaryDirectory(
        prefix="e20-private-panel-", dir=output_parent
    )
    private_root = Path(private_runtime.name)
    snapshot_root = private_root / "harness-snapshot"
    harness = helper.snapshot_harness(root, snapshot_root, opponents)
    output.mkdir(parents=False, exist_ok=False)
    shutil.copytree(snapshot_root, output / ".harness-snapshot")

    evaluator_path = snapshot_root / helper.EVALUATOR
    loader = snapshot_root / "20260907-offline-agent/evaluate.py"
    evaluator = load_path(evaluator_path, "e20_evaluator")
    pack = load_path(snapshot_root / "cloud-pack/pack.py", "e20_pack")
    bridge = load_path(
        snapshot_root / helper.BANK / "reference_policies.py", "e20_reference_bank"
    )
    engine_hashes = evaluator.verify_sources(engine_dir)

    runtime = {}
    opponent_receipts = {}
    expected_bridge = harness["repository_files"][
        helper.BANK + "/reference_policies.py"]["sha256"]
    expected_registry = harness["repository_files"][
        helper.BANK + "/REFERENCE-POLICIES.json"]["sha256"]
    for opponent in opponents:
        runtime[opponent] = private_root / "opponents" / opponent
        receipt = bridge.prepare(opponent, snapshot_root, runtime[opponent])
        if (receipt.get("bridge_sha256") != expected_bridge
                or receipt.get("source_registry_sha256") != expected_registry
                or receipt.get("support_files") != harness["opponent_support_sha256"]):
            raise ValueError(f"opponent escaped authenticated harness: {opponent}")
        if Path(receipt.get("support_root", "")).resolve(strict=True) != snapshot_root:
            raise ValueError(f"opponent did not bind private snapshot root: {opponent}")
        opponent_receipts[opponent] = receipt

    arms = {
        "control": control_members,
        "e20_detour_off": treatment_members,
    }
    run = {
        "schema": SCHEMA,
        "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "runner_git_head": git_head(repo_root),
        "baseline_archive_sha256": sha256_bytes(baseline_raw),
        "treatment_archive_sha256": sha256_bytes(treatment_raw),
        "treatment_receipt": treatment_receipt,
        "treatment_contract": (
            "Exact retained submitted-V4 archive; one semantic member "
            "reference/titan-current/redundant_hire.py changes by authenticated "
            "post-certificate tail ablation; SOURCE.json changes only as truthful "
            "metadata; every other member exact."
        ),
        "helper_git_blob": HELPER_GIT_BLOB,
        "helper_sha256": sha256_bytes(helper_raw),
        "trace_pattern_git_blob": trace.SOURCE_PATTERN_GIT_BLOB,
        "harness": harness,
        "engine": engine_hashes,
        "execution_custody": {
            "candidate_payload_root": "private_panel_tempdir",
            "opponent_runtime_root": "private_panel_tempdir",
            "harness_execution_root": "private_panel_tempdir",
            "public_harness_copy": "evidence_only_never_executed",
            "engine_root": "external_verified_path_pending_shared_private_ingest",
        },
        "opponent_receipts": opponent_receipts,
        "seeds": seeds,
        "seats": seats,
        "opponents": opponents,
        "rng_seed": args.rng_seed,
        "limits": {
            "action_timeout": args.action_timeout,
            "startup_timeout": args.startup_timeout,
            "game_timeout": args.game_timeout,
        },
        "engagement_definition": (
            "first returned-action divergence between exact V4 control and detour-OFF; "
            "the treatment's only gameplay semantic change is E20 detour protection."
        ),
    }
    write_json(output / "run.json", run)

    cells: list[dict] = []
    for opponent in opponents:
        for seed in seeds:
            for seat in seats:
                cell_id = f"{opponent}-s{seed}-p{seat}"
                cell = {
                    "schema": SCHEMA,
                    "cell_id": cell_id,
                    "opponent": opponent,
                    "seed": seed,
                    "seat": seat,
                    "games": {},
                    "own_action_trace_sha256": {},
                }
                action_traces = {}
                order = list(ARMS if len(cells) % 2 == 0 else reversed(ARMS))
                cell["execution_order"] = order
                for arm in order:
                    with tempfile.TemporaryDirectory(
                        prefix=f"{cell_id}-{arm}-", dir=private_root
                    ) as temp:
                        directory = Path(temp)
                        payload = directory / "payload"
                        extract_members(arms[arm], payload)
                        adapter = directory / "adapter.py"
                        pack.write_adapter(adapter, payload / "main.py")
                        candidate_spec = str(adapter)
                        rival_spec = str(runtime[opponent] / "adapter.py")
                        specs = ([candidate_spec, rival_spec] if seat == 0
                                 else [rival_spec, candidate_spec])
                        engine, _ = evaluator.get_engine(engine_dir, loader)
                        game, actions = trace.play_with_candidate_trace(
                            evaluator,
                            engine, specs, engine_dir, loader, seed, seat,
                            args.rng_seed, args.action_timeout, args.startup_timeout,
                            args.game_timeout,
                            candidate_spec=candidate_spec,
                        )
                        game["variant"] = arm
                        game["opponent"] = opponent
                        cell["games"][arm] = game
                        action_traces[arm] = actions
                        cell["own_action_trace_sha256"][arm] = trace.action_trace_sha256(actions)
                        write_json(output / f"{cell_id}-{arm}.json", game)
                        print(json.dumps({
                            "cell_id": cell_id,
                            "variant": arm,
                            "status": game.get("status"),
                            "steps": game.get("steps"),
                            "scores": game.get("scores"),
                            "failure": game.get("failure"),
                        }), flush=True)

                control_scores = trace.game_scores(cell["games"]["control"], seat)
                treatment_scores = trace.game_scores(
                    cell["games"]["e20_detour_off"], seat
                )
                valid = control_scores is not None and treatment_scores is not None
                cell["status"] = "complete_pair" if valid else "incomplete_pair"
                if valid:
                    cell["scores"] = {
                        "control": control_scores,
                        "e20_detour_off": treatment_scores,
                    }
                    cell["score_delta"] = {
                        key: treatment_scores[key] - control_scores[key]
                        for key in ("own", "rival", "margin")
                    }
                    divergence = trace.first_action_divergence(
                        action_traces["control"], action_traces["e20_detour_off"]
                    )
                    cell["engaged"] = divergence is not None
                    cell["first_action_divergence"] = divergence
                else:
                    cell["scores"] = None
                    cell["score_delta"] = None
                    cell["engaged"] = None
                    cell["first_action_divergence"] = None
                cell["action_calls"] = {
                    arm: len(action_traces[arm]) for arm in ARMS
                }
                write_json(output / f"{cell_id}.json", cell)
                cells.append(cell)
                write_json(
                    output / "report.json",
                    {"run": run, "summary": summarize(cells), "cells": cells},
                )
                print("PAIR " + json.dumps({
                    key: value for key, value in cell.items() if key != "games"
                }, allow_nan=False), flush=True)

    summary = summarize(cells)
    write_json(output / "report.json", {"run": run, "summary": summary, "cells": cells})
    print("SUMMARY " + json.dumps(summary, allow_nan=False), flush=True)
    private_runtime.cleanup()
    return int(any(cell["status"] != "complete_pair" for cell in cells))


if __name__ == "__main__":
    raise SystemExit(main())
