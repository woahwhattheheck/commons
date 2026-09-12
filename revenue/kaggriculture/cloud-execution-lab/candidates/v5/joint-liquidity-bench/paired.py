#!/usr/bin/env python3
"""ASTRA joint-liquidity paired games; reuse the Commons evaluator and bank."""
from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import io
import json
import math
import os
from pathlib import Path, PurePosixPath
import platform
import shutil
import statistics
import sys
import tarfile
import tempfile
import time

BASELINE_SHA256 = "4d9601552b5e25d02d8a33961c0bed54ed92d032dbcd4a72f6ab8e03515ed21b"
OVERLAY_COMMIT = "3447b9f1f157aab8a98c0b3a283a7058e477482b"
OVERLAY_SHA256 = "340149a3d9e68b14440825943a5f98067401c913af42727ac9a3ba5b3d829cc6"
BANK = "cloud-execution-lab/candidates/v4/research/reference-policy-bank"
EVALUATOR = "cloud-execution-lab/reference/evaluator/evaluate.py"
SCHEMA = "astra.v5.joint-liquidity.paired.v1"
UPSTREAM_MANIFEST = "cloud-pack/upstream/manifest.json"
HARNESS_GIT_BLOBS = {
    EVALUATOR: "1fb6b655bb4ca1e1684be165a8ef513e2e6c2325",
    "20260907-offline-agent/evaluate.py": "23948e10cfc3d32f46c9abb1321b0d8fc8db21d5",
    "cloud-pack/pack.py": "2407c7467fc60eda8864283d736c743a886bc549",
    "cloud-pack/official.py": "65fe4058deeaa5fb983a0ec9c6e7e53fdd8368ec",
    BANK + "/reference_policies.py": "37d3c885c0e51c1883ef70711d65cbfd404d6d22",
    BANK + "/REFERENCE-POLICIES.json": "6bce02dad705ccc57656ff2e2139db215f9fcc57",
    "cloud-eval/evaluate.py": "077feb2208b6e0c1727835eb4f8089709bf67f3b",
    "cloud-frontier-policy/next-panel/offline.py": "ffaa4b6aae1ca64d9fd90db9de441ff818d59aab",
    UPSTREAM_MANIFEST: "15367ad38c0b3fbf2da324bbf5ad5574759812e7",
}
BRIDGE_SUPPORT_CORE = (
    "cloud-eval/evaluate.py",
    "20260907-offline-agent/evaluate.py",
    "cloud-pack/pack.py",
    "cloud-pack/official.py",
    "cloud-frontier-policy/next-panel/offline.py",
    UPSTREAM_MANIFEST,
)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def git_blob_id(path):
    data = Path(path).read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def checked_repo_file(root, relative):
    root = Path(root).resolve(strict=True)
    rel = PurePosixPath(relative)
    if (not isinstance(relative, str) or not relative or "\\" in relative
            or rel.is_absolute() or ".." in rel.parts or str(rel) != relative):
        raise ValueError(f"Unsafe harness source path: {relative!r}")
    cursor = root
    for part in rel.parts:
        cursor = cursor / part
        if cursor.is_symlink():
            raise ValueError(f"Symlink harness source path: {relative}")
    path = cursor.resolve(strict=True)
    path.relative_to(root)
    if not path.is_file():
        raise ValueError(f"Harness source is not a file: {relative}")
    return path


def verify_git_blobs(root, pins):
    """Bind repository harness bytes to immutable published Git blob ids."""
    if not isinstance(pins, dict) or not pins:
        raise ValueError("Empty harness source pin set")
    verified = {}
    for relative, expected in pins.items():
        path = checked_repo_file(root, relative)
        actual = git_blob_id(path)
        if actual != expected:
            raise ValueError(
                f"Harness source mismatch: {relative}; expected blob {expected}, got {actual}"
            )
        verified[relative] = {"git_blob": expected, "sha256": digest(path)}
    return verified


