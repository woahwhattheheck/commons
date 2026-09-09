"""Shared deterministic I/O and release-verification helpers for Titan W06."""
from __future__ import annotations

import gzip
import hashlib
import importlib.util
import json
from pathlib import Path, PurePosixPath
import sys
import tarfile
from typing import Any

SCHEMA = "titan.w06.apex-counterexample.v1"


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def plain(value: Any) -> Any:
    """Detach mutable engine structs using the same JSON value contract as IPC."""
    return json.loads(canonical(value))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")


def write_gzip_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8") + b"\n"
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as stream:
            stream.write(payload)


def import_file(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ValueError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _safe_members(archive: tarfile.TarFile) -> list[tarfile.TarInfo]:
    members = archive.getmembers()
    seen: set[str] = set()
    for member in members:
        rel = PurePosixPath(member.name)
        if not member.name or rel.is_absolute() or ".." in rel.parts:
            raise ValueError(f"unsafe archive member: {member.name!r}")
        normalized = str(rel)
        if normalized in seen:
            raise ValueError(f"duplicate archive member: {normalized}")
        seen.add(normalized)
        if not (member.isfile() or member.isdir()):
            raise ValueError(f"non-regular archive member: {normalized}")
    return members


def verify_and_extract(archive_path: Path, pin_path: Path, output: Path) -> dict[str, Any]:
    pin = json.loads(pin_path.read_text(encoding="utf-8"))
    release = pin["release"]
    actual_size = archive_path.stat().st_size
    actual_hash = sha256_file(archive_path)
    if actual_size != release["bytes"] or actual_hash != release["sha256"]:
        raise ValueError(
            f"release mismatch: got {actual_size} B / {actual_hash}; "
            f"expected {release['bytes']} B / {release['sha256']}"
        )
    if output.exists():
        raise FileExistsError(f"preserve existing extraction and choose a new path: {output}")
    output.mkdir(parents=True)
    with tarfile.open(archive_path, "r:gz") as archive:
        members = _safe_members(archive)
        regular = [member for member in members if member.isfile()]
        if len(regular) != release["runtime_files"]:
            raise ValueError(f"runtime file count mismatch: {len(regular)} != {release['runtime_files']}")
        archive.extractall(output, members=members, filter="data")
    entry_file = output / release["entrypoint"].partition("::")[0]
    config_file = output / release["config"]
    if not entry_file.is_file() or not config_file.is_file():
        raise ValueError("verified archive lacks its declared entrypoint or config")
    return {
        "schema": SCHEMA,
        "pin": pin,
        "archive": {"path": str(archive_path), "bytes": actual_size, "sha256": actual_hash},
        "extraction": {"path": str(output), "regular_files": len(regular)},
        "entrypoint": str(entry_file),
        "config": str(config_file),
    }
