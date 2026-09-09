#!/usr/bin/env python3
"""Bounded public entrypoint for the Kaggriculture replay differential.

The analysis implementation lives in ``replay_program_diff_core``. This facade
owns all file ingestion so raw and gzip evidence is admitted under hard byte
limits before the core sees parsed JSON.
"""
from __future__ import annotations

import gzip
import hashlib
import io
import os
import stat
from pathlib import Path
from typing import Any, Sequence

import replay_program_diff_core as _core
from replay_program_diff_core import *  # noqa: F401,F403 - public analysis API

MAX_COMPRESSED_BYTES = 512 * 1024 * 1024
MAX_DECOMPRESSED_BYTES = 2 * 1024 * 1024 * 1024


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _bounded_source_read(path: Path) -> bytes:
    """Read one regular file without ever consuming more than the input cap.

    ``Path.read_bytes()`` would allocate an arbitrarily large local input before
    the size check.  Opening first, checking the descriptor, and reading at
    most ``MAX_COMPRESSED_BYTES + 1`` makes the compressed/source ceiling an
    admission boundary rather than only a post-allocation assertion.
    """
    try:
        with path.open("rb") as stream:
            descriptor = os.fstat(stream.fileno())
            if not stat.S_ISREG(descriptor.st_mode):
                raise ReplayError("input must resolve to a regular file")
            if descriptor.st_size > MAX_COMPRESSED_BYTES:
                raise ReplayError(
                    "input exceeds compressed-size limit: "
                    f"{descriptor.st_size} > {MAX_COMPRESSED_BYTES}"
                )
            raw = stream.read(MAX_COMPRESSED_BYTES + 1)
    except ReplayError:
        raise
    except OSError as exc:
        raise ReplayError(f"could not read replay input: {exc}") from exc
    if len(raw) > MAX_COMPRESSED_BYTES:
        raise ReplayError(
            "input exceeds compressed-size limit: "
            f"> {MAX_COMPRESSED_BYTES}"
        )
    return raw


def _bounded_gzip_decompress(raw: bytes) -> bytes:
    chunks: list[bytes] = []
    total = 0
    try:
        with gzip.GzipFile(fileobj=io.BytesIO(raw), mode="rb") as stream:
            while True:
                remaining = MAX_DECOMPRESSED_BYTES + 1 - total
                chunk = stream.read(min(1024 * 1024, remaining))
                if not chunk:
                    break
                chunks.append(chunk)
                total += len(chunk)
                if total > MAX_DECOMPRESSED_BYTES:
                    raise ReplayError(
                        "input exceeds decompressed-size limit: "
                        f"> {MAX_DECOMPRESSED_BYTES}"
                    )
    except ReplayError:
        raise
    except (EOFError, OSError) as exc:
        raise ReplayError(f"invalid gzip stream: {exc}") from exc
    return b"".join(chunks)


def _read_input(path: Path) -> tuple[Any, dict[str, Any]]:
    raw = _bounded_source_read(path)
    is_gzip = raw.startswith(b"\x1f\x8b")
    decoded = _bounded_gzip_decompress(raw) if is_gzip else raw
    if len(decoded) > MAX_DECOMPRESSED_BYTES:
        raise ReplayError(
            f"input exceeds decompressed-size limit: {len(decoded)} > {MAX_DECOMPRESSED_BYTES}"
        )
    try:
        text = decoded.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ReplayError(f"input is not strict UTF-8: {exc}") from exc
    payload = strict_json_loads(text, str(path))
    return payload, {
        "path": str(path),
        "compressed": is_gzip,
        "input_bytes": len(raw),
        "decoded_bytes": len(decoded),
        "input_sha256": _sha256(raw),
        "decoded_sha256": _sha256(decoded),
    }


def main(argv: Sequence[str] | None = None) -> int:
    # The core's CLI resolves this symbol in its own module. Bind it only to
    # this bounded implementation; parser, analysis, and rendering stay exact.
    _core._read_input = _read_input
    return _core.main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
