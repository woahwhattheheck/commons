#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Authenticated current-V5 engagement census for canonical PLANTQUORUM.

This is evidence tooling only.  The current TITAN action is always the action
sent to the official interpreter.  The canonical PLANTQUORUM helper is invoked
on a private copy solely to answer whether its source-certain atomic-PLANT
relief would change the *engine-effective* unit vector.

One process runs one seed/seat.  Aggregate a fixed 8x2 panel separately.  Zero
engagement is reported only as ``NO_STARTER_ENGAGEMENT``; it is not a global
COLD claim and it does not authorize a production hook or default change.
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
import types
from typing import Any, Mapping

HERE = Path(__file__).resolve().parent
LAB = HERE.parents[2]
ARCHIVE = LAB / "exports/titan-current.tar.gz"
POINTER = LAB / "runtime/integrated-selected/CURRENT-ARCHIVE.json"
NATIVE_CENSUS = LAB / "candidates/v4/research/unit-phase-chaining/native_census.py"
UNITPIPE = LAB / "candidates/v4/research/unit-phase-chaining/unit_pipeline_admission.py"
PLANTQUORUM = LAB / "candidates/v4/research/unit-phase-chaining/plant_quorum_admission.py"

BASE_COMMIT = "b9d696d4dd803bc0345f73cdd52cc35346f503f6"
ARCHIVE_SHA256 = "fe67d2daa00ba84348ef364db3b6dea9671d6b01349001e51546874e277adec3"
SOURCE_SHA256 = "8182785b03f3c771901d6124d11b7e04d37c1ddcaabf6174d9748227a91c5526"
RUNTIME_FILES = 116
POINTER_GIT_BLOB = "e041598b2ab31ac370b4d2285fe38477c3aa3f78"
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
    """Read once; the captured bytes, not the live path, become authority."""
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
        "bytes": 466983,
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
    """Authenticate archive bytes once, then extract only that immutable buffer."""
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
    total = 0
    count = 0
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
    """Snapshot the already-reviewed generic custody loader plus its own dependency."""
    native = _capture_pinned(NATIVE_CENSUS, NATIVE_CENSUS_GIT_BLOB, "native_census.py")
    unitpipe = _capture_pinned(UNITPIPE, UNITPIPE_GIT_BLOB, "unit_pipeline_admission.py")
    root.mkdir()
    (root / "native_census.py").write_bytes(native)
    (root / "unit_pipeline_admission.py").write_bytes(unitpipe)
    return _load_module(root / "native_census.py", "titan_v5_plantquorum_native_census")


def _load_plantquorum_snapshot():
    data = _capture_pinned(PLANTQUORUM, PLANTQUORUM_GIT_BLOB, "plant_quorum_admission.py")
    module = types.ModuleType("titan_v5_plantquorum_admission")
    module.__file__ = str(PLANTQUORUM)
    exec(compile(data, str(PLANTQUORUM), "exec"), module.__dict__, module.__dict__)
    if not callable(getattr(module, "relieve_atomic_plant_collateral", None)):
        raise ValueError("captured PLANTQUORUM helper lacks relief function")
    if not callable(getattr(module, "effective_rows_under_engine_preflight", None)):
        raise ValueError("captured PLANTQUORUM helper lacks engine-preflight model")
    return module


def _source_rows(action: Mapping[str, Any]) -> list[Any]:
    hands = action.get("hands", [])
    if not isinstance(hands, list):
        hands = []
    return [copy.deepcopy(action.get("farmer", ["PASS"])), *copy.deepcopy(hands)]


