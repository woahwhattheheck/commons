"""Filesystem custody and create-exclusive publication helpers."""
from __future__ import annotations

import os
import stat
from pathlib import Path, PurePosixPath
from typing import Any

from .schema import AssemblyError, ArtifactCustodyError, MAX_ARTIFACT_BYTES, MAX_JSON_BYTES

def _read_regular_bounded(path: Path, max_bytes: int) -> bytes:
    # Refuse special files before open: opening a FIFO read-only can block forever,
    # and a symlink must never become an implicit artifact-custody redirect.
    try:
        lst = path.lstat()
    except OSError as exc:
        raise ArtifactCustodyError(str(exc)) from exc
    if stat.S_ISLNK(lst.st_mode):
        raise ArtifactCustodyError("symlink forbidden")
    if not stat.S_ISREG(lst.st_mode):
        raise ArtifactCustodyError("regular file required")
    if lst.st_size > max_bytes:
        raise ArtifactCustodyError("file exceeds byte cap")

    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = None
    try:
        fd = os.open(str(path), flags)
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode):
            raise ArtifactCustodyError("regular file required")
        if before.st_size > max_bytes:
            raise ArtifactCustodyError("file exceeds byte cap")
        chunks = []
        remaining = max_bytes + 1
        while remaining > 0:
            chunk = os.read(fd, min(65536, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        data = b"".join(chunks)
        if len(data) > max_bytes:
            raise ArtifactCustodyError("file exceeds byte cap")
        after = os.fstat(fd)
        identity_before = (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns)
        identity_after = (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns)
        if identity_before != identity_after or len(data) != after.st_size:
            raise ArtifactCustodyError("file changed while being read")
        return data
    except OSError as exc:
        raise ArtifactCustodyError(str(exc)) from exc
    finally:
        if fd is not None:
            os.close(fd)


def artifact_loader_from_root(root: Path):
    try:
        root_lstat = root.lstat()
    except OSError as exc:
        raise ArtifactCustodyError(f"artifact root unavailable: {exc}") from exc
    if stat.S_ISLNK(root_lstat.st_mode) or not stat.S_ISDIR(root_lstat.st_mode):
        raise ArtifactCustodyError("artifact root must be a real directory, not a symlink")
    root_real = root.resolve(strict=True)

    def load(artifact: dict[str, Any]) -> bytes:
        rel = PurePosixPath(artifact["path"])
        candidate = root_real.joinpath(*rel.parts)
        try:
            parent_real = candidate.parent.resolve(strict=True)
        except OSError as exc:
            raise ArtifactCustodyError(f"artifact parent unavailable: {exc}") from exc
        try:
            parent_real.relative_to(root_real)
        except ValueError as exc:
            raise ArtifactCustodyError("artifact escapes root") from exc
        return _read_regular_bounded(candidate, MAX_ARTIFACT_BYTES)

    return load


def _ensure_real_dir(path: Path):
    if path.exists() or path.is_symlink():
        mode = path.lstat().st_mode
        if stat.S_ISLNK(mode) or not stat.S_ISDIR(mode):
            raise AssemblyError("output path must be a real directory")
    else:
        path.mkdir(parents=True, mode=0o700)
    if stat.S_ISLNK(path.lstat().st_mode):
        raise AssemblyError("output directory symlink forbidden")


def _write_exclusive(path: Path, data: bytes):
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = None
    try:
        fd = os.open(str(path), flags, 0o600)
        with os.fdopen(fd, "wb", closefd=False) as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
    except OSError as exc:
        raise AssemblyError(f"exclusive output failed for {path.name}: {exc}") from exc
    finally:
        if fd is not None:
            os.close(fd)


def _load_input_file(path: Path) -> bytes:
    return _read_regular_bounded(path, MAX_JSON_BYTES)
