"""Retained-directory publisher for authenticated pursuit-portfolio artifacts.

The caller must create the destination directory first. This module opens that
exact directory generation through the no-symlink component walk and creates
final files relative to the retained descriptor. Every final pathname is
confirmed to still name the inode written by this process before success. A late
failure preserves already-published files; rollback never unlinks by pathname.
"""
from __future__ import annotations

import os
from pathlib import Path
import stat

from .core import MAX_FILE_BYTES, PortfolioError
from .current import (
    MAX_AUTHORITY_BYTES,
    AuthorizedPortfolio,
    _open_dir_chain,
    _read_relative,
)
from .host import HostAuthorizedPortfolio


def _write_owned_relative(dir_fd: int, name: str, data: bytes) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW
    fd = os.open(name, flags, 0o600, dir_fd=dir_fd)
    try:
        opened = os.fstat(fd)
        if not stat.S_ISREG(opened.st_mode):
            raise PortfolioError(f"publication: {name} is not a regular file")
        view = memoryview(data)
        while view:
            written = os.write(fd, view)
            if written <= 0:
                raise PortfolioError(f"publication: short write for {name}")
            view = view[written:]
        os.fsync(fd)
        final = os.fstat(fd)
        try:
            visible = os.stat(name, dir_fd=dir_fd, follow_symlinks=False)
        except OSError as exc:
            raise PortfolioError(f"publication: visible output disappeared: {name}") from exc
        if (int(final.st_dev), int(final.st_ino)) != (
            int(visible.st_dev),
            int(visible.st_ino),
        ):
            raise PortfolioError(f"publication: visible output ownership changed: {name}")
        if not stat.S_ISREG(visible.st_mode):
            raise PortfolioError(f"publication: visible output is not regular: {name}")
    finally:
        os.close(fd)


def _publish_files(out_dir: str | Path, files: tuple[tuple[str, bytes], ...]) -> None:
    dir_fd = _open_dir_chain(out_dir)
    published: list[str] = []
    try:
        for filename, raw in files:
            try:
                _write_owned_relative(dir_fd, filename, raw)
            except Exception as exc:
                raise PortfolioError(
                    "publication failed; retained output generation preserved; "
                    f"already-published files: {','.join(published) or 'none'}"
                ) from exc
            published.append(filename)
        os.fsync(dir_fd)
    finally:
        os.close(dir_fd)


def publish_authorized(value: AuthorizedPortfolio, out_dir: str | Path) -> None:
    """Internal explicit-key publisher used by focused current-layer tests."""
    _publish_files(
        out_dir,
        (
            ("portfolio.json", value.compiled.result_bytes),
            ("portfolio.md", value.compiled.markdown_bytes),
            ("receipt.json", value.compiled.receipt_bytes),
            ("upstream-authority.json", value.authority_bytes),
            ("current-receipt.json", value.current_receipt_bytes),
        ),
    )


def publish_current(value: HostAuthorizedPortfolio, out_dir: str | Path) -> None:
    """Production publisher: includes the fixed-host HMAC seal."""
    authorized = value.authorized
    _publish_files(
        out_dir,
        (
            ("portfolio.json", authorized.compiled.result_bytes),
            ("portfolio.md", authorized.compiled.markdown_bytes),
            ("receipt.json", authorized.compiled.receipt_bytes),
            ("upstream-authority.json", authorized.authority_bytes),
            ("current-receipt.json", authorized.current_receipt_bytes),
            ("host-seal.json", value.host_seal_bytes),
        ),
    )


def read_current(out_dir: str | Path) -> tuple[bytes, bytes, bytes, bytes, bytes, bytes]:
    """Read one retained production package generation."""
    dir_fd = _open_dir_chain(out_dir)
    try:
        return (
            _read_relative(dir_fd, "portfolio.json", MAX_FILE_BYTES, "portfolio.json"),
            _read_relative(dir_fd, "portfolio.md", MAX_FILE_BYTES, "portfolio.md"),
            _read_relative(dir_fd, "receipt.json", MAX_FILE_BYTES, "receipt.json"),
            _read_relative(dir_fd, "upstream-authority.json", MAX_AUTHORITY_BYTES, "upstream-authority.json"),
            _read_relative(dir_fd, "current-receipt.json", MAX_AUTHORITY_BYTES, "current-receipt.json"),
            _read_relative(dir_fd, "host-seal.json", MAX_AUTHORITY_BYTES, "host-seal.json"),
        )
    finally:
        os.close(dir_fd)
