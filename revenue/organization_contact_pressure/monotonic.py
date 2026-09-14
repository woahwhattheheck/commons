"""Root-owned monotonic ledger-floor custody.

The mutable ledger and audit journal live under /var/lib. Current-ledger
acceptance is anchored by one root-owned floor file under /etc so an actor able
to restore mutable ledger bytes cannot lower currentness by deleting journal
entries. Test code may inject an explicit non-production floor root only through
``_test_api``.
"""

from __future__ import annotations

import os
import stat
from pathlib import Path

from .core import AuthorityUnavailable, MAX_JSON_BYTES
from .storage import _read_regular_file

_PRODUCTION_FLOOR_ROOT = Path("/etc/commons/organization-contact-pressure/ledger-floors")


def _ledger_floor_root() -> Path:
    if os.name == "nt":
        raise AuthorityUnavailable(
            "Windows monotonic-ledger custody is unsupported until handle-bound "
            "reparse-point and ACL verification is implemented"
        )
    return _PRODUCTION_FLOOR_ROOT


def _directory_flags() -> int:
    return (
        os.O_RDONLY
        | getattr(os, "O_DIRECTORY", 0)
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_NOFOLLOW", 0)
    )


def _read_flags() -> int:
    return (
        os.O_RDONLY
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_NONBLOCK", 0)
    )


def _validate_trusted_directory(info: os.stat_result, *, expected_uid: int, name: str) -> None:
    if not stat.S_ISDIR(info.st_mode):
        raise AuthorityUnavailable(f"monotonic path component is not a directory: {name}")
    if info.st_uid != expected_uid:
        raise AuthorityUnavailable(f"monotonic path component owner mismatch: {name}")
    if stat.S_IMODE(info.st_mode) & 0o022:
        raise AuthorityUnavailable(f"monotonic path component is group/other writable: {name}")


def _open_trusted_floor_file(path: Path, *, expected_uid: int) -> int:
    candidate = Path(path)
    if os.name == "nt" or not candidate.is_absolute():
        raise AuthorityUnavailable("production monotonic floor path must be absolute POSIX")
    parts = candidate.parts[1:]
    if not parts:
        raise AuthorityUnavailable("monotonic floor path has no file component")

    parent_fd = os.open(os.sep, _directory_flags())
    try:
        _validate_trusted_directory(os.fstat(parent_fd), expected_uid=expected_uid, name=os.sep)
        for component in parts[:-1]:
            if component in {"", ".", ".."}:
                raise AuthorityUnavailable("unsafe monotonic path component")
            next_fd = os.open(component, _directory_flags(), dir_fd=parent_fd)
            try:
                _validate_trusted_directory(
                    os.fstat(next_fd), expected_uid=expected_uid, name=component
                )
            except Exception:
                os.close(next_fd)
                raise
            os.close(parent_fd)
            parent_fd = next_fd
        final_name = parts[-1]
        if final_name in {"", ".", ".."} or os.sep in final_name:
            raise AuthorityUnavailable("unsafe monotonic floor filename")
        try:
            fd = os.open(final_name, _read_flags(), dir_fd=parent_fd)
        except OSError as exc:
            raise AuthorityUnavailable("cannot open monotonic ledger floor") from exc
        return fd
    finally:
        os.close(parent_fd)


def _read_trusted_floor(path: Path, *, expected_uid: int, limit: int = 16_384) -> bytes:
    fd = _open_trusted_floor_file(path, expected_uid=expected_uid)
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode):
            raise AuthorityUnavailable("monotonic ledger floor is not regular")
        if before.st_uid != expected_uid:
            raise AuthorityUnavailable("monotonic ledger floor owner mismatch")
        if before.st_nlink != 1:
            raise AuthorityUnavailable("monotonic ledger floor must have one link")
        if stat.S_IMODE(before.st_mode) & 0o077:
            raise AuthorityUnavailable("monotonic ledger floor permissions are not private")
        if before.st_size < 0 or before.st_size > limit:
            raise AuthorityUnavailable("monotonic ledger floor size invalid")
        chunks: list[bytes] = []
        remaining = limit + 1
        while remaining:
            chunk = os.read(fd, min(65_536, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        data = b"".join(chunks)
        if len(data) != before.st_size or len(data) > limit:
            raise AuthorityUnavailable("monotonic ledger floor changed during read")
        after = os.fstat(fd)
        if (
            after.st_dev != before.st_dev
            or after.st_ino != before.st_ino
            or after.st_mode != before.st_mode
            or after.st_nlink != before.st_nlink
            or after.st_size != before.st_size
            or after.st_mtime_ns != before.st_mtime_ns
            or after.st_ctime_ns != before.st_ctime_ns
        ):
            raise AuthorityUnavailable("monotonic ledger floor changed during read")
        return data
    finally:
        os.close(fd)


def _read_floor(
    floor_root: Path,
    organization_scope_sha256: str,
    *,
    expected_uid: int,
    enforce_production_custody: bool,
) -> bytes:
    path = floor_root / f"{organization_scope_sha256}.json"
    if enforce_production_custody:
        return _read_trusted_floor(path, expected_uid=expected_uid)
    return _read_regular_file(path, limit=min(MAX_JSON_BYTES, 16_384), private=True)
