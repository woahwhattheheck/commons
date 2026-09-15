from __future__ import annotations

import os
import secrets
import stat
from pathlib import Path


class AtomicOutputError(RuntimeError):
    """Raised when output cannot be bound to one safe directory generation."""


def _directory_flags() -> int:
    missing = [name for name in ("O_DIRECTORY", "O_NOFOLLOW") if not hasattr(os, name)]
    if missing:
        raise AtomicOutputError(
            "retained-directory output unsupported: missing " + ",".join(missing)
        )
    return (
        os.O_RDONLY
        | getattr(os, "O_CLOEXEC", 0)
        | os.O_DIRECTORY
        | os.O_NOFOLLOW
    )


def _open_directory_chain(path: Path) -> int:
    """Open every path component without following symlinks and retain the leaf fd."""
    absolute = Path(os.path.abspath(os.fspath(path)))
    parts = absolute.parts
    flags = _directory_flags()
    fd = os.open(parts[0], flags)
    try:
        for part in parts[1:]:
            next_fd = os.open(part, flags, dir_fd=fd)
            os.close(fd)
            fd = next_fd
        return fd
    except BaseException:
        os.close(fd)
        raise


def _open_parent_dir(path: Path) -> int:
    try:
        return _open_directory_chain(path)
    except (OSError, TypeError, NotImplementedError) as exc:
        raise AtomicOutputError(
            f"cannot open output directory without following symlinks: {exc}"
        ) from exc


def _same_visible_parent(path: Path, held_fd: int) -> bool:
    visible_fd = -1
    try:
        visible_fd = _open_directory_chain(path)
        held = os.fstat(held_fd)
        visible = os.fstat(visible_fd)
        return (held.st_dev, held.st_ino) == (visible.st_dev, visible.st_ino)
    except (OSError, TypeError, NotImplementedError, AtomicOutputError):
        return False
    finally:
        if visible_fd >= 0:
            os.close(visible_fd)


def _assert_visible_parent(path: Path, held_fd: int) -> None:
    if not _same_visible_parent(path, held_fd):
        raise AtomicOutputError("output directory generation changed during publication")


def _check_existing_leaf(parent_fd: int, leaf: str) -> None:
    try:
        existing = os.stat(leaf, dir_fd=parent_fd, follow_symlinks=False)
    except FileNotFoundError:
        return
    except (OSError, TypeError, NotImplementedError) as exc:
        raise AtomicOutputError(f"cannot inspect output leaf safely: {exc}") from exc
    if stat.S_ISLNK(existing.st_mode):
        raise AtomicOutputError("refusing to replace a symlink output")
    if not stat.S_ISREG(existing.st_mode):
        raise AtomicOutputError("output must be a regular file when it already exists")


def _create_temp(parent_fd: int, leaf: str) -> tuple[int, str]:
    flags = (
        os.O_WRONLY
        | os.O_CREAT
        | os.O_EXCL
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_NOFOLLOW", 0)
    )
    for _ in range(128):
        name = f".{leaf}.{secrets.token_hex(12)}.tmp"
        try:
            return os.open(name, flags, 0o600, dir_fd=parent_fd), name
        except FileExistsError:
            continue
        except (OSError, TypeError, NotImplementedError) as exc:
            raise AtomicOutputError(
                f"cannot create retained-directory temporary output: {exc}"
            ) from exc
    raise AtomicOutputError("cannot allocate unique temporary output")


def _write_all(fd: int, payload: bytes) -> None:
    view = memoryview(payload)
    while view:
        written = os.write(fd, view)
        if written <= 0:
            raise AtomicOutputError("short write while publishing output")
        view = view[written:]


def write_atomic_bytes(path: Path, payload: bytes) -> None:
    """Atomically replace *path* without re-resolving its directory for writes.

    The parent path is created first, then reopened component-by-component with
    O_NOFOLLOW. Temporary creation and replacement are both relative to that one
    retained directory descriptor. Namespace movement can therefore make the
    operation fail its visible-parent fence, but cannot redirect output through a
    substituted symlink directory.
    """
    path = Path(path)
    if not isinstance(payload, bytes):
        raise TypeError("payload must be bytes")
    leaf = path.name
    if leaf in {"", ".", ".."}:
        raise AtomicOutputError("output path must name a file")

    parent = path.parent
    try:
        parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise AtomicOutputError(f"cannot create output directory: {exc}") from exc

    parent_fd = _open_parent_dir(parent)
    temp_fd = -1
    temp_name: str | None = None
    try:
        _assert_visible_parent(parent, parent_fd)
        _check_existing_leaf(parent_fd, leaf)
        temp_fd, temp_name = _create_temp(parent_fd, leaf)
        _write_all(temp_fd, payload)
        os.fsync(temp_fd)
        owned = os.fstat(temp_fd)

        _assert_visible_parent(parent, parent_fd)
        try:
            os.replace(
                temp_name,
                leaf,
                src_dir_fd=parent_fd,
                dst_dir_fd=parent_fd,
            )
        except (OSError, TypeError, NotImplementedError) as exc:
            raise AtomicOutputError(
                f"cannot atomically replace output in retained directory: {exc}"
            ) from exc
        temp_name = None

        visible = os.stat(leaf, dir_fd=parent_fd, follow_symlinks=False)
        if (visible.st_dev, visible.st_ino) != (owned.st_dev, owned.st_ino):
            raise AtomicOutputError(
                "published output generation does not match owned temporary file"
            )
        os.fsync(parent_fd)
        _assert_visible_parent(parent, parent_fd)
    except OSError as exc:
        raise AtomicOutputError(f"retained-directory publication failed: {exc}") from exc
    finally:
        if temp_name is not None:
            try:
                os.unlink(temp_name, dir_fd=parent_fd)
            except (FileNotFoundError, OSError):
                pass
        if temp_fd >= 0:
            os.close(temp_fd)
        os.close(parent_fd)
