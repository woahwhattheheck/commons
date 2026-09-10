# SPDX-License-Identifier: Apache-2.0
"""Exact no-overlay control carrier for the Capillary action-bound panel.

This entrypoint independently verifies and materializes the same canonical
standalone archive consumed by the admitted Capillary carrier, then delegates
to the archive's unmodified ``main.py::agent``. It never imports repository
runtime modules or any Capillary overlay.
"""
from __future__ import annotations

import hashlib
import importlib.util
import io
import json
from pathlib import Path, PurePosixPath
import sys
import tarfile
import tempfile
from typing import Any, Mapping

HERE = Path(__file__).resolve().parent
LAB = HERE.parents[1]
ARCHIVE = LAB / "exports" / "titan-current.tar.gz"

EXPECTED_ARCHIVE_SHA256 = "17f536087b3a6baf4ae1222a051285766a3ea8c2ca5af6edc190d4f527e12b86"
EXPECTED_ARCHIVE_BYTES = 427_870
EXPECTED_SOURCE_MANIFEST_SHA256 = "1feec5a68ffde28ab7b5c7d2c92a34aa66ff5705b7d88182ef6af98df8bb5083"
EXPECTED_RUNTIME_FILES = 109
EXPECTED_ARCHIVE_MEMBERS = EXPECTED_RUNTIME_FILES + 1
MAX_MEMBER_BYTES = 8 * 1024 * 1024
MAX_TOTAL_BYTES = 32 * 1024 * 1024


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _safe_member_parts(name: str) -> tuple[str, ...]:
    if not isinstance(name, str) or not name or "\\" in name or "\x00" in name:
        raise RuntimeError("canonical archive contains an invalid member name")
    pure = PurePosixPath(name)
    parts = pure.parts
    if pure.is_absolute() or not parts or any(part in ("", ".", "..") for part in parts):
        raise RuntimeError(f"unsafe canonical archive member: {name!r}")
    if PurePosixPath(*parts).as_posix() != name:
        raise RuntimeError(f"noncanonical canonical archive member: {name!r}")
    return tuple(parts)


def _verify_manifest(root: Path, members: Mapping[str, bytes]) -> dict[str, Any]:
    raw = members.get("SOURCE.json")
    if raw is None or _sha256(raw) != EXPECTED_SOURCE_MANIFEST_SHA256:
        raise RuntimeError("canonical SOURCE.json identity drift")
    try:
        manifest = json.loads(raw)
    except (TypeError, ValueError) as exc:
        raise RuntimeError("canonical SOURCE.json is invalid") from exc
    runtime = manifest.get("runtime")
    if not isinstance(runtime, dict) or len(runtime) != EXPECTED_RUNTIME_FILES:
        raise RuntimeError("canonical runtime cardinality drift")
    if manifest.get("entrypoint") != "main.py::agent":
        raise RuntimeError("canonical entrypoint drift")
    if manifest.get("config") != "TITAN-CONFIG.json":
        raise RuntimeError("canonical config identity drift")
    expected = set(runtime) | {"SOURCE.json"}
    if set(members) != expected:
        raise RuntimeError(
            "canonical archive/member manifest mismatch; "
            f"missing={sorted(expected-set(members))[:4]}, "
            f"extra={sorted(set(members)-expected)[:4]}"
        )
    for name, metadata in runtime.items():
        _safe_member_parts(name)
        if not isinstance(metadata, dict):
            raise RuntimeError(f"invalid runtime metadata: {name}")
        data = members[name]
        if type(metadata.get("bytes")) is not int or metadata["bytes"] != len(data):
            raise RuntimeError(f"runtime byte-count drift: {name}")
        if metadata.get("sha256") != _sha256(data):
            raise RuntimeError(f"runtime digest drift: {name}")
        if not isinstance(metadata.get("source_path"), str):
            raise RuntimeError(f"runtime source identity missing: {name}")
        target = root.joinpath(*PurePosixPath(name).parts)
        if not target.is_file() or target.is_symlink() or target.read_bytes() != data:
            raise RuntimeError(f"private control materialization drift: {name}")
    return manifest


