"""Fixed-root, no-symlink retained authority storage."""

from __future__ import annotations

import hmac
import os
import stat
from pathlib import Path
from typing import Optional

from .core import (
    ActiveKey,
    AuthorityUnavailable,
    InputError,
    KEY_POINTER_SCHEMA,
    MAX_JSON_BYTES,
    _expect_exact_fields,
    _expect_key_id,
    _expect_object,
    _expect_slug,
    strict_json_loads,
)


def _authority_root() -> Path:
    if os.name == "nt":
        raise AuthorityUnavailable(
            "organization-contact-pressure production storage is unsupported on Windows"
        )
    return Path("/var/lib/commons/organization-contact-pressure")


def _open_flags_read() -> int:
    flags = os.O_RDONLY
    flags |= getattr(os, "O_CLOEXEC", 0)
    flags |= getattr(os, "O_NOFOLLOW", 0)
    flags |= getattr(os, "O_NONBLOCK", 0)
    return flags


def _directory_flags() -> int:
    flags = os.O_RDONLY
    flags |= getattr(os, "O_DIRECTORY", 0)
    flags |= getattr(os, "O_CLOEXEC", 0)
    flags |= getattr(os, "O_NOFOLLOW", 0)
    return flags


def _open_no_symlink_path(path: Path, flags: int, mode: int = 0o600) -> tuple[int, Optional[int], str]:
    """Open a POSIX path without following any path-component symlink.

    Production deliberately fails closed on Windows because pathname prechecks
    cannot establish a handle-bound no-reparse trust boundary there.
    """
    candidate = Path(path)
    if not candidate.name or candidate.name in {".", ".."}:
        raise OSError("path has no safe final component")
    if os.name == "nt":
        raise OSError("safe retained-path traversal is unsupported on Windows")

    parts = candidate.parts
    if candidate.is_absolute():
        parent_fd = os.open(os.sep, _directory_flags())
        components = parts[1:]
    else:
        parent_fd = os.open(".", _directory_flags())
        components = parts
    if not components:
        os.close(parent_fd)
        raise OSError("path has no components")
    try:
        for component in components[:-1]:
            if component in {"", ".", ".."}:
                raise OSError("unsafe path component")
            next_fd = os.open(component, _directory_flags(), dir_fd=parent_fd)
            try:
                if not stat.S_ISDIR(os.fstat(next_fd).st_mode):
                    raise OSError("path component is not a directory")
            except Exception:
                os.close(next_fd)
                raise
            os.close(parent_fd)
            parent_fd = next_fd
        final_name = components[-1]
        if final_name in {"", ".", ".."} or os.sep in final_name:
            raise OSError("unsafe final path component")
        fd = os.open(final_name, flags, mode, dir_fd=parent_fd)
        return fd, parent_fd, final_name
    except Exception:
        os.close(parent_fd)
        raise


