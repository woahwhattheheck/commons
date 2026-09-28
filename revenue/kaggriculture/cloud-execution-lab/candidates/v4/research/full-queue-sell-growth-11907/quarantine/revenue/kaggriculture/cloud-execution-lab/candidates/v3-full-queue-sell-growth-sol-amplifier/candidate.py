# SPDX-License-Identifier: Apache-2.0
"""Canonical TITAN entrypoint with isolated saturated-queue SELL expansion."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import sys
import tempfile
from typing import Any, Mapping

HERE = Path(__file__).resolve().parent
LAB = HERE.parents[1]
REPOSITORY = LAB.parents[2].resolve()
BUILD_INTEGRATED = LAB / "build_integrated.py"
SOURCE_MANIFEST = LAB / "runtime/integrated-selected/CURRENT-SOURCE.json"
EXPECTED_GIT_BLOBS = {
    HERE / "growth_patch.py": "f1803dafb558745376f28d3c9e005c4688ff4452",
    LAB / "main.py": "4a8cf7bcda1f0fea231a144692cb84a779a9e73e",
    LAB / "titan_runtime.py": "b952c9c228ecbde592bf3d2df01638677abb0d24",
    LAB / "frozen_selected.py": "fc7baf5c179818a55037f6a61d92984d81d1a21c",
    LAB / "TITAN-CONFIG.json": "3a3bef83899d3010fad623b628d9e95d9978111b",
    BUILD_INTEGRATED: "05994d946885ff0fe2a2ce77439fd335174900aa",
    SOURCE_MANIFEST: "f5d8a9f1338dbef5396de8f23262453b0f70e832",
}
REQUIRED_ROOT_MODULES = {
    "frozen_selected",
    "mechanics",
    "observed_clone",
    "scheduler",
    "selected_sell_core",
    "seller_snapshot",
    "titan_runtime",
}
_SOURCE_TREE_HOLDER: tempfile.TemporaryDirectory[str] | None = None
_SOURCE_ROOT: Path | None = None


def _regular_repository_file(path: Path) -> Path:
    """Return a normalized regular file below the checkout with no symlink hop."""
    lexical = Path(os.path.abspath(path))
    try:
        relative = lexical.relative_to(REPOSITORY)
    except ValueError as error:
        raise RuntimeError(f"SOL-AMPLIFIER source escapes checkout: {path}") from error
    cursor = REPOSITORY
    for part in relative.parts:
        cursor = cursor / part
        if cursor.is_symlink():
            raise RuntimeError(f"SOL-AMPLIFIER source uses a symlink: {cursor}")
    if not lexical.is_file():
        raise RuntimeError(f"SOL-AMPLIFIER dependency is not a regular file: {lexical}")
    resolved = lexical.resolve(strict=True)
    if resolved != lexical:
        raise RuntimeError(f"SOL-AMPLIFIER source resolution changed: {lexical} -> {resolved}")
    return lexical


def _git_blob_sha1(path: Path) -> str:
    data = _regular_repository_file(path).read_bytes()
    return hashlib.sha1(f"blob {len(data)}\0".encode("ascii") + data).hexdigest()


def _sha256(path: Path) -> str:
    return hashlib.sha256(_regular_repository_file(path).read_bytes()).hexdigest()


def _sha256_unrestricted(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _load_private(name: str, path: Path):
    """Execute an exact source file without publishing a process-global alias."""
    source = _regular_repository_file(path)
    spec = importlib.util.spec_from_file_location(name, source)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {source}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _verify_entry_files() -> dict[str, str]:
    receipt: dict[str, str] = {}
    for path, expected in EXPECTED_GIT_BLOBS.items():
        actual = _git_blob_sha1(path)
        if actual != expected:
            raise RuntimeError(
                f"SOL-AMPLIFIER dependency drift: {path.name}; "
                f"expected {expected}, got {actual}"
            )
        receipt[path.relative_to(REPOSITORY).as_posix()] = actual
    return receipt


def _manifest_runtime() -> Mapping[str, Mapping[str, Any]]:
    payload = json.loads(_regular_repository_file(SOURCE_MANIFEST).read_text(encoding="utf-8"))
    runtime = payload.get("runtime")
    if not isinstance(runtime, dict):
        raise RuntimeError("SOL-AMPLIFIER current source manifest has no runtime map")
    return runtime


def _safe_member(member: str) -> PurePosixPath:
    path = PurePosixPath(member)
    if not member or path.is_absolute() or any(part in ("", ".", "..") for part in path.parts):
        raise RuntimeError(f"SOL-AMPLIFIER unsafe archive member: {member!r}")
    return path


def _verify_and_install_source_roots() -> dict[str, Any]:
    """Materialize the verified canonical archive closure for bare imports.

    Canonical source members can be mapped from byte-distinct repository files
    whose own directories do not contain their packaged relative dependencies.
    Verify every source byte against the pinned current manifest, copy those
    bytes into one private archive-shaped tree, and expose only that tree after
    the candidate-local path.  This preserves package-relative file access and
    prevents same-named LAB mirrors from entering the execution closure.
    """
    global _SOURCE_TREE_HOLDER, _SOURCE_ROOT
    builder = _load_private("_sol_amplifier_build_integrated", BUILD_INTEGRATED)
    mapping = builder.source_files()
    if not isinstance(mapping, dict) or not mapping:
        raise RuntimeError("SOL-AMPLIFIER canonical source map is empty")
    runtime = _manifest_runtime()
    if set(mapping) != set(runtime):
        missing = sorted(set(mapping) - set(runtime))
        extra = sorted(set(runtime) - set(mapping))
        raise RuntimeError(
            f"SOL-AMPLIFIER source-map/manifest mismatch; missing={missing[:4]} extra={extra[:4]}"
        )

    holder = tempfile.TemporaryDirectory(prefix="sol-amplifier-source-")
    materialized_root = Path(holder.name).resolve()
    source_records: dict[str, dict[str, Any]] = {}
    root_records: dict[str, dict[str, Any]] = {}
    closure_digest = hashlib.sha256()

    try:
        for member in sorted(mapping):
            raw_source = mapping[member]
            if not isinstance(member, str) or not isinstance(raw_source, str):
                raise RuntimeError("SOL-AMPLIFIER source map must contain string paths")
            member_path = _safe_member(member)
            record = runtime.get(member)
            if not isinstance(record, dict):
                raise RuntimeError(f"SOL-AMPLIFIER manifest record missing for {member}")
            origin = _regular_repository_file(LAB / raw_source)
            data = origin.read_bytes()
            digest = hashlib.sha256(data).hexdigest()
            if (
                record.get("source_path") != raw_source
                or type(record.get("bytes")) is not int
                or record.get("bytes") != len(data)
                or record.get("sha256") != digest
            ):
                raise RuntimeError(f"SOL-AMPLIFIER manifest byte mismatch for {member}")

            relative_origin = origin.relative_to(REPOSITORY).as_posix()
            target = materialized_root.joinpath(*member_path.parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("xb") as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
            if target.is_symlink() or target.resolve(strict=True) != target:
                raise RuntimeError(f"SOL-AMPLIFIER materialized source changed: {member}")
            if target.stat().st_size != len(data) or _sha256_unrestricted(target) != digest:
                raise RuntimeError(f"SOL-AMPLIFIER materialized byte mismatch for {member}")

            source_records[member] = {
                "source_path": raw_source,
                "repository_path": relative_origin,
                "materialized_member": member,
                "bytes": len(data),
                "sha256": digest,
            }
            closure_digest.update(member.encode("utf-8") + b"\0")
            closure_digest.update(relative_origin.encode("utf-8") + b"\0")
            closure_digest.update(bytes.fromhex(digest))

            if member_path.parent != PurePosixPath(".") or member_path.suffix != ".py":
                continue
            module_name = member_path.stem
            if not module_name.isidentifier() or module_name in root_records:
                raise RuntimeError(f"SOL-AMPLIFIER invalid root module mapping: {member}")
            root_records[module_name] = {
                "member": member,
                "declared_origin": relative_origin,
                "materialized_member": member,
                "sha256": digest,
            }

        if not REQUIRED_ROOT_MODULES.issubset(root_records):
            absent = sorted(REQUIRED_ROOT_MODULES - set(root_records))
            raise RuntimeError(f"SOL-AMPLIFIER required root modules absent: {absent}")

        ordered = [HERE.resolve(), materialized_root]
        for root in reversed(ordered):
            value = str(root)
            while value in sys.path:
                sys.path.remove(value)
            sys.path.insert(0, value)

        for module_name, record in root_records.items():
            expected = materialized_root.joinpath(*PurePosixPath(record["member"]).parts)
            loaded = sys.modules.get(module_name)
            if loaded is not None:
                loaded_file = getattr(loaded, "__file__", None)
                if not loaded_file or Path(loaded_file).resolve(strict=True) != expected:
                    raise RuntimeError(
                        f"SOL-AMPLIFIER preloaded module collision: {module_name}"
                    )
            spec = importlib.util.find_spec(module_name)
            if spec is None or spec.origin is None:
                raise RuntimeError(f"SOL-AMPLIFIER root module is not importable: {module_name}")
            actual = Path(spec.origin).resolve(strict=True)
            if actual != expected or _sha256_unrestricted(actual) != record["sha256"]:
                raise RuntimeError(
                    f"SOL-AMPLIFIER root module resolves outside closure: "
                    f"{module_name} -> {actual}"
                )
            record["import_origin"] = record["materialized_member"]

        _SOURCE_TREE_HOLDER = holder
        _SOURCE_ROOT = materialized_root
        observed = root_records["observed_clone"]
        return {
            "mapped_files": len(source_records),
            "mapped_sha256": closure_digest.hexdigest(),
            "root_modules": root_records,
            "pythonpath": ["candidate", "materialized-current-archive"],
            "materialization": {
                "mode": "verified-private-copy",
                "files": len(source_records),
                "root_retained_for_process_lifetime": True,
            },
            "observed_clone": {
                "import_origin": observed["import_origin"],
                "sha256": observed["sha256"],
            },
        }
    except BaseException:
        holder.cleanup()
        raise


_ENTRY_FILES = _verify_entry_files()
_SOURCE_CLOSURE = _verify_and_install_source_roots()
_GROWTH_PATCH = _load_private(
    "_sol_amplifier_full_queue_growth_patch", HERE / "growth_patch.py"
)
attach = _GROWTH_PATCH.attach
_CANONICAL = _load_private(
    "_sol_amplifier_full_queue_growth_main", LAB / "main.py"
)
_ORIGINAL_NEW_INSTANCE = _CANONICAL._new_instance
_LAST_INSTALL_RECEIPT: dict[str, Any] | None = None


def _candidate_new_instance(root: Path, feature_data: dict[str, Any]):
    """Attach the private selected-seller class before canonical lazy init."""
    global _LAST_INSTALL_RECEIPT
    instance = _ORIGINAL_NEW_INSTANCE(root, feature_data)
    import frozen_selected

    record = _SOURCE_CLOSURE["root_modules"]["frozen_selected"]
    if _SOURCE_ROOT is None:
        raise RuntimeError("SOL-AMPLIFIER materialized source root is unavailable")
    expected = _SOURCE_ROOT.joinpath(*PurePosixPath(record["member"]).parts)
    actual = Path(frozen_selected.__file__).resolve(strict=True)
    if actual != expected or _sha256_unrestricted(actual) != record["sha256"]:
        raise RuntimeError(f"SOL-AMPLIFIER selected consumer alias: {actual} != {expected}")
    _LAST_INSTALL_RECEIPT = {
        **attach(instance, frozen_selected),
        "entry_files": dict(_ENTRY_FILES),
        "source_closure": dict(_SOURCE_CLOSURE),
    }
    return instance


# Canonical agent resolves this global during its existing timed construction.
# Its prelude, whole-call deadline, fallback, reconstruction and final-pressure
# return boundary remain the original implementation.
_CANONICAL._new_instance = _candidate_new_instance


def agent(observation, configuration=None):
    return _CANONICAL.agent(observation, configuration)