def verify_upstream_loader(root):
    """Authenticate the loader bundle through the exact Git-pinned manifest."""
    root = Path(root).resolve(strict=True)
    manifest_path = checked_repo_file(root, UPSTREAM_MANIFEST)
    manifest = json.loads(manifest_path.read_text())
    files = manifest.get("files")
    if not isinstance(files, dict) or not files:
        raise ValueError("Pinned upstream manifest has no files")
    verified = {}
    for name, record in files.items():
        if (not isinstance(record, dict) or not isinstance(record.get("sha256"), str)
                or len(record["sha256"]) != 64):
            raise ValueError(f"Malformed upstream manifest record: {name}")
        relative = "cloud-pack/upstream/" + name
        path = checked_repo_file(root, relative)
        actual = digest(path)
        if actual != record["sha256"]:
            raise ValueError(f"Upstream loader source mismatch: {name}")
        verified[relative] = actual
    return verified


def authenticate_harness(root):
    """Authenticate every repository executable used by this evidence run."""
    root = Path(root).resolve(strict=True)
    repository_files = verify_git_blobs(root, HARNESS_GIT_BLOBS)
    upstream_files = verify_upstream_loader(root)
    support = {name: repository_files[name]["sha256"] for name in BRIDGE_SUPPORT_CORE}
    support.update(upstream_files)
    return {
        "repository_files": repository_files,
        "upstream_files": upstream_files,
        "opponent_support_sha256": support,
    }


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def write_json(path, value):
    path = Path(path)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def published_overlay_sha256(value):
    """Bind the accepted overlay bytes to the immutable published source commit."""
    if type(value) is not str or value != OVERLAY_SHA256:
        raise ValueError(
            f"Overlay SHA256 must match published {OVERLAY_COMMIT}: {OVERLAY_SHA256}"
        )
    return value


def archive_members(path):
    data = {}
    with tarfile.open(path, "r:*") as archive:
        for member in archive:
            rel = PurePosixPath(member.name)
            if (not member.name or "\\" in member.name or rel.is_absolute()
                    or ".." in rel.parts or str(rel) != member.name.rstrip("/")):
                raise ValueError(f"Invalid archive path: {member.name}")
            if member.isdir():
                continue
            if not member.isfile() or member.name in data:
                raise ValueError(f"Non-file or duplicate member: {member.name}")
            if member.size > 100 * 1024**2:
                raise ValueError(f"Oversized member: {member.name}")
            with archive.extractfile(member) as stream:
                data[member.name] = stream.read()
    if "main.py" not in data or "frozen_selected.py" not in data:
        raise ValueError("Expected canonical V4 flat archive layout")
    return data


def make_overlay(baseline, overlay, output):
    replacement = Path(overlay).read_bytes()
    with tarfile.open(baseline, "r:*") as source, tarfile.open(output, "w:gz") as target:
        for member in source:
            info = copy.copy(member)
            if member.name == "frozen_selected.py":
                info.size = len(replacement)
                target.addfile(info, io.BytesIO(replacement))
            elif member.isfile():
                with source.extractfile(member) as stream:
                    target.addfile(info, stream)
            else:
                target.addfile(info)


def extract_members(members, directory):
    directory.mkdir()
    for name, data in members.items():
        path = directory.joinpath(*PurePosixPath(name).parts)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)


def margin(game, seat):
    if game["status"] != "complete" or game["steps"] != 719:
        return None
    return game["scores"][seat] - game["scores"][1-seat]


