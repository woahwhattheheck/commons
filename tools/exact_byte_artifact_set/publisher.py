"""Exact-byte, retained-descriptor publication for small artifact sets.

This module intentionally solves only filesystem custody.  It grants no business,
provider, publication-policy, or external-send authority.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

RECEIPT_SCHEMA = "exact-byte-artifact-set-receipt/v1"
MAX_FILES = 64
MAX_LEAF_BYTES = 8 * 1024 * 1024
MAX_TOTAL_BYTES = 32 * 1024 * 1024
_SAFE_LEAF = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}\Z")


class PublicationError(RuntimeError):
    """Publication failed before a complete artifact set was proven."""


class PartialPublicationError(PublicationError):
    """Publication failed after at least one leaf was created.

    Created leaves are deliberately *not* unlinked.  Their names are reported so
    an operator can reconcile the retained evidence without a pathname-delete race.
    """

    def __init__(self, message: str, created_leaves: tuple[str, ...]):
        super().__init__(message)
        self.created_leaves = created_leaves


@dataclass(frozen=True)
class _FileGeneration:
    dev: int
    ino: int
    mode: int
    size: int
    mtime_ns: int
    ctime_ns: int

    @classmethod
    def from_stat(cls, value: os.stat_result) -> "_FileGeneration":
        return cls(
            dev=value.st_dev,
            ino=value.st_ino,
            mode=value.st_mode,
            size=value.st_size,
            mtime_ns=value.st_mtime_ns,
            ctime_ns=value.st_ctime_ns,
        )


@dataclass(frozen=True)
class _DirGeneration:
    dev: int
    ino: int
    mode: int

    @classmethod
    def from_stat(cls, value: os.stat_result) -> "_DirGeneration":
        return cls(dev=value.st_dev, ino=value.st_ino, mode=value.st_mode)


def _required_platform_flags() -> tuple[int, int]:
    missing = [name for name in ("O_DIRECTORY", "O_NOFOLLOW") if not hasattr(os, name)]
    if missing or os.open not in getattr(os, "supports_dir_fd", set()):
        detail = ", ".join(missing) if missing else "dir_fd os.open"
        raise PublicationError(f"required retained-directory primitives unavailable: {detail}")
    return os.O_DIRECTORY, os.O_NOFOLLOW


def _safe_leaf_name(name: object) -> str:
    if not isinstance(name, str) or not _SAFE_LEAF.fullmatch(name):
        raise PublicationError(f"unsafe artifact leaf name: {name!r}")
    if name in {".", ".."} or "/" in name or "\\" in name or "\x00" in name:
        raise PublicationError(f"unsafe artifact leaf name: {name!r}")
    return name


def _normalize_artifacts(artifacts: Mapping[str, bytes]) -> tuple[tuple[str, bytes], ...]:
    if not isinstance(artifacts, Mapping):
        raise PublicationError("artifacts must be a mapping of leaf name to exact bytes")
    if not artifacts:
        raise PublicationError("artifact set must be non-empty")
    if len(artifacts) > MAX_FILES:
        raise PublicationError(f"artifact set exceeds {MAX_FILES} leaves")

    normalized: list[tuple[str, bytes]] = []
    total = 0
    seen: set[str] = set()
    for raw_name, raw_bytes in artifacts.items():
        name = _safe_leaf_name(raw_name)
        if name in seen:
            raise PublicationError(f"duplicate artifact leaf name: {name}")
        seen.add(name)
        if type(raw_bytes) is not bytes:
            raise PublicationError(f"artifact {name!r} must be exact bytes")
        if len(raw_bytes) > MAX_LEAF_BYTES:
            raise PublicationError(f"artifact {name!r} exceeds {MAX_LEAF_BYTES} bytes")
        total += len(raw_bytes)
        if total > MAX_TOTAL_BYTES:
            raise PublicationError(f"artifact set exceeds {MAX_TOTAL_BYTES} bytes")
        normalized.append((name, raw_bytes))
    normalized.sort(key=lambda item: item[0])
    return tuple(normalized)


def _split_path(path: Path) -> tuple[bool, tuple[str, ...]]:
    text = os.fspath(path)
    if not isinstance(text, str) or not text:
        raise PublicationError("output directory path must be non-empty text")
    absolute = os.path.isabs(text)
    norm = os.path.normpath(text)
    if norm == os.curdir:
        return absolute, ()
    if absolute:
        parts = tuple(part for part in Path(norm).parts if part not in (os.sep, ""))
    else:
        parts = tuple(part for part in Path(norm).parts if part not in ("", os.curdir))
    if any(part == os.pardir for part in parts):
        raise PublicationError("output directory path may not contain '..'")
    return absolute, parts


def _open_retained_directory(path: Path) -> tuple[int, _DirGeneration]:
    o_directory, o_nofollow = _required_platform_flags()
    absolute, parts = _split_path(path)
    base = os.sep if absolute else os.curdir
    flags = os.O_RDONLY | o_directory | o_nofollow
    current_fd = os.open(base, flags)
    try:
        for component in parts:
            next_fd = os.open(component, flags, dir_fd=current_fd)
            os.close(current_fd)
            current_fd = next_fd
        st = os.fstat(current_fd)
        if not stat.S_ISDIR(st.st_mode):
            raise PublicationError("retained output generation is not a directory")
        return current_fd, _DirGeneration.from_stat(st)
    except BaseException:
        os.close(current_fd)
        raise


def _assert_dir_generation(fd: int, expected: _DirGeneration) -> None:
    actual = _DirGeneration.from_stat(os.fstat(fd))
    if actual != expected or not stat.S_ISDIR(actual.mode):
        raise PublicationError("retained output directory generation changed")


def _preflight_absent(dir_fd: int, names: tuple[str, ...]) -> None:
    for name in names:
        try:
            os.stat(name, dir_fd=dir_fd, follow_symlinks=False)
        except FileNotFoundError:
            continue
        raise PublicationError(f"artifact leaf already exists: {name}")


def _write_all(fd: int, payload: bytes) -> None:
    view = memoryview(payload)
    offset = 0
    while offset < len(view):
        written = os.write(fd, view[offset:])
        if written <= 0:
            raise PublicationError("short write made no progress")
        offset += written


def _read_exact_retained(fd: int, expected_len: int) -> bytes:
    os.lseek(fd, 0, os.SEEK_SET)
    remaining = expected_len + 1
    chunks: list[bytes] = []
    while remaining:
        chunk = os.read(fd, min(65536, remaining))
        if not chunk:
            break
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


def _assert_retained_bytes(fd: int, expected: bytes, final_generation: _FileGeneration) -> None:
    before = _FileGeneration.from_stat(os.fstat(fd))
    if before != final_generation:
        raise PublicationError("retained artifact metadata changed before byte verification")
    actual = _read_exact_retained(fd, len(expected))
    after = _FileGeneration.from_stat(os.fstat(fd))
    if after != before:
        raise PublicationError("retained artifact generation changed during byte verification")
    if actual != expected:
        raise PublicationError("retained artifact bytes differ from expected bytes")


def _assert_visible_identity(
    dir_fd: int, name: str, expected: _FileGeneration, expected_size: int
) -> None:
    try:
        visible = os.stat(name, dir_fd=dir_fd, follow_symlinks=False)
    except FileNotFoundError as exc:
        raise PublicationError(f"visible artifact disappeared: {name}") from exc
    if not stat.S_ISREG(visible.st_mode):
        raise PublicationError(f"visible artifact is not a regular file: {name}")
    if (visible.st_dev, visible.st_ino, visible.st_mode, visible.st_size) != (
        expected.dev,
        expected.ino,
        expected.mode,
        expected_size,
    ):
        raise PublicationError(f"visible artifact no longer names retained generation: {name}")


def _fsync_directory(dir_fd: int) -> None:
    os.fsync(dir_fd)


def _receipt(normalized: tuple[tuple[str, bytes], ...]) -> dict[str, object]:
    artifact_rows = [
        {
            "name": name,
            "length": len(payload),
            "sha256": hashlib.sha256(payload).hexdigest(),
        }
        for name, payload in normalized
    ]
    projection = {"schema": RECEIPT_SCHEMA, "artifacts": artifact_rows}
    canonical = json.dumps(
        projection, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return {
        "schema": RECEIPT_SCHEMA,
        "publication_complete": True,
        "artifacts": artifact_rows,
        "artifact_set_sha256": hashlib.sha256(canonical).hexdigest(),
    }


def publish_artifact_set(
    output_dir: str | os.PathLike[str], artifacts: Mapping[str, bytes]
) -> dict[str, object]:
    """Publish a create-exclusive artifact set into one retained directory generation.

    On any failure after the first leaf is created, no visible leaf is removed.  The
    raised :class:`PartialPublicationError` reports only names created by this call.
    """

    normalized = _normalize_artifacts(artifacts)
    names = tuple(name for name, _ in normalized)
    dir_fd = -1
    retained: dict[str, tuple[int, bytes, _FileGeneration]] = {}
    created: list[str] = []
    try:
        dir_fd, dir_generation = _open_retained_directory(Path(output_dir))
        _assert_dir_generation(dir_fd, dir_generation)
        _preflight_absent(dir_fd, names)
        _assert_dir_generation(dir_fd, dir_generation)

        o_nofollow = os.O_NOFOLLOW
        flags = os.O_CREAT | os.O_EXCL | os.O_RDWR | o_nofollow
        for name, payload in normalized:
            fd = os.open(name, flags, 0o600, dir_fd=dir_fd)
            created.append(name)
            try:
                _write_all(fd, payload)
                os.fsync(fd)
                generation = _FileGeneration.from_stat(os.fstat(fd))
                if not stat.S_ISREG(generation.mode) or generation.size != len(payload):
                    raise PublicationError(f"retained artifact has unexpected metadata: {name}")
                retained[name] = (fd, payload, generation)
            except BaseException:
                os.close(fd)
                raise

        _fsync_directory(dir_fd)
        _assert_dir_generation(dir_fd, dir_generation)

        # First exact-byte pass proves each retained descriptor contains exactly the
        # intended bytes after the package-wide write and directory durability step.
        for name in names:
            fd, payload, generation = retained[name]
            _assert_retained_bytes(fd, payload, generation)

        # Visible names must still resolve to those same retained file generations.
        for name in names:
            _fd, payload, generation = retained[name]
            _assert_visible_identity(dir_fd, name, generation, len(payload))

        _assert_dir_generation(dir_fd, dir_generation)

        # Complete the final directory durability step *before* the last leaf fence.
        # No mutating/durability filesystem operation may occur after the final
        # exact-byte + visible-generation verification and inherit a stale verdict.
        _fsync_directory(dir_fd)
        _assert_dir_generation(dir_fd, dir_generation)

        # Final exact-byte/visibility pass. From here to the success receipt, only
        # non-mutating metadata/read checks remain inside the transaction.
        for name in names:
            fd, payload, generation = retained[name]
            _assert_retained_bytes(fd, payload, generation)
            _assert_visible_identity(dir_fd, name, generation, len(payload))

        _assert_dir_generation(dir_fd, dir_generation)
        return _receipt(normalized)
    except BaseException as exc:
        if created and not isinstance(exc, PartialPublicationError):
            raise PartialPublicationError(str(exc), tuple(created)) from exc
        raise
    finally:
        for fd, _payload, _generation in retained.values():
            try:
                os.close(fd)
            except OSError:
                pass
        if dir_fd >= 0:
            try:
                os.close(dir_fd)
            except OSError:
                pass
