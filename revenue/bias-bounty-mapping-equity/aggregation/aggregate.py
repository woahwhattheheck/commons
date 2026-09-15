#!/usr/bin/env python3
"""Sealed-generation authority wrapper for Mapping Equity aggregation.

The exact runner merged by #14579 is preserved byte-for-byte in
`_aggregate_unsealed.py`. This successor changes one authority primitive only:
remote source bytes are retained in a kernel-sealed memfd so the public
`/proc/self/fd/<n>` read path cannot be reopened and mutated between preflight
and scored aggregation.

Primary implementation/source credit remains ZSA-D6P2. ZFS-R7 supplied
alternate-carrier review evidence; ZHD-K8P3 recovered/finalized M1 and the
first generation/policy fix; ZRH-H7N4 owns the sealed-generation fix-forward.
"""
from __future__ import annotations

import fcntl
import hashlib
import os
from pathlib import Path
from typing import BinaryIO

import _aggregate_unsealed as _legacy

# Re-export the exact landed surface, including underscore helpers used by the
# contract/recovery suites. Dunder import identity stays owned by this wrapper.
for _name, _value in vars(_legacy).items():
    if not _name.startswith("__"):
        globals()[_name] = _value


def _required_memfd_seals() -> int:
    names = ("F_SEAL_WRITE", "F_SEAL_GROW", "F_SEAL_SHRINK", "F_SEAL_SEAL")
    missing = [name for name in names if not hasattr(fcntl, name)]
    if missing or not hasattr(fcntl, "F_ADD_SEALS") or not hasattr(fcntl, "F_GET_SEALS"):
        raise AggregationError(
            "run requires Linux memfd sealing support; missing fcntl seal constants"
        )
    return (
        fcntl.F_SEAL_WRITE
        | fcntl.F_SEAL_GROW
        | fcntl.F_SEAL_SHRINK
        | fcntl.F_SEAL_SEAL
    )


def _stream_response_to_retained_fd(
    key: str,
    uri: str,
    response: BinaryIO,
    temp_root: Path,
) -> tuple[int, str, dict[str, object]]:
    """Stream one response into a sealed memfd and retain it read-only.

    A plain anonymous tempfile is still mutable through `/proc/self/fd/<n>`:
    reopening that proc magic path with `O_WRONLY` creates a new writable file
    description whenever inode permissions allow it. Linux memfd seals make the
    generation invariant kernel-enforced instead of depending on pathname
    absence or on dropping the original write handle.
    """
    del temp_root  # retained for the predecessor-compatible call signature
    if not hasattr(os, "memfd_create") or not hasattr(os, "MFD_ALLOW_SEALING"):
        raise AggregationError("run requires Linux os.memfd_create with MFD_ALLOW_SEALING")

    required_seals = _required_memfd_seals()
    flags = getattr(os, "MFD_CLOEXEC", 0) | os.MFD_ALLOW_SEALING
    try:
        writer_fd = os.memfd_create(f"mapping-equity-{key}", flags=flags)
    except OSError as exc:
        raise AggregationError(f"{key}: sealed source memfd creation failed") from exc

    retained_fd: int | None = None
    hasher = hashlib.sha256()
    byte_count = 0
    try:
        while True:
            chunk = response.read(8 * 1024 * 1024)
            if not chunk:
                break
            if not isinstance(chunk, (bytes, bytearray)):
                raise AggregationError(f"{key}: source response yielded non-bytes")
            view = memoryview(chunk)
            while view:
                written = os.write(writer_fd, view)
                if written <= 0:
                    raise AggregationError(f"{key}: zero-byte write while materializing source")
                view = view[written:]
            hasher.update(chunk)
            byte_count += len(chunk)

        os.fsync(writer_fd)
        if byte_count <= 0:
            raise AggregationError(f"{key}: empty source object")

        try:
            fcntl.fcntl(writer_fd, fcntl.F_ADD_SEALS, required_seals)
            observed_seals = fcntl.fcntl(writer_fd, fcntl.F_GET_SEALS)
        except OSError as exc:
            raise AggregationError(f"{key}: kernel refused immutable source seals") from exc
        if observed_seals & required_seals != required_seals:
            raise AggregationError(f"{key}: retained source generation is not fully sealed")

        retained_fd = os.open(
            f"/proc/self/fd/{writer_fd}",
            os.O_RDONLY | getattr(os, "O_CLOEXEC", 0),
        )
        stat = os.fstat(retained_fd)
        if stat.st_size != byte_count:
            raise AggregationError(f"{key}: retained source size changed during materialization")

        digest = hasher.hexdigest()
        result_fd = retained_fd
        retained_fd = None
        return result_fd, f"/proc/self/fd/{result_fd}", {
            "uri": uri,
            "sha256": digest,
            "bytes": byte_count,
            "generation": f"sha256:{digest}",
        }
    finally:
        if retained_fd is not None:
            try:
                os.close(retained_fd)
            except OSError:
                pass
        try:
            os.close(writer_fd)
        except OSError:
            pass


# The landed `_materialize_one` resolves this helper through its module globals
# at call time. Patching that one global therefore preserves its URL/open/redirect
# policy and every higher-level default-bound function while replacing only the
# generation-retention primitive.
_legacy._stream_response_to_retained_fd = _stream_response_to_retained_fd


if __name__ == "__main__":
    raise SystemExit(_legacy.main())
