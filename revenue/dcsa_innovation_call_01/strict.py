"""Strict JSON, timestamp, and file-custody helpers for the DCSA pursuit carrier."""

from __future__ import annotations

import datetime as dt
import json
import math
import os
import stat
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, MutableMapping, Sequence, Tuple

MAX_INPUT_BYTES = 4 * 1024 * 1024
MAX_OUTPUT_BYTES = 8 * 1024 * 1024
UTC = dt.timezone.utc


class DcsaError(Exception):
    """Base class for deterministic, user-facing carrier failures."""


class ValidationError(DcsaError):
    """Input did not satisfy the strict carrier contract."""


class CustodyError(DcsaError):
    """A path or file generation could not be safely captured or published."""


def _pairs_to_dict(pairs: Sequence[Tuple[str, Any]]) -> Dict[str, Any]:
    result: Dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValidationError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_constant(token: str) -> None:
    raise ValidationError(f"non-finite JSON number is forbidden: {token}")


def strict_json_loads(data: bytes | str) -> Any:
    """Parse JSON while rejecting duplicate keys and non-finite numbers."""

    if isinstance(data, bytes):
        try:
            text = data.decode("utf-8", errors="strict")
        except UnicodeDecodeError as exc:
            raise ValidationError("JSON input is not strict UTF-8") from exc
    elif isinstance(data, str):
        text = data
    else:
        raise ValidationError("JSON input must be bytes or text")
    try:
        return json.loads(
            text,
            object_pairs_hook=_pairs_to_dict,
            parse_constant=_reject_constant,
        )
    except ValidationError:
        raise
    except (json.JSONDecodeError, TypeError, ValueError) as exc:
        raise ValidationError("JSON input is malformed") from exc


