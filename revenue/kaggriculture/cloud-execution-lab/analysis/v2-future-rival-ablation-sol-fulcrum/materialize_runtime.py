# SPDX-License-Identifier: Apache-2.0
"""Inventory and verify the immutable frozen-V2 runtime tree."""
from __future__ import annotations

import json
from pathlib import Path
import re
import stat
from typing import Any

from materialize_identity import (
    ENTRYPOINT_SHA256,
    FREEZE_GIT_BLOB,
    MaterializeError,
    SCHEDULER_GIT_BLOB,
    SCHEDULER_SHA256,
    git_blob_bytes,
    sha256_bytes,
    strict_json,
)

def _regular_files(root: Path) -> list[Path]:
    if root.is_symlink():
        raise MaterializeError(f"source root is a symlink: {root}")
    try:
        root_mode = root.stat().st_mode
    except OSError as exc:
        raise MaterializeError(f"cannot stat source root {root}: {exc}") from exc
    if not stat.S_ISDIR(root_mode):
        raise MaterializeError(f"source root is not a directory: {root}")

    files: list[Path] = []

    def visit(directory: Path) -> None:
        try:
            entries = sorted(directory.iterdir(), key=lambda item: item.name)
        except OSError as exc:
            raise MaterializeError(f"cannot list {directory}: {exc}") from exc
        for entry in entries:
            try:
                mode = entry.lstat().st_mode
            except OSError as exc:
                raise MaterializeError(f"cannot lstat {entry}: {exc}") from exc
            if stat.S_ISDIR(mode):
                visit(entry)
            elif stat.S_ISREG(mode):
                files.append(entry)
            else:
                raise MaterializeError(f"non-regular source member: {entry}")

    visit(root)
    return files

def inventory(root: Path) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for path in _regular_files(root):
        relative = path.relative_to(root).as_posix()
        try:
            data = path.read_bytes()
        except OSError as exc:
            raise MaterializeError(f"cannot read {path}: {exc}") from exc
        result[relative] = {"bytes": len(data), "sha256": sha256_bytes(data)}
    return result

def closure_digest(value: dict[str, dict[str, Any]]) -> str:
    payload = json.dumps(
        value, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")
    return sha256_bytes(payload)

def verify_frozen_source(root: Path) -> dict[str, Any]:
    observed = inventory(root)
    freeze_path = root / "FREEZE.json"
    freeze_bytes = freeze_path.read_bytes()
    if git_blob_bytes(freeze_bytes) != FREEZE_GIT_BLOB:
        raise MaterializeError("frozen V2 FREEZE.json Git blob drift")
    freeze = strict_json(freeze_path)
    if freeze.get("variant") != "v2":
        raise MaterializeError("FREEZE.json is not the frozen v2 variant")
    declared = freeze.get("files")
    if not isinstance(declared, dict) or not declared:
        raise MaterializeError("FREEZE.json files must be a nonempty object")

    prefix = "runtime/variants/v2/"
    expected: dict[str, dict[str, Any]] = {
        "FREEZE.json": {"bytes": len(freeze_bytes), "sha256": sha256_bytes(freeze_bytes)}
    }
    for raw_name, raw_meta in declared.items():
        if not isinstance(raw_name, str) or not raw_name.startswith(prefix):
            raise MaterializeError(f"out-of-root FREEZE path: {raw_name!r}")
        name = raw_name[len(prefix) :]
        if not name or name.startswith("/") or ".." in Path(name).parts:
            raise MaterializeError(f"unsafe FREEZE path: {raw_name!r}")
        if not isinstance(raw_meta, dict):
            raise MaterializeError(f"invalid FREEZE metadata for {raw_name}")
        size, digest = raw_meta.get("bytes"), raw_meta.get("sha256")
        if type(size) is not int or size < 0:
            raise MaterializeError(f"invalid FREEZE byte count for {raw_name}")
        if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise MaterializeError(f"invalid FREEZE digest for {raw_name}")
        expected[name] = {"bytes": size, "sha256": digest}

    if observed != dict(sorted(expected.items())):
        missing = sorted(set(expected) - set(observed))
        extra = sorted(set(observed) - set(expected))
        mismatched = sorted(
            name for name in set(expected) & set(observed) if expected[name] != observed[name]
        )
        raise MaterializeError(
            "frozen V2 inventory drift: "
            f"missing={missing}, extra={extra}, mismatched={mismatched}"
        )

    scheduler = (root / "scheduler.py").read_bytes()
    if git_blob_bytes(scheduler) != SCHEDULER_GIT_BLOB:
        raise MaterializeError("frozen V2 scheduler Git blob drift")
    if sha256_bytes(scheduler) != SCHEDULER_SHA256:
        raise MaterializeError("frozen V2 scheduler SHA-256 drift")
    candidate = (root / "candidate.py").read_bytes()
    if sha256_bytes(candidate) != ENTRYPOINT_SHA256:
        raise MaterializeError("frozen V2 candidate entrypoint drift")

    return {
        "freeze": freeze,
        "inventory": observed,
        "closure_sha256": closure_digest(observed),
        "freeze_git_blob": FREEZE_GIT_BLOB,
        "scheduler_git_blob": SCHEDULER_GIT_BLOB,
        "scheduler_sha256": SCHEDULER_SHA256,
    }
