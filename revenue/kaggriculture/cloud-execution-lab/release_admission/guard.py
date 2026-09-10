#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Fail-closed admission control for Titan's canonical archive pointer.

The guard compares a trusted base checkout with a candidate checkout.  It allows
an unchanged release, an exact rollback to the measured champion, or a new
champion only when a complete paired-game gate report is present, hash-bound to
all of its inputs, and reproducible with the gate implementation from the base
checkout.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import subprocess
import sys
import tempfile
from typing import Any, Callable, Mapping, Sequence

SCHEMA_VERSION = 1
MAX_JSON_BYTES = 2 * 1024 * 1024
MAX_GAMES_BYTES = 1024 * 1024 * 1024
LAB_REL = PurePosixPath("revenue/kaggriculture/cloud-execution-lab")
POINTER_REL = LAB_REL / "runtime/integrated-selected/CURRENT-ARCHIVE.json"
POLICY_REL = LAB_REL / "release_admission/POLICY.json"
CHAMPION_REL = LAB_REL / "release_admission/CHAMPION.json"

HEX64 = 64


class AdmissionError(ValueError):
    """The proposed release transition is not admissible."""


def _reject_constant(value: str) -> None:
    raise AdmissionError(f"non-finite JSON constant {value!r}")


def _unique_object(pairs: Sequence[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise AdmissionError(f"duplicate JSON object key {key!r}")
        result[key] = value
    return result


def strict_loads(text: str, *, label: str) -> Any:
    try:
        return json.loads(
            text,
            parse_constant=_reject_constant,
            object_pairs_hook=_unique_object,
        )
    except AdmissionError:
        raise
    except json.JSONDecodeError as exc:
        raise AdmissionError(
            f"{label}: malformed JSON at line {exc.lineno}, column {exc.colno}: {exc.msg}"
        ) from exc


def _require_keys(obj: Mapping[str, Any], keys: set[str], *, label: str) -> None:
    missing = sorted(keys - set(obj))
    extra = sorted(set(obj) - keys)
    if missing or extra:
        raise AdmissionError(f"{label}: keys mismatch; missing={missing}, extra={extra}")


def _hex64(value: Any, *, label: str) -> str:
    if not isinstance(value, str) or len(value) != HEX64:
        raise AdmissionError(f"{label}: expected 64 hexadecimal characters")
    try:
        int(value, 16)
    except ValueError as exc:
        raise AdmissionError(f"{label}: expected hexadecimal characters") from exc
    return value.lower()


def _git_object(value: Any, *, label: str) -> str:
    if not isinstance(value, str) or len(value) not in (40, 64):
        raise AdmissionError(f"{label}: expected 40 or 64 hexadecimal characters")
    try:
        int(value, 16)
    except ValueError as exc:
        raise AdmissionError(f"{label}: expected hexadecimal characters") from exc
    return value.lower()


def _positive_int(value: Any, *, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise AdmissionError(f"{label}: expected a positive integer")
    return value


def _relative_path(value: Any, *, label: str) -> PurePosixPath:
    if not isinstance(value, str) or not value:
        raise AdmissionError(f"{label}: expected a non-empty relative POSIX path")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or "." in path.parts or "" in path.parts:
        raise AdmissionError(f"{label}: unsafe relative path {value!r}")
    if "\\" in value:
        raise AdmissionError(f"{label}: backslashes are not accepted")
    return path


def _under_lab(value: Any, *, label: str) -> PurePosixPath:
    path = _relative_path(value, label=label)
    return LAB_REL / path


def _candidate_file(root: Path, relative: PurePosixPath, *, label: str, max_bytes: int) -> Path:
    root = root.resolve(strict=True)
    raw = root.joinpath(*relative.parts)
    current = root
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise AdmissionError(f"{label}: symbolic links are not accepted ({relative})")
    try:
        resolved = raw.resolve(strict=True)
    except OSError as exc:
        raise AdmissionError(f"{label}: missing or unreadable file {relative}: {exc}") from exc
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise AdmissionError(f"{label}: path escapes checkout: {relative}") from exc
    if not resolved.is_file():
        raise AdmissionError(f"{label}: expected a regular file: {relative}")
    size = resolved.stat().st_size
    if size > max_bytes:
        raise AdmissionError(f"{label}: {size} bytes exceeds limit {max_bytes}")
    return resolved


def _optional_file(root: Path, relative: PurePosixPath) -> Path | None:
    path = root.joinpath(*relative.parts)
    if not path.exists() and not path.is_symlink():
        return None
    return _candidate_file(root, relative, label=str(relative), max_bytes=MAX_JSON_BYTES)


def _read_json(root: Path, relative: PurePosixPath, *, label: str) -> dict[str, Any]:
    path = _candidate_file(root, relative, label=label, max_bytes=MAX_JSON_BYTES)
    obj = strict_loads(path.read_text(encoding="utf-8"), label=label)
    if not isinstance(obj, dict):
        raise AdmissionError(f"{label}: top level must be an object")
    return obj


def _read_optional_json(root: Path, relative: PurePosixPath, *, label: str) -> dict[str, Any] | None:
    if _optional_file(root, relative) is None:
        return None
    return _read_json(root, relative, label=label)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _validate_policy(obj: Mapping[str, Any]) -> dict[str, Any]:
    _require_keys(
        obj,
        {
            "schema_version",
            "pointer_path",
            "champion_path",
            "gate_tool_path",
            "bootstrap_champion",
            "minimum_grid",
            "required_checks",
        },
        label="policy",
    )
    if obj["schema_version"] != SCHEMA_VERSION:
        raise AdmissionError(f"policy.schema_version must equal {SCHEMA_VERSION}")
    pointer_path = _relative_path(obj["pointer_path"], label="policy.pointer_path")
    champion_path = _relative_path(obj["champion_path"], label="policy.champion_path")
    gate_tool_path = _relative_path(obj["gate_tool_path"], label="policy.gate_tool_path")
    if pointer_path != POINTER_REL:
        raise AdmissionError(f"policy.pointer_path must equal {POINTER_REL}")
    if champion_path != CHAMPION_REL:
        raise AdmissionError(f"policy.champion_path must equal {CHAMPION_REL}")
    if not gate_tool_path.parts[: len(LAB_REL.parts)] == LAB_REL.parts:
        raise AdmissionError("policy.gate_tool_path must remain inside the Titan lab")

    bootstrap = obj["bootstrap_champion"]
    if not isinstance(bootstrap, dict):
        raise AdmissionError("policy.bootstrap_champion must be an object")
    _require_keys(
        bootstrap,
        {"champion_name", "archive_path", "archive_sha256", "status"},
        label="policy.bootstrap_champion",
    )
    if not isinstance(bootstrap["champion_name"], str) or not bootstrap["champion_name"].strip():
        raise AdmissionError("policy.bootstrap_champion.champion_name must be non-empty")
    archive_path = _relative_path(
        bootstrap["archive_path"], label="policy.bootstrap_champion.archive_path"
    )
    archive_sha = _hex64(
        bootstrap["archive_sha256"], label="policy.bootstrap_champion.archive_sha256"
    )
    expected_historical = PurePosixPath(f"exports/historical/titan-{archive_sha}.tar.gz")
    if archive_path != expected_historical:
        raise AdmissionError(
            "policy.bootstrap_champion.archive_path must be the content-addressed historical archive"
        )
    if bootstrap["status"] != "grandfathered_submitted_baseline":
        raise AdmissionError(
            "policy.bootstrap_champion.status must equal grandfathered_submitted_baseline"
        )

    grid = obj["minimum_grid"]
    if not isinstance(grid, dict):
        raise AdmissionError("policy.minimum_grid must be an object")
    _require_keys(grid, {"seeds", "opponents", "seats", "expected_cells"}, label="policy.minimum_grid")
    seats = grid["seats"]
    if not isinstance(seats, list) or len(seats) != 2 or set(seats) != {0, 1}:
        raise AdmissionError("policy.minimum_grid.seats must contain exactly [0, 1]")
    minimum_grid = {
        "seeds": _positive_int(grid["seeds"], label="policy.minimum_grid.seeds"),
        "opponents": _positive_int(grid["opponents"], label="policy.minimum_grid.opponents"),
        "seats": [0, 1],
        "expected_cells": _positive_int(
            grid["expected_cells"], label="policy.minimum_grid.expected_cells"
        ),
    }
    cartesian_floor = minimum_grid["seeds"] * minimum_grid["opponents"] * 2
    if minimum_grid["expected_cells"] < cartesian_floor:
        raise AdmissionError(
            "policy.minimum_grid.expected_cells cannot be below seeds * opponents * two seats"
        )

    checks = obj["required_checks"]
    if not isinstance(checks, list) or not checks:
        raise AdmissionError("policy.required_checks must be a non-empty list")
    normalized_checks: list[str] = []
    seen: set[str] = set()
    for index, value in enumerate(checks):
        if not isinstance(value, str) or not value.strip():
            raise AdmissionError(f"policy.required_checks[{index}] must be a non-empty string")
        if value in seen:
            raise AdmissionError(f"policy.required_checks contains duplicate {value!r}")
        seen.add(value)
        normalized_checks.append(value)

    return {
        "schema_version": SCHEMA_VERSION,
        "pointer_path": str(pointer_path),
        "champion_path": str(champion_path),
        "gate_tool_path": str(gate_tool_path),
        "bootstrap_champion": {
            "champion_name": bootstrap["champion_name"],
            "archive_path": str(archive_path),
            "archive_sha256": archive_sha,
            "status": bootstrap["status"],
        },
        "minimum_grid": minimum_grid,
        "required_checks": normalized_checks,
    }


def _policy_not_weakened(base: Mapping[str, Any], head: Mapping[str, Any]) -> None:
    for key in ("schema_version", "pointer_path", "champion_path", "gate_tool_path", "bootstrap_champion"):
        if base[key] != head[key]:
            raise AdmissionError(f"policy.{key} is immutable after bootstrap")
    for key in ("seeds", "opponents", "expected_cells"):
        if head["minimum_grid"][key] < base["minimum_grid"][key]:
            raise AdmissionError(f"policy.minimum_grid.{key} cannot be weakened")
    if set(head["required_checks"]) < set(base["required_checks"]):
        removed = sorted(set(base["required_checks"]) - set(head["required_checks"]))
        raise AdmissionError(f"policy.required_checks cannot remove checks: {removed}")


def _validate_pointer(obj: Mapping[str, Any], *, label: str) -> dict[str, Any]:
    keys = {
        "path", "entrypoint", "config", "sha256", "bytes", "runtime_files",
        "source_manifest", "source_manifest_sha256",
    }
    _require_keys(obj, keys, label=label)
    archive_path = _relative_path(obj["path"], label=f"{label}.path")
    source_manifest = _relative_path(obj["source_manifest"], label=f"{label}.source_manifest")
    if archive_path != PurePosixPath("exports/titan-current.tar.gz"):
        raise AdmissionError(f"{label}.path must equal exports/titan-current.tar.gz")
    if obj["entrypoint"] != "main.py::agent":
        raise AdmissionError(f"{label}.entrypoint must equal main.py::agent")
    if obj["config"] != "TITAN-CONFIG.json":
        raise AdmissionError(f"{label}.config must equal TITAN-CONFIG.json")
    if source_manifest != PurePosixPath("runtime/integrated-selected/CURRENT-SOURCE.json"):
        raise AdmissionError(
            f"{label}.source_manifest must equal runtime/integrated-selected/CURRENT-SOURCE.json"
        )
    archive_bytes = _positive_int(obj["bytes"], label=f"{label}.bytes")
    runtime_files = _positive_int(obj["runtime_files"], label=f"{label}.runtime_files")
    return {
        "path": str(archive_path),
        "entrypoint": obj["entrypoint"],
        "config": obj["config"],
        "sha256": _hex64(obj["sha256"], label=f"{label}.sha256"),
        "bytes": archive_bytes,
        "runtime_files": runtime_files,
        "source_manifest": str(source_manifest),
        "source_manifest_sha256": _hex64(
            obj["source_manifest_sha256"], label=f"{label}.source_manifest_sha256"
        ),
    }


def _verify_pointer_files(root: Path, pointer: Mapping[str, Any], *, label: str) -> dict[str, Any]:
    archive = _candidate_file(
        root,
        LAB_REL / _relative_path(pointer["path"], label=f"{label}.path"),
        label=f"{label} archive",
        max_bytes=max(pointer["bytes"], 1),
    )
    size = archive.stat().st_size
    if size != pointer["bytes"]:
        raise AdmissionError(f"{label} archive size mismatch: pointer={pointer['bytes']}, file={size}")
    digest = _sha256(archive)
    if digest != pointer["sha256"]:
        raise AdmissionError(f"{label} archive SHA-256 mismatch: pointer={pointer['sha256']}, file={digest}")
    source = _candidate_file(
        root,
        LAB_REL / _relative_path(pointer["source_manifest"], label=f"{label}.source_manifest"),
        label=f"{label} source manifest",
        max_bytes=MAX_JSON_BYTES,
    )
    source_digest = _sha256(source)
    if source_digest != pointer["source_manifest_sha256"]:
        raise AdmissionError(
            f"{label} source-manifest SHA-256 mismatch: "
            f"pointer={pointer['source_manifest_sha256']}, file={source_digest}"
        )
    source_obj = strict_loads(source.read_text(encoding="utf-8"), label=f"{label} source manifest")
    if not isinstance(source_obj, dict):
        raise AdmissionError(f"{label} source manifest top level must be an object")
    current = source_obj.get("current")
    if not isinstance(current, dict):
        raise AdmissionError(f"{label} source manifest must contain a current object")
    expected_current = {
        "archive": pointer["path"],
        "configuration": pointer["config"],
        "entrypoint": pointer["entrypoint"],
        "manifest": pointer["source_manifest"],
        "receipt": "runtime/integrated-selected/CURRENT-ARCHIVE.json",
    }
    for key, expected in expected_current.items():
        if current.get(key) != expected:
            raise AdmissionError(
                f"{label} source manifest current.{key} mismatch: "
                f"expected={expected!r}, observed={current.get(key)!r}"
            )
    return source_obj


def _validate_manifest_admission(
    source_manifest: Mapping[str, Any],
    *,
    mode: str,
    archive_sha: str,
    previous_pointer_sha: str,
    champion_sha: str,
    evidence_dir: str | None,
    minimum_games: int | None,
) -> None:
    admission = source_manifest.get("release_admission")
    if not isinstance(admission, dict):
        raise AdmissionError("candidate source manifest must contain release_admission metadata")
    _require_keys(
        admission,
        {
            "schema_version", "mode", "archive_sha256", "previous_pointer_sha256",
            "champion_sha256", "evidence_dir",
        },
        label="source manifest release_admission",
    )
    expected = {
        "schema_version": SCHEMA_VERSION,
        "mode": mode,
        "archive_sha256": archive_sha,
        "previous_pointer_sha256": previous_pointer_sha,
        "champion_sha256": champion_sha,
        "evidence_dir": evidence_dir,
    }
    if admission != expected:
        raise AdmissionError(
            "candidate source manifest release_admission metadata does not match the proposed transition"
        )
    if minimum_games is not None:
        game_evidence = source_manifest.get("game_evidence_for_this_archive")
        if not isinstance(game_evidence, dict):
            raise AdmissionError(
                "measured promotion source manifest must contain game_evidence_for_this_archive"
            )
        observed = game_evidence.get("new_full_games")
        if isinstance(observed, bool) or not isinstance(observed, int) or observed < minimum_games:
            raise AdmissionError(
                "source manifest new_full_games is below the measured promotion panel size"
            )


def _validate_champion(obj: Mapping[str, Any], *, label: str) -> dict[str, Any]:
    _require_keys(
        obj,
        {
            "schema_version", "champion_name", "archive_path", "archive_sha256",
            "source_manifest_sha256", "previous_champion_sha256",
            "promotion_evidence_dir", "status",
        },
        label=label,
    )
    if obj["schema_version"] != SCHEMA_VERSION:
        raise AdmissionError(f"{label}.schema_version must equal {SCHEMA_VERSION}")
    if not isinstance(obj["champion_name"], str) or not obj["champion_name"].strip():
        raise AdmissionError(f"{label}.champion_name must be non-empty")
    archive_sha = _hex64(obj["archive_sha256"], label=f"{label}.archive_sha256")
    archive_path = _relative_path(obj["archive_path"], label=f"{label}.archive_path")
    expected = PurePosixPath(f"exports/historical/titan-{archive_sha}.tar.gz")
    if archive_path != expected:
        raise AdmissionError(f"{label}.archive_path must equal {expected}")
    status = obj["status"]
    if status not in {"grandfathered_submitted_baseline", "measured_promotion"}:
        raise AdmissionError(f"{label}.status is unsupported: {status!r}")

    source_sha = obj["source_manifest_sha256"]
    previous_sha = obj["previous_champion_sha256"]
    evidence_dir = obj["promotion_evidence_dir"]
    if status == "grandfathered_submitted_baseline":
        if any(value is not None for value in (source_sha, previous_sha, evidence_dir)):
            raise AdmissionError(
                f"{label}: grandfathered baseline must have null source, previous, and evidence fields"
            )
    else:
        source_sha = _hex64(source_sha, label=f"{label}.source_manifest_sha256")
        previous_sha = _hex64(previous_sha, label=f"{label}.previous_champion_sha256")
        evidence = _relative_path(evidence_dir, label=f"{label}.promotion_evidence_dir")
        expected_dir = PurePosixPath(f"release_admission/evidence/{archive_sha}")
        if evidence != expected_dir:
            raise AdmissionError(f"{label}.promotion_evidence_dir must equal {expected_dir}")
        evidence_dir = str(evidence)

    return {
        "schema_version": SCHEMA_VERSION,
        "champion_name": obj["champion_name"],
        "archive_path": str(archive_path),
        "archive_sha256": archive_sha,
        "source_manifest_sha256": source_sha,
        "previous_champion_sha256": previous_sha,
        "promotion_evidence_dir": evidence_dir,
        "status": status,
    }


def _verify_champion_archive(root: Path, champion: Mapping[str, Any], *, label: str) -> None:
    path = _candidate_file(
        root,
        LAB_REL / _relative_path(champion["archive_path"], label=f"{label}.archive_path"),
        label=f"{label} archive",
        max_bytes=1024 * 1024 * 1024,
    )
    digest = _sha256(path)
    if digest != champion["archive_sha256"]:
        raise AdmissionError(
            f"{label} archive SHA-256 mismatch: ledger={champion['archive_sha256']}, file={digest}"
        )


def _validate_gate_report(
    report: Mapping[str, Any],
    *,
    policy: Mapping[str, Any],
    baseline_sha: str,
    candidate_sha: str,
) -> None:
    _require_keys(
        report,
        {
            "schema_version", "verdict", "valid", "panel_id", "baseline_name",
            "candidate_name", "input_sha256", "input_bytes", "input_binding",
            "provenance", "exact_command", "grid", "policy", "checks", "metrics",
        },
        label="gate report",
    )
    if report["schema_version"] != SCHEMA_VERSION:
        raise AdmissionError("gate report schema_version must equal 1")
    if report["valid"] is not True or report["verdict"] != "PROMOTE":
        raise AdmissionError("gate report must be valid=true and verdict=PROMOTE")
    for key in ("panel_id", "baseline_name", "candidate_name", "exact_command"):
        if not isinstance(report[key], str) or not report[key].strip():
            raise AdmissionError(f"gate report {key} must be non-empty")

    provenance = report["provenance"]
    if not isinstance(provenance, dict):
        raise AdmissionError("gate report provenance must be an object")
    _require_keys(
        provenance,
        {
            "engine_commit", "engine_sha256", "runner_commit", "runner_sha256",
            "baseline_artifact_sha256", "candidate_artifact_sha256",
        },
        label="gate report provenance",
    )
    for key in ("engine_commit", "runner_commit"):
        _git_object(provenance[key], label=f"gate report provenance.{key}")
    for key in ("engine_sha256", "runner_sha256", "baseline_artifact_sha256", "candidate_artifact_sha256"):
        _hex64(provenance[key], label=f"gate report provenance.{key}")
    if provenance["baseline_artifact_sha256"].lower() != baseline_sha:
        raise AdmissionError("gate report baseline artifact does not equal the measured champion")
    if provenance["candidate_artifact_sha256"].lower() != candidate_sha:
        raise AdmissionError("gate report candidate artifact does not equal the proposed pointer")

    grid = report["grid"]
    if not isinstance(grid, dict):
        raise AdmissionError("gate report grid must be an object")
    _require_keys(
        grid,
        {"seeds", "opponents", "seats", "expected_cells", "observed_baseline_cells", "observed_candidate_cells"},
        label="gate report grid",
    )
    seeds, opponents, seats = grid["seeds"], grid["opponents"], grid["seats"]
    if not isinstance(seeds, list) or not seeds or len(set(seeds)) != len(seeds):
        raise AdmissionError("gate report grid seeds must be non-empty and unique")
    if any(isinstance(seed, bool) or not isinstance(seed, int) for seed in seeds):
        raise AdmissionError("gate report grid seeds must be integers")
    if not isinstance(opponents, list) or not opponents or len(set(opponents)) != len(opponents):
        raise AdmissionError("gate report grid opponents must be non-empty and unique")
    if any(not isinstance(value, str) or not value for value in opponents):
        raise AdmissionError("gate report grid opponents must be non-empty strings")
    if not isinstance(seats, list) or len(seats) != 2 or set(seats) != {0, 1}:
        raise AdmissionError("gate report grid must contain both candidate seats")
    expected = len(seeds) * len(opponents) * 2
    if grid["expected_cells"] != expected:
        raise AdmissionError("gate report expected_cells is not the exact Cartesian grid size")
    if grid["observed_baseline_cells"] != expected or grid["observed_candidate_cells"] != expected:
        raise AdmissionError("gate report does not contain a complete baseline/candidate grid")
    minimum = policy["minimum_grid"]
    if len(seeds) < minimum["seeds"]:
        raise AdmissionError("gate report seed count is below the admission floor")
    if len(opponents) < minimum["opponents"]:
        raise AdmissionError("gate report opponent count is below the admission floor")
    if expected < minimum["expected_cells"]:
        raise AdmissionError("gate report cell count is below the admission floor")

    checks = report["checks"]
    if not isinstance(checks, list) or not checks:
        raise AdmissionError("gate report checks must be a non-empty list")
    by_name: dict[str, Mapping[str, Any]] = {}
    for index, check in enumerate(checks):
        if not isinstance(check, dict):
            raise AdmissionError(f"gate report checks[{index}] must be an object")
        name = check.get("name")
        if not isinstance(name, str) or not name:
            raise AdmissionError(f"gate report checks[{index}] has no valid name")
        if name in by_name:
            raise AdmissionError(f"gate report contains duplicate check {name!r}")
        if check.get("pass") is not True:
            raise AdmissionError(f"gate report check did not pass: {name}")
        by_name[name] = check
    missing_checks = sorted(set(policy["required_checks"]) - set(by_name))
    if missing_checks:
        raise AdmissionError(f"gate report is missing required checks: {missing_checks}")

    hashes = report["input_sha256"]
    if not isinstance(hashes, dict):
        raise AdmissionError("gate report input_sha256 must be an object")
    _require_keys(
        hashes,
        {"contract", "evidence", "baseline_games", "candidate_games"},
        label="gate report input_sha256",
    )
    for key, value in hashes.items():
        _hex64(value, label=f"gate report input_sha256.{key}")

    sizes = report["input_bytes"]
    if not isinstance(sizes, dict):
        raise AdmissionError("gate report input_bytes must be an object")
    _require_keys(
        sizes,
        {"contract", "evidence", "baseline_games", "candidate_games"},
        label="gate report input_bytes",
    )
    for key, value in sizes.items():
        _positive_int(value, label=f"gate report input_bytes.{key}")
    if report["input_binding"] != (
        "single-open private snapshots; hashes cover exactly parsed bytes"
    ):
        raise AdmissionError("gate report input_binding is not the hardened snapshot contract")


def _verify_evidence_files(
    root: Path,
    champion: Mapping[str, Any],
    report: Mapping[str, Any],
) -> dict[str, Path]:
    evidence_dir = _relative_path(
        champion["promotion_evidence_dir"], label="champion.promotion_evidence_dir"
    )
    names = {
        "contract": "CONTRACT.json",
        "evidence": "PROVENANCE.json",
        "baseline_games": "baseline.GAMES.jsonl",
        "candidate_games": "candidate.GAMES.jsonl",
        "report": "GATE.json",
    }
    paths: dict[str, Path] = {}
    for key, name in names.items():
        limit = MAX_GAMES_BYTES if name.endswith(".jsonl") else MAX_JSON_BYTES
        paths[key] = _candidate_file(
            root,
            LAB_REL / evidence_dir / name,
            label=f"promotion evidence {name}",
            max_bytes=limit,
        )
    expected_hashes = report["input_sha256"]
    for key in ("contract", "evidence", "baseline_games", "candidate_games"):
        observed = _sha256(paths[key])
        if observed != expected_hashes[key].lower():
            raise AdmissionError(
                f"promotion evidence digest mismatch for {key}: report={expected_hashes[key]}, file={observed}"
            )
        observed_bytes = paths[key].stat().st_size
        if observed_bytes != report["input_bytes"][key]:
            raise AdmissionError(
                f"promotion evidence byte-count mismatch for {key}: "
                f"report={report['input_bytes'][key]}, file={observed_bytes}"
            )
    return paths


GateRunner = Callable[[Path, Path, Mapping[str, Path], Mapping[str, Any]], Mapping[str, Any]]


def rerun_trusted_gate(
    base_root: Path,
    candidate_root: Path,
    evidence_paths: Mapping[str, Path],
    policy: Mapping[str, Any],
) -> Mapping[str, Any]:
    tool_rel = _relative_path(policy["gate_tool_path"], label="policy.gate_tool_path")
    gate_tool = _candidate_file(
        base_root, tool_rel, label="trusted paired-game gate", max_bytes=MAX_JSON_BYTES
    )
    with tempfile.TemporaryDirectory(prefix="titan-admission-") as td:
        report_path = Path(td) / "GATE.json"
        command = [
            sys.executable,
            str(gate_tool),
            "--contract", str(evidence_paths["contract"]),
            "--evidence", str(evidence_paths["evidence"]),
            "--baseline", str(evidence_paths["baseline_games"]),
            "--candidate", str(evidence_paths["candidate_games"]),
            "--report", str(report_path),
            "--quiet",
        ]
        env = dict(os.environ)
        env.update(PYTHONDONTWRITEBYTECODE="1", PYTHONHASHSEED="0")
        process = subprocess.run(
            command,
            cwd=gate_tool.parent,
            env=env,
            capture_output=True,
            text=True,
            timeout=180,
            check=False,
        )
        if process.returncode != 0:
            raise AdmissionError(
                "trusted paired-game gate replay did not PROMOTE: "
                f"exit={process.returncode}, stdout={process.stdout[-2000:]!r}, "
                f"stderr={process.stderr[-2000:]!r}"
            )
        replay = strict_loads(report_path.read_text(encoding="utf-8"), label="replayed gate report")
        if not isinstance(replay, dict):
            raise AdmissionError("replayed gate report top level must be an object")
        return replay


def evaluate_transition(
    base_root: Path,
    candidate_root: Path,
    *,
    gate_runner: GateRunner = rerun_trusted_gate,
) -> dict[str, Any]:
    base_root = base_root.resolve(strict=True)
    candidate_root = candidate_root.resolve(strict=True)

    head_policy = _validate_policy(_read_json(candidate_root, POLICY_REL, label="candidate policy"))
    base_policy_obj = _read_optional_json(base_root, POLICY_REL, label="base policy")
    base_policy = _validate_policy(base_policy_obj) if base_policy_obj is not None else None
    if base_policy is not None:
        _policy_not_weakened(base_policy, head_policy)

    base_pointer = _validate_pointer(
        _read_json(base_root, POINTER_REL, label="base pointer"), label="base pointer"
    )
    head_pointer = _validate_pointer(
        _read_json(candidate_root, POINTER_REL, label="candidate pointer"), label="candidate pointer"
    )
    _verify_pointer_files(base_root, base_pointer, label="base pointer")
    head_source_manifest = _verify_pointer_files(
        candidate_root, head_pointer, label="candidate pointer"
    )

    base_champion_obj = _read_optional_json(base_root, CHAMPION_REL, label="base champion")
    head_champion = _validate_champion(
        _read_json(candidate_root, CHAMPION_REL, label="candidate champion"),
        label="candidate champion",
    )
    _verify_champion_archive(candidate_root, head_champion, label="candidate champion")

    pointer_changed = base_pointer != head_pointer
    policy_changed = base_policy is not None and base_policy != head_policy

    if base_champion_obj is None:
        if pointer_changed:
            raise AdmissionError("release pointer cannot change while the admission ledger is bootstrapped")
        expected = head_policy["bootstrap_champion"]
        for key in ("champion_name", "archive_path", "archive_sha256", "status"):
            if head_champion[key] != expected[key]:
                raise AdmissionError(f"bootstrap champion {key} does not match immutable policy")
        if any(
            head_champion[key] is not None
            for key in ("source_manifest_sha256", "previous_champion_sha256", "promotion_evidence_dir")
        ):
            raise AdmissionError("bootstrap champion contains unexpected promotion metadata")
        return {
            "schema_version": SCHEMA_VERSION,
            "valid": True,
            "verdict": "BOOTSTRAP_MEASURED_BASELINE",
            "pointer_changed": False,
            "champion_sha256": head_champion["archive_sha256"],
        }

    base_champion = _validate_champion(base_champion_obj, label="base champion")
    _verify_champion_archive(base_root, base_champion, label="base champion")

    if not pointer_changed:
        if head_champion != base_champion:
            raise AdmissionError("champion ledger cannot change without a release-pointer transition")
        return {
            "schema_version": SCHEMA_VERSION,
            "valid": True,
            "verdict": "UNCHANGED_RELEASE",
            "pointer_changed": False,
            "policy_strengthened": policy_changed,
            "champion_sha256": head_champion["archive_sha256"],
        }

    if policy_changed:
        raise AdmissionError("admission policy cannot change in the same proposal as the release pointer")

    if head_pointer["sha256"] == base_champion["archive_sha256"]:
        if head_champion != base_champion:
            raise AdmissionError("rollback to measured champion must leave the champion ledger unchanged")
        _validate_manifest_admission(
            head_source_manifest,
            mode="rollback_to_measured_champion",
            archive_sha=head_pointer["sha256"],
            previous_pointer_sha=base_pointer["sha256"],
            champion_sha=base_champion["archive_sha256"],
            evidence_dir=None,
            minimum_games=None,
        )
        return {
            "schema_version": SCHEMA_VERSION,
            "valid": True,
            "verdict": "ROLLBACK_TO_MEASURED_CHAMPION",
            "pointer_changed": True,
            "from_sha256": base_pointer["sha256"],
            "to_sha256": head_pointer["sha256"],
            "champion_sha256": base_champion["archive_sha256"],
        }

    if head_champion["status"] != "measured_promotion":
        raise AdmissionError("new pointer requires a measured_promotion champion ledger entry")
    if head_champion["archive_sha256"] != head_pointer["sha256"]:
        raise AdmissionError("promoted champion archive does not equal the proposed release pointer")
    if head_champion["source_manifest_sha256"] != head_pointer["source_manifest_sha256"]:
        raise AdmissionError("promoted champion source manifest does not equal the proposed release pointer")
    if head_champion["previous_champion_sha256"] != base_champion["archive_sha256"]:
        raise AdmissionError("promoted champion does not chain to the measured base champion")

    report_rel = (
        LAB_REL
        / _relative_path(
            head_champion["promotion_evidence_dir"], label="candidate champion promotion_evidence_dir"
        )
        / "GATE.json"
    )
    report = _read_json(candidate_root, report_rel, label="committed gate report")
    _validate_gate_report(
        report,
        policy=head_policy,
        baseline_sha=base_champion["archive_sha256"],
        candidate_sha=head_pointer["sha256"],
    )
    evidence_paths = _verify_evidence_files(candidate_root, head_champion, report)
    replay = gate_runner(base_root, candidate_root, evidence_paths, head_policy)
    if replay != report:
        raise AdmissionError("committed gate report does not exactly match trusted replay output")
    _validate_manifest_admission(
        head_source_manifest,
        mode="measured_promotion",
        archive_sha=head_pointer["sha256"],
        previous_pointer_sha=base_pointer["sha256"],
        champion_sha=head_champion["archive_sha256"],
        evidence_dir=head_champion["promotion_evidence_dir"],
        minimum_games=report["grid"]["expected_cells"],
    )

    return {
        "schema_version": SCHEMA_VERSION,
        "valid": True,
        "verdict": "PROMOTE_MEASURED_CHAMPION",
        "pointer_changed": True,
        "from_pointer_sha256": base_pointer["sha256"],
        "from_champion_sha256": base_champion["archive_sha256"],
        "to_sha256": head_pointer["sha256"],
        "panel_id": report["panel_id"],
        "expected_cells": report["grid"]["expected_cells"],
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-root", required=True, type=Path)
    parser.add_argument("--candidate-root", required=True, type=Path)
    parser.add_argument("--json-output", type=Path)
    args = parser.parse_args(argv)
    try:
        report = evaluate_transition(args.base_root, args.candidate_root)
        code = 0
    except (AdmissionError, OSError, UnicodeError, subprocess.SubprocessError) as exc:
        report = {
            "schema_version": SCHEMA_VERSION,
            "valid": False,
            "verdict": "BLOCK",
            "error": str(exc),
        }
        code = 2
    encoded = json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n"
    print(encoded, end="")
    if args.json_output is not None:
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        args.json_output.write_text(encoded, encoding="utf-8")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
