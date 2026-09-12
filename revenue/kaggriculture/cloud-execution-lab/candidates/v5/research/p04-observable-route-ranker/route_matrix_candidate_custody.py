#!/usr/bin/env python3
"""Candidate-custody CLI for P04 route-matrix row receipts.

The public ``route_matrix_row_receipt.py`` facade dispatches here. The older
row/snapshot helpers live in ``_route_matrix_row_receipt_core.py``; this layer
adds the missing proof that the route manifest, materialized payload and bytes
actually executed by the pinned evaluator are the same candidate.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any

import _route_matrix_row_receipt_core as core

OFFICIAL_FILE_LOADER_SHA256 = "65fe4058deeaa5fb983a0ec9c6e7e53fdd8368ec"


def _safe_member(name: Any) -> str:
    if not isinstance(name, str) or not name:
        raise ValueError("candidate manifest member names must be nonempty strings")
    path = Path(name)
    if path.is_absolute() or name.startswith(("/", "\\")) or any(part in ("", ".", "..") for part in path.parts):
        raise ValueError(f"unsafe candidate manifest member path: {name!r}")
    return Path(*path.parts).as_posix()


def capture_candidate(root: Path, archive: Path, manifest: dict[str, Any]):
    """Single-read the exact manifest-bound route payload and archive."""
    root, archive = Path(root), Path(archive)
    if root.is_symlink() or not root.is_dir():
        raise ValueError("candidate root must be an ordinary directory")
    if archive.is_symlink() or not archive.is_file():
        raise ValueError("candidate archive must be an ordinary file")

    raw_files = core._mapping(manifest.get("files"), "route manifest files")
    expected: dict[str, str] = {}
    for raw_name, digest in raw_files.items():
        name = _safe_member(raw_name)
        if name in expected:
            raise ValueError("duplicate normalized candidate member")
        if not isinstance(digest, str) or len(digest) != 64:
            raise ValueError(f"invalid candidate member SHA256: {name}")
        expected[name] = digest
    if "main.py" not in expected or core.ROUTER not in expected:
        raise ValueError("candidate manifest must bind main.py and r04_full_router.py")

    actual: set[str] = set()
    for path in root.rglob("*"):
        if path.is_symlink():
            raise ValueError(f"candidate root contains symlink: {path.relative_to(root)}")
        if path.is_file():
            actual.add(path.relative_to(root).as_posix())
        elif not path.is_dir():
            raise ValueError(f"unsupported candidate filesystem entry: {path}")
    if actual != set(expected):
        raise ValueError(
            "candidate root member set drift: "
            f"missing={sorted(set(expected)-actual)} extra={sorted(actual-set(expected))}"
        )

    captured: dict[str, bytes] = {}
    for name in sorted(expected):
        body = (root / Path(name)).read_bytes()
        if hashlib.sha256(body).hexdigest() != expected[name]:
            raise ValueError(f"candidate root member SHA256 drift: {name}")
        captured[name] = body

    archive_bytes = archive.read_bytes()
    archive_sha = hashlib.sha256(archive_bytes).hexdigest()
    if archive_sha != manifest["candidate_archive_sha256"]:
        raise ValueError("candidate archive does not match route manifest")
    manifest_sha = hashlib.sha256(
        json.dumps(expected, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return captured, {
        "candidate_archive_sha256": archive_sha,
        "candidate_files_manifest_sha256": manifest_sha,
        "member_count": len(captured),
    }


def private_snapshot(captured: dict[str, bytes], official_loader: Path):
    """Publish captured payload bytes privately and make a canonical file-loader adapter."""
    official_loader = Path(official_loader).resolve(strict=True)
    if official_loader.is_symlink() or not official_loader.is_file():
        raise ValueError("official file loader must be an ordinary file")
    loader_sha = core.sha256_file(official_loader)
    if loader_sha != OFFICIAL_FILE_LOADER_SHA256:
        raise ValueError(f"official file-loader identity drift: {loader_sha}")

    custody = tempfile.TemporaryDirectory(prefix="titan-route-candidate-captured-")
    root = Path(custody.name) / "payload"
    root.mkdir()
    try:
        for name, body in captured.items():
            target = root / Path(name)
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("xb") as stream:
                stream.write(body)
                stream.flush()
                os.fsync(stream.fileno())
        adapter = Path(custody.name) / "candidate-adapter.py"
        source = (
            "from pathlib import Path\n"
            "import importlib.util\n"
            "def _load(path):\n"
            "    spec=importlib.util.spec_from_file_location('titan_route_official_file_loader', path)\n"
            "    if spec is None or spec.loader is None: raise ValueError('cannot import pinned file loader')\n"
            "    module=importlib.util.module_from_spec(spec)\n"
            "    spec.loader.exec_module(module)\n"
            "    return module\n"
            f"_official=_load(Path({str(official_loader)!r}))\n"
            f"agent=_official.make_agent(Path({str(root / 'main.py')!r}))\n"
        )
        with adapter.open("x", encoding="utf-8") as stream:
            stream.write(source)
            stream.flush()
            os.fsync(stream.fileno())
        authority = {
            "official_file_loader_sha256": loader_sha,
            "generated_adapter_sha256": core.sha256_file(adapter),
            "private_snapshot_member_count": len(captured),
        }
        return custody, root, adapter, authority
    except BaseException:
        custody.cleanup()
        raise


def verify_snapshot(root: Path, captured: dict[str, bytes]) -> None:
    actual = {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()}
    if actual != set(captured):
        raise ValueError("private candidate snapshot member set changed during game")
    for name, body in captured.items():
        if core.sha256_file(root / Path(name)) != hashlib.sha256(body).hexdigest():
            raise ValueError(f"private candidate snapshot changed during game: {name}")


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--evaluator", type=Path, required=True)
    p.add_argument("--engine-dir", type=Path, required=True)
    p.add_argument("--loader", type=Path, required=True)
    p.add_argument("--official-file-loader", type=Path, required=True)
    p.add_argument("--candidate-root", type=Path, required=True)
    p.add_argument("--candidate-archive", type=Path, required=True)
    p.add_argument("--route-manifest", type=Path, required=True)
    p.add_argument("--opponent-label", required=True)
    p.add_argument("--opponent", required=True)
    p.add_argument("--opponent-entry-sha256", required=True)
    p.add_argument("--seed", type=int, required=True)
    p.add_argument("--seat", type=int, choices=(0, 1), required=True)
    p.add_argument("--plan-index", type=int, choices=range(13), required=True)
    p.add_argument("--rng-seed", type=int, default=20260912)
    p.add_argument("--action-timeout", type=float, default=1.25)
    p.add_argument("--startup-timeout", type=float, default=10.0)
    p.add_argument("--game-timeout", type=float, default=900.0)
    p.add_argument("--row-out", type=Path, required=True)
    p.add_argument("--receipt-out", type=Path, required=True)
    args = p.parse_args()

    manifest = core.validate_route_manifest(core._load_json(args.route_manifest, "route manifest"), args.plan_index)
    if core.sha256_file(args.loader) != core.LOADER_SHA256:
        raise ValueError("loader identity drift")
    evaluator = core._import_exact_evaluator(args.evaluator)
    captured, materialization = capture_candidate(args.candidate_root, args.candidate_archive, manifest)
    custody, snapshot_root, adapter, snapshot_authority = private_snapshot(captured, args.official_file_loader)
    try:
        candidate = evaluator.resolve_spec(str(adapter) + "::agent")
        opponent = evaluator.resolve_spec(args.opponent)
        c_before = core._entry_fingerprint(evaluator, candidate, snapshot_authority["generated_adapter_sha256"], "candidate")
        o_before = core._entry_fingerprint(evaluator, opponent, args.opponent_entry_sha256, "opponent")
        engine, engine_hashes = evaluator.get_engine(args.engine_dir, args.loader)
        pair = [candidate, opponent] if args.seat == 0 else [opponent, candidate]
        game, snapshot = core.play_with_public_snapshot(
            evaluator, engine, pair, args.engine_dir, args.loader, args.seed, args.seat,
            args.rng_seed, args.action_timeout, args.startup_timeout, args.game_timeout,
        )
        verify_snapshot(snapshot_root, captured)
        if core.sha256_file(args.official_file_loader) != OFFICIAL_FILE_LOADER_SHA256:
            raise ValueError("official file loader changed during native game")
        c_after = core._entry_fingerprint(evaluator, candidate, snapshot_authority["generated_adapter_sha256"], "candidate")
        o_after = core._entry_fingerprint(evaluator, opponent, args.opponent_entry_sha256, "opponent")
        if c_after != c_before or o_after != o_before:
            raise ValueError("entry fingerprint changed during native game")
    finally:
        custody.cleanup()

    row = core.make_row(manifest, args.plan_index, args.seed, args.opponent_label, args.seat, snapshot, game)
    receipt = {
        "schema": core.SCHEMA,
        "route_candidate_archive_sha256": manifest["candidate_archive_sha256"],
        "baseline_candidate_archive_sha256": core.PRODUCTION_ARCHIVE_SHA256,
        "forced_plan": args.plan_index,
        "selection_step": core.ROUTE_STEP,
        "evaluator_sha256": core.EVALUATOR_SHA256,
        "loader_sha256": core.LOADER_SHA256,
        "engine_ref": core.ENGINE_REF,
        "engine_sha256": engine_hashes,
        "candidate": c_after,
        "candidate_materialization": materialization,
        "candidate_snapshot_authority": snapshot_authority,
        "opponent_label": args.opponent_label,
        "opponent": o_after,
        "seed": args.seed,
        "seat": args.seat,
        "rng_seed": args.rng_seed,
        "snapshot_sha256": row["snapshot_sha256"],
        "game_trace_sha256": game.get("trace_sha256"),
        "steps": game.get("steps"),
        "episode_steps": game.get("episode_steps"),
        "private_observation_persisted": False,
        "p04_row_sha256": hashlib.sha256(
            json.dumps(row, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
        ).hexdigest(),
    }
    core._publish_pair(args.row_out, args.receipt_out, row, receipt)
    print(json.dumps({
        "seed": args.seed, "opponent": args.opponent_label, "seat": args.seat,
        "forced_plan": args.plan_index, "snapshot_sha256": row["snapshot_sha256"],
        "terminal_margin": row["terminal_margin"],
    }, sort_keys=True))
    return 0
