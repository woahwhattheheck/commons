"""Fail-closed Hamilton pursuit gate with inode-custody retained evidence.

The decision engine lives in ``_gate_core``.  This front module hardens the only
source-tree trust boundary for owner/partner evidence, then installs that binder
into the core before re-exporting the public gate API.
"""
from __future__ import annotations

import os
import stat
from pathlib import Path, PurePosixPath
from typing import Any, Mapping

from . import _gate_core as _core

GateError = _core.GateError
OPPORTUNITY_ID = _core.OPPORTUNITY_ID
EVIDENCE_ARTIFACT_SCHEMA = _core.EVIDENCE_ARTIFACT_SCHEMA
MAX_RETAINED_EVIDENCE_BYTES = _core.MAX_RETAINED_EVIDENCE_BYTES
BUYER_CONTROL_FIELDS = _core.BUYER_CONTROL_FIELDS
SOURCE_AUTHORITIES = _core.SOURCE_AUTHORITIES
PRIME_GATES = _core.PRIME_GATES
SPECIALIST_GATES = _core.SPECIALIST_GATES
ALL_GATES = _core.ALL_GATES
EVIDENCE_CLASSES = _core.EVIDENCE_CLASSES
OFFICIAL_EVIDENCE_CLASSES = _core.OFFICIAL_EVIDENCE_CLASSES
INTERNAL_EVIDENCE_KIND = _core.INTERNAL_EVIDENCE_KIND
loads_strict = _core.loads_strict
canonical_bytes = _core.canonical_bytes
digest = _core.digest
_raw_digest = _core._raw_digest
_str = _core._str
_sha = _core._sha
_string_list = _core._string_list


def _retained_evidence_path(value: Any, sid: str) -> Path:
    raw = _str(value, f"{sid}.retained_artifact.path")
    if "\\" in raw:
        raise GateError(f"{sid}.retained_artifact.path must use POSIX separators")
    rel = PurePosixPath(raw)
    if rel.is_absolute() or ".." in rel.parts or rel.parts[:1] != ("retained_evidence",):
        raise GateError(f"{sid}.retained_artifact.path must stay under retained_evidence/")
    if len(rel.parts) != 2 or rel.suffix != ".json":
        raise GateError(
            f"{sid}.retained_artifact.path must name one JSON file directly under retained_evidence/"
        )

    package_dir = Path(__file__).resolve().parent
    base = package_dir / "retained_evidence"
    try:
        base_st = os.lstat(base)
    except OSError as exc:
        raise GateError(f"{sid}.retained_artifact retained_evidence directory is unavailable") from exc
    if not stat.S_ISDIR(base_st.st_mode) or stat.S_ISLNK(base_st.st_mode):
        raise GateError(f"{sid}.retained_artifact retained_evidence directory must be a real directory")
    return base / rel.name


def _generation(st: os.stat_result) -> tuple[int, int, int, int, int, int, int]:
    return (
        st.st_dev,
        st.st_ino,
        stat.S_IFMT(st.st_mode),
        st.st_nlink,
        st.st_size,
        getattr(st, "st_mtime_ns", int(st.st_mtime * 1_000_000_000)),
        getattr(st, "st_ctime_ns", int(st.st_ctime * 1_000_000_000)),
    )


def _validate_retained_stat(st: os.stat_result, sid: str) -> None:
    if not stat.S_ISREG(st.st_mode):
        raise GateError(f"{sid}.retained_artifact must resolve to a regular file")
    if st.st_nlink != 1:
        raise GateError(f"{sid}.retained_artifact must have exactly one filesystem link")
    if st.st_size <= 0 or st.st_size > MAX_RETAINED_EVIDENCE_BYTES:
        raise GateError(f"{sid}.retained_artifact has invalid retained byte length")


