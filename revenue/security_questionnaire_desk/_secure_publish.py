"""Descriptor-retained, create-exclusive artifact publication."""
from __future__ import annotations

import os
import stat
from pathlib import Path
from typing import Any, Callable, Mapping

try:
    from . import _engine as core
except ImportError:
    import _engine as core  # type: ignore[no-redef]

DeskError = core.DeskError


def _open_output_directory(path: str | os.PathLike[str]) -> tuple[int, Path]:
    if os.name == "nt" or not hasattr(os, "O_DIRECTORY"):
        raise DeskError("descriptor-bound publication requires a POSIX directory API")
    display = Path(path)
    absolute = Path(os.path.abspath(os.fspath(display)))
    components = absolute.parts[1:]
    flags = (
        os.O_RDONLY | os.O_DIRECTORY
        | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0)
    )
    current_fd = os.open(os.sep, flags)
    try:
        for index, component in enumerate(components):
            if component in ("", ".", ".."):
                raise DeskError("output path contains an unsafe component")
            final = index == len(components) - 1
            try:
                next_fd = os.open(component, flags, dir_fd=current_fd)
            except FileNotFoundError:
                if not final:
                    raise DeskError("output parent directory does not exist") from None
                try:
                    os.mkdir(component, mode=0o700, dir_fd=current_fd)
                    next_fd = os.open(component, flags, dir_fd=current_fd)
                except OSError as exc:
                    raise DeskError(f"cannot create output directory safely: {exc}") from exc
            except OSError as exc:
                raise DeskError(f"cannot open output directory safely: {exc}") from exc
            os.close(current_fd)
            current_fd = next_fd
        if not stat.S_ISDIR(os.fstat(current_fd).st_mode):
            raise DeskError("output path must resolve to a retained directory")
        return current_fd, display
    except Exception:
        os.close(current_fd)
        raise


def publish_artifacts(
    packet: Mapping[str, Any],
    output_dir: str | os.PathLike[str],
    artifact_builder: Callable[[Mapping[str, Any]], dict[str, bytes]],
) -> list[str]:
    directory_fd, display = _open_output_directory(output_dir)
    artifacts = artifact_builder(packet)
    try:
        for name in artifacts:
            try:
                entry = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
            except FileNotFoundError:
                continue
            if stat.S_ISLNK(entry.st_mode):
                raise DeskError(f"refusing final symlink: {name}")
            raise DeskError(f"refusing existing output: {name}")

        published: list[str] = []
        for name, payload in artifacts.items():
            flags = (
                os.O_WRONLY | os.O_CREAT | os.O_EXCL
                | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0)
            )
            if hasattr(os, "O_BINARY"):
                flags |= os.O_BINARY
            try:
                fd = os.open(name, flags, 0o600, dir_fd=directory_fd)
            except OSError as exc:
                raise DeskError(f"failed create-exclusive publication for {name}: {exc}") from exc
            try:
                total = 0
                while total < len(payload):
                    written = os.write(fd, payload[total:])
                    if written <= 0:
                        raise DeskError(f"short write while publishing {name}")
                    total += written
                os.fsync(fd)
                if not stat.S_ISREG(os.fstat(fd).st_mode):
                    raise DeskError(f"published target is not regular: {name}")
            finally:
                os.close(fd)
            published.append(str(display / name))
        os.fsync(directory_fd)
        return published
    finally:
        os.close(directory_fd)
