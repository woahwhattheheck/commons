"""Race-resistant publication for connector-preflight JSON receipts."""
from __future__ import annotations

import json
import os
import stat
from pathlib import Path
from typing import Any

from .core import PreflightError


def _same_identity(left: os.stat_result, right: os.stat_result) -> bool:
    return (left.st_dev, left.st_ino) == (right.st_dev, right.st_ino)


def _same_generation(left: os.stat_result, right: os.stat_result) -> bool:
    return (
        _same_identity(left, right)
        and left.st_mode == right.st_mode
        and left.st_nlink == right.st_nlink
        and left.st_size == right.st_size
        and left.st_mtime_ns == right.st_mtime_ns
        and left.st_ctime_ns == right.st_ctime_ns
    )


def _cleanup_owned_path(path: Path, created: os.stat_result) -> None:
    """Remove only the pathname generation created by this writer."""
    try:
        visible = os.lstat(path)
    except OSError:
        return
    if not stat.S_ISREG(visible.st_mode) or not _same_identity(visible, created):
        return
    try:
        os.unlink(path)
    except OSError:
        pass


def _verify_visible_bytes(path: Path, data: bytes, created: os.stat_result) -> None:
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        fd = os.open(path, flags)
    except OSError as exc:
        raise PreflightError(f"cannot reopen published output safely: {exc}") from exc
    try:
        opened = os.fstat(fd)
        if not stat.S_ISREG(opened.st_mode) or not _same_generation(opened, created):
            raise PreflightError("published output path changed generation")
        chunks: list[bytes] = []
        remaining = len(data) + 1
        while remaining:
            part = os.read(fd, min(65536, remaining))
            if not part:
                break
            chunks.append(part)
            remaining -= len(part)
        if b"".join(chunks) != data:
            raise PreflightError("published output bytes differ from retained write")
        after_read = os.fstat(fd)
        if not _same_generation(after_read, created):
            raise PreflightError("published output changed during readback")
    finally:
        os.close(fd)

    try:
        visible = os.lstat(path)
    except OSError as exc:
        raise PreflightError(f"published output path disappeared: {exc}") from exc
    if not stat.S_ISREG(visible.st_mode) or not _same_generation(visible, created):
        raise PreflightError("published output path changed after readback")


def write_json_exclusive(path: Path, value: Any) -> None:
    """Create JSON exactly once and prove the visible pathname owns those bytes."""
    data = (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n").encode("utf-8")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        fd = os.open(path, flags, 0o600)
    except OSError as exc:
        raise PreflightError(f"cannot create output exclusively: {exc}") from exc

    created = os.fstat(fd)
    try:
        if not stat.S_ISREG(created.st_mode) or created.st_nlink != 1:
            raise PreflightError("new output must be one regular pathname")
        view = memoryview(data)
        while view:
            written = os.write(fd, view)
            if written <= 0:
                raise PreflightError("short output write")
            view = view[written:]
        os.fsync(fd)
        retained = os.fstat(fd)
        if not stat.S_ISREG(retained.st_mode) or retained.st_nlink != 1:
            raise PreflightError("retained output generation is not singly linked regular data")
        if not _same_identity(retained, created) or retained.st_size != len(data):
            raise PreflightError("retained output generation changed during write")
        _verify_visible_bytes(path, data, retained)
    except Exception as exc:
        _cleanup_owned_path(path, created)
        if isinstance(exc, PreflightError):
            raise
        if isinstance(exc, OSError):
            raise PreflightError(f"cannot publish output safely: {exc}") from exc
        raise
    finally:
        os.close(fd)
