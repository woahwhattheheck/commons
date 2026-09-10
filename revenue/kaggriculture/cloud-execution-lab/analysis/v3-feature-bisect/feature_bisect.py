#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Fail-closed, config-only causal bisection for TITAN Kaggriculture agents.

The tool has three stages:

* ``prepare`` safely materializes an immutable TITAN archive and config-only
  variants.  Every non-config member must remain byte-identical.
* ``run`` executes every variant on the same official-evaluator cell grid and
  records resumable, hash-bound receipts.
* ``analyze`` rejects partial or incomparable grids, then produces paired
  outcome/margin/trace deltas and bounded pair-interaction diagnostics.

This is an experiment screen, not a leaderboard or promotion oracle.  A result
can nominate a smaller full panel; it cannot authorize a release by itself.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import statistics
import subprocess
import sys
import tarfile
import tempfile
from typing import Any, Iterable, Mapping, Sequence

SCHEMA_VERSION = 1
CONFIG_MEMBER = "TITAN-CONFIG.json"
ENTRYPOINT_MEMBER = "main.py"
MAX_MEMBER_BYTES = 32 * 1024 * 1024
MAX_ARCHIVE_BYTES = 256 * 1024 * 1024
NAME_RE = re.compile(r"^[a-z0-9][a-z0-9._+-]{0,95}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
ARCHIVE_SHA_RE = re.compile(r"^titan-([0-9a-f]{64})\.tar\.gz$")


class EvidenceError(ValueError):
    """Raised when evidence is malformed, incomplete, or incomparable."""


def canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8")


def pretty_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n").encode("utf-8")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def digest_payload(value: Mapping[str, Any], field: str = "receipt_sha256") -> str:
    payload = dict(value)
    payload.pop(field, None)
    return sha256_bytes(canonical_bytes(payload))


def seal_payload(value: Mapping[str, Any], field: str = "receipt_sha256") -> dict[str, Any]:
    payload = dict(value)
    payload.pop(field, None)
    payload[field] = sha256_bytes(canonical_bytes(payload))
    return payload


def verify_sealed(value: Mapping[str, Any], field: str = "receipt_sha256") -> None:
    actual = value.get(field)
    if not isinstance(actual, str) or not SHA256_RE.fullmatch(actual):
        raise EvidenceError(f"missing or malformed {field}")
    expected = digest_payload(value, field)
    if actual != expected:
        raise EvidenceError(f"{field} mismatch: expected {expected}, got {actual}")


def atomic_write(path: Path, data: bytes, *, overwrite: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not overwrite:
        raise EvidenceError(f"refusing to overwrite {path}")
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass


def _framed_update(digest: "hashlib._Hash", name: str, data: bytes) -> None:
    encoded = name.encode("utf-8")
    digest.update(len(encoded).to_bytes(8, "big"))
    digest.update(encoded)
    digest.update(len(data).to_bytes(8, "big"))
    digest.update(data)


def tree_sha256(members: Mapping[str, bytes], *, exclude: Iterable[str] = ()) -> str:
    omitted = set(exclude)
    digest = hashlib.sha256()
    for name in sorted(members):
        if name not in omitted:
            _framed_update(digest, name, members[name])
    return digest.hexdigest()


def file_tree(root: Path) -> dict[str, bytes]:
    root = root.resolve(strict=True)
    output: dict[str, bytes] = {}
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise EvidenceError(f"symlink in candidate tree: {path}")
        if path.is_dir():
            continue
        if not path.is_file():
            raise EvidenceError(f"unsupported candidate object: {path}")
        name = path.relative_to(root).as_posix()
        output[name] = path.read_bytes()
    return output


def _validate_member_name(name: str) -> str:
    if not isinstance(name, str) or not name or "\x00" in name or "\\" in name:
        raise EvidenceError(f"unsafe archive member name: {name!r}")
    pure = PurePosixPath(name)
    if pure.is_absolute() or any(part in ("", ".", "..") for part in pure.parts):
        raise EvidenceError(f"unsafe archive member path: {name!r}")
    normalized = pure.as_posix()
    if normalized != name:
        raise EvidenceError(f"noncanonical archive member path: {name!r}")
    return normalized


def read_archive(path: Path, expected_sha256: str | None = None) -> tuple[dict[str, bytes], dict[str, Any]]:
    path = path.resolve(strict=True)
    raw_size = path.stat().st_size
    if raw_size > MAX_ARCHIVE_BYTES:
        raise EvidenceError(f"archive exceeds {MAX_ARCHIVE_BYTES} bytes")
    actual_archive_sha = sha256_file(path)
    if expected_sha256 is not None:
        expected_sha256 = expected_sha256.lower()
        if not SHA256_RE.fullmatch(expected_sha256):
            raise EvidenceError("archive SHA-256 must be 64 lowercase hexadecimal characters")
        if actual_archive_sha != expected_sha256:
            raise EvidenceError(
                f"archive SHA-256 mismatch for {path.name}: expected {expected_sha256}, got {actual_archive_sha}"
            )
    members: dict[str, bytes] = {}
    total = 0
    with tarfile.open(path, mode="r:*") as archive:
        for member in archive:
            name = _validate_member_name(member.name)
            if member.isdir():
                continue
            if not member.isfile():
                raise EvidenceError(f"archive contains non-regular member: {name}")
            if name in members:
                raise EvidenceError(f"archive contains duplicate member: {name}")
            if member.size < 0 or member.size > MAX_MEMBER_BYTES:
                raise EvidenceError(f"archive member size rejected: {name} ({member.size})")
            total += member.size
            if total > MAX_ARCHIVE_BYTES:
                raise EvidenceError("expanded archive exceeds safety limit")
            stream = archive.extractfile(member)
            if stream is None:
                raise EvidenceError(f"cannot read archive member: {name}")
            data = stream.read(MAX_MEMBER_BYTES + 1)
            if len(data) != member.size:
                raise EvidenceError(f"archive member length mismatch: {name}")
            members[name] = data
    for required in (CONFIG_MEMBER, ENTRYPOINT_MEMBER):
        if required not in members:
            raise EvidenceError(f"archive is missing required member {required}")
    try:
        config = json.loads(members[CONFIG_MEMBER])
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise EvidenceError(f"invalid {CONFIG_MEMBER}: {exc}") from exc
    if not isinstance(config, dict) or not all(isinstance(key, str) for key in config):
        raise EvidenceError(f"{CONFIG_MEMBER} must contain a JSON object")
    metadata = {
        "path": str(path),
        "filename": path.name,
        "sha256": actual_archive_sha,
        "bytes": raw_size,
        "member_count": len(members),
        "tree_sha256": tree_sha256(members),
        "non_config_tree_sha256": tree_sha256(members, exclude=(CONFIG_MEMBER,)),
        "config_sha256": sha256_bytes(members[CONFIG_MEMBER]),
        "entrypoint_sha256": sha256_bytes(members[ENTRYPOINT_MEMBER]),
        "config": config,
    }
    return members, metadata


def _validate_name(name: str, what: str = "name") -> str:
    if not isinstance(name, str) or not NAME_RE.fullmatch(name):
        raise EvidenceError(f"invalid {what} {name!r}; expected {NAME_RE.pattern}")
    return name


def parse_named_archive(value: str) -> tuple[str, Path, str | None]:
    name, sep, specification = value.partition("=")
    _validate_name(name, "archive label")
    if not sep or not specification:
        raise EvidenceError("archive arguments require NAME=PATH[@SHA256]")
    expected = None
    path_text = specification
    possible_path, marker, possible_sha = specification.rpartition("@")
    if marker and SHA256_RE.fullmatch(possible_sha.lower()):
        path_text, expected = possible_path, possible_sha.lower()
    path = Path(path_text)
    if expected is None:
        match = ARCHIVE_SHA_RE.fullmatch(path.name)
        if match:
            expected = match.group(1)
    return name, path, expected


def parse_json_assignment(value: str) -> tuple[str, Any]:
    key, sep, encoded_value = value.partition("=")
    if not sep or not key:
        raise EvidenceError("override requires KEY=JSON_VALUE")
    try:
        decoded = json.loads(encoded_value)
    except json.JSONDecodeError as exc:
        raise EvidenceError(f"override value for {key!r} is not valid JSON") from exc
    return key, decoded


def parse_pair(value: str) -> tuple[str, str]:
    values = [part.strip() for part in value.split(",")]
    if len(values) != 2 or not all(values) or values[0] == values[1]:
        raise EvidenceError("pair requires two distinct comma-separated config keys")
    return tuple(sorted(values))  # type: ignore[return-value]


def config_bytes(config: Mapping[str, Any], original_order: Sequence[str]) -> bytes:
    ordered = {key: config[key] for key in original_order}
    return (json.dumps(ordered, indent=2, ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")


def _make_read_only(root: Path) -> None:
    # Source members are immutable; directories remain writable so test and CI
    # cleanup is portable.  ``run`` hashes the complete tree before and after
    # evaluation, so added/deleted files are still detected fail-closed.
    for path in sorted(root.rglob("*"), reverse=True):
        if path.is_file():
            path.chmod(0o444)


def materialize_variant(
    *,
    name: str,
    kind: str,
    archive_members: Mapping[str, bytes],
    archive_meta: Mapping[str, Any],
    overrides: Mapping[str, Any],
    variants_root: Path,
    manifests_root: Path,
) -> dict[str, Any]:
    _validate_name(name, "variant name")
    config = dict(archive_meta["config"])
    original_order = list(config)
    for key, value in sorted(overrides.items()):
        if key not in config:
            raise EvidenceError(f"variant {name} references unknown config key {key!r}")
        if type(config[key]) is not type(value):
            raise EvidenceError(
                f"variant {name} changes config type for {key!r}: {type(config[key]).__name__} -> {type(value).__name__}"
            )
        if config[key] == value:
            raise EvidenceError(f"variant {name} override {key!r} does not change the baseline value")
        config[key] = value
    candidate_members = dict(archive_members)
    if overrides:
        candidate_members[CONFIG_MEMBER] = config_bytes(config, original_order)
    changed = sorted(name_ for name_ in candidate_members if candidate_members[name_] != archive_members[name_])
    expected_changed = [CONFIG_MEMBER] if overrides else []
    if changed != expected_changed:
        raise EvidenceError(f"variant {name} changed unexpected members: {changed}")
    if tree_sha256(candidate_members, exclude=(CONFIG_MEMBER,)) != archive_meta["non_config_tree_sha256"]:
        raise EvidenceError(f"variant {name} changed non-config bytes")

    destination = variants_root / name
    if destination.exists():
        raise EvidenceError(f"variant destination already exists: {destination}")
    temporary = Path(tempfile.mkdtemp(prefix=f".{name}.", dir=variants_root))
    try:
        for member_name, data in sorted(candidate_members.items()):
            target = temporary / member_name
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("xb") as stream:
                stream.write(data)
        os.replace(temporary, destination)
    except BaseException:
        shutil.rmtree(temporary, ignore_errors=True)
        raise

    member_hashes = {member_name: sha256_bytes(data) for member_name, data in sorted(candidate_members.items())}
    manifest = seal_payload(
        {
            "schema_version": SCHEMA_VERSION,
            "name": name,
            "kind": kind,
            "source_archive": {
                key: archive_meta[key]
                for key in ("filename", "sha256", "bytes", "member_count", "tree_sha256", "non_config_tree_sha256")
            },
            "overrides": dict(sorted(overrides.items())),
            "changed_members": changed,
            "candidate_root": f"../variants/{name}",
            "member_count": len(candidate_members),
            "member_sha256": member_hashes,
            "tree_sha256": tree_sha256(candidate_members),
            "non_config_tree_sha256": tree_sha256(candidate_members, exclude=(CONFIG_MEMBER,)),
            "config_sha256": member_hashes[CONFIG_MEMBER],
            "entrypoint_sha256": member_hashes[ENTRYPOINT_MEMBER],
            "config": config,
        }
    )
    manifest_path = manifests_root / f"{name}.json"
    atomic_write(manifest_path, pretty_bytes(manifest))
    _make_read_only(destination)
    return {
        "name": name,
        "kind": kind,
        "overrides": dict(sorted(overrides.items())),
        "root": f"variants/{name}",
        "manifest": f"manifests/{name}.json",
        "manifest_sha256": sha256_file(manifest_path),
        "candidate_tree_sha256": manifest["tree_sha256"],
        "entrypoint_sha256": manifest["entrypoint_sha256"],
        "source_archive_sha256": archive_meta["sha256"],
    }


def _disable_name(keys: Sequence[str]) -> str:
    return "without-" + "+".join(key.replace("_", "-") for key in sorted(keys))


def prepare_matrix(args: argparse.Namespace) -> int:
    output = args.output_dir.resolve()
    if output.exists():
        if any(output.iterdir()):
            raise EvidenceError(f"output directory is not empty: {output}")
    else:
        output.mkdir(parents=True)
    variants_root = output / "variants"
    manifests_root = output / "manifests"
    variants_root.mkdir()
    manifests_root.mkdir()

    baseline_name, baseline_path, baseline_expected = parse_named_archive(args.baseline)
    baseline_members, baseline_meta = read_archive(baseline_path, baseline_expected)
    variants: list[dict[str, Any]] = []
    variants.append(
        materialize_variant(
            name=baseline_name,
            kind="baseline",
            archive_members=baseline_members,
            archive_meta=baseline_meta,
            overrides={},
            variants_root=variants_root,
            manifests_root=manifests_root,
        )
    )

    baseline_config = baseline_meta["config"]
    toggle_keys: list[str] = []
    for key in args.toggle:
        if key in toggle_keys:
            raise EvidenceError(f"duplicate toggle {key!r}")
        if key not in baseline_config:
            raise EvidenceError(f"unknown toggle {key!r}")
        if type(baseline_config[key]) is not bool:
            raise EvidenceError(f"toggle {key!r} is not boolean")
        if baseline_config[key] is not True:
            raise EvidenceError(f"toggle {key!r} is not enabled in the baseline")
        toggle_keys.append(key)

    custom_overrides: dict[str, dict[str, Any]] = {}
    for specification in args.variant:
        name, separator, assignments = specification.partition(":")
        _validate_name(name, "variant name")
        if not separator or not assignments:
            raise EvidenceError("custom variant requires NAME:KEY=JSON[,KEY=JSON]")
        if name in custom_overrides:
            raise EvidenceError(f"duplicate custom variant name {name}")
        values: dict[str, Any] = {}
        for assignment in assignments.split(","):
            key, value = parse_json_assignment(assignment)
            if key in values:
                raise EvidenceError(f"duplicate override {key!r} in {name}")
            values[key] = value
        custom_overrides[name] = values

    requested: list[tuple[str, dict[str, Any], str]] = []
    for key in toggle_keys:
        requested.append((_disable_name((key,)), {key: False}, "single_ablation"))
    seen_pairs: set[tuple[str, str]] = set()
    for pair_text in args.pair:
        pair = parse_pair(pair_text)
        if pair in seen_pairs:
            raise EvidenceError(f"duplicate pair {pair}")
        seen_pairs.add(pair)
        for key in pair:
            if key not in toggle_keys:
                raise EvidenceError(f"pair key {key!r} must also be declared with --toggle")
        requested.append((_disable_name(pair), {pair[0]: False, pair[1]: False}, "pair_ablation"))
    for name, overrides in custom_overrides.items():
        requested.append((name, overrides, "custom_ablation"))

    used_names = {baseline_name}
    used_configs = {canonical_bytes(baseline_meta["config"]): baseline_name}
    for name, overrides, kind in requested:
        if name in used_names:
            raise EvidenceError(f"duplicate variant name {name}")
        candidate_config = dict(baseline_meta["config"])
        for key, value in overrides.items():
            if key not in candidate_config:
                raise EvidenceError(f"variant {name} references unknown config key {key!r}")
            candidate_config[key] = value
        fingerprint = canonical_bytes(candidate_config)
        if fingerprint in used_configs:
            raise EvidenceError(f"variant {name} duplicates config of {used_configs[fingerprint]}")
        used_names.add(name)
        used_configs[fingerprint] = name
        variants.append(
            materialize_variant(
                name=name,
                kind=kind,
                archive_members=baseline_members,
                archive_meta=baseline_meta,
                overrides=overrides,
                variants_root=variants_root,
                manifests_root=manifests_root,
            )
        )

    controls: list[dict[str, Any]] = []
    for control_text in args.control:
        name, path, expected = parse_named_archive(control_text)
        if name in used_names:
            raise EvidenceError(f"duplicate control/variant name {name}")
        control_members, control_meta = read_archive(path, expected)
        if control_meta["tree_sha256"] == baseline_meta["tree_sha256"]:
            raise EvidenceError(f"control {name} duplicates the baseline archive tree")
        used_names.add(name)
        control = materialize_variant(
            name=name,
            kind="control",
            archive_members=control_members,
            archive_meta=control_meta,
            overrides={},
            variants_root=variants_root,
            manifests_root=manifests_root,
        )
        controls.append(control)
        variants.append(control)

    matrix = seal_payload(
        {
            "schema_version": SCHEMA_VERSION,
            "baseline": baseline_name,
            "baseline_archive": {
                key: baseline_meta[key]
                for key in ("filename", "sha256", "bytes", "member_count", "tree_sha256", "non_config_tree_sha256")
            },
            "toggle_keys": sorted(toggle_keys),
            "variants": variants,
            "controls": [item["name"] for item in controls],
            "tool_sha256": sha256_file(Path(__file__)),
            "truth_boundary": (
                "Config-only variants preserve every non-config archive member. Controls may use different immutable archives. "
                "The matrix nominates experiments; it does not establish leaderboard strength or authorize release."
            ),
        },
        field="matrix_sha256",
    )
    matrix_path = output / "matrix.json"
    atomic_write(matrix_path, pretty_bytes(matrix))
    print(json.dumps({"matrix": str(matrix_path), "matrix_sha256": matrix["matrix_sha256"], "variants": len(variants)}))
    return 0


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise EvidenceError(f"cannot read JSON {path}: {exc}") from exc


def _safe_relative(base: Path, relative: str) -> Path:
    if not isinstance(relative, str):
        raise EvidenceError("manifest path must be a string")
    pure = PurePosixPath(relative)
    if pure.is_absolute() or any(part in ("", ".", "..") for part in pure.parts):
        raise EvidenceError(f"unsafe relative path {relative!r}")
    path = (base / Path(*pure.parts)).resolve(strict=True)
    try:
        path.relative_to(base.resolve(strict=True))
    except ValueError as exc:
        raise EvidenceError(f"path escapes matrix root: {relative!r}") from exc
    return path


def load_matrix(path: Path, *, verify_candidates: bool = True) -> tuple[dict[str, Any], Path]:
    path = path.resolve(strict=True)
    matrix = load_json(path)
    if not isinstance(matrix, dict) or matrix.get("schema_version") != SCHEMA_VERSION:
        raise EvidenceError("unsupported matrix schema")
    verify_sealed(matrix, "matrix_sha256")
    variants = matrix.get("variants")
    if not isinstance(variants, list) or not variants:
        raise EvidenceError("matrix has no variants")
    names: set[str] = set()
    root = path.parent
    for item in variants:
        if not isinstance(item, dict):
            raise EvidenceError("variant entry must be an object")
        name = _validate_name(item.get("name"), "variant name")
        if name in names:
            raise EvidenceError(f"duplicate variant {name}")
        names.add(name)
        manifest_path = _safe_relative(root, item.get("manifest"))
        if sha256_file(manifest_path) != item.get("manifest_sha256"):
            raise EvidenceError(f"variant manifest hash mismatch for {name}")
        manifest = load_json(manifest_path)
        if not isinstance(manifest, dict):
            raise EvidenceError(f"variant manifest is not an object for {name}")
        verify_sealed(manifest)
        if manifest.get("name") != name or manifest.get("tree_sha256") != item.get("candidate_tree_sha256"):
            raise EvidenceError(f"variant summary/manifest mismatch for {name}")
        if verify_candidates:
            candidate_root = _safe_relative(root, item.get("root"))
            actual_members = file_tree(candidate_root)
            if len(actual_members) != manifest.get("member_count"):
                raise EvidenceError(f"candidate member count mismatch for {name}")
            actual_hashes = {member: sha256_bytes(data) for member, data in sorted(actual_members.items())}
            if actual_hashes != manifest.get("member_sha256"):
                raise EvidenceError(f"candidate member hash mismatch for {name}")
            if tree_sha256(actual_members) != manifest.get("tree_sha256"):
                raise EvidenceError(f"candidate tree hash mismatch for {name}")
            if tree_sha256(actual_members, exclude=(CONFIG_MEMBER,)) != manifest.get("non_config_tree_sha256"):
                raise EvidenceError(f"candidate non-config tree hash mismatch for {name}")
    if matrix.get("baseline") not in names:
        raise EvidenceError("matrix baseline is absent")
    return matrix, root


def _tree_metadata(root: Path) -> dict[str, Any]:
    members = file_tree(root)
    return {"file_count": len(members), "tree_sha256": tree_sha256(members)}


def _spec_fingerprint(specification: str, cwd: Path) -> dict[str, Any]:
    label, separator, spec = specification.partition("=")
    if not separator or not label or not spec:
        raise EvidenceError("opponent requires LABEL=PATH[::CALLABLE] or LABEL=official_starter")
    _validate_name(label, "opponent label")
    if spec == "official_starter":
        return {"label": label, "spec": spec, "kind": "official_starter"}
    path_text, call_separator, callable_name = spec.partition("::")
    path = Path(path_text)
    if not path.is_absolute():
        path = (cwd / path).resolve(strict=True)
    else:
        path = path.resolve(strict=True)
    if not path.is_file():
        raise EvidenceError(f"opponent source is not a file: {path}")
    canonical_spec = str(path) + (("::" + callable_name) if call_separator else "")
    return {"label": label, "spec": canonical_spec, "kind": "file", "sha256": sha256_file(path)}


def _parse_seeds(value: str) -> list[int]:
    try:
        seeds = [int(item.strip()) for item in value.split(",") if item.strip()]
    except ValueError as exc:
        raise EvidenceError("seeds must be comma-separated integers") from exc
    if not seeds or len(seeds) != len(set(seeds)):
        raise EvidenceError("seeds must be nonempty and distinct")
    return seeds


def _read_valid_receipt(path: Path, contract_sha: str, report_path: Path) -> dict[str, Any] | None:
    if not path.is_file() or not report_path.is_file():
        return None
    try:
        receipt = load_json(path)
        if not isinstance(receipt, dict):
            return None
        verify_sealed(receipt)
        if receipt.get("contract_sha256") != contract_sha or receipt.get("exit_code") != 0:
            return None
        if receipt.get("report_sha256") != sha256_file(report_path):
            return None
        return receipt
    except EvidenceError:
        return None


def run_matrix(args: argparse.Namespace) -> int:
    matrix_path = args.matrix.resolve(strict=True)
    matrix, matrix_root = load_matrix(matrix_path, verify_candidates=True)
    cwd = Path.cwd().resolve()
    evaluator = args.evaluator.resolve(strict=True)
    if not evaluator.is_file():
        raise EvidenceError("evaluator must be a file")
    engine_dir = args.engine_dir.resolve(strict=True)
    if not engine_dir.is_dir():
        raise EvidenceError("engine-dir must be a directory")
    loader = args.loader.resolve(strict=True) if args.loader else None
    if loader is not None and not loader.is_file():
        raise EvidenceError("loader must be a file")
    seeds = _parse_seeds(args.seeds)
    opponents = [_spec_fingerprint(value, cwd) for value in args.opponent]
    labels = [item["label"] for item in opponents]
    if len(labels) != len(set(labels)):
        raise EvidenceError("opponent labels must be unique")
    if not opponents:
        raise EvidenceError("at least one explicit opponent is required")
    if any(not math.isfinite(value) or value <= 0 for value in (
        args.action_timeout,
        args.startup_timeout,
        args.game_timeout,
        args.process_timeout,
    )):
        raise EvidenceError("timeouts must be finite and positive")

    results_dir = args.results_dir.resolve()
    results_dir.mkdir(parents=True, exist_ok=True)
    engine_meta = _tree_metadata(engine_dir)
    run_contract = {
        "schema_version": SCHEMA_VERSION,
        "matrix_sha256": matrix["matrix_sha256"],
        "evaluator": {"path": str(evaluator), "sha256": sha256_file(evaluator)},
        "loader": None if loader is None else {"path": str(loader), "sha256": sha256_file(loader)},
        "engine": {"path": str(engine_dir), **engine_meta},
        "opponents": opponents,
        "seeds": seeds,
        "rng_seed": args.rng_seed,
        "limits": {
            "action_timeout": args.action_timeout,
            "startup_timeout": args.startup_timeout,
            "game_timeout": args.game_timeout,
            "process_timeout": args.process_timeout,
            "episode_steps": args.episode_steps,
        },
        "python": sys.version,
    }
    contract_sha = sha256_bytes(canonical_bytes(run_contract))
    run_rows: dict[str, Any] = {}
    failures = 0

    for item in matrix["variants"]:
        name = item["name"]
        candidate_root = _safe_relative(matrix_root, item["root"])
        candidate = candidate_root / ENTRYPOINT_MEMBER
        before = _tree_metadata(candidate_root)
        if before["tree_sha256"] != item["candidate_tree_sha256"]:
            raise EvidenceError(f"candidate changed before run: {name}")
        report_path = results_dir / f"{name}.report.json"
        receipt_path = results_dir / f"{name}.run.json"
        stdout_path = results_dir / f"{name}.stdout.txt"
        stderr_path = results_dir / f"{name}.stderr.txt"
        cached = None if args.no_resume else _read_valid_receipt(receipt_path, contract_sha, report_path)
        if cached is not None:
            run_rows[name] = {**cached, "reused": True, "receipt": receipt_path.name}
            continue

        command = [
            sys.executable,
            str(evaluator),
            "--engine-dir",
            str(engine_dir),
            "--candidate",
            str(candidate),
            "--seeds",
            ",".join(map(str, seeds)),
            "--rng-seed",
            str(args.rng_seed),
            "--action-timeout",
            str(args.action_timeout),
            "--startup-timeout",
            str(args.startup_timeout),
            "--game-timeout",
            str(args.game_timeout),
            "--output",
            str(report_path),
            "--recheck-first",
        ]
        if loader is not None:
            command.extend(("--loader", str(loader)))
        if args.episode_steps is not None:
            command.extend(("--episode-steps", str(args.episode_steps)))
        for opponent in opponents:
            command.extend(("--opponent", f"{opponent['label']}={opponent['spec']}"))
        try:
            completed = subprocess.run(
                command,
                cwd=cwd,
                text=True,
                capture_output=True,
                timeout=args.process_timeout,
                check=False,
                env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
            )
            exit_code = completed.returncode
            stdout, stderr = completed.stdout, completed.stderr
        except subprocess.TimeoutExpired as exc:
            exit_code = 124
            stdout = exc.stdout or ""
            stderr = (exc.stderr or "") + "\nfeature-bisect: evaluator process timeout\n"
        atomic_write(stdout_path, stdout.encode("utf-8", errors="replace"), overwrite=True)
        atomic_write(stderr_path, stderr.encode("utf-8", errors="replace"), overwrite=True)
        after = _tree_metadata(candidate_root)
        if after != before:
            raise EvidenceError(f"candidate tree mutated during run: {name}")
        report_sha = sha256_file(report_path) if report_path.is_file() else None
        receipt = seal_payload(
            {
                "schema_version": SCHEMA_VERSION,
                "name": name,
                "kind": item["kind"],
                "matrix_sha256": matrix["matrix_sha256"],
                "variant_manifest_sha256": item["manifest_sha256"],
                "candidate_tree_sha256": before["tree_sha256"],
                "contract_sha256": contract_sha,
                "command": command,
                "exit_code": exit_code,
                "report": report_path.name if report_sha else None,
                "report_sha256": report_sha,
                "stdout": stdout_path.name,
                "stdout_sha256": sha256_file(stdout_path),
                "stderr": stderr_path.name,
                "stderr_sha256": sha256_file(stderr_path),
                "post_tree_sha256": after["tree_sha256"],
            }
        )
        atomic_write(receipt_path, pretty_bytes(receipt), overwrite=True)
        run_rows[name] = {**receipt, "reused": False, "receipt": receipt_path.name}
        if exit_code != 0 or report_sha is None:
            failures += 1

    run_manifest = seal_payload(
        {
            "schema_version": SCHEMA_VERSION,
            "matrix": os.path.relpath(matrix_path, results_dir),
            "matrix_sha256": matrix["matrix_sha256"],
            "contract": run_contract,
            "contract_sha256": contract_sha,
            "variants": run_rows,
            "all_evaluators_succeeded": failures == 0,
            "truth_boundary": "A successful run proves a complete local official-interpreter grid for these exact bytes and cells, not hosted rating strength.",
        },
        field="run_sha256",
    )
    run_path = results_dir / "runs.json"
    atomic_write(run_path, pretty_bytes(run_manifest), overwrite=True)
    print(json.dumps({"runs": str(run_path), "run_sha256": run_manifest["run_sha256"], "failures": failures}))
    return 0 if failures == 0 else 2


def _finite_number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise EvidenceError(f"{label} must be a finite number")
    return float(value)


def _outcome(margin: float) -> str:
    if margin > 0:
        return "W"
    if margin < 0:
        return "L"
    return "T"


def _validate_report(name: str, report: Any) -> tuple[dict[tuple[str, int, int], dict[str, Any]], dict[str, Any]]:
    if not isinstance(report, dict) or report.get("schema_version") != 1:
        raise EvidenceError(f"unsupported evaluator report for {name}")
    engine_ref = report.get("engine_ref")
    engine_sha = report.get("engine_sha256")
    if not isinstance(engine_ref, str) or not isinstance(engine_sha, dict):
        raise EvidenceError(f"missing engine identity for {name}")
    opponents = report.get("opponents")
    seeds = report.get("seeds")
    games = report.get("games")
    if not isinstance(opponents, dict) or not opponents:
        raise EvidenceError(f"missing opponents for {name}")
    if not isinstance(seeds, list) or not seeds or any(isinstance(seed, bool) or not isinstance(seed, int) for seed in seeds):
        raise EvidenceError(f"invalid seeds for {name}")
    if len(seeds) != len(set(seeds)):
        raise EvidenceError(f"duplicate seeds for {name}")
    if not isinstance(games, list):
        raise EvidenceError(f"missing games for {name}")
    expected = {(opponent, seed, seat) for opponent in opponents for seed in seeds for seat in (0, 1)}
    rows: dict[tuple[str, int, int], dict[str, Any]] = {}
    for index, game in enumerate(games):
        if not isinstance(game, dict):
            raise EvidenceError(f"game {index} is not an object for {name}")
        opponent = game.get("opponent")
        seed = game.get("seed")
        seat = game.get("candidate_seat")
        if isinstance(seed, bool) or not isinstance(seed, int) or isinstance(seat, bool) or seat not in (0, 1):
            raise EvidenceError(f"invalid game identity for {name} row {index}")
        key = (opponent, seed, seat)
        if key not in expected:
            raise EvidenceError(f"unexpected cell for {name}: {key}")
        if key in rows:
            raise EvidenceError(f"duplicate cell for {name}: {key}")
        if game.get("status") != "complete" or game.get("failure") not in (None, {}):
            raise EvidenceError(f"incomplete cell for {name}: {key}")
        scores = game.get("scores")
        if not isinstance(scores, list) or len(scores) != 2:
            raise EvidenceError(f"invalid scores for {name}: {key}")
        score0 = _finite_number(scores[0], f"{name} score0 {key}")
        score1 = _finite_number(scores[1], f"{name} score1 {key}")
        trace = game.get("trace_sha256")
        if not isinstance(trace, str) or not SHA256_RE.fullmatch(trace):
            raise EvidenceError(f"invalid trace hash for {name}: {key}")
        actors = game.get("actors")
        max_call = 0.0
        if isinstance(actors, list):
            for actor in actors:
                if isinstance(actor, dict):
                    max_call = max(max_call, _finite_number(actor.get("max_call_seconds", 0.0), "max_call_seconds"))
        own, rival = (score0, score1) if seat == 0 else (score1, score0)
        margin = own - rival
        rows[key] = {
            "own": own,
            "rival": rival,
            "margin": margin,
            "outcome": _outcome(margin),
            "trace_sha256": trace,
            "wall_seconds": _finite_number(game.get("wall_seconds", 0.0), "wall_seconds"),
            "max_call_seconds": max_call,
        }
    missing = sorted(expected - set(rows))
    if missing:
        raise EvidenceError(f"missing cells for {name}: {missing[:5]}{'...' if len(missing) > 5 else ''}")
    if len(rows) != len(expected):
        raise EvidenceError(f"cell count mismatch for {name}")
    reproducibility = report.get("reproducibility")
    if not isinstance(reproducibility, dict) or reproducibility.get("checked") is not True or reproducibility.get("same_trace_and_scores") is not True:
        raise EvidenceError(f"reproducibility recheck did not pass for {name}")
    identity = {
        "engine_ref": engine_ref,
        "engine_sha256": engine_sha,
        "evaluator_sha256": report.get("evaluator_sha256"),
        "loader_sha256": report.get("loader_sha256"),
        "opponents": opponents,
        "seeds": seeds,
        "agent_rng_seed": report.get("agent_rng_seed"),
        "limits": report.get("limits"),
    }
    return rows, identity


def _quantile(values: Sequence[float], fraction: float) -> float:
    if not values:
        raise EvidenceError("cannot take quantile of empty values")
    ordered = sorted(values)
    position = fraction * (len(ordered) - 1)
    low = int(math.floor(position))
    high = int(math.ceil(position))
    if low == high:
        return ordered[low]
    weight = position - low
    return ordered[low] * (1.0 - weight) + ordered[high] * weight


def _paired_summary(
    baseline: Mapping[tuple[str, int, int], Mapping[str, Any]],
    challenger: Mapping[tuple[str, int, int], Mapping[str, Any]],
) -> dict[str, Any]:
    if set(baseline) != set(challenger):
        raise EvidenceError("paired summary requires exact identical cell keys")
    cells = []
    for key in sorted(baseline):
        base, trial = baseline[key], challenger[key]
        delta = trial["margin"] - base["margin"]
        cells.append(
            {
                "opponent": key[0],
                "seed": key[1],
                "candidate_seat": key[2],
                "baseline_outcome": base["outcome"],
                "challenger_outcome": trial["outcome"],
                "flip": f"{base['outcome']}->{trial['outcome']}",
                "baseline_own": base["own"],
                "challenger_own": trial["own"],
                "baseline_rival": base["rival"],
                "challenger_rival": trial["rival"],
                "baseline_margin": base["margin"],
                "challenger_margin": trial["margin"],
                "own_delta": trial["own"] - base["own"],
                "rival_delta": trial["rival"] - base["rival"],
                "margin_delta": delta,
                "same_trace": trial["trace_sha256"] == base["trace_sha256"],
            }
        )
    baseline_outcomes = [row["baseline_outcome"] for row in cells]
    trial_outcomes = [row["challenger_outcome"] for row in cells]
    deltas = [row["margin_delta"] for row in cells]
    own_deltas = [row["own_delta"] for row in cells]
    rival_deltas = [row["rival_delta"] for row in cells]
    reverse_wins = sum(row["baseline_outcome"] == "W" and row["challenger_outcome"] != "W" for row in cells)
    recovered = sum(row["baseline_outcome"] != "W" and row["challenger_outcome"] == "W" for row in cells)
    positive = sum(value > 0 for value in deltas)
    negative = sum(value < 0 for value in deltas)
    baseline_wins = baseline_outcomes.count("W")
    baseline_losses = baseline_outcomes.count("L")
    trial_wins = trial_outcomes.count("W")
    trial_losses = trial_outcomes.count("L")
    mean_delta = statistics.mean(deltas)
    median_delta = statistics.median(deltas)
    if (
        trial_wins >= baseline_wins
        and trial_losses <= baseline_losses
        and reverse_wins == 0
        and mean_delta > 0
        and positive > negative
        and (trial_wins > baseline_wins or trial_losses < baseline_losses or median_delta > 0)
    ):
        screen = "ESCALATE_FULL_PANEL"
    elif (
        trial_wins < baseline_wins
        or trial_losses > baseline_losses
        or reverse_wins > 0
        or (mean_delta < 0 and negative > positive)
    ):
        screen = "REJECT_SCREEN"
    elif mean_delta > 0 and positive > negative:
        screen = "POSITIVE_MARGIN_SIGNAL"
    else:
        screen = "INCONCLUSIVE"
    return {
        "cells": len(cells),
        "baseline": {
            "wins": baseline_wins,
            "ties": baseline_outcomes.count("T"),
            "losses": baseline_losses,
            "mean_margin": statistics.mean(row["baseline_margin"] for row in cells),
        },
        "challenger": {
            "wins": trial_wins,
            "ties": trial_outcomes.count("T"),
            "losses": trial_losses,
            "mean_margin": statistics.mean(row["challenger_margin"] for row in cells),
        },
        "delta": {
            "wins": trial_wins - baseline_wins,
            "losses": trial_losses - baseline_losses,
            "recovered_to_win": recovered,
            "reverse_wins": reverse_wins,
            "mean_own": statistics.mean(own_deltas),
            "mean_rival": statistics.mean(rival_deltas),
            "mean_margin": mean_delta,
            "median_margin": median_delta,
            "min_margin": min(deltas),
            "max_margin": max(deltas),
            "q25_margin": _quantile(deltas, 0.25),
            "q75_margin": _quantile(deltas, 0.75),
            "positive_cells": positive,
            "zero_cells": sum(value == 0 for value in deltas),
            "negative_cells": negative,
            "trace_divergent_cells": sum(not row["same_trace"] for row in cells),
        },
        "screen": screen,
        "cell_deltas": cells,
    }


def _same_identity(left: Mapping[str, Any], right: Mapping[str, Any]) -> bool:
    return canonical_bytes(left) == canonical_bytes(right)


def _load_runs(path: Path) -> tuple[dict[str, Any], Path, dict[str, Any], Path]:
    path = path.resolve(strict=True)
    runs = load_json(path)
    if not isinstance(runs, dict) or runs.get("schema_version") != SCHEMA_VERSION:
        raise EvidenceError("unsupported run manifest schema")
    verify_sealed(runs, "run_sha256")
    if runs.get("all_evaluators_succeeded") is not True:
        raise EvidenceError("run manifest includes failed evaluators")
    matrix_path = (path.parent / runs.get("matrix", "")).resolve(strict=True)
    matrix, matrix_root = load_matrix(matrix_path, verify_candidates=True)
    if matrix.get("matrix_sha256") != runs.get("matrix_sha256"):
        raise EvidenceError("run/matrix hash mismatch")
    return runs, path.parent, matrix, matrix_root


def analyze_runs(args: argparse.Namespace) -> int:
    runs, results_root, matrix, _ = _load_runs(args.runs)
    baseline_name = args.baseline or matrix["baseline"]
    variant_summaries = {item["name"]: item for item in matrix["variants"]}
    if baseline_name not in variant_summaries:
        raise EvidenceError(f"unknown baseline {baseline_name}")
    reports: dict[str, Any] = {}
    rows_by_name: dict[str, dict[tuple[str, int, int], dict[str, Any]]] = {}
    identities: dict[str, dict[str, Any]] = {}
    report_hashes: set[str] = set()
    for name, run in runs.get("variants", {}).items():
        if name not in variant_summaries:
            raise EvidenceError(f"run manifest contains unknown variant {name}")
        if run.get("exit_code") != 0 or not isinstance(run.get("report"), str):
            raise EvidenceError(f"variant {name} did not complete successfully")
        report_path = _safe_relative(results_root, run["report"])
        actual_hash = sha256_file(report_path)
        if actual_hash != run.get("report_sha256"):
            raise EvidenceError(f"report hash mismatch for {name}")
        if actual_hash in report_hashes:
            raise EvidenceError(f"duplicate evaluator report bytes: {name}")
        report_hashes.add(actual_hash)
        report = load_json(report_path)
        rows, identity = _validate_report(name, report)
        candidate_identity = report.get("candidate") if isinstance(report, dict) else None
        if not isinstance(candidate_identity, dict) or candidate_identity.get("sha256") != variant_summaries[name].get("entrypoint_sha256"):
            raise EvidenceError(f"evaluator candidate identity mismatch for {name}")
        reports[name] = {"path": report_path.name, "sha256": actual_hash}
        rows_by_name[name] = rows
        identities[name] = identity
    if set(rows_by_name) != set(variant_summaries):
        missing = sorted(set(variant_summaries) - set(rows_by_name))
        extra = sorted(set(rows_by_name) - set(variant_summaries))
        raise EvidenceError(f"run variant set mismatch; missing={missing}, extra={extra}")
    baseline_identity = identities[baseline_name]
    for name, identity in identities.items():
        if not _same_identity(baseline_identity, identity):
            raise EvidenceError(f"evaluator/engine/grid identity drift for {name}")

    comparisons: dict[str, Any] = {}
    for name in sorted(rows_by_name):
        if name != baseline_name:
            summary = _paired_summary(rows_by_name[baseline_name], rows_by_name[name])
            summary["kind"] = variant_summaries[name]["kind"]
            summary["overrides"] = variant_summaries[name].get("overrides", {})
            comparisons[name] = summary

    ordered = sorted(
        comparisons,
        key=lambda name: (
            -comparisons[name]["delta"]["wins"],
            comparisons[name]["delta"]["losses"],
            -comparisons[name]["delta"]["mean_margin"],
            -comparisons[name]["delta"]["min_margin"],
            name,
        ),
    )
    escalation = [name for name in ordered if comparisons[name]["screen"] == "ESCALATE_FULL_PANEL"]
    positive = [name for name in ordered if comparisons[name]["screen"] == "POSITIVE_MARGIN_SIGNAL"]

    single_by_key: dict[str, str] = {}
    for name, comparison in comparisons.items():
        overrides = comparison.get("overrides")
        if comparison.get("kind") == "single_ablation" and isinstance(overrides, dict) and len(overrides) == 1:
            single_by_key[next(iter(overrides))] = name
    interactions = []
    for name, comparison in comparisons.items():
        overrides = comparison.get("overrides")
        if comparison.get("kind") != "pair_ablation" or not isinstance(overrides, dict) or len(overrides) != 2:
            continue
        keys = sorted(overrides)
        if not all(key in single_by_key for key in keys):
            raise EvidenceError(f"pair {name} lacks both single-ablation parents")
        left, right = (comparisons[single_by_key[key]] for key in keys)
        interactions.append(
            {
                "pair": name,
                "keys": keys,
                "mean_margin_interaction": comparison["delta"]["mean_margin"]
                - left["delta"]["mean_margin"]
                - right["delta"]["mean_margin"],
                "win_delta_interaction": comparison["delta"]["wins"]
                - left["delta"]["wins"]
                - right["delta"]["wins"],
                "loss_delta_interaction": comparison["delta"]["losses"]
                - left["delta"]["losses"]
                - right["delta"]["losses"],
            }
        )

    analysis = seal_payload(
        {
            "schema_version": SCHEMA_VERSION,
            "run_sha256": runs["run_sha256"],
            "matrix_sha256": matrix["matrix_sha256"],
            "baseline": baseline_name,
            "identity": baseline_identity,
            "reports": reports,
            "ranking": ordered,
            "full_panel_candidates": escalation,
            "positive_margin_candidates": positive,
            "comparisons": comparisons,
            "pair_interactions": sorted(interactions, key=lambda item: item["pair"]),
            "decision": (
                "ESCALATE_FULL_PANEL" if escalation else "NO_CONFIG_RESTORE_CANDIDATE"
            ),
            "truth_boundary": (
                "A screen candidate must still pass a preregistered broader both-seat reacting-opponent panel. "
                "This report neither changes TITAN-CONFIG.json nor authorizes a release or Kaggle submission."
            ),
        },
        field="analysis_sha256",
    )
    output = args.output.resolve()
    atomic_write(output, pretty_bytes(analysis), overwrite=args.overwrite)
    markdown = render_markdown(analysis)
    markdown_path = args.markdown.resolve() if args.markdown else output.with_suffix(".md")
    atomic_write(markdown_path, markdown.encode("utf-8"), overwrite=args.overwrite)
    print(json.dumps({"analysis": str(output), "analysis_sha256": analysis["analysis_sha256"], "decision": analysis["decision"]}))
    return 0


def render_markdown(analysis: Mapping[str, Any]) -> str:
    lines = [
        "# TITAN V3 config causal-bisection screen",
        "",
        f"Baseline: `{analysis['baseline']}`  ",
        f"Decision: **{analysis['decision']}**  ",
        f"Analysis SHA-256: `{analysis['analysis_sha256']}`",
        "",
        "| Rank | Variant | Kind | Screen | ΔW | ΔL | Mean Δmargin | Worst Δmargin | + / 0 / - cells |",
        "| ---: | --- | --- | --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for rank, name in enumerate(analysis["ranking"], 1):
        row = analysis["comparisons"][name]
        delta = row["delta"]
        lines.append(
            f"| {rank} | `{name}` | {row['kind']} | {row['screen']} | {delta['wins']:+d} | {delta['losses']:+d} | "
            f"{delta['mean_margin']:+.3f} | {delta['min_margin']:+.3f} | "
            f"{delta['positive_cells']} / {delta['zero_cells']} / {delta['negative_cells']} |"
        )
    lines.extend(("", "## Full-panel nominees", ""))
    if analysis["full_panel_candidates"]:
        for name in analysis["full_panel_candidates"]:
            lines.append(f"- `{name}`")
    else:
        lines.append("No config-only restore candidate cleared the conservative screen.")
    if analysis["pair_interactions"]:
        lines.extend(("", "## Pair interactions", ""))
        for item in analysis["pair_interactions"]:
            lines.append(
                f"- `{item['pair']}`: mean-margin interaction {item['mean_margin_interaction']:+.3f}; "
                f"win interaction {item['win_delta_interaction']:+d}; loss interaction {item['loss_delta_interaction']:+d}."
            )
    lines.extend(("", "## Boundary", "", str(analysis["truth_boundary"]), ""))
    return "\n".join(lines)


def verify_artifact(args: argparse.Namespace) -> int:
    path = args.path.resolve(strict=True)
    value = load_json(path)
    if not isinstance(value, dict):
        raise EvidenceError("artifact must be a JSON object")
    field = args.field
    verify_sealed(value, field)
    print(json.dumps({"path": str(path), field: value[field], "status": "PASS"}))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    prepare = subparsers.add_parser("prepare", help="materialize config-only variants from immutable archives")
    prepare.add_argument("--baseline", required=True, help="NAME=PATH[@SHA256]")
    prepare.add_argument("--control", action="append", default=[], help="NAME=PATH[@SHA256]")
    prepare.add_argument("--toggle", action="append", default=[], help="enabled boolean key to disable as a single ablation")
    prepare.add_argument("--pair", action="append", default=[], help="two --toggle keys, comma-separated")
    prepare.add_argument("--variant", action="append", default=[], help="custom NAME:KEY=JSON[,KEY=JSON]")
    prepare.add_argument("--output-dir", type=Path, required=True)
    prepare.set_defaults(func=prepare_matrix)

    run = subparsers.add_parser("run", help="run every matrix variant through the same evaluator grid")
    run.add_argument("--matrix", type=Path, required=True)
    run.add_argument("--evaluator", type=Path, required=True)
    run.add_argument("--engine-dir", type=Path, required=True)
    run.add_argument("--loader", type=Path)
    run.add_argument("--opponent", action="append", default=[], help="LABEL=PATH[::CALLABLE]")
    run.add_argument("--seeds", required=True)
    run.add_argument("--rng-seed", type=int, default=20260907)
    run.add_argument("--action-timeout", type=float, default=1.0)
    run.add_argument("--startup-timeout", type=float, default=10.0)
    run.add_argument("--game-timeout", type=float, default=120.0)
    run.add_argument("--process-timeout", type=float, default=1800.0)
    run.add_argument("--episode-steps", type=int)
    run.add_argument("--results-dir", type=Path, required=True)
    run.add_argument("--no-resume", action="store_true", help="rerun and replace this tool's prior receipts")
    run.set_defaults(func=run_matrix)

    analyze = subparsers.add_parser("analyze", help="reject partial grids and compute paired causal deltas")
    analyze.add_argument("--runs", type=Path, required=True)
    analyze.add_argument("--baseline")
    analyze.add_argument("--output", type=Path, required=True)
    analyze.add_argument("--markdown", type=Path)
    analyze.add_argument("--overwrite", action="store_true")
    analyze.set_defaults(func=analyze_runs)

    verify = subparsers.add_parser("verify", help="verify a sealed JSON artifact")
    verify.add_argument("--path", type=Path, required=True)
    verify.add_argument("--field", default="analysis_sha256")
    verify.set_defaults(func=verify_artifact)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except EvidenceError as exc:
        print(f"INVALID: {exc}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
