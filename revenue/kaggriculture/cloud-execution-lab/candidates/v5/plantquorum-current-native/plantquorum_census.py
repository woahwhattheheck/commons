#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Authenticated current-V5 engagement runner for canonical PLANTQUORUM.

`census.py` is the single theorem/engine observer boundary. This file adds exact
current-archive custody, official gameplay, one-cell execution, and strict fixed
panel aggregation. Candidate bytes are observation-only and are never sent to
the interpreter.
"""
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
import shutil
import sys
import tarfile
import tempfile
from typing import Any

HERE = Path(__file__).resolve().parent
LAB = HERE.parents[2]
ARCHIVE = LAB / "exports/titan-current.tar.gz"
POINTER = LAB / "runtime/integrated-selected/CURRENT-ARCHIVE.json"
OBSERVER = HERE / "census.py"
NATIVE_CENSUS = LAB / "candidates/v4/research/unit-phase-chaining/native_census.py"
UNITPIPE = LAB / "candidates/v4/research/unit-phase-chaining/unit_pipeline_admission.py"
PLANTQUORUM = LAB / "candidates/v4/research/unit-phase-chaining/plant_quorum_admission.py"

BASE_COMMIT = "b9d696d4dd803bc0345f73cdd52cc35346f503f6"
ARCHIVE_SHA256 = "fe67d2daa00ba84348ef364db3b6dea9671d6b01349001e51546874e277adec3"
ARCHIVE_BYTES = 466983
SOURCE_SHA256 = "8182785b03f3c771901d6124d11b7e04d37c1ddcaabf6174d9748227a91c5526"
RUNTIME_FILES = 116
POINTER_GIT_BLOB = "e041598b2ab31ac370b4d2285fe38477c3aa3f78"
OBSERVER_GIT_BLOB = "0d55822177714a4df22d5dc9084441d02d4319ae"
NATIVE_CENSUS_GIT_BLOB = "27ec7f411b0da36aeeecab2729d5d65adcf81dd2"
UNITPIPE_GIT_BLOB = "f02448806f66e524fdc317c23b620fde45a926c9"
PLANTQUORUM_GIT_BLOB = "15c24fbe305dfb7b4b1b2c39897af4af9b49f31f"
ENGINE_GIT_BLOB = "3c202c7ee921da239356789e266b694635103fc4"
MAIN_GIT_BLOB = "9cf8feaa9a755ffdf85d8878baa07b1fc7940192"
CONFIG_GIT_BLOB = "ef0bfb1dfa1ce65103a0b178647fc16bc9c7e791"

CELL_SCHEMA = "titan-v5-plantquorum-current-native-cell/v1"
PANEL_SCHEMA = "titan-v5-plantquorum-current-native-panel/v1"
PANEL_SEEDS = (17, 101, 6607, 9922999, 2026091201, 2026091207, 2026091213, 2026091219)
PANEL_SEATS = (0, 1)
EXPECTED_CALLBACKS = 719
MAX_EXAMPLES = 64
MAX_ARCHIVE_MEMBER = 64 * 1024 * 1024
MAX_ARCHIVE_TOTAL = 256 * 1024 * 1024
MAX_ARCHIVE_FILES = 512

REQUIRED_RUNTIME_GIT_BLOBS = {
    "checks/reference/engine/kaggriculture.py": ENGINE_GIT_BLOB,
    "main.py": MAIN_GIT_BLOB,
    "TITAN-CONFIG.json": CONFIG_GIT_BLOB,
}

EXPECTED_SOURCE = {
    "base_commit": BASE_COMMIT,
    "archive_sha256": ARCHIVE_SHA256,
    "source_sha256": SOURCE_SHA256,
    "runtime_files": RUNTIME_FILES,
    "pointer_git_blob": POINTER_GIT_BLOB,
    "observer_git_blob": OBSERVER_GIT_BLOB,
    "native_census_git_blob": NATIVE_CENSUS_GIT_BLOB,
    "unitpipe_support_git_blob": UNITPIPE_GIT_BLOB,
    "plantquorum_git_blob": PLANTQUORUM_GIT_BLOB,
    "engine_git_blob": ENGINE_GIT_BLOB,
    "main_git_blob": MAIN_GIT_BLOB,
    "config_git_blob": CONFIG_GIT_BLOB,
}


def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(f"blob {len(data)}\0".encode("ascii") + data).hexdigest()


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _capture_pinned(path: Path, expected_blob: str, label: str) -> bytes:
    data = Path(path).read_bytes()
    actual = git_blob_sha(data)
    if actual != expected_blob:
        raise ValueError(f"{label} Git blob mismatch: expected {expected_blob}, got {actual}")
    return data


def _reject_constant(value: str) -> None:
    raise ValueError(f"non-finite JSON constant: {value}")


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key!r}")
        result[key] = value
    return result


def _strict_json_bytes(data: bytes, label: str) -> Any:
    try:
        return json.loads(
            data.decode("utf-8"),
            object_pairs_hook=_strict_object,
            parse_constant=_reject_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise ValueError(f"invalid strict JSON in {label}: {exc}") from exc


def _strict_json_file(path: Path) -> Any:
    return _strict_json_bytes(Path(path).read_bytes(), str(path))


def _pointer_contract() -> dict[str, Any]:
    data = _capture_pinned(POINTER, POINTER_GIT_BLOB, "CURRENT-ARCHIVE.json")
    value = _strict_json_bytes(data, "CURRENT-ARCHIVE.json")
    expected = {
        "path": "exports/titan-current.tar.gz",
        "entrypoint": "main.py::agent",
        "config": "TITAN-CONFIG.json",
        "sha256": ARCHIVE_SHA256,
        "bytes": ARCHIVE_BYTES,
        "runtime_files": RUNTIME_FILES,
        "source_manifest": "runtime/integrated-selected/CURRENT-SOURCE.json",
        "source_manifest_sha256": SOURCE_SHA256,
    }
    if value != expected:
        raise ValueError("CURRENT-ARCHIVE.json differs from the pinned current-V5 contract")
    return value


def _safe_member(name: Any) -> PurePosixPath:
    if type(name) is not str or not name or "\\" in name:
        raise ValueError(f"unsafe archive member: {name!r}")
    rel = PurePosixPath(name)
    if rel.is_absolute() or rel.as_posix() != name or any(part in ("", ".", "..") for part in rel.parts):
        raise ValueError(f"unsafe archive member: {name!r}")
    return rel


def _materialize_archive_snapshot(destination: Path) -> dict[str, Any]:
    """Authenticate current archive once, then extract only that immutable buffer."""
    pointer = _pointer_contract()
    archive_bytes = ARCHIVE.read_bytes()
    if len(archive_bytes) != pointer["bytes"]:
        raise ValueError("current archive byte count differs from pointer")
    actual = sha256(archive_bytes)
    if actual != ARCHIVE_SHA256:
        raise ValueError(f"current archive SHA256 mismatch: expected {ARCHIVE_SHA256}, got {actual}")
    if destination.exists():
        raise FileExistsError(destination)
    destination.mkdir(parents=True)
    seen: set[str] = set()
    total = count = 0
    try:
        with tarfile.open(fileobj=io.BytesIO(archive_bytes), mode="r:gz") as archive:
            for member in archive:
                rel = _safe_member(member.name)
                if member.isdir():
                    continue
                if not member.isfile() or member.name in seen:
                    raise ValueError(f"non-file or duplicate archive member: {member.name}")
                if member.size < 0 or member.size > MAX_ARCHIVE_MEMBER:
                    raise ValueError(f"archive member outside size bound: {member.name}")
                count += 1
                total += member.size
                if count > MAX_ARCHIVE_FILES or total > MAX_ARCHIVE_TOTAL:
                    raise ValueError("current archive exceeds custody bounds")
                stream = archive.extractfile(member)
                if stream is None:
                    raise ValueError(f"cannot read archive member: {member.name}")
                data = stream.read(MAX_ARCHIVE_MEMBER + 1)
                if len(data) != member.size:
                    raise ValueError(f"archive member size changed: {member.name}")
                target = destination.joinpath(*rel.parts)
                target.parent.mkdir(parents=True, exist_ok=True)
                with target.open("xb") as output:
                    output.write(data)
                seen.add(member.name)
    except BaseException:
        shutil.rmtree(destination, ignore_errors=True)
        raise
    if "SOURCE.json" not in seen or "main.py" not in seen or "TITAN-CONFIG.json" not in seen:
        shutil.rmtree(destination, ignore_errors=True)
        raise ValueError("current archive is missing canonical runtime members")
    if count != RUNTIME_FILES + 1:
        shutil.rmtree(destination, ignore_errors=True)
        raise ValueError("current archive member count differs from runtime closure + SOURCE.json")
    return {"sha256": actual, "bytes": len(archive_bytes), "members": count}


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(str(path))
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:
        sys.modules.pop(name, None)
        raise
    return module


def _load_native_census_snapshot(root: Path):
    native = _capture_pinned(NATIVE_CENSUS, NATIVE_CENSUS_GIT_BLOB, "native_census.py")
    unitpipe = _capture_pinned(UNITPIPE, UNITPIPE_GIT_BLOB, "unit_pipeline_admission.py")
    root.mkdir()
    (root / "native_census.py").write_bytes(native)
    (root / "unit_pipeline_admission.py").write_bytes(unitpipe)
    return _load_module(root / "native_census.py", "titan_v5_plantquorum_native_census")


def _load_observer_snapshot(root: Path):
    observer = _capture_pinned(OBSERVER, OBSERVER_GIT_BLOB, "census.py")
    root.mkdir()
    (root / "census.py").write_bytes(observer)
    return _load_module(root / "census.py", "titan_v5_plantquorum_observer")


def _current_runtime(temp: Path):
    package = temp / "current-runtime"
    native = _load_native_census_snapshot(temp / "native-support")
    observer = _load_observer_snapshot(temp / "observer-support")
    archive_receipt = _materialize_archive_snapshot(package)
    capture = native._capture_native_runtime(
        package,
        required_git_blobs=REQUIRED_RUNTIME_GIT_BLOBS,
        required_source_sha256=SOURCE_SHA256,
    )
    runtime = capture["manifest"].get("runtime")
    if type(runtime) is not dict or len(runtime) != RUNTIME_FILES:
        raise ValueError("captured current runtime file count differs from pointer")
    engine, ev, main = native._load_fixture_from_capture(capture)
    authority, provenance = observer.load_authority(
        theorem_path=PLANTQUORUM,
        engine_path=package / "checks/reference/engine/kaggriculture.py",
    )
    if provenance.get("theorem_git_blob") != PLANTQUORUM_GIT_BLOB:
        raise ValueError("observer did not bind canonical PLANTQUORUM theorem")
    if provenance.get("engine_git_blob") != ENGINE_GIT_BLOB:
        raise ValueError("observer did not bind packaged official engine")
    return archive_receipt, engine, ev, main, observer, authority, provenance


def _exact_int(value: Any, label: str, *, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise ValueError(f"{label} must be an exact integer >= {minimum}")
    return value


def run_cell(seed: int, seat: int) -> dict[str, Any]:
    _exact_int(seed, "seed")
    if type(seat) is not int or seat not in PANEL_SEATS:
        raise ValueError("seat must be exact int 0 or 1")
    with tempfile.TemporaryDirectory(prefix="titan-v5-plantquorum-") as directory:
        (archive_receipt, engine, ev, main,
         observer, authority, provenance) = _current_runtime(Path(directory))
        cfg = ev.Struct({
            key: (value.get("default") if isinstance(value, dict) else value)
            for key, value in engine.specification["configuration"].items()
        })
        cfg.seed = seed
        env = ev.Struct(configuration=cfg, done=False, info={})
        state = [
            ev.Struct(observation=ev.Struct(), action={}, status="ACTIVE", reward=0)
            for _ in range(2)
        ]
        engine.interpreter(state, env)

        callbacks = engagements = 0
        examples: list[dict[str, Any]] = []
        for step in range(int(cfg.episodeSteps)):
            actions = []
            for player in range(2):
                state[player].observation.step = step
                state[player].observation.remainingOverageTime = 0
                if player == seat:
                    observation = state[player].observation
                    action = main.agent(copy.deepcopy(observation), cfg)
                    callbacks += 1
                    control, witness = observer.observe_with_authority(
                        authority, provenance, observation, action
                    )
                    if control != action:
                        raise ValueError("observer control differs from current-V5 return")
                    if witness.get("control_action_preserved") is not True:
                        raise ValueError("observer did not certify baseline control preservation")
                    if witness.get("changed") is True:
                        engagements += 1
                        if len(examples) < MAX_EXAMPLES:
                            examples.append({"step": step, **copy.deepcopy(witness)})
                    # Critical: candidate/control copies are evidence only. The exact
                    # original current-V5 return is what reaches official gameplay.
                    actions.append(action)
                else:
                    actions.append(engine.starter_agent(copy.deepcopy(state[player].observation)))
            for player, action in enumerate(actions):
                state[player].action = action
            engine.interpreter(state, env)
            if all(player.status == "DONE" for player in state):
                break

        return {
            "schema": CELL_SCHEMA,
            "source": copy.deepcopy(EXPECTED_SOURCE),
            "archive_receipt": archive_receipt,
            "seed": seed,
            "seat": seat,
            "callbacks": callbacks,
            "engagements": engagements,
            "candidate_applied_to_gameplay": False,
            "examples": examples,
            "scores": [player.reward for player in state],
        }


def _finite_number(value: Any, label: str) -> float | int:
    if type(value) not in (int, float) or (type(value) is float and not math.isfinite(value)):
        raise ValueError(f"{label} must be a finite exact int/float")
    return value


def _validate_cell(cell: Any) -> tuple[int, int, int]:
    if type(cell) is not dict or cell.get("schema") != CELL_SCHEMA:
        raise ValueError("cell schema mismatch")
    if cell.get("source") != EXPECTED_SOURCE:
        raise ValueError("cell source identity mismatch")
    receipt = cell.get("archive_receipt")
    if receipt != {"sha256": ARCHIVE_SHA256, "bytes": ARCHIVE_BYTES, "members": RUNTIME_FILES + 1}:
        raise ValueError("cell archive receipt mismatch")
    seed = _exact_int(cell.get("seed"), "cell seed")
    seat = cell.get("seat")
    if type(seat) is not int or seat not in PANEL_SEATS:
        raise ValueError("cell seat must be exact int 0 or 1")
    callbacks = _exact_int(cell.get("callbacks"), "cell callbacks")
    if callbacks != EXPECTED_CALLBACKS:
        raise ValueError(f"cell callbacks must equal {EXPECTED_CALLBACKS}")
    engagements = _exact_int(cell.get("engagements"), "cell engagements")
    if engagements > callbacks:
        raise ValueError("cell engagements exceed callbacks")
    if cell.get("candidate_applied_to_gameplay") is not False:
        raise ValueError("evidence cell claims candidate gameplay mutation")
    examples = cell.get("examples")
    if type(examples) is not list or len(examples) > MAX_EXAMPLES:
        raise ValueError("cell examples malformed or over limit")
    if engagements and not examples:
        raise ValueError("engaged cell has no witness example")
    scores = cell.get("scores")
    if type(scores) is not list or len(scores) != 2:
        raise ValueError("cell scores must contain exactly two values")
    for index, score in enumerate(scores):
        _finite_number(score, f"cell score {index}")
    return seed, seat, engagements


def aggregate_cells(cells: list[dict[str, Any]]) -> dict[str, Any]:
    expected = {(seed, seat) for seed in PANEL_SEEDS for seat in PANEL_SEATS}
    if type(cells) is not list or len(cells) != len(expected):
        raise ValueError(f"panel requires exactly {len(expected)} cells")
    seen: set[tuple[int, int]] = set()
    engagements = engaged_cells = 0
    examples: list[dict[str, Any]] = []
    for cell in cells:
        seed, seat, count = _validate_cell(cell)
        coord = (seed, seat)
        if coord not in expected:
            raise ValueError(f"unexpected panel coordinate: {coord}")
        if coord in seen:
            raise ValueError(f"duplicate panel coordinate: {coord}")
        seen.add(coord)
        engagements += count
        engaged_cells += int(count > 0)
        for example in cell["examples"]:
            if len(examples) >= MAX_EXAMPLES:
                break
            examples.append({"seed": seed, "seat": seat, **copy.deepcopy(example)})
    if seen != expected:
        raise ValueError(f"panel coordinate mismatch; missing={sorted(expected-seen)!r}")
    return {
        "schema": PANEL_SCHEMA,
        "source": copy.deepcopy(EXPECTED_SOURCE),
        "panel": {"seeds": list(PANEL_SEEDS), "seats": list(PANEL_SEATS)},
        "cells": len(cells),
        "callbacks": len(cells) * EXPECTED_CALLBACKS,
        "engaged_cells": engaged_cells,
        "engagements": engagements,
        "candidate_applied_to_gameplay": False,
        "verdict": "ENGAGED_CURRENT_NATIVE_STARTER" if engagements else "NO_STARTER_ENGAGEMENT",
        "interpretation": (
            "Route engaged witnesses to matched official-engine OFF/ON economics before any production hook."
            if engagements
            else "Starter-opponent panel only; widen natural census before declaring the lane globally COLD."
        ),
        "examples": examples,
    }


def _write_new_json(path: Path, value: Any) -> None:
    path = Path(path)
    if path.exists():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n").encode("utf-8")
    temporary = path.with_name("." + path.name + ".tmp")
    with temporary.open("xb") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    cell = sub.add_parser("cell", help="run one current-V5 seed/seat engagement cell")
    cell.add_argument("--seed", type=int, required=True)
    cell.add_argument("--seat", type=int, choices=PANEL_SEATS, required=True)
    cell.add_argument("--output", type=Path, required=True)
    panel = sub.add_parser("aggregate", help="strictly aggregate the fixed 8x2 panel")
    panel.add_argument("--output", type=Path, required=True)
    panel.add_argument("cells", type=Path, nargs="+")
    args = parser.parse_args()

    result = (
        run_cell(args.seed, args.seat)
        if args.command == "cell"
        else aggregate_cells([_strict_json_file(path) for path in args.cells])
    )
    _write_new_json(args.output, result)
    print(json.dumps({
        key: result[key]
        for key in ("schema", "seed", "seat", "callbacks", "engagements", "verdict")
        if key in result
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
