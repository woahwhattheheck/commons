"""Retained-directory publisher for authenticated pursuit-portfolio artifacts.

The caller must create the destination directory first.  This module opens that
exact directory generation through the no-symlink component walk and creates
final files relative to the retained descriptor.  A late failure preserves any
already-published files; it never unlinks a visible pathname it may no longer
own.
"""
from __future__ import annotations

import os
from pathlib import Path

from .core import PortfolioError
from .current import AuthorizedPortfolio, _open_dir_chain, _write_relative


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
                _write_relative(dir_fd, filename, raw)
            except Exception as exc:
                raise PortfolioError(
                    "publication failed; retained output generation preserved; "
                    f"already-published files: {','.join(published) or 'none'}"
                ) from exc
            published.append(filename)
        os.fsync(dir_fd)
    finally:
        os.close(dir_fd)