def _read_retained_evidence(path: Path, sid: str) -> bytes:
    """Read one confined, single-link file generation through one descriptor."""
    try:
        parent_pre = os.lstat(path.parent)
        pre = os.lstat(path)
    except FileNotFoundError as exc:
        raise GateError(f"{sid}.retained_artifact is not retained in source tree") from exc
    except OSError as exc:
        raise GateError(f"{sid}.retained_artifact cannot be inspected") from exc
    if not stat.S_ISDIR(parent_pre.st_mode) or stat.S_ISLNK(parent_pre.st_mode):
        raise GateError(f"{sid}.retained_artifact.path must not traverse symlinks")
    if stat.S_ISLNK(pre.st_mode):
        raise GateError(f"{sid}.retained_artifact.path must not traverse symlinks")
    _validate_retained_stat(pre, sid)

    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = os.open(path, flags)
    except OSError as exc:
        raise GateError(f"{sid}.retained_artifact cannot be opened without following links") from exc
    try:
        opened = os.fstat(fd)
        _validate_retained_stat(opened, sid)
        if _generation(opened) != _generation(pre):
            raise GateError(f"{sid}.retained_artifact generation changed before read")

        chunks: list[bytes] = []
        remaining = MAX_RETAINED_EVIDENCE_BYTES + 1
        while remaining > 0:
            chunk = os.read(fd, min(65_536, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        raw = b"".join(chunks)
        after_fd = os.fstat(fd)
    except OSError as exc:
        raise GateError(f"{sid}.retained_artifact cannot be read") from exc
    finally:
        os.close(fd)

    try:
        parent_post = os.lstat(path.parent)
        post = os.lstat(path)
    except OSError as exc:
        raise GateError(f"{sid}.retained_artifact generation disappeared during read") from exc
    _validate_retained_stat(after_fd, sid)
    _validate_retained_stat(post, sid)
    if (parent_pre.st_dev, parent_pre.st_ino) != (parent_post.st_dev, parent_post.st_ino):
        raise GateError(f"{sid}.retained_artifact directory generation changed during read")
    expected = _generation(pre)
    if _generation(after_fd) != expected or _generation(post) != expected:
        raise GateError(f"{sid}.retained_artifact generation changed during read")
    if len(raw) != pre.st_size or len(raw) > MAX_RETAINED_EVIDENCE_BYTES:
        raise GateError(f"{sid}.retained_artifact has invalid retained byte length")
    return raw


def _internal_artifact_binding(source: Mapping[str, Any], sid: str) -> tuple[str, str]:
    locator = source.get("retained_artifact")
    if type(locator) is not dict or set(locator) != {"path", "sha256"}:
        raise GateError(f"{sid}.retained_artifact must contain exact path and sha256 fields")
    expected_sha = _sha(locator.get("sha256"), f"{sid}.retained_artifact.sha256")
    source_sha = _sha(source.get("content_sha256"), f"{sid}.content_sha256")
    if expected_sha != source_sha:
        raise GateError(f"{sid}.retained_artifact.sha256 must equal source content_sha256")

    path = _retained_evidence_path(locator.get("path"), sid)
    raw = _read_retained_evidence(path, sid)
    if _raw_digest(raw) != expected_sha:
        raise GateError(f"{sid}.content_sha256 does not authenticate retained file bytes")
    try:
        artifact = loads_strict(raw.decode("utf-8"))
    except UnicodeDecodeError as exc:
        raise GateError(f"{sid}.retained_artifact is not utf-8") from exc

    required = {"schema", "source_id", "opportunity_id", "binding", "evidence"}
    if type(artifact) is not dict or set(artifact) != required:
        raise GateError(f"{sid}.retained_artifact has unexpected record fields")
    if artifact.get("schema") != EVIDENCE_ARTIFACT_SCHEMA:
        raise GateError(f"{sid}.retained_artifact schema mismatch")
    if artifact.get("source_id") != sid:
        raise GateError(f"{sid}.retained_artifact source_id mismatch")
    if artifact.get("opportunity_id") != OPPORTUNITY_ID:
        raise GateError(f"{sid}.retained_artifact opportunity_id mismatch")

    binding = artifact.get("binding")
    if type(binding) is not dict or set(binding) != {"requirement_id", "evidence_class"}:
        raise GateError(f"{sid}.retained_artifact.binding must contain exact binding fields")
    rid = _str(binding.get("requirement_id"), f"{sid}.retained_artifact.binding.requirement_id")
    evidence_class = _str(binding.get("evidence_class"), f"{sid}.retained_artifact.binding.evidence_class")
    if rid not in EVIDENCE_CLASSES or evidence_class not in EVIDENCE_CLASSES[rid]:
        raise GateError(f"{sid}.retained_artifact binding is not admissible: {rid}/{evidence_class}")
    if evidence_class in OFFICIAL_EVIDENCE_CLASSES:
        raise GateError(f"{sid}.retained_artifact cannot use an official evidence class")
    expected_kind = INTERNAL_EVIDENCE_KIND.get(evidence_class)
    if expected_kind is None:
        raise GateError(f"{sid}.retained_artifact unsupported internal evidence class")

    evidence = artifact.get("evidence")
    if type(evidence) is not dict or set(evidence) != {"kind", "facts", "refs"}:
        raise GateError(f"{sid}.retained_artifact.evidence must contain exact kind/facts/refs")
    if evidence.get("kind") != expected_kind:
        raise GateError(f"{sid}.retained_artifact.evidence.kind must be {expected_kind}")
    _string_list(evidence.get("facts"), f"{sid}.retained_artifact.evidence.facts")
    _string_list(evidence.get("refs"), f"{sid}.retained_artifact.evidence.refs")
    return rid, evidence_class


# Install the hardened trust boundary into the byte-stable reviewed core.
_core._retained_evidence_path = _retained_evidence_path
_core._internal_artifact_binding = _internal_artifact_binding

compile_pursuit = _core.compile_pursuit
verify_receipt = _core.verify_receipt
main = _core.main


def __getattr__(name: str):
    return getattr(_core, name)


if __name__ == "__main__":
    raise SystemExit(main())