def _materialize():
    if not ARCHIVE.is_file() or ARCHIVE.is_symlink():
        raise RuntimeError(f"canonical archive is not one regular file: {ARCHIVE}")
    archive = ARCHIVE.read_bytes()
    if len(archive) != EXPECTED_ARCHIVE_BYTES:
        raise RuntimeError(
            f"canonical archive length drift: expected {EXPECTED_ARCHIVE_BYTES}, "
            f"got {len(archive)}"
        )
    digest = _sha256(archive)
    if digest != EXPECTED_ARCHIVE_SHA256:
        raise RuntimeError(
            f"canonical archive digest drift: expected {EXPECTED_ARCHIVE_SHA256}, "
            f"got {digest}"
        )

    owner = tempfile.TemporaryDirectory(prefix="titan-sol-cambium-control-")
    root = Path(owner.name).resolve()
    members: dict[str, bytes] = {}
    total = 0
    try:
        with tarfile.open(fileobj=io.BytesIO(archive), mode="r:gz") as bundle:
            for member in bundle:
                if not member.isfile():
                    raise RuntimeError(
                        f"non-regular canonical archive member: {member.name!r}"
                    )
                parts = _safe_member_parts(member.name)
                if member.name in members:
                    raise RuntimeError(
                        f"duplicate canonical archive member: {member.name}"
                    )
                if type(member.size) is not int or not 0 <= member.size <= MAX_MEMBER_BYTES:
                    raise RuntimeError(
                        f"canonical archive member size rejected: {member.name}"
                    )
                stream = bundle.extractfile(member)
                if stream is None:
                    raise RuntimeError(
                        f"cannot read canonical archive member: {member.name}"
                    )
                data = stream.read(member.size + 1)
                if len(data) != member.size:
                    raise RuntimeError(
                        f"canonical archive member length mismatch: {member.name}"
                    )
                total += len(data)
                if total > MAX_TOTAL_BYTES:
                    raise RuntimeError("canonical archive exceeds byte ceiling")
                target = root.joinpath(*parts)
                target.parent.mkdir(parents=True, exist_ok=True)
                with target.open("xb") as handle:
                    handle.write(data)
                members[member.name] = data
        if len(members) != EXPECTED_ARCHIVE_MEMBERS:
            raise RuntimeError(
                f"canonical member cardinality drift: expected "
                f"{EXPECTED_ARCHIVE_MEMBERS}, got {len(members)}"
            )
        manifest = _verify_manifest(root, members)
    except BaseException:
        owner.cleanup()
        raise
    return owner, root, manifest


def _module_origin(module: Any) -> Path | None:
    raw = getattr(module, "__file__", None)
    if not raw:
        return None
    try:
        return Path(raw).resolve()
    except (OSError, RuntimeError, TypeError, ValueError):
        return None


def _inside(root: Path, path: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _runtime_names(manifest: Mapping[str, Any]) -> tuple[str, ...]:
    names: set[str] = set()
    for raw_name in manifest["runtime"]:
        path = PurePosixPath(raw_name)
        if len(path.parts) == 1 and path.suffix == ".py" and path.stem != "main":
            names.add(path.stem)
        elif len(path.parts) > 1 and path.parts[0] == "reference":
            names.add("reference")
    return tuple(sorted(names))


def _assert_runtime_modules() -> None:
    for name in _RUNTIME_NAMES:
        module = sys.modules.get(name)
        if module is None:
            continue
        origin = _module_origin(module)
        if origin is None or not _inside(_ARENA_ROOT, origin):
            raise RuntimeError(
                f"ambient runtime module collision: {name} from {origin or '<unknown>'}"
            )


def _load_entry():
    entry = _ARENA_ROOT / "main.py"
    if not entry.is_file() or entry.is_symlink():
        raise RuntimeError("canonical main.py is not one regular file")
    name = "_sol_cambium_exact_control_main"
    spec = importlib.util.spec_from_file_location(name, entry)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load exact control entry: {entry}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    origin = _module_origin(module)
    if origin != entry.resolve():
        raise RuntimeError(f"control entry escaped arena: {origin}")
    function = getattr(module, "agent", None)
    if not callable(function):
        raise TypeError("canonical control agent is not callable")
    return function


_ARENA_OWNER, _ARENA_ROOT, _ARENA_MANIFEST = _materialize()
_RUNTIME_NAMES = _runtime_names(_ARENA_MANIFEST)
_assert_runtime_modules()

_arena_text = str(_ARENA_ROOT)
while _arena_text in sys.path:
    sys.path.remove(_arena_text)
sys.path.insert(0, _arena_text)

agent = _load_entry()
_assert_runtime_modules()

__all__ = ["agent"]