def observe_admission(helper, observation: Mapping[str, Any], action: Mapping[str, Any]) -> dict[str, Any]:
    """Observe candidate semantics on copies; never return an action for gameplay."""
    if not isinstance(action, Mapping):
        raise ValueError("returned action must be a mapping")
    source_action = copy.deepcopy(dict(action))
    player = observation.get("player")
    farms = observation.get("farms")
    private = observation.get("private")
    report_obs = {
        "player": player,
        "farms": copy.deepcopy(farms),
        "private": copy.deepcopy(private),
    }
    candidate, report = helper.relieve_atomic_plant_collateral(
        report_obs, copy.deepcopy(source_action), enabled=True
    )
    if dict(action) != source_action:
        raise ValueError("PLANTQUORUM observation mutated the returned baseline action")
    if not isinstance(report, dict) or report.get("schema") != "titan-v4-plantquorum-admission-v1":
        raise ValueError("PLANTQUORUM report schema mismatch")
    changed = report.get("changed")
    if type(changed) is not bool:
        raise ValueError("PLANTQUORUM changed flag must be exact bool")
    if not changed:
        if candidate != source_action:
            raise ValueError("unchanged PLANTQUORUM report returned changed candidate bytes")
        return {"changed": False, "changed_actors": [], "crops": report.get("crops", [])}

    if candidate == source_action:
        raise ValueError("changed PLANTQUORUM report returned identical candidate")
    seeds = report_obs["private"].get("seeds", {}) if isinstance(report_obs["private"], Mapping) else {}
    before_rows = _source_rows(source_action)
    after_rows = _source_rows(candidate)
    before_effective = helper.effective_rows_under_engine_preflight(before_rows, seeds)
    after_effective = helper.effective_rows_under_engine_preflight(after_rows, seeds)
    if before_effective == after_effective:
        raise ValueError("PLANTQUORUM changed source rows without changing engine preflight")
    if not any(isinstance(row, list) and len(row) >= 2 and row[0] == "PLANT" for row in after_effective):
        raise ValueError("PLANTQUORUM engagement left no effective PLANT survivor")
    changed_actors = report.get("changed_actors")
    if not isinstance(changed_actors, list) or not changed_actors:
        raise ValueError("engaged PLANTQUORUM report lacks changed actors")
    return {
        "changed": True,
        "changed_actors": copy.deepcopy(changed_actors),
        "crops": copy.deepcopy(report.get("crops", [])),
        "source_rows": before_rows,
        "candidate_rows": after_rows,
        "effective_before": before_effective,
        "effective_after": after_effective,
    }


def _current_runtime(temp: Path):
    support = temp / "native-support"
    package = temp / "current-runtime"
    native = _load_native_census_snapshot(support)
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
    plant = _load_plantquorum_snapshot()
    engine_path = package / "checks/reference/engine/kaggriculture.py"
    plant_source = plant.verify_engine_source(engine_path)
    if plant_source.get("engine_blob") != ENGINE_GIT_BLOB:
        raise ValueError("PLANTQUORUM helper did not bind the current packaged engine")
    return archive_receipt, engine, ev, main, plant


def _exact_int(value: Any, label: str, *, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise ValueError(f"{label} must be an exact integer >= {minimum}")
    return value


def run_cell(seed: int, seat: int) -> dict[str, Any]:
    _exact_int(seed, "seed")
    if type(seat) is not int or seat not in PANEL_SEATS:
        raise ValueError("seat must be exact int 0 or 1")
    with tempfile.TemporaryDirectory(prefix="titan-v5-plantquorum-") as directory:
        archive_receipt, engine, ev, main, plant = _current_runtime(Path(directory))
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

        callbacks = 0
        engagements = 0
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
                    witness = observe_admission(plant, observation, action)
                    if witness["changed"]:
                        engagements += 1
                        if len(examples) < MAX_EXAMPLES:
                            examples.append({"step": step, **witness})
                    # Evidence-only invariant: candidate bytes are never placed in
                    # `actions`; only the original current-V5 return reaches engine.
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
    engagements = 0
    engaged_cells = 0
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

    if args.command == "cell":
        result = run_cell(args.seed, args.seat)
    else:
        values = [_strict_json_file(path) for path in args.cells]
        result = aggregate_cells(values)
    _write_new_json(args.output, result)
    print(json.dumps({
        key: result[key]
        for key in ("schema", "seed", "seat", "callbacks", "engagements", "verdict")
        if key in result
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
