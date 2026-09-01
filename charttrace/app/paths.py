"""Reject UNC, device, symlink, traversal, and network-share destinations."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Union


PathLike = Union[str, Path]

WINDOWS_DEVICES = frozenset(
    {
        "CON",
        "PRN",
        "AUX",
        "NUL",
        "COM1",
        "COM2",
        "COM3",
        "COM4",
        "COM5",
        "COM6",
        "COM7",
        "COM8",
        "COM9",
        "LPT1",
        "LPT2",
        "LPT3",
        "LPT4",
        "LPT5",
        "LPT6",
        "LPT7",
        "LPT8",
        "LPT9",
    }
)

_SCHEME_RE = re.compile(r"^(https?|ftp|smb|nfs|file|unc):", re.IGNORECASE)
_DRIVE_RELATIVE_RE = re.compile(r"^[A-Za-z]:[^\\/]")


class PathEgressError(ValueError):
    """Raised when a destination is not a local regular filesystem path."""


def _normalized_windows(raw: str) -> str:
    return raw.replace("/", "\\")


def _looks_like_unc_or_share(raw: str) -> bool:
    slashed = _normalized_windows(raw)
    upper = slashed.upper()
    if slashed.startswith("\\\\"):
        return True
    if upper.startswith("UNC\\") or "\\UNC\\" in upper:
        return True
    if upper.startswith("\\\\?\\UNC\\") or upper.startswith("//?/UNC/".upper()):
        return True
    return False


def _looks_like_device(raw: str) -> bool:
    slashed = _normalized_windows(raw)
    upper = slashed.upper()
    if upper.startswith("\\\\.\\") or upper.startswith("\\\\?\\"):
        return True
    if upper.startswith("//./") or upper.startswith("//?/"):
        return True
    parts = [part for part in re.split(r"[\\/]", slashed) if part]
    for part in parts:
        stem = part.split(".")[0].upper()
        if stem in WINDOWS_DEVICES:
            return True
    return False


def assert_local_filesystem_path(path: PathLike) -> Path:
    """Canonicalize and reject every non-local or escape destination."""
    raw = os.fspath(path)
    if not raw or raw.strip() != raw:
        raise PathEgressError("Path must be a nonempty local filesystem path.")
    if "\x00" in raw:
        raise PathEgressError("Null bytes are rejected.")
    if _SCHEME_RE.match(raw):
        raise PathEgressError("URL and remote schemes are rejected.")
    if _looks_like_unc_or_share(raw):
        raise PathEgressError("UNC and network-share destinations are rejected.")
    if _looks_like_device(raw):
        raise PathEgressError("Device paths are rejected.")
    if _DRIVE_RELATIVE_RE.match(raw):
        raise PathEgressError("Drive-relative destinations are rejected.")

    candidate = Path(raw)
    if ".." in candidate.parts:
        raise PathEgressError("Path traversal is rejected.")

    for ancestor in (candidate, *candidate.parents):
        try:
            if ancestor.exists() and (
                ancestor.is_symlink() or os.path.islink(ancestor)
            ):
                raise PathEgressError("Symlink destinations are rejected.")
        except OSError as error:
            raise PathEgressError("Path is not a readable local destination.") from error

    if candidate.exists():
        if candidate.is_symlink() or os.path.islink(candidate):
            raise PathEgressError("Symlink destinations are rejected.")
        resolved = candidate.resolve()
        if os.path.islink(candidate) or (
            resolved.exists() and candidate.exists() and candidate.is_symlink()
        ):
            raise PathEgressError("Symlink destinations are rejected.")
    return candidate