def _read_regular_file(path: Path, *, limit: int, private: bool) -> bytes:
    try:
        fd, parent_fd, _ = _open_no_symlink_path(path, _open_flags_read())
    except OSError as exc:
        raise AuthorityUnavailable(f"cannot open retained file: {path.name}") from exc
    if parent_fd is not None:
        os.close(parent_fd)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode):
            raise AuthorityUnavailable(f"retained file is not regular: {path.name}")
        if info.st_size < 0 or info.st_size > limit:
            raise AuthorityUnavailable(f"retained file size invalid: {path.name}")
        if private and (stat.S_IMODE(info.st_mode) & 0o077):
            raise AuthorityUnavailable(f"retained file permissions are not private: {path.name}")
        chunks: list[bytes] = []
        remaining = limit + 1
        while remaining:
            chunk = os.read(fd, min(65536, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        data = b"".join(chunks)
        if len(data) > limit:
            raise AuthorityUnavailable(f"retained file exceeds limit: {path.name}")
        if len(data) != info.st_size:
            raise AuthorityUnavailable(f"retained file changed during read: {path.name}")
        return data
    finally:
        os.close(fd)


def _read_request_file(path: Path, *, limit: int = MAX_JSON_BYTES) -> bytes:
    try:
        fd, parent_fd, _ = _open_no_symlink_path(path, _open_flags_read())
    except OSError as exc:
        raise InputError(f"cannot open request file: {path}") from exc
    if parent_fd is not None:
        os.close(parent_fd)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode):
            raise InputError("request must be a regular non-symlink file")
        if info.st_size < 0 or info.st_size > limit:
            raise InputError("request file exceeds size limit")
        data = b""
        while len(data) <= limit:
            chunk = os.read(fd, min(65536, limit + 1 - len(data)))
            if not chunk:
                break
            data += chunk
        if len(data) > limit or len(data) != info.st_size:
            raise InputError("request file changed or exceeded size limit")
        return data
    finally:
        os.close(fd)


def _same_file(left: os.stat_result, right: os.stat_result) -> bool:
    return left.st_dev == right.st_dev and left.st_ino == right.st_ino


def _read_exact_fd(fd: int, expected_size: int) -> bytes:
    chunks: list[bytes] = []
    remaining = expected_size + 1
    while remaining:
        chunk = os.read(fd, min(65536, remaining))
        if not chunk:
            break
        chunks.append(chunk)
        remaining -= len(chunk)
    data = b"".join(chunks)
    if len(data) != expected_size:
        raise OSError("published output size changed")
    return data


def _verify_visible_output(path: Path, authored: os.stat_result, expected: bytes) -> None:
    visible_fd: Optional[int] = None
    visible_parent: Optional[int] = None
    try:
        visible_fd, visible_parent, _ = _open_no_symlink_path(path, _open_flags_read())
        visible = os.fstat(visible_fd)
        if not stat.S_ISREG(visible.st_mode):
            raise OSError("published output is not regular")
        if not _same_file(authored, visible):
            raise OSError("published output pathname no longer names the authored inode")
        if visible.st_size != len(expected):
            raise OSError("published output length mismatch")
        observed = _read_exact_fd(visible_fd, len(expected))
        if not hmac.compare_digest(observed, expected):
            raise OSError("published output bytes mismatch")
    finally:
        if visible_fd is not None:
            os.close(visible_fd)
        if visible_parent is not None:
            os.close(visible_parent)


def _write_exclusive(path: Path, data: bytes) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    flags |= getattr(os, "O_CLOEXEC", 0)
    flags |= getattr(os, "O_NOFOLLOW", 0)
    try:
        fd, parent_fd, final_name = _open_no_symlink_path(path, flags, 0o600)
    except OSError as exc:
        raise InputError("output path is unsafe, missing, unsupported, or already exists") from exc

    authored = os.fstat(fd)
    succeeded = False
    failure: Optional[BaseException] = None
    try:
        if not stat.S_ISREG(authored.st_mode):
            raise OSError("created output is not regular")
        offset = 0
        while offset < len(data):
            written = os.write(fd, data[offset:])
            if written <= 0:
                raise OSError("short write")
            offset += written
        os.fsync(fd)
        after_write = os.fstat(fd)
        if not _same_file(authored, after_write) or after_write.st_size != len(data):
            raise OSError("authored output identity or size changed")
        if parent_fd is not None:
            os.fsync(parent_fd)
        _verify_visible_output(path, after_write, data)
        succeeded = True
    except BaseException as exc:
        failure = exc
    finally:
        os.close(fd)
        if not succeeded:
            try:
                if parent_fd is not None:
                    current = os.stat(final_name, dir_fd=parent_fd, follow_symlinks=False)
                    if _same_file(authored, current):
                        os.unlink(final_name, dir_fd=parent_fd)
            except OSError:
                pass
        if parent_fd is not None:
            os.close(parent_fd)
    if failure is not None:
        raise InputError("output publication failed without deleting a foreign replacement") from failure


def _load_key_by_id(root: Path, key_id: str) -> bytes:
    _expect_key_id(key_id)
    raw = _read_regular_file(root / "keys" / f"{key_id}.key", limit=128, private=True)
    stripped = raw.strip()
    if len(stripped) != 64:
        raise AuthorityUnavailable("verifier key must be exactly 32 bytes encoded as hex")
    try:
        key = bytes.fromhex(stripped.decode("ascii"))
    except (UnicodeDecodeError, ValueError) as exc:
        raise AuthorityUnavailable("verifier key encoding is invalid") from exc
    if len(key) != 32:
        raise AuthorityUnavailable("verifier key length is invalid")
    return key


def _load_active_key(root: Path) -> ActiveKey:
    raw = _read_regular_file(root / "active-key.json", limit=4096, private=True)
    try:
        pointer = _expect_object(strict_json_loads(raw), "active key pointer")
        _expect_exact_fields(pointer, {"schema", "key_id", "verifier_id"}, "active key pointer")
        if pointer["schema"] != KEY_POINTER_SCHEMA:
            raise InputError("unsupported key pointer schema")
        key_id = _expect_key_id(pointer["key_id"])
        verifier_id = _expect_slug(pointer["verifier_id"], "verifier_id")
    except InputError as exc:
        raise AuthorityUnavailable("active key pointer is malformed") from exc
    return ActiveKey(key_id=key_id, verifier_id=verifier_id, key=_load_key_by_id(root, key_id))