def canonical_json_bytes(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ValidationError("value is not canonical-JSON serializable") from exc


def require_exact_keys(value: Any, expected: Iterable[str], *, field: str) -> Mapping[str, Any]:
    if type(value) is not dict:
        raise ValidationError(f"{field} must be a plain JSON object")
    expected_set = set(expected)
    actual_set = set(value)
    missing = sorted(expected_set - actual_set)
    extra = sorted(actual_set - expected_set)
    if missing or extra:
        raise ValidationError(
            f"{field} has an invalid schema; missing={missing}, extra={extra}"
        )
    return value


def require_plain_list(value: Any, *, field: str) -> list[Any]:
    if type(value) is not list:
        raise ValidationError(f"{field} must be a JSON array")
    return value


def require_string(value: Any, *, field: str, minimum: int = 1, maximum: int = 512) -> str:
    if type(value) is not str:
        raise ValidationError(f"{field} must be a string")
    if not minimum <= len(value) <= maximum:
        raise ValidationError(f"{field} length must be between {minimum} and {maximum}")
    if any(ord(ch) < 32 or ord(ch) == 127 for ch in value):
        raise ValidationError(f"{field} contains a control character")
    return value


def require_bool(value: Any, *, field: str) -> bool:
    if type(value) is not bool:
        raise ValidationError(f"{field} must be a JSON boolean")
    return value


def require_int(value: Any, *, field: str, minimum: int = 0, maximum: int = 2**31 - 1) -> int:
    if type(value) is not int:
        raise ValidationError(f"{field} must be an integer")
    if not minimum <= value <= maximum:
        raise ValidationError(f"{field} must be between {minimum} and {maximum}")
    return value


def require_hex64(value: Any, *, field: str) -> str:
    text = require_string(value, field=field, minimum=64, maximum=64)
    if any(ch not in "0123456789abcdef" for ch in text):
        raise ValidationError(f"{field} must be 64 lowercase hexadecimal characters")
    return text


def require_nullable_hex64(value: Any, *, field: str) -> str | None:
    if value is None:
        return None
    return require_hex64(value, field=field)


def parse_utc(value: Any, *, field: str) -> dt.datetime:
    text = require_string(value, field=field, minimum=20, maximum=20)
    if not text.endswith("Z"):
        raise ValidationError(f"{field} must use canonical UTC seconds")
    try:
        parsed = dt.datetime.fromisoformat(text[:-1] + "+00:00")
    except ValueError as exc:
        raise ValidationError(f"{field} is not a valid timestamp") from exc
    if parsed.microsecond != 0 or parsed.tzinfo is None:
        raise ValidationError(f"{field} must use canonical UTC seconds")
    canonical = parsed.astimezone(UTC).isoformat().replace("+00:00", "Z")
    if canonical != text:
        raise ValidationError(f"{field} must be canonical UTC")
    return parsed.astimezone(UTC)


def format_utc(value: dt.datetime) -> str:
    if not isinstance(value, dt.datetime) or value.tzinfo is None:
        raise ValidationError("timestamp must be timezone-aware")
    return value.astimezone(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _path_parts(path: Path) -> tuple[Path, list[str]]:
    if path.is_absolute():
        root = Path(path.anchor)
        parts = list(path.parts[1:])
    else:
        root = Path(".")
        parts = list(path.parts)
    if not parts or any(part in {"", ".", ".."} for part in parts):
        raise CustodyError("path must not contain empty, dot, or dot-dot components")
    return root, parts


def _open_parent_dir(path: Path) -> tuple[int, str]:
    root, parts = _path_parts(path)
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0)
    if hasattr(os, "O_DIRECTORY"):
        flags |= os.O_DIRECTORY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        fd = os.open(str(root), flags)
    except OSError as exc:
        raise CustodyError("could not open path root") from exc
    try:
        for component in parts[:-1]:
            try:
                next_fd = os.open(component, flags, dir_fd=fd)
            except OSError as exc:
                raise CustodyError("path ancestor is missing, non-directory, or symlinked") from exc
            os.close(fd)
            fd = next_fd
        return fd, parts[-1]
    except Exception:
        os.close(fd)
        raise


def _metadata_tuple(st: os.stat_result) -> tuple[int, int, int, int, int, int, int]:
    return (
        int(st.st_dev),
        int(st.st_ino),
        int(st.st_mode),
        int(st.st_nlink),
        int(st.st_size),
        int(st.st_mtime_ns),
        int(st.st_ctime_ns),
    )


def read_bounded_regular_file(path: str | os.PathLike[str], *, limit: int = MAX_INPUT_BYTES) -> bytes:
    """Read one stable, non-symlink regular-file generation.

    Every ancestor and the final component are opened without following symlinks. The
    accepted generation binds device, inode, mode, link count, size, mtime, and ctime
    before and after the read, then proves the visible final name still identifies the
    retained descriptor generation.
    """

    if type(limit) is not int or isinstance(limit, bool) or limit < 1:
        raise ValidationError("file limit must be a positive integer")
    parent_fd, name = _open_parent_dir(Path(path))
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NONBLOCK", 0)
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        try:
            fd = os.open(name, flags, dir_fd=parent_fd)
        except OSError as exc:
            raise CustodyError("input is missing, inaccessible, or symlinked") from exc
        try:
            before = os.fstat(fd)
            if not stat.S_ISREG(before.st_mode):
                raise CustodyError("input must be a regular file")
            if before.st_nlink < 1:
                raise CustodyError("input file has no stable link")
            if before.st_size > limit:
                raise CustodyError("input exceeds the byte limit")
            chunks: list[bytes] = []
            remaining = limit + 1
            while remaining > 0:
                chunk = os.read(fd, min(64 * 1024, remaining))
                if not chunk:
                    break
                chunks.append(chunk)
                remaining -= len(chunk)
            data = b"".join(chunks)
            if len(data) > limit:
                raise CustodyError("input exceeds the byte limit")
            after = os.fstat(fd)
            if _metadata_tuple(before) != _metadata_tuple(after):
                raise CustodyError("input file generation changed during capture")
            try:
                visible = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
            except OSError as exc:
                raise CustodyError("input pathname changed after capture") from exc
            if stat.S_ISLNK(visible.st_mode):
                raise CustodyError("input pathname became a symlink")
            if (visible.st_dev, visible.st_ino) != (after.st_dev, after.st_ino):
                raise CustodyError("input pathname no longer names the captured generation")
            if len(data) != after.st_size:
                raise CustodyError("captured byte count does not match the stable file size")
            return data
        finally:
            os.close(fd)
    finally:
        os.close(parent_fd)


def write_exclusive_regular_file(
    path: str | os.PathLike[str],
    data: bytes,
    *,
    limit: int = MAX_OUTPUT_BYTES,
) -> None:
    """Create one new file without following symlinks or overwriting prior output."""

    if not isinstance(data, bytes):
        raise ValidationError("output data must be bytes")
    if len(data) > limit:
        raise CustodyError("output exceeds the byte limit")
    parent_fd, name = _open_parent_dir(Path(path))
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_CLOEXEC", 0)
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        try:
            fd = os.open(name, flags, 0o600, dir_fd=parent_fd)
        except OSError as exc:
            raise CustodyError("output already exists, is symlinked, or is inaccessible") from exc
        try:
            view = memoryview(data)
            written = 0
            while written < len(view):
                count = os.write(fd, view[written:])
                if count <= 0:
                    raise CustodyError("short output write made no progress")
                written += count
            os.fsync(fd)
            st = os.fstat(fd)
            if not stat.S_ISREG(st.st_mode) or st.st_size != len(data):
                raise CustodyError("output descriptor does not match the requested file")
            visible = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
            if stat.S_ISLNK(visible.st_mode) or (visible.st_dev, visible.st_ino) != (st.st_dev, st.st_ino):
                raise CustodyError("visible output pathname does not name the written generation")
            os.fsync(parent_fd)
        finally:
            os.close(fd)
    finally:
        os.close(parent_fd)
