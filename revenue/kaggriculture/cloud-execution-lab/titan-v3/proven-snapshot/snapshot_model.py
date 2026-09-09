# SPDX-License-Identifier: Apache-2.0
"""Immutable identity and bounded archive primitives for proven Titan v3."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import tarfile
from typing import Mapping

SCHEMA = "titan-v3-proven-snapshot/v1"
OUTPUT_ENTRYPOINT = "main.py::agent"
SOURCE_ENTRYPOINT = "candidate.py::agent"
MAX_MEMBER_BYTES = 4 * 1024 * 1024
MAX_TOTAL_BYTES = 16 * 1024 * 1024
MAX_MEMBER_COUNT = 64

SOURCE_MEMBERS = (
    "scheduler.py",
    "mechanics.py",
    "candidate.py",
    "SOURCE-FREEZE.json",
    "CALLABLE.md",
    "NOTICE",
    "LICENSE",
    "reference/next-panel/vendor/arlene.py",
    "reference/next-panel/LICENSE",
    "reference/next-panel/NEXT-DISTRIBUTION-NOTICE.txt",
    "reference/next-panel/UPSTREAM.json",
    "reference/decision/decision.py",
    "reference/decision/README.md",
    "reference/decision/LICENSE-MIT.txt",
    "reference/engine/LICENSE",
)

FREEZE_PATHS = {
    "scheduler.py": "scheduler.py",
    "mechanics.py": "mechanics.py",
    "candidate.py": "candidate.py",
    "reference/next-panel/vendor/arlene.py": "reference/next-panel/vendor/arlene.py",
    "reference/decision/decision.py": "reference/decision/decision.py",
}

MAIN_BYTES = (
    b"# SPDX-License-Identifier: Apache-2.0\n"
    b'"""Entrypoint alias for the byte-frozen finite-horizon v3 policy."""\n'
    b"from candidate import agent\n"
)


class SnapshotError(ValueError):
    """The source evidence or candidate package failed closed."""


@dataclass(frozen=True)
class EvidenceLedgerPin:
    """Immutable identity plus required cell domain for one retained result ledger."""

    name: str
    path: str
    sha256: str
    bytes: int
    seeds: tuple[int, ...]
    opponents: tuple[str, ...]
    variants: tuple[str, ...]


@dataclass(frozen=True)
class Pin:
    source_commit: str
    source_archive: str
    source_archive_sha256: str
    source_archive_bytes: int
    source_member_count: int
    source_freeze_sha256: str
    source_freeze_version: str
    frozen_hashes: Mapping[str, str]
    evidence_ledgers: tuple[EvidenceLedgerPin, ...]


PRODUCTION_PIN = Pin(
    source_commit="9f89a2cd75c5c89198caa1617a9e399900553ce3",
    source_archive="exports/titan-sell-v3-source.tar.gz",
    source_archive_sha256="a14f9bbc7e10753fef2d5e983e9746e107940d7081b8934fb499561191e9c3c7",
    source_archive_bytes=59_966,
    source_member_count=15,
    source_freeze_sha256="37ffcba618a4a640ceae08b54a1770569904cc29b2698eb6377a7b3aa62eb283",
    source_freeze_version="finite-horizon-v3",
    frozen_hashes={
        "scheduler.py": "32c8610c9827d1686a6f831e2c4b6af4c00d32d2aa04dcf25699d976d6d97dd9",
        "mechanics.py": "579965e589237d1e5bbcc8b8448188f91b173d4480430d34b3a7f0e07e0c48d3",
        "candidate.py": "2e4897fb3aa8b0bee3e97709808c3aa25fa5055bcf5ce7d433b493eb334870f2",
        "reference/next-panel/vendor/arlene.py": "1dc166ae2bf0c56a44fac4482f469b8812968c4cb32459cb9860f5077897a7d4",
        "reference/decision/decision.py": "9d78406668c927785b29f5bf2b5a67f0263bfcd63f626c881a60bad5f8293c52",
    },
    evidence_ledgers=(
        EvidenceLedgerPin(
            name="development",
            path="runtime/development-v3.json",
            sha256="b73243356f991864e6d6e8aa7a0bf24d7a2646114f7e6745bd9977b287514f60",
            bytes=143_452,
            seeds=(9_600_803, 9_600_821, 9_600_839),
            opponents=("arlene", "apex"),
            variants=("candidate",),
        ),
        EvidenceLedgerPin(
            name="held_out",
            path="runtime/heldout-v3.json",
            sha256="b903365f7ce4cf61580c4ae0de7001f640534a338238fdb5383a2bde9aa3ab77",
            bytes=181_214,
            seeds=(9_600_901, 9_600_919),
            opponents=("arlene", "apex"),
            variants=("baseline", "candidate"),
        ),
    ),
)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise SnapshotError(f"cannot read JSON evidence {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise SnapshotError(f"JSON evidence must be an object: {path}")
    return value


def safe_name(raw: str) -> str:
    if not raw or "\\" in raw:
        raise SnapshotError(f"unsafe archive member name: {raw!r}")
    path = PurePosixPath(raw)
    if path.is_absolute() or any(part in ("", ".", "..") for part in path.parts):
        raise SnapshotError(f"unsafe archive member name: {raw!r}")
    normalized = path.as_posix()
    if normalized != raw:
        raise SnapshotError(f"noncanonical archive member name: {raw!r}")
    return normalized


def read_archive(data: bytes) -> dict[str, bytes]:
    members: dict[str, bytes] = {}
    total = 0
    try:
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as archive:
            for info in archive:
                if len(members) >= MAX_MEMBER_COUNT:
                    raise SnapshotError("archive contains too many members")
                name = safe_name(info.name)
                if name in members:
                    raise SnapshotError(f"duplicate archive member: {name}")
                if not info.isfile() or info.issym() or info.islnk():
                    raise SnapshotError(f"archive member is not a regular file: {name}")
                if info.size < 0 or info.size > MAX_MEMBER_BYTES:
                    raise SnapshotError(f"archive member size is unsafe: {name} ({info.size})")
                total += info.size
                if total > MAX_TOTAL_BYTES:
                    raise SnapshotError("archive expands beyond the bounded source budget")
                stream = archive.extractfile(info)
                if stream is None:
                    raise SnapshotError(f"archive member has no readable payload: {name}")
                payload = stream.read(MAX_MEMBER_BYTES + 1)
                if len(payload) != info.size:
                    raise SnapshotError(f"archive member length mismatch: {name}")
                if info.mode & 0o777 != 0o644 or int(info.mtime) != 0:
                    raise SnapshotError(f"archive member metadata drift: {name}")
                members[name] = payload
    except SnapshotError:
        raise
    except (tarfile.TarError, OSError, EOFError) as exc:
        raise SnapshotError(f"invalid source archive: {exc}") from exc
    return members
