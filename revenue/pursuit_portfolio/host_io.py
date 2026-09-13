"""Production package-generation custody for Pursuit Portfolio v2.

This is the package/CLI I/O surface layered on ``host.py``.  It strengthens
success from "each file was owned when written" to "the complete visible
package is still the exact retained generation at the end of publication" and
reads the complete package twice under one retained directory generation before
current verification.
"""
from __future__ import annotations

import os
from pathlib import Path
import stat
from typing import Any

from . import core_v2 as core
from . import host

_PACKAGE = (
    ("portfolio.json", core.MAX_FILE_BYTES),
    ("portfolio.md", core.MAX_FILE_BYTES),
    ("receipt.json", core.MAX_FILE_BYTES),
    ("host-seal.json", host.MAX_SEAL_BYTES),
)


def _same_generation(info: os.stat_result, generation: tuple[int, int]) -> bool:
    return (int(info.st_dev), int(info.st_ino)) == generation


def _dir_metadata(info: os.stat_result) -> tuple[int, int, int, int]:
    return (
        int(info.st_dev),
        int(info.st_ino),
        int(getattr(info, "st_mtime_ns", int(info.st_mtime * 1_000_000_000))),
        int(getattr(info, "st_ctime_ns", int(info.st_ctime * 1_000_000_000))),
    )


def _write_owned_relative(dir_fd: int, name: str, data: bytes) -> tuple[int, int]:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC
    fd = os.open(name, flags, 0o600, dir_fd=dir_fd)
    try:
        opened = os.fstat(fd)
        if not stat.S_ISREG(opened.st_mode):
            raise core.PortfolioError(f"publication: {name} is not a regular file")
        view = memoryview(data)
        while view:
            written = os.write(fd, view)
            if written <= 0:
                raise core.PortfolioError(f"publication: short write for {name}")
            view = view[written:]
        os.fsync(fd)
        final = os.fstat(fd)
        visible = os.stat(name, dir_fd=dir_fd, follow_symlinks=False)
        generation = (int(final.st_dev), int(final.st_ino))
        if not _same_generation(visible, generation):
            raise core.PortfolioError(
                f"publication: visible output ownership changed: {name}"
            )
        if not stat.S_ISREG(visible.st_mode):
            raise core.PortfolioError(
                f"publication: visible output is not regular: {name}"
            )
        return generation
    finally:
        os.close(fd)


def publish_current(value: host.HostCompiledPortfolio, out_dir: str | Path) -> None:
    """Publish one complete package into a pre-existing retained directory."""
    absolute = os.path.abspath(os.fspath(out_dir))
    dir_fd = host._open_dir_chain(absolute)
    published: dict[str, tuple[int, int]] = {}
    try:
        retained_dir = os.fstat(dir_fd)
        files = (
            ("portfolio.json", value.compiled.result_bytes),
            ("portfolio.md", value.compiled.markdown_bytes),
            ("receipt.json", value.compiled.receipt_bytes),
            ("host-seal.json", value.host_seal_bytes),
        )
        for name, raw in files:
            try:
                published[name] = _write_owned_relative(dir_fd, name, raw)
            except Exception as exc:
                raise core.PortfolioError(
                    "publication failed; retained output generation preserved; "
                    f"already-published files: {','.join(published) or 'none'}"
                ) from exc

        os.fsync(dir_fd)

        # Success is package-wide, not per-write.  A file replaced after its
        # individual write check invalidates the publication before success.
        for name, generation in published.items():
            try:
                visible = os.stat(name, dir_fd=dir_fd, follow_symlinks=False)
            except OSError as exc:
                raise core.PortfolioError(
                    f"publication: visible output disappeared after publication: {name}"
                ) from exc
            if not _same_generation(visible, generation) or not stat.S_ISREG(
                visible.st_mode
            ):
                raise core.PortfolioError(
                    f"publication: visible output generation changed after publication: {name}"
                )

        # Also require the user-visible output pathname to still resolve to the
        # retained directory inode.  We do not delete anything on mismatch.
        try:
            visible_dir = os.stat(absolute, follow_symlinks=False)
        except OSError as exc:
            raise core.PortfolioError(
                "publication: output directory pathname disappeared"
            ) from exc
        retained_generation = (int(retained_dir.st_dev), int(retained_dir.st_ino))
        if not _same_generation(visible_dir, retained_generation) or not stat.S_ISDIR(
            visible_dir.st_mode
        ):
            raise core.PortfolioError(
                "publication: output directory pathname no longer names retained generation"
            )
        os.fsync(dir_fd)
    finally:
        os.close(dir_fd)


def _scan(dir_fd: int) -> tuple[bytes, bytes, bytes, bytes]:
    parts: list[bytes] = []
    for name, maximum in _PACKAGE:
        parts.append(host._read_relative(dir_fd, name, maximum, name))
    return parts[0], parts[1], parts[2], parts[3]


def read_current_directory(root: str | Path) -> tuple[bytes, bytes, bytes, bytes]:
    """Read one stable complete package generation under a retained directory."""
    absolute = os.path.abspath(os.fspath(root))
    dir_fd = host._open_dir_chain(absolute)
    try:
        before = os.fstat(dir_fd)
        first = _scan(dir_fd)
        middle = os.fstat(dir_fd)
        second = _scan(dir_fd)
        after = os.fstat(dir_fd)
        if first != second:
            raise core.PortfolioError(
                "verify: package generation changed between complete scans"
            )
        if not (
            _dir_metadata(before) == _dir_metadata(middle) == _dir_metadata(after)
        ):
            raise core.PortfolioError(
                "verify: retained directory generation changed while reading package"
            )
        try:
            visible_dir = os.stat(absolute, follow_symlinks=False)
        except OSError as exc:
            raise core.PortfolioError(
                "verify: package directory pathname disappeared"
            ) from exc
        retained_generation = (int(after.st_dev), int(after.st_ino))
        if not _same_generation(visible_dir, retained_generation) or not stat.S_ISDIR(
            visible_dir.st_mode
        ):
            raise core.PortfolioError(
                "verify: package directory pathname no longer names retained generation"
            )
        return first
    finally:
        os.close(dir_fd)


def verify_current_directory(root: str | Path) -> dict[str, Any]:
    return host.verify_current_bytes(*read_current_directory(root))