def summarize(cells):
    groups = {}
    for opponent in sorted({cell["opponent"] for cell in cells}):
        rows = [cell for cell in cells if cell["opponent"] == opponent]
        values = [cell["margin_delta"] for cell in rows if cell["margin_delta"] is not None]
        groups[opponent] = {
            "pairs": len(rows), "complete_pairs": len(values),
            "improved": sum(value > 0 for value in values),
            "unchanged": sum(value == 0 for value in values),
            "regressed": sum(value < 0 for value in values),
            "mean_margin_delta": statistics.mean(values) if values else None,
            "min_margin_delta": min(values) if values else None,
            "baseline_failed": sum(row["baseline_margin"] is None for row in rows),
            "candidate_failed": sum(row["candidate_margin"] is None for row in rows),
        }
    return groups


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kg-root", type=Path, required=True, help="Existing revenue/kaggriculture directory")
    parser.add_argument("--engine-dir", type=Path, required=True, help="Existing exact three-file official engine cache")
    parser.add_argument("--baseline", type=Path, required=True)
    candidate = parser.add_mutually_exclusive_group(required=True)
    candidate.add_argument("--overlay", type=Path, help="Exact published frozen_selected.py; replaces only that member")
    candidate.add_argument("--candidate", type=Path, help="Already rebuilt candidate archive")
    parser.add_argument("--overlay-sha256", required=True, help="Expected SHA256 of the published frozen_selected.py")
    parser.add_argument("--output", type=Path, required=True, help="New result directory")
    parser.add_argument("--seeds", default="1209120226,1209120711")
    parser.add_argument("--opponents", default="apex_v7,arlene_v14")
    parser.add_argument("--seats", default="0,1")
    parser.add_argument("--rng-seed", type=int, default=20260912)
    parser.add_argument("--action-timeout", type=float, default=1.25)
    parser.add_argument("--startup-timeout", type=float, default=10.0)
    parser.add_argument("--game-timeout", type=float, default=900.0)
    args = parser.parse_args()
    expected_overlay_sha256 = published_overlay_sha256(args.overlay_sha256)
    if sys.platform != "linux":
        parser.error("Run games on a Linux fleet VM; no Windows timeout shim is used")
    seeds = [int(value) for value in args.seeds.split(",")]
    seats = [int(value) for value in args.seats.split(",")]
    opponents = args.opponents.split(",")
    if (not seeds or len(seeds) != len(set(seeds)) or not seats
            or len(seats) != len(set(seats)) or not set(seats) <= {0, 1}
            or len(opponents) != len(set(opponents))
            or not set(opponents) <= {"apex_v7", "arlene_v14"}):
        parser.error("Use distinct seeds, seats 0/1, and apex_v7/arlene_v14")
    if any(not math.isfinite(value) or value <= 0 for value in
           (args.action_timeout, args.startup_timeout, args.game_timeout)):
        parser.error("Timeouts must be finite and positive")
    args.kg_root = args.kg_root.resolve(strict=True)
    args.engine_dir = args.engine_dir.resolve(strict=True)
    args.baseline = args.baseline.resolve(strict=True)
    if digest(args.baseline) != BASELINE_SHA256:
        raise ValueError("Baseline is not the accepted V4 archive SHA256")
    baseline_files = archive_members(args.baseline)
    harness = authenticate_harness(args.kg_root)
    args.output = args.output.resolve()
    args.output.mkdir(parents=True, exist_ok=False)
    if args.overlay:
        if digest(args.overlay) != expected_overlay_sha256:
            raise ValueError("Overlay file differs from published frozen_selected.py")
        args.candidate = args.output / "joint-liquidity-candidate.tar.gz"
        make_overlay(args.baseline, args.overlay, args.candidate)
    args.candidate = args.candidate.resolve(strict=True)
    candidate_files = archive_members(args.candidate)
    if set(candidate_files) != set(baseline_files):
        raise ValueError("Candidate archive membership differs from V4")
    changed = [name for name in baseline_files if baseline_files[name] != candidate_files[name]]
    if changed != ["frozen_selected.py"]:
        raise ValueError(f"Expected only frozen_selected.py to change; got {changed}")
    if hashlib.sha256(candidate_files["frozen_selected.py"]).hexdigest() != expected_overlay_sha256:
        raise ValueError("Archived frozen_selected.py differs from published source")
    evaluator_path = args.kg_root / EVALUATOR
    loader = args.kg_root / "20260907-offline-agent/evaluate.py"
    evaluator = load(evaluator_path, "astra_existing_evaluator")
    pack = load(args.kg_root / "cloud-pack/pack.py", "astra_existing_pack")
    bridge = load(args.kg_root / BANK / "reference_policies.py", "astra_existing_bank")
    engine_hashes = evaluator.verify_sources(args.engine_dir)
    runtime = {}
    opponent_receipts = {}
    expected_bridge = harness["repository_files"][BANK + "/reference_policies.py"]["sha256"]
    expected_registry = harness["repository_files"][BANK + "/REFERENCE-POLICIES.json"]["sha256"]
    for opponent in opponents:
        runtime[opponent] = args.output / "opponents" / opponent
        receipt = bridge.prepare(opponent, args.kg_root, runtime[opponent])
        if (receipt.get("bridge_sha256") != expected_bridge
                or receipt.get("source_registry_sha256") != expected_registry
                or receipt.get("support_files") != harness["opponent_support_sha256"]):
            raise ValueError(f"Opponent preparation escaped authenticated harness: {opponent}")
        opponent_receipts[opponent] = receipt
    metadata = {
        "schema": SCHEMA, "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "candidate_source_commit": OVERLAY_COMMIT,
        "baseline_sha256": digest(args.baseline), "candidate_sha256": digest(args.candidate),
        "changed_members": changed, "overlay_sha256": expected_overlay_sha256,
        "engine_ref": evaluator.ENGINE_REF, "engine_sha256": engine_hashes,
        "harness": harness,
        "evaluator_sha256": digest(evaluator_path), "loader_sha256": digest(loader),
        "launcher_sha256": digest(__file__), "python": sys.version, "platform": platform.platform(),
        "limits": {"action_rpc_seconds": args.action_timeout, "startup_seconds": args.startup_timeout,
                   "game_seconds": args.game_timeout, "remaining_overage_time": 0},
        "seeds": seeds, "seats": seats, "opponents": opponents, "agent_rng_seed": args.rng_seed,
        "opponent_receipts": opponent_receipts,
        "method": "Full pinned official interpreter. Each game freshly extracts the selected archive and uses fresh persistent agent processes and private working directories. Existing pinned raw-file loader initializes in first timed call. Baseline and candidate share seed, seat, opponent source, VM and role RNG; game order alternates. 1.25s RPC default includes IPC headroom; this is not hosted Kaggle timing or scoring.",
    }
    write_json(args.output / "run.json", metadata)
    cells = []
    for opponent in opponents:
        for seed in seeds:
            for seat in seats:
                cell_id = f"{opponent}-s{seed}-p{seat}"
                cell = {"schema": SCHEMA, "cell_id": cell_id, "opponent": opponent,
                        "seed": seed, "seat": seat, "baseline_sha256": metadata["baseline_sha256"],
                        "candidate_sha256": metadata["candidate_sha256"], "games": {}}
                order = ["baseline", "candidate"] if len(cells) % 2 == 0 else ["candidate", "baseline"]
                cell["execution_order"] = order
                for label in order:
                    with tempfile.TemporaryDirectory(prefix=cell_id + "-" + label + "-", dir=args.output) as temp:
                        directory = Path(temp)
                        payload = directory / "payload"
                        extract_members(baseline_files if label == "baseline" else candidate_files, payload)
                        adapter = directory / "adapter.py"
                        pack.write_adapter(adapter, payload / "main.py")
                        rival = str(runtime[opponent] / "adapter.py")
                        specs = [str(adapter), rival] if seat == 0 else [rival, str(adapter)]
                        engine, _ = evaluator.get_engine(args.engine_dir, loader)
                        game = evaluator.play(engine, specs, args.engine_dir, loader, seed, seat,
                                              args.rng_seed, args.action_timeout, args.startup_timeout,
                                              args.game_timeout)
                        game["variant"] = label
                        game["opponent"] = opponent
                        cell["games"][label] = game
                        write_json(args.output / (cell_id + "-" + label + ".json"), game)
                        print(json.dumps({"cell_id": cell_id, "variant": label, "status": game["status"],
                                          "steps": game["steps"], "scores": game["scores"],
                                          "failure": game["failure"], "wall_seconds": game["wall_seconds"]}), flush=True)
                cell["baseline_margin"] = margin(cell["games"]["baseline"], seat)
                cell["candidate_margin"] = margin(cell["games"]["candidate"], seat)
                valid = cell["baseline_margin"] is not None and cell["candidate_margin"] is not None
                cell["status"] = "complete_pair" if valid else "incomplete_pair"
                cell["margin_delta"] = cell["candidate_margin"] - cell["baseline_margin"] if valid else None
                write_json(args.output / (cell_id + ".json"), cell)
                cells.append(cell)
                report = {"run": metadata, "summary": summarize(cells), "cells": cells}
                write_json(args.output / "report.json", report)
                print("PAIR " + json.dumps({key: value for key, value in cell.items() if key != "games"}), flush=True)
    print("SUMMARY " + json.dumps(summarize(cells)), flush=True)
    return int(any(cell["status"] != "complete_pair" for cell in cells))


if __name__ == "__main__":
    raise SystemExit(main())