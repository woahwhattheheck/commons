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

_SCHEME_RE = re.compile(r"^(https?|ftp|smb|nfs|file):", re.IGNORECASE)


class PathEgressError(ValueError):
    """Raised when a destination is not a local regular filesystem path."""


def assert_local_filesystem_path(path: PathLike) -> Path:
    """Canonicalize and reject every non-local or escape destination."""
    raw = os.fspath(path)
    if not raw or raw.strip() != raw:
        raise PathEgressError("Path must be a nonempty local filesystem path.")
    if "\x00" in raw:
        raise PathEgressError("Null bytes are rejected.")
    if _SCHEME_RE.match(raw):
        raise PathEgressError("URL and remote schemes are rejected.")
    if raw.startswith("\\\\") or raw.startswith("//"):
        raise PathEgressError("UNC and network-share destinations are rejected.")
    if raw.startswith("\\\\?\\") or raw.startswith("\\\\.\\"):
        raise PathEgressError("Device paths are rejected.")
    # Drive-relative UNC form: \\host\share already caught; also reject mixed.
    if raw[:2] in {"\\\\", "//"} or "\\\\" in raw.replace("\\\\?\\", ""):
        if not (len(raw) >= 3 and raw[1] == ":" and raw[0].isalpha()):
            if "\\" in raw[2:] and not os.path.isabs(raw):
                raise PathEgressError("Network-share destinations are rejected.")

    candidate = Path(raw)
    name = candidate.name.split(".")[0].upper()
    if name in WINDOWS_DEVICES:
        raise PathEgressError("Windows device names are rejected.")
    if ".." in candidate.parts:
        raise PathEgressError("Path traversal is rejected.")

    for ancestor in (candidate, *candidate.parents):
        try:
            if ancestor.exists() and ancestor.is_symlink():
                raise PathEgressError("Symlink destinations are rejected.")
        except OSError as error:
            raise PathEgressError("Path is not a readable local destination.") from error

    if candidate.exists():
        if candidate.is_symlink():
            raise PathEgressError("Symlink destinations are rejected.")
        resolved = candidate.resolve()
        if resolved != candidate and candidate.is_symlink():
            raise PathEgressError("Symlink destinations are rejected.")
    return candidate
