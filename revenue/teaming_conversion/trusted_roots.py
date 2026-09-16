from __future__ import annotations

import os
import stat
from pathlib import Path

from .common import ControlError, MAX_JSON_BYTES

_ROOTS_PATH = Path(__file__).with_name("trusted_roots.json")


def load_current_roots_bytes() -> bytes:
    """Read the repository-owned current evidence-root registry.

    There is intentionally no caller-supplied path or environment override on the
    current road. Historical/replay APIs accept explicit roots but label their
    output historical-only.
    """

    flags = os.O_RDONLY
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        fd = os.open(_ROOTS_PATH, flags)
    except OSError as exc:
        raise ControlError("current trusted-root registry cannot be opened") from exc
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode):
            raise ControlError("current trusted-root registry must be a regular file")
        if info.st_size > MAX_JSON_BYTES:
            raise ControlError("current trusted-root registry is too large")
        chunks: list[bytes] = []
        remaining = MAX_JSON_BYTES + 1
        while remaining:
            chunk = os.read(fd, min(65_536, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        data = b"".join(chunks)
        if len(data) > MAX_JSON_BYTES:
            raise ControlError("current trusted-root registry is too large")
        return data
    finally:
        os.close(fd)
