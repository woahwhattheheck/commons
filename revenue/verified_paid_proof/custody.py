"""Descriptor-bound custody for verified paid-proof artifacts."""
from __future__ import annotations

import os
import stat
from dataclasses import dataclass
from pathlib import Path

from .compiler import _verify_compiled, public_json, public_payload
from .core import CompiledProof, ProofError

_DIR_FLAGS = (
    os.O_RDONLY
    | getattr(os, "O_DIRECTORY", 0)
    | getattr(os, "O_CLOEXEC", 0)
    | getattr(os, "O_NOFOLLOW", 0)
)
_FILE_FLAGS = (
    os.O_WRONLY
    | os.O_CREAT
    | os.O_EXCL
    | getattr(os, "O_CLOEXEC", 0)
    | getattr(os, "O_NOFOLLOW", 0)
)


@dataclass
class _BoundDirectory:
    path: Path
    name: str
    parent_fd: int
    fd: int
    identity: tuple[int, int]


def _require_descriptor_custody() -> None:
    supported = (
        hasattr(os, "O_DIRECTORY"),
        hasattr(os, "O_NOFOLLOW"),
        os.open in os.supports_dir_fd,
        os.mkdir in os.supports_dir_fd,
        os.stat in os.supports_dir_fd,
        os.unlink in os.supports_dir_fd,
        os.rmdir in os.supports_dir_fd,
        os.listdir in os.supports_fd,
    )
    if not all(supported):
        raise ProofError(
            "split-custody output requires POSIX dir_fd, O_DIRECTORY, and O_NOFOLLOW support"
        )


def _absolute(path: Path) -> Path:
    return Path(os.path.abspath(os.fspath(path)))


def _identity(fd: int) -> tuple[int, int]:
    info = os.fstat(fd)
    if not stat.S_ISDIR(info.st_mode):
        raise ProofError("custody descriptor is not a directory")
    return info.st_dev, info.st_ino


def _assert_mutation_safe(fd: int, path: Path) -> None:
    info = os.fstat(fd)
    if not stat.S_ISDIR(info.st_mode):
        raise ProofError(f"output ancestor is not a directory: {path}")
    writable = info.st_mode & (stat.S_IWGRP | stat.S_IWOTH)
    if writable and not info.st_mode & stat.S_ISVTX:
        raise ProofError(
            f"output ancestor is group/other writable without sticky protection: {path}"
        )


def _open_existing_dir(path: Path) -> int:
    _require_descriptor_custody()
    absolute = _absolute(path)
    parts = absolute.parts
    if not parts:
        raise ProofError(f"invalid output path: {path}")
    try:
        fd = os.open(parts[0], _DIR_FLAGS)
    except OSError as exc:
        raise ProofError(f"cannot open output root: {absolute}") from exc
    traversed = Path(parts[0])
    try:
        for part in parts[1:]:
            if part in {"", ".", ".."}:
                raise ProofError(f"invalid output path component: {part!r}")
            _assert_mutation_safe(fd, traversed)
            next_fd = os.open(part, _DIR_FLAGS, dir_fd=fd)
            os.close(fd)
            fd = next_fd
            traversed /= part
        return fd
    except OSError as exc:
        os.close(fd)
        raise ProofError(
            f"output ancestry is not a stable no-follow directory path: {absolute}"
        ) from exc
    except Exception:
        os.close(fd)
        raise


def _create_dir_exclusive(path: Path) -> _BoundDirectory:
    absolute = _absolute(path)
    if absolute == Path(absolute.anchor):
        raise ProofError("output directory cannot be a filesystem root")
    parent, name = absolute.parent, absolute.name
    if not name or name in {".", ".."}:
        raise ProofError(f"invalid output directory name: {absolute}")
    parent_fd = _open_existing_dir(parent)
    created = False
    fd = -1
    try:
        _assert_mutation_safe(parent_fd, parent)
        try:
            os.mkdir(name, 0o700, dir_fd=parent_fd)
            created = True
        except FileExistsError as exc:
            raise ProofError(f"output directory already exists: {absolute}") from exc
        fd = os.open(name, _DIR_FLAGS, dir_fd=parent_fd)
        identity = _identity(fd)
        entry = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
        if not stat.S_ISDIR(entry.st_mode) or (entry.st_dev, entry.st_ino) != identity:
            raise ProofError(f"created output directory path was replaced: {absolute}")
        os.fsync(parent_fd)
        return _BoundDirectory(absolute, name, parent_fd, fd, identity)
    except Exception:
        if fd >= 0:
            os.close(fd)
        if created:
            try:
                os.rmdir(name, dir_fd=parent_fd)
            except OSError:
                pass
        os.close(parent_fd)
        raise


