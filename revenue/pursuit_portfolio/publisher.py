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

from .core import PortfolioError
from .current import AuthorizedPortfolio, _open_dir_chain


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


def publish_authorized(value: AuthorizedPortfolio, out_dir: str | Path) -> None:
    dir_fd = _open_dir_chain(out_dir)
    published: list[str] = []
    try:
        files = (
            ("portfolio.json", value.compiled.result_bytes),
            ("portfolio.md", value.compiled.markdown_bytes),
            ("receipt.json", value.compiled.receipt_bytes),
            ("upstream-authority.json", value.authority_bytes),
            ("current-receipt.json", value.current_receipt_bytes),
        )
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
