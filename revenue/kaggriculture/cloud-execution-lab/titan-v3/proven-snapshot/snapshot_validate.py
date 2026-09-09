# SPDX-License-Identifier: Apache-2.0
"""Compile, import-closure, and provenance validation for proven Titan v3."""
from __future__ import annotations

import ast
import json
from pathlib import Path, PurePosixPath
import sys
from typing import Mapping

from snapshot_model import (
    FREEZE_PATHS,
    SOURCE_MEMBERS,
    Pin,
    SnapshotError,
    read_archive,
    read_json,
    sha256,
)


def assert_candidate_entrypoint(payload: bytes) -> None:
    try:
        tree = ast.parse(payload.decode("utf-8"), filename="candidate.py")
    except (UnicodeError, SyntaxError) as exc:
        raise SnapshotError(f"candidate.py is not valid UTF-8 Python: {exc}") from exc
    body = [node for node in tree.body if not (
        isinstance(node, ast.Expr)
        and isinstance(node.value, ast.Constant)
        and isinstance(node.value.value, str)
    )]
    valid = (
        len(body) == 1
        and isinstance(body[0], ast.ImportFrom)
        and body[0].level == 0
        and body[0].module == "scheduler"
        and len(body[0].names) == 1
        and body[0].names[0].name == "agent"
        and body[0].names[0].asname in (None, "agent")
    )
    if not valid:
        raise SnapshotError("candidate.py must expose only scheduler.agent")


def assert_python_closure(members: Mapping[str, bytes]) -> dict[str, list[str]]:
    """Compile source and reject undeclared top-level Python imports."""
    available_roots = {
        PurePosixPath(name).parts[0].removesuffix(".py")
        for name in members
        if name.endswith(".py")
    }
    stdlib = set(getattr(sys, "stdlib_module_names", ())) | {"__future__"}
    imports: dict[str, list[str]] = {}
    for name, payload in sorted(members.items()):
        if not name.endswith(".py"):
            continue
        try:
            tree = ast.parse(payload.decode("utf-8"), filename=name)
            compile(tree, name, "exec")
        except (UnicodeError, SyntaxError) as exc:
            raise SnapshotError(f"Python source is not compilable: {name}: {exc}") from exc
        seen: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                seen.update(alias.name.split(".", 1)[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                seen.add(node.module.split(".", 1)[0])
        external = sorted(root for root in seen if root not in stdlib and root not in available_roots)
        if external:
            raise SnapshotError(f"undeclared Python import(s) in {name}: {', '.join(external)}")
        imports[name] = sorted(seen)
    assert_candidate_entrypoint(members["candidate.py"])
    return imports


def validate_source(lab_root: Path, pin: Pin) -> tuple[dict[str, bytes], dict, dict, dict[str, list[str]]]:
    archive_path = lab_root / pin.source_archive
    try:
        archive_data = archive_path.read_bytes()
    except OSError as exc:
        raise SnapshotError(f"cannot read pinned source archive {archive_path}: {exc}") from exc
    if len(archive_data) != pin.source_archive_bytes:
        raise SnapshotError(
            f"source archive byte count drift: expected {pin.source_archive_bytes}, got {len(archive_data)}"
        )
    if sha256(archive_data) != pin.source_archive_sha256:
        raise SnapshotError("source archive SHA-256 drift")

    artifacts = read_json(lab_root / "exports" / "ARTIFACTS.json")
    selected = artifacts.get("selected_source")
    expected_selected = {
        "file": pin.source_archive,
        "bytes": pin.source_archive_bytes,
        "sha256": pin.source_archive_sha256,
        "files": pin.source_member_count,
    }
    if selected != expected_selected:
        raise SnapshotError("ARTIFACTS.json selected_source does not match the immutable pin")

    file_manifest = read_json(lab_root / "exports" / "FILES.json")
    members = read_archive(archive_data)
    if len(members) != pin.source_member_count:
        raise SnapshotError(
            f"source archive member count drift: expected {pin.source_member_count}, got {len(members)}"
        )
    if set(members) != set(SOURCE_MEMBERS):
        missing = sorted(set(SOURCE_MEMBERS) - set(members))
        extra = sorted(set(members) - set(SOURCE_MEMBERS))
        raise SnapshotError(f"source member-set drift; missing={missing}, extra={extra}")

    for name, payload in sorted(members.items()):
        record = file_manifest.get(name)
        expected = {"bytes": len(payload), "sha256": sha256(payload)}
        if record != expected:
            raise SnapshotError(f"FILES.json does not bind archive member {name}")

    freeze_payload = members["SOURCE-FREEZE.json"]
    if sha256(freeze_payload) != pin.source_freeze_sha256:
        raise SnapshotError("SOURCE-FREEZE.json SHA-256 drift")
    try:
        freeze = json.loads(freeze_payload.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise SnapshotError(f"invalid SOURCE-FREEZE.json: {exc}") from exc
    if freeze.get("version") != pin.source_freeze_version:
        raise SnapshotError("SOURCE-FREEZE.json version drift")
    frozen = freeze.get("files")
    if not isinstance(frozen, dict):
        raise SnapshotError("SOURCE-FREEZE.json files must be an object")
    for freeze_name, archive_name in FREEZE_PATHS.items():
        actual = sha256(members[archive_name])
        if frozen.get(freeze_name) != actual or pin.frozen_hashes.get(freeze_name) != actual:
            raise SnapshotError(f"freeze identity mismatch: {freeze_name}")

    imports = assert_python_closure(members)
    return members, freeze, selected, imports