def _verify_dir_binding(bound: _BoundDirectory) -> None:
    if _identity(bound.fd) != bound.identity:
        raise ProofError(f"output directory descriptor changed identity: {bound.path}")
    try:
        entry = os.stat(bound.name, dir_fd=bound.parent_fd, follow_symlinks=False)
    except OSError as exc:
        raise ProofError(f"output directory lost its path binding: {bound.path}") from exc
    if not stat.S_ISDIR(entry.st_mode) or (entry.st_dev, entry.st_ino) != bound.identity:
        raise ProofError(f"output directory path was replaced during write: {bound.path}")


def _write_new_text(bound: _BoundDirectory, name: str, text: str) -> None:
    if not name or "/" in name or name in {".", ".."}:
        raise ProofError(f"invalid output filename: {name!r}")
    try:
        fd = os.open(name, _FILE_FLAGS, 0o600, dir_fd=bound.fd)
    except FileExistsError as exc:
        raise ProofError(f"output file already exists: {bound.path / name}") from exc
    except OSError as exc:
        raise ProofError(f"could not create output file: {bound.path / name}") from exc
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            fd = -1
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
    finally:
        if fd >= 0:
            os.close(fd)


def _rollback(bound: _BoundDirectory) -> None:
    try:
        names = os.listdir(bound.fd)
    except OSError:
        names = []
    for name in names:
        try:
            os.unlink(name, dir_fd=bound.fd)
        except OSError:
            pass
    try:
        os.fsync(bound.fd)
    except OSError:
        pass
    try:
        os.rmdir(bound.name, dir_fd=bound.parent_fd)
    except OSError:
        pass
    try:
        os.fsync(bound.parent_fd)
    except OSError:
        pass


def _close(bound: _BoundDirectory) -> None:
    for fd in (bound.fd, bound.parent_fd):
        try:
            os.close(fd)
        except OSError:
            pass


def write_outputs(
    compiled: CompiledProof,
    internal_dir: Path,
    public_dir: Path,
) -> None:
    """Write private/public artifacts only through retained no-follow dir fds."""

    _verify_compiled(compiled)
    _require_descriptor_custody()
    internal_path = _absolute(internal_dir)
    public_path = _absolute(public_dir)
    if (
        internal_path == public_path
        or internal_path in public_path.parents
        or public_path in internal_path.parents
    ):
        raise ProofError("internal and public output directories must be disjoint")

    bounds: list[_BoundDirectory] = []
    try:
        internal = _create_dir_exclusive(internal_path)
        bounds.append(internal)
        public = _create_dir_exclusive(public_path)
        bounds.append(public)
        outputs = [
            (internal, "proof.json", compiled.proof_json()),
            (internal, "receipt.sha256", compiled.receipt_sha256 + "\n"),
            (public, "proof.md", compiled.markdown),
            (public, "public.json", public_json(compiled)),
            (
                public,
                "receipt.sha256",
                public_payload(compiled)["public_receipt_sha256"] + "\n",
            ),
        ]
        for bound, name, text in outputs:
            _write_new_text(bound, name, text)
        for bound in bounds:
            os.fsync(bound.fd)
            _verify_dir_binding(bound)
        for bound in bounds:
            os.fsync(bound.parent_fd)
    except Exception:
        for bound in reversed(bounds):
            _rollback(bound)
        raise
    finally:
        for bound in reversed(bounds):
            _close(bound)
