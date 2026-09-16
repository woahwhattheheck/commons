"""Descriptor-bound custody for verified paid-proof artifacts.

The public compiler writes private and public artifacts only through retained
POSIX directory descriptors. Pathnames are used to select the destination,
but not as write authority after the destination directory has been created.
"""
from __future__ import annotations

import os
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from ._compiler_impl import (
    _verify_compiled,
    public_json,
    public_payload,
)
from .core import CompiledProof, ProofError


_DIR_OPEN_FLAGS = (
    os.O_RDONLY
    | getattr(os, "O_DIRECTORY", 0)
    | getattr(os, "O_CLOEXEC", 0)
    | getattr(os, "O_NOFOLLOW", 0)
)
_FILE_OPEN_FLAGS = (
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
    created_files: list[str]


def _require_descriptor_custody() -> None:
    required = (
        hasattr(os, "O_DIRECTORY"),
        hasattr(os, "O_NOFOLLOW"),
        os.open in os.supports_dir_fd,
        os.mkdir in os.supports_dir_fd,
        os.stat in os.supports_dir_fd,
        os.unlink in os.supports_dir_fd,
        os.rmdir in os.supports_dir_fd,
    )
    if not all(required):
        raise ProofError(
            "split-custody output requires POSIX dir_fd, O_DIRECTORY, and O_NOFOLLOW support"
        )


def _absolute(path: Path) -> Path:
    return Path(os.path.abspath(os.fspath(path)))


def _identity(fd: int) -> tuple[int, int]:
    info = os.fstat(fd)
    if not stat.S_ISDIR(info.st_mode):
        raise ProofError("custody descriptor is not a directory")
    return (info.st_dev, info.st_ino)


def _assert_mutation_safe(fd: int, display_path: Path) -> None:
    """Reject directories where another uid/group can replace child entries.

    Sticky writable directories such as /tmp are permitted: the sticky bit
    prevents other users from removing or replacing entries owned by this uid.
    A same-uid process has the same filesystem authority and is outside this
    custody boundary.
    """

    info = os.fstat(fd)
    if not stat.S_ISDIR(info.st_mode):
        raise ProofError(f"output ancestor is not a directory: {display_path}")
    writable_by_others = info.st_mode & (stat.S_IWGRP | stat.S_IWOTH)
    if writable_by_others and not (info.st_mode & stat.S_ISVTX):
        raise ProofError(
            f"output ancestor is group/other writable without sticky protection: {display_path}"
        )


def _open_existing_dir(path: Path) -> int:
    """Open an absolute directory component-by-component without following links."""

    _require_descriptor_custody()
    absolute = _absolute(path)
    if not absolute.is_absolute():
        raise ProofError(f"output path must resolve to an absolute path: {path}")

    parts = absolute.parts
    if not parts:
        raise ProofError(f"invalid output path: {path}")

    fd = os.open(parts[0], _DIR_OPEN_FLAGS)
    traversed = Path(parts[0])
    try:
        for part in parts[1:]:
            if part in {"", ".", ".."}:
                raise ProofError(f"invalid output path component: {part!r}")
            _assert_mutation_safe(fd, traversed)
            next_fd = os.open(part, _DIR_OPEN_FLAGS, dir_fd=fd)
            os.close(fd)
            fd = next_fd
            traversed /= part
        return fd
    except OSError as exc:
        os.close(fd)
        raise ProofError(f"output ancestry is not a stable no-follow directory path: {absolute}") from exc
    except Exception:
        os.close(fd)
        raise


def _create_dir_exclusive(path: Path) -> _BoundDirectory:
    absolute = _absolute(path)
    if absolute == Path(absolute.anchor):
        raise ProofError("output directory cannot be a filesystem root")

    parent = absolute.parent
    name = absolute.name
    if not name or name in {".", ".."}:
        raise ProofError(f"invalid output directory name: {absolute}")

    parent_fd = _open_existing_dir(parent)
    try:
        _assert_mutation_safe(parent_fd, parent)
        try:
            os.mkdir(name, 0o700, dir_fd=parent_fd)
        except FileExistsError as exc:
            raise ProofError(f"output directory already exists: {absolute}") from exc
        except OSError as exc:
            raise ProofError(f"could not create output directory: {absolute}") from exc

        try:
            fd = os.open(name, _DIR_OPEN_FLAGS, dir_fd=parent_fd)
        except OSError as exc:
            try:
                os.rmdir(name, dir_fd=parent_fd)
            except OSError:
                pass
            raise ProofError(f"could not bind created output directory: {absolute}") from exc

        identity = _identity(fd)
        try:
            entry = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
        except OSError as exc:
            os.close(fd)
            raise ProofError(f"created output directory lost its path binding: {absolute}") from exc
        if not stat.S_ISDIR(entry.st_mode) or (entry.st_dev, entry.st_ino) != identity:
            os.close(fd)
            raise ProofError(f"created output directory path was replaced: {absolute}")

        os.fsync(parent_fd)
        return _BoundDirectory(
            path=absolute,
            name=name,
            parent_fd=parent_fd,
            fd=fd,
            identity=identity,
            created_files=[],
        )
    except Exception:
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
        fd = os.open(name, _FILE_OPEN_FLAGS, 0o600, dir_fd=bound.fd)
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
        bound.created_files.append(name)
    finally:
        if fd >= 0:
            os.close(fd)


def _rollback(bound: _BoundDirectory) -> None:
    for name in reversed(bound.created_files):
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
    os.close(bound.fd)
    os.close(bound.parent_fd)


def _close_all(bounds: Iterable[_BoundDirectory]) -> None:
    for bound in bounds:
        try:
            _close(bound)
        except OSError:
            pass


def write_outputs(
    compiled: CompiledProof,
    internal_dir: Path,
    public_dir: Path,
) -> None:
    """Write private/public artifacts through retained, revalidated directory fds.

    Destinations must be fresh, disjoint, non-nested directories. The operation
    fails closed on platforms without POSIX descriptor-relative no-follow support.
    """

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
        _close_all(reversed(bounds))
