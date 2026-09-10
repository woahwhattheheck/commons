# SPDX-License-Identifier: Apache-2.0
"""Authenticated private import closure for source-tree route-regret arms.

The canonical archive places ``observed_clone.py`` beside ``scheduler.py``.
The repository source keeps that exact file in ``cloud-runtime-pulse`` instead.
Route-regret executes the source tree from a fresh private worker directory, so
it must reproduce that one archive-root binding explicitly without changing any
canonical policy source.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import importlib.util
import inspect
import os
from pathlib import Path
import stat
import sys
from types import ModuleType
from typing import Any

from source_contract import git_blob_sha1, sha256, source_path, verify_source_contract

MODULE_NAME = "observed_clone"
SOURCE_KEY = "../cloud-runtime-pulse/observed_clone.py"
SCHEDULER_KEY = "../cloud-execution-lab/scheduler.py"
PRIVATE_DIRECTORY = ".titan-route-regret-imports"
EXPECTED_EXPORT = "detached_json_value"

_INSTALLED: dict[str, Any] | None = None


def _regular_bytes(path: Path, label: str) -> bytes:
    """Read one regular non-symlink file without accepting path substitution."""
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"{label} must be a regular non-symlink file: {path}")
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise ValueError(f"{label} is not a regular file: {path}")
        chunks: list[bytes] = []
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
        after = os.fstat(descriptor)
        if (before.st_dev, before.st_ino, before.st_size) != (
            after.st_dev,
            after.st_ino,
            after.st_size,
        ):
            raise ValueError(f"{label} changed while it was read: {path}")
        return b"".join(chunks)
    finally:
        os.close(descriptor)


def _validate_bytes(data: bytes, metadata: dict[str, Any], label: str) -> None:
    expected_blob = metadata.get("git_blob")
    expected_sha256 = metadata.get("sha256")
    expected_bytes = metadata.get("bytes")
    if not isinstance(expected_blob, str) or len(expected_blob) != 40:
        raise ValueError(f"{label} has no valid Git-blob binding")
    if not isinstance(expected_sha256, str) or len(expected_sha256) != 64:
        raise ValueError(f"{label} has no valid SHA-256 binding")
    if type(expected_bytes) is not int or expected_bytes < 0:
        raise ValueError(f"{label} has no valid byte-count binding")
    actual_blob = hashlib.sha1(
        b"blob " + str(len(data)).encode("ascii") + b"\0" + data
    ).hexdigest()
    actual_sha256 = hashlib.sha256(data).hexdigest()
    if actual_blob != expected_blob:
        raise ValueError(
            f"{label} Git blob mismatch: expected {expected_blob}, got {actual_blob}"
        )
    if actual_sha256 != expected_sha256:
        raise ValueError(
            f"{label} SHA-256 mismatch: expected {expected_sha256}, got {actual_sha256}"
        )
    if len(data) != expected_bytes:
        raise ValueError(
            f"{label} byte-count mismatch: expected {expected_bytes}, got {len(data)}"
        )


def _normalized_private_root(path: Path | None) -> Path:
    raw = (Path.cwd() / PRIVATE_DIRECTORY) if path is None else Path(path)
    if not raw.name or raw.name in {".", ".."}:
        raise ValueError(f"invalid private import root: {raw}")
    parent = raw.parent.resolve(strict=True)
    return parent / raw.name


def _create_private_root(path: Path | None) -> Path:
    root = _normalized_private_root(path)
    if root.exists() or root.is_symlink():
        raise FileExistsError(f"private import root already exists: {root}")
    os.mkdir(root, 0o700)
    return root.resolve(strict=True)


def _publish_exclusive(path: Path, data: bytes) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags, 0o600)
    try:
        remaining = memoryview(data)
        while remaining:
            written = os.write(descriptor, remaining)
            if written <= 0:
                raise OSError("private import write made no progress")
            remaining = remaining[written:]
        os.fsync(descriptor)
    except BaseException:
        try:
            os.close(descriptor)
        finally:
            try:
                path.unlink()
            except FileNotFoundError:
                pass
        raise
    else:
        os.close(descriptor)
    directory_descriptor = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(directory_descriptor)
    finally:
        os.close(directory_descriptor)


def _load_exact(name: str, path: Path) -> ModuleType:
    existing = sys.modules.get(name)
    if existing is not None:
        origin = getattr(existing, "__file__", None)
        raise ValueError(
            f"ambient module already occupies {name!r}: {origin!r}; "
            "fresh-worker import custody is required"
        )
    specification = importlib.util.spec_from_file_location(name, path)
    if specification is None or specification.loader is None:
        raise RuntimeError(f"cannot create import specification for {path}")
    module = importlib.util.module_from_spec(specification)
    sys.modules[name] = module
    try:
        specification.loader.exec_module(module)
    except BaseException:
        if sys.modules.get(name) is module:
            sys.modules.pop(name, None)
        raise
    origin = Path(getattr(module, "__file__", "")).resolve(strict=True)
    if origin != path.resolve(strict=True):
        sys.modules.pop(name, None)
        raise ValueError(f"module origin drift for {name}: {origin} != {path}")
    exported = getattr(module, EXPECTED_EXPORT, None)
    if not callable(exported):
        sys.modules.pop(name, None)
        raise ValueError(f"bound module does not export callable {EXPECTED_EXPORT}")
    return module


def install(
    source_receipt: dict[str, Any] | None = None,
    *,
    private_root: Path | None = None,
) -> dict[str, Any]:
    """Copy and preload the one archive-root-only dependency in this worker.

    The operation is idempotent only for the exact root already installed by
    this module instance. Any pre-existing module, destination, or divergent
    root fails closed instead of inheriting ambient import state.
    """
    global _INSTALLED
    receipt = source_receipt or verify_source_contract()
    bindings = receipt.get("import_bindings")
    if bindings != {MODULE_NAME: SOURCE_KEY}:
        raise ValueError(f"unexpected import bindings: {bindings!r}")
    source_metadata = (receipt.get("git_blobs") or {}).get(SOURCE_KEY)
    scheduler_metadata = (receipt.get("git_blobs") or {}).get(SCHEDULER_KEY)
    if not isinstance(source_metadata, dict):
        raise ValueError(f"source receipt omits import binding {SOURCE_KEY}")
    if not isinstance(scheduler_metadata, dict):
        raise ValueError(f"source receipt omits scheduler binding {SCHEDULER_KEY}")
    source = source_path(SOURCE_KEY)
    source_data = _regular_bytes(source, "bound import source")
    _validate_bytes(source_data, source_metadata, "bound import source")

    requested_root = _normalized_private_root(private_root)
    if _INSTALLED is not None:
        installed_root = Path(_INSTALLED["private_root"])
        if requested_root != installed_root:
            raise ValueError(
                f"import closure already installed at {installed_root}, "
                f"not requested root {requested_root}"
            )
        destination = Path(_INSTALLED["private_path"])
        staged_data = _regular_bytes(destination, "installed private import")
        _validate_bytes(staged_data, source_metadata, "installed private import")
        module = sys.modules.get(MODULE_NAME)
        if module is None or Path(getattr(module, "__file__", "")).resolve() != destination:
            raise ValueError("installed import module identity was replaced")
        if _INSTALLED.get("scheduler_binding") != scheduler_metadata:
            raise ValueError("scheduler binding changed after private import installation")
        return deepcopy(_INSTALLED)

    if MODULE_NAME in sys.modules:
        origin = getattr(sys.modules[MODULE_NAME], "__file__", None)
        raise ValueError(f"ambient module already occupies {MODULE_NAME!r}: {origin!r}")
    root = _create_private_root(private_root)
    destination = root / f"{MODULE_NAME}.py"
    try:
        _publish_exclusive(destination, source_data)
        staged_data = _regular_bytes(destination, "private import copy")
        _validate_bytes(staged_data, source_metadata, "private import copy")
        module = _load_exact(MODULE_NAME, destination)
        exported = getattr(module, EXPECTED_EXPORT)
        function_origin = Path(inspect.getsourcefile(exported) or "").resolve(strict=True)
        if function_origin != destination.resolve(strict=True):
            raise ValueError(
                f"bound export origin drift: {function_origin} != {destination.resolve()}"
            )
    except BaseException:
        sys.modules.pop(MODULE_NAME, None)
        try:
            destination.unlink()
        except FileNotFoundError:
            pass
        try:
            root.rmdir()
        except OSError:
            pass
        raise
    _INSTALLED = {
        "schema": "titan-route-regret-private-import/v1",
        "module": MODULE_NAME,
        "export": EXPECTED_EXPORT,
        "source_key": SOURCE_KEY,
        "source_path": str(source),
        "private_root": str(root),
        "private_path": str(destination.resolve(strict=True)),
        "git_blob": git_blob_sha1(destination),
        "sha256": sha256(destination),
        "bytes": destination.stat().st_size,
        "scheduler_binding": deepcopy(scheduler_metadata),
    }
    return deepcopy(_INSTALLED)


def attest_scheduler() -> dict[str, Any]:
    """Prove the selected current scheduler consumed the staged exact export."""
    if _INSTALLED is None:
        raise ValueError("private import closure was not installed")
    bound_module = sys.modules.get(MODULE_NAME)
    scheduler = sys.modules.get("scheduler")
    if bound_module is None:
        raise ValueError("bound import module disappeared")
    if scheduler is None:
        raise ValueError("canonical scheduler has not been imported")
    expected_scheduler = source_path(SCHEDULER_KEY)
    scheduler_origin = Path(getattr(scheduler, "__file__", "")).resolve(strict=True)
    if scheduler_origin != expected_scheduler:
        raise ValueError(
            f"canonical scheduler origin drift: {scheduler_origin} != {expected_scheduler}"
        )
    scheduler_data = _regular_bytes(scheduler_origin, "imported canonical scheduler")
    _validate_bytes(
        scheduler_data,
        _INSTALLED["scheduler_binding"],
        "imported canonical scheduler",
    )
    consumed = getattr(scheduler, EXPECTED_EXPORT, None)
    exported = getattr(bound_module, EXPECTED_EXPORT, None)
    if consumed is not exported or not callable(consumed):
        raise ValueError("canonical scheduler did not consume the bound exact export")
    function_origin = Path(inspect.getsourcefile(consumed) or "").resolve(strict=True)
    private_path = Path(_INSTALLED["private_path"]).resolve(strict=True)
    if function_origin != private_path:
        raise ValueError(
            f"scheduler export origin drift: {function_origin} != {private_path}"
        )
    result = deepcopy(_INSTALLED)
    result.update(
        scheduler_path=str(scheduler_origin),
        scheduler_git_blob=git_blob_sha1(scheduler_origin),
        scheduler_sha256=sha256(scheduler_origin),
        scheduler_bytes=scheduler_origin.stat().st_size,
        identity_bound=True,
    )
    return result


def _reset_for_tests() -> None:
    """Test-only reset; production workers never reuse an interpreter."""
    global _INSTALLED
    sys.modules.pop(MODULE_NAME, None)
    _INSTALLED = None
