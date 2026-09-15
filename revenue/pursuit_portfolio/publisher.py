"""Retained-directory publisher for authenticated pursuit-portfolio artifacts.

The caller must create the destination directory first. This module opens that
exact directory generation through the no-symlink component walk and creates
final files relative to the retained descriptor. Every output descriptor stays
open through one collective final boundary: exact bytes, stable file metadata,
and visible pathname identity are all revalidated before success. Late failure
preserves evidence; rollback never unlinks by pathname.
"""
from __future__ import annotations

import os
from pathlib import Path
import stat

from .authority_protocol import PRODUCTION_HOST_SEAL_SCHEMA
from .core import MAX_FILE_BYTES, PortfolioError, load_json_bytes
from .current import (
    MAX_AUTHORITY_BYTES,
    AuthorizedPortfolio,
    _canonical,
    _open_dir_chain,
    _read_relative,
)
from .host import HostAuthorizedPortfolio

_FileIdentity = tuple[int, int]
_FileGuard = tuple[int, int, int, int, int]


def _identity(info: os.stat_result) -> _FileIdentity:
    return (int(info.st_dev), int(info.st_ino))


def _guard(info: os.stat_result) -> _FileGuard:
    return (
        int(info.st_dev),
        int(info.st_ino),
        int(info.st_size),
        int(getattr(info, "st_mtime_ns", int(info.st_mtime * 1_000_000_000))),
        int(getattr(info, "st_ctime_ns", int(info.st_ctime * 1_000_000_000))),
    )


def _require_visible_identity(
    dir_fd: int, name: str, expected: _FileIdentity
) -> None:
    try:
        visible = os.stat(name, dir_fd=dir_fd, follow_symlinks=False)
    except OSError as exc:
        raise PortfolioError(f"publication: visible output disappeared: {name}") from exc
    if _identity(visible) != expected:
        raise PortfolioError(f"publication: visible output ownership changed: {name}")
    if not stat.S_ISREG(visible.st_mode):
        raise PortfolioError(f"publication: visible output is not regular: {name}")


def _readback_exact(fd: int, expected: bytes, expected_guard: _FileGuard, name: str) -> None:
    before = os.fstat(fd)
    if _guard(before) != expected_guard:
        raise PortfolioError(f"publication: output generation changed: {name}")
    os.lseek(fd, 0, os.SEEK_SET)
    chunks: list[bytes] = []
    remaining = len(expected) + 1
    while remaining > 0:
        chunk = os.read(fd, min(65536, remaining))
        if not chunk:
            break
        chunks.append(chunk)
        remaining -= len(chunk)
    observed = b"".join(chunks)
    after = os.fstat(fd)
    if _guard(after) != expected_guard:
        raise PortfolioError(f"publication: output generation changed while reading: {name}")
    if observed != expected:
        raise PortfolioError(f"publication: exact output bytes changed: {name}")


def _write_owned_relative(
    dir_fd: int, name: str, data: bytes
) -> tuple[int, _FileIdentity, _FileGuard]:
    flags = os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW
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
        identity = _identity(final)
        guard = _guard(final)
        _require_visible_identity(dir_fd, name, identity)
        _readback_exact(fd, data, guard, name)
        return fd, identity, guard
    except Exception:
        os.close(fd)
        raise


def _published_names(
    published: list[tuple[str, bytes, int, _FileIdentity, _FileGuard]]
) -> str:
    return ",".join(name for name, *_ in published) or "none"


def _publish_files(out_dir: str | Path, files: tuple[tuple[str, bytes], ...]) -> None:
    dir_fd = _open_dir_chain(out_dir)
    published: list[tuple[str, bytes, int, _FileIdentity, _FileGuard]] = []
    try:
        try:
            for filename, raw in files:
                fd, identity, guard = _write_owned_relative(dir_fd, filename, raw)
                published.append((filename, raw, fd, identity, guard))
            os.fsync(dir_fd)

            # One package-level success fence. This catches replacement of an
            # earlier pathname while later artifacts are written, and also
            # same-inode mutation because each retained descriptor is read back
            # against its exact bytes and post-write metadata generation.
            for filename, raw, fd, identity, guard in published:
                _require_visible_identity(dir_fd, filename, identity)
                _readback_exact(fd, raw, guard, filename)
        except Exception as exc:
            message = (
                "publication failed; retained output generation preserved; "
                f"already-published files: {_published_names(published)}"
            )
            if isinstance(exc, PortfolioError):
                message = f"{message}; {exc}"
            raise PortfolioError(message) from exc
    finally:
        for _, _, fd, _, _ in published:
            try:
                os.close(fd)
            except OSError:
                pass
        os.close(dir_fd)


def publish_authorized(value: AuthorizedPortfolio, out_dir: str | Path) -> None:
    """Internal explicit-key publisher used by focused historical tests."""
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
    """Production publisher: accepts only isolated-worker v3 host seals."""
    seal = load_json_bytes(value.host_seal_bytes, "host seal")
    if seal != value.host_seal or value.host_seal_bytes != _canonical(seal):
        raise PortfolioError("publication: host seal object/bytes mismatch")
    if seal.get("schema") != PRODUCTION_HOST_SEAL_SCHEMA:
        raise PortfolioError("publication: isolated-worker v3 host seal required")
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
            _read_relative(
                dir_fd,
                "upstream-authority.json",
                MAX_AUTHORITY_BYTES,
                "upstream-authority.json",
            ),
            _read_relative(
                dir_fd,
                "current-receipt.json",
                MAX_AUTHORITY_BYTES,
                "current-receipt.json",
            ),
            _read_relative(
                dir_fd,
                "host-seal.json",
                MAX_AUTHORITY_BYTES,
                "host-seal.json",
            ),
        )
    finally:
        os.close(dir_fd)
