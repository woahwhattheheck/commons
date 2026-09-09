# SPDX-License-Identifier: Apache-2.0
"""Dependency-complete executable carrier for the admitted Capillary candidate.

The repository evaluator intentionally gives each agent a private working
directory and a minimal environment without repository ``PYTHONPATH``.  This
entrypoint therefore never imports the mutable source runtime directly.  It
verifies and safely materializes the exact canonical standalone archive into a
process-owned arena, overlays four source-pinned Capillary modules, rejects
ambient runtime collisions, and delegates only to the arena entrypoint.
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
EXPECTED_ARCHIVE_MEMBERS = EXPECTED_RUNTIME_FILES + 1  # SOURCE.json
MAX_MEMBER_BYTES = 8 * 1024 * 1024
MAX_TOTAL_BYTES = 32 * 1024 * 1024

# Destination in the private arena -> immutable source path + exact Git blob.
OVERLAYS = {
    "jit_seed_staging.py": (
        LAB / "jit_seed_staging.py",
        "e1cf2485ab869cf3c6f5eec455b0a25f6aeaa505",
    ),
    "jit_seed_order_rail.py": (
        LAB / "jit_seed_order_rail.py",
        "f5d2c3775bc527ef7f950a850eac8036bd71e865",
    ),
    "titan_capillary.py": (
        LAB / "titan_capillary.py",
        "afbfb0859d7a3219d2f3e5c4178d72c128f31911",
    ),
    "capillary_main.py": (
        LAB / "capillary_main.py",
        "e545a65d99f81f7982ee70fd4c336b78ad957afc",
    ),
}
EXPECTED_CONFIG_GIT_BLOB = "3a3bef83899d3010fad623b628d9e95d9978111b"


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _git_blob_sha1_bytes(data: bytes) -> str:
    return hashlib.sha1(f"blob {len(data)}\0".encode("ascii") + data).hexdigest()


def _git_blob_sha1(path: Path) -> str:
    return _git_blob_sha1_bytes(path.read_bytes())


def _load(name: str, path: Path):
    """Load one exact arena file under a collision-resistant private name."""
    if not path.is_file() or path.is_symlink():
        raise RuntimeError(f"private candidate source is not a regular file: {path}")
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    missing = object()
    previous = sys.modules.get(name, missing)
    try:
        sys.modules[name] = module
        spec.loader.exec_module(module)
    except BaseException:
        if sys.modules.get(name) is module:
            if previous is missing:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = previous
        raise
    return module


def _safe_member_parts(name: str) -> tuple[str, ...]:
    """Return one canonical relative POSIX member path or fail closed."""
    if not isinstance(name, str) or not name or "\\" in name or "\x00" in name:
        raise RuntimeError("canonical archive contains an invalid member name")
    pure = PurePosixPath(name)
    parts = pure.parts
    if pure.is_absolute() or not parts or any(part in ("", ".", "..") for part in parts):
        raise RuntimeError(f"unsafe canonical archive member: {name!r}")
    if PurePosixPath(*parts).as_posix() != name:
        raise RuntimeError(f"noncanonical archive member path: {name!r}")
    return tuple(parts)


def _verify_manifest(root: Path, members: Mapping[str, bytes]) -> dict[str, Any]:
    manifest_bytes = members.get("SOURCE.json")
    if manifest_bytes is None:
        raise RuntimeError("canonical archive is missing SOURCE.json")
    if _sha256(manifest_bytes) != EXPECTED_SOURCE_MANIFEST_SHA256:
        raise RuntimeError("canonical SOURCE.json digest drift")
    try:
        manifest = json.loads(manifest_bytes)
    except (TypeError, ValueError) as exc:
        raise RuntimeError("canonical SOURCE.json is not valid JSON") from exc
    runtime = manifest.get("runtime")
    if not isinstance(runtime, dict) or len(runtime) != EXPECTED_RUNTIME_FILES:
        raise RuntimeError("canonical runtime member cardinality drift")
    if manifest.get("entrypoint") != "main.py::agent":
        raise RuntimeError("canonical archive entrypoint drift")
    if manifest.get("config") != "TITAN-CONFIG.json":
        raise RuntimeError("canonical archive config drift")
    expected_names = set(runtime) | {"SOURCE.json"}
    if set(members) != expected_names:
        missing = sorted(expected_names - set(members))
        extra = sorted(set(members) - expected_names)
        raise RuntimeError(
            "canonical archive/member manifest mismatch; "
            f"missing={missing[:4]}, extra={extra[:4]}"
        )
    for name, metadata in runtime.items():
        _safe_member_parts(name)
        if not isinstance(metadata, dict):
            raise RuntimeError(f"invalid canonical runtime metadata for {name}")
        data = members[name]
        if type(metadata.get("bytes")) is not int or metadata["bytes"] != len(data):
            raise RuntimeError(f"canonical runtime byte-count drift for {name}")
        digest = metadata.get("sha256")
        if not isinstance(digest, str) or digest != _sha256(data):
            raise RuntimeError(f"canonical runtime digest drift for {name}")
        if not isinstance(metadata.get("source_path"), str):
            raise RuntimeError(f"canonical runtime source identity missing for {name}")
        target = root.joinpath(*PurePosixPath(name).parts)
        if not target.is_file() or target.is_symlink() or target.read_bytes() != data:
            raise RuntimeError(f"private runtime materialization drift for {name}")
    return manifest


def _materialize_private_runtime():
    """Verify and materialize the exact standalone canonical archive."""
    if not ARCHIVE.is_file() or ARCHIVE.is_symlink():
        raise RuntimeError(f"canonical archive is not a regular file: {ARCHIVE}")
    archive_bytes = ARCHIVE.read_bytes()
    if len(archive_bytes) != EXPECTED_ARCHIVE_BYTES:
        raise RuntimeError(
            "canonical archive length drift: "
            f"expected {EXPECTED_ARCHIVE_BYTES}, got {len(archive_bytes)}"
        )
    actual_archive_sha256 = _sha256(archive_bytes)
    if actual_archive_sha256 != EXPECTED_ARCHIVE_SHA256:
        raise RuntimeError(
            "canonical archive digest drift: "
            f"expected {EXPECTED_ARCHIVE_SHA256}, got {actual_archive_sha256}"
        )

    owner = tempfile.TemporaryDirectory(prefix="titan-sol-prism-capillary-")
    root = Path(owner.name).resolve()
    members: dict[str, bytes] = {}
    total = 0
    try:
        with tarfile.open(fileobj=io.BytesIO(archive_bytes), mode="r:gz") as bundle:
            for member in bundle:
                if not member.isfile():
                    raise RuntimeError(
                        f"canonical archive member is not a regular file: {member.name!r}"
                    )
                parts = _safe_member_parts(member.name)
                if member.name in members:
                    raise RuntimeError(f"duplicate canonical archive member: {member.name}")
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
                    raise RuntimeError(
                        "canonical archive exceeds private-runtime byte ceiling"
                    )
                target = root.joinpath(*parts)
                target.parent.mkdir(parents=True, exist_ok=True)
                with target.open("xb") as handle:
                    handle.write(data)
                members[member.name] = data
        if len(members) != EXPECTED_ARCHIVE_MEMBERS:
            raise RuntimeError(
                "canonical archive member cardinality drift: "
                f"expected {EXPECTED_ARCHIVE_MEMBERS}, got {len(members)}"
            )
        manifest = _verify_manifest(root, members)
    except BaseException:
        owner.cleanup()
        raise

    receipt = {
        "archive_sha256": actual_archive_sha256,
        "archive_bytes": len(archive_bytes),
        "source_manifest_sha256": EXPECTED_SOURCE_MANIFEST_SHA256,
        "runtime_files": len(manifest["runtime"]),
        "archive_members": len(members),
        "materialized_bytes": total,
        "entrypoint": manifest["entrypoint"],
        "config": manifest["config"],
    }
    return owner, root, manifest, receipt


def _install_overlays(root: Path) -> dict[str, dict[str, Any]]:
    """Copy only exact source-pinned Capillary modules into the private arena."""
    receipt: dict[str, dict[str, Any]] = {}
    for destination, (source, expected_blob) in OVERLAYS.items():
        if not source.is_file() or source.is_symlink():
            raise RuntimeError(f"Capillary overlay is not a regular file: {source}")
        data = source.read_bytes()
        actual_blob = _git_blob_sha1_bytes(data)
        if actual_blob != expected_blob:
            raise RuntimeError(
                f"Capillary overlay drift for {source.name}: "
                f"expected {expected_blob}, got {actual_blob}"
            )
        target = root / destination
        if target.exists() or target.is_symlink():
            raise RuntimeError(
                f"Capillary overlay would replace canonical member: {destination}"
            )
        with target.open("xb") as handle:
            handle.write(data)
        if target.read_bytes() != data:
            raise RuntimeError(f"Capillary overlay readback drift: {destination}")
        receipt[destination] = {
            "source": str(source),
            "git_blob": actual_blob,
            "sha256": _sha256(data),
            "bytes": len(data),
        }

    source_config = LAB / "TITAN-CONFIG.json"
    arena_config = root / "TITAN-CONFIG.json"
    if (
        not source_config.is_file()
        or source_config.is_symlink()
        or _git_blob_sha1(source_config) != EXPECTED_CONFIG_GIT_BLOB
        or source_config.read_bytes() != arena_config.read_bytes()
    ):
        raise RuntimeError("Capillary source config differs from canonical arena config")
    return receipt


def _runtime_collision_names(manifest: Mapping[str, Any]) -> tuple[str, ...]:
    names: set[str] = {PurePosixPath(name).stem for name in OVERLAYS}
    for raw_name in manifest["runtime"]:
        path = PurePosixPath(raw_name)
        if len(path.parts) == 1 and path.suffix == ".py" and path.stem != "main":
            names.add(path.stem)
        elif len(path.parts) > 1 and path.parts[0] == "reference":
            names.add("reference")
    return tuple(sorted(names))


def _module_origin(module: Any) -> Path | None:
    value = getattr(module, "__file__", None)
    if not value:
        return None
    try:
        return Path(value).resolve()
    except (OSError, RuntimeError, TypeError, ValueError):
        return None


def _inside(root: Path, path: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _assert_private_runtime_modules() -> None:
    """Never consume a same-named runtime module imported outside this arena."""
    for name in _RUNTIME_NAMES:
        module = sys.modules.get(name)
        if module is None:
            continue
        origin = _module_origin(module)
        if origin is None or not _inside(_ARENA_ROOT, origin):
            raise RuntimeError(
                f"ambient runtime module collision: {name} from {origin or '<unknown>'}"
            )


def _assert_arena_module(module: Any, relative: str) -> None:
    origin = _module_origin(module)
    expected = (_ARENA_ROOT / relative).resolve()
    if origin != expected:
        raise RuntimeError(
            f"private runtime import escaped arena: expected {expected}, got {origin}"
        )


_ARENA_OWNER, _ARENA_ROOT, _ARENA_MANIFEST, _ARENA_RECEIPT = (
    _materialize_private_runtime()
)
_OVERLAY_RECEIPT = _install_overlays(_ARENA_ROOT)
_ARENA_RECEIPT["overlays"] = _OVERLAY_RECEIPT
_RUNTIME_NAMES = _runtime_collision_names(_ARENA_MANIFEST)
_assert_private_runtime_modules()

_arena_text = str(_ARENA_ROOT)
while _arena_text in sys.path:
    sys.path.remove(_arena_text)
sys.path.insert(0, _arena_text)

_ENTRY = _load(
    "_sol_prism_capillary_private_entry",
    _ARENA_ROOT / "capillary_main.py",
)
_assert_arena_module(_ENTRY, "capillary_main.py")
_assert_arena_module(_ENTRY._CANDIDATE_RUNTIME, "titan_capillary.py")
_assert_arena_module(_ENTRY._canonical_module(), "main.py")
_assert_private_runtime_modules()


def agent(observation, configuration=None):
    """Delegate through the admitted Capillary entry inside the private arena."""
    return _ENTRY.agent(observation, configuration)
