#!/usr/bin/env python3
"""Fail-closed package-vs-checkout freshness gate for TITAN V4 native execution.

This module does not build, mutate, or extract a package. It authenticates an
already-built tar archive, binds the live files to an exact Git commit, and
compares the small production-core byte set that execution lanes depend on.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import stat
import subprocess
import tarfile
from typing import Iterable

SCHEMA = "titan.v4.native_freshness.v1"
CORE_PATHS = (
    "main.py",
    "titan_runtime.py",
    "scheduler.py",
    "frozen_selected.py",
    "TITAN-CONFIG.json",
)
MAX_ARCHIVE_BYTES = 32 * 1024 * 1024
MAX_CORE_MEMBER_BYTES = 4 * 1024 * 1024
MAX_TAR_MEMBERS = 4096
_HEX = frozenset("0123456789abcdef")


class InvalidEvidence(ValueError):
    """Raised when inputs cannot support a freshness claim."""


def _is_hex(value: str, length: int) -> bool:
    return isinstance(value, str) and len(value) == length and all(c in _HEX for c in value)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _git_blob(data: bytes) -> str:
    header = b"blob " + str(len(data)).encode("ascii") + b"\0"
    return hashlib.sha1(header + data).hexdigest()


def _git(repo_root: Path, *args: str) -> str:
    try:
        proc = subprocess.run(
            ["git", "-C", str(repo_root), *args],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        detail = getattr(exc, "stderr", "") or str(exc)
        raise InvalidEvidence("git binding failed: " + detail.strip()) from exc
    return proc.stdout.strip()


def _safe_relative_path(value: str) -> PurePosixPath:
    if not isinstance(value, str) or not value:
        raise InvalidEvidence("live directory must be a non-empty relative path")
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in ("", ".", "..") for part in path.parts):
        raise InvalidEvidence("live directory must be normalized and repository-relative")
    return path


def _no_symlink_ancestry(root: Path, relative: PurePosixPath) -> Path:
    current = root
    if current.is_symlink():
        raise InvalidEvidence("repository root may not be a symlink")
    for part in relative.parts:
        current = current / part
        try:
            mode = current.lstat().st_mode
        except OSError as exc:
            raise InvalidEvidence(f"missing live path: {relative.as_posix()}") from exc
        if stat.S_ISLNK(mode):
            raise InvalidEvidence(f"symlink live path forbidden: {relative.as_posix()}")
    return current


def _read_live_file(repo_root: Path, relative: PurePosixPath) -> bytes:
    path = _no_symlink_ancestry(repo_root, relative)
    try:
        before = path.stat()
    except OSError as exc:
        raise InvalidEvidence(f"cannot stat live file: {relative.as_posix()}") from exc
    if not stat.S_ISREG(before.st_mode):
        raise InvalidEvidence(f"live core member is not a regular file: {relative.as_posix()}")
    if before.st_size > MAX_CORE_MEMBER_BYTES:
        raise InvalidEvidence(f"live core member exceeds size bound: {relative.as_posix()}")
    try:
        data = path.read_bytes()
        after = path.stat()
    except OSError as exc:
        raise InvalidEvidence(f"cannot read live file: {relative.as_posix()}") from exc
    identity_before = (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
    identity_after = (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
    if identity_before != identity_after or len(data) != after.st_size:
        raise InvalidEvidence(f"live file changed during read: {relative.as_posix()}")
    return data


def _read_archive_core(archive: Path, expected_sha256: str) -> tuple[str, dict[str, bytes]]:
    if not _is_hex(expected_sha256, 64):
        raise InvalidEvidence("expected archive sha256 must be lowercase 64-hex")
    if archive.is_symlink():
        raise InvalidEvidence("archive path may not be a symlink")
    try:
        st = archive.stat()
    except OSError as exc:
        raise InvalidEvidence("archive is missing or unreadable") from exc
    if not stat.S_ISREG(st.st_mode):
        raise InvalidEvidence("archive must be a regular file")
    if st.st_size <= 0 or st.st_size > MAX_ARCHIVE_BYTES:
        raise InvalidEvidence("archive size is outside the accepted bound")
    try:
        raw = archive.read_bytes()
    except OSError as exc:
        raise InvalidEvidence("archive read failed") from exc
    actual_sha256 = _sha256(raw)
    if actual_sha256 != expected_sha256:
        raise InvalidEvidence("archive sha256 does not match the authenticated digest")

    wanted = set(CORE_PATHS)
    found: dict[str, bytes] = {}
    counts = {name: 0 for name in CORE_PATHS}
    try:
        with tarfile.open(fileobj=io.BytesIO(raw), mode="r:*") as tf:
            for index, member in enumerate(tf, start=1):
                if index > MAX_TAR_MEMBERS:
                    raise InvalidEvidence("archive member count exceeds accepted bound")
                name = member.name
                if name not in wanted:
                    continue
                counts[name] += 1
                if counts[name] > 1:
                    raise InvalidEvidence(f"duplicate archive core member: {name}")
                if not member.isfile():
                    raise InvalidEvidence(f"archive core member is not a regular file: {name}")
                if member.size < 0 or member.size > MAX_CORE_MEMBER_BYTES:
                    raise InvalidEvidence(f"archive core member exceeds size bound: {name}")
                stream = tf.extractfile(member)
                if stream is None:
                    raise InvalidEvidence(f"archive core member is unreadable: {name}")
                data = stream.read(MAX_CORE_MEMBER_BYTES + 1)
                if len(data) != member.size or len(data) > MAX_CORE_MEMBER_BYTES:
                    raise InvalidEvidence(f"archive core member size mismatch: {name}")
                found[name] = data
    except InvalidEvidence:
        raise
    except (tarfile.TarError, OSError, EOFError) as exc:
        raise InvalidEvidence("archive is not a readable tar package") from exc

    missing = [name for name in CORE_PATHS if counts[name] != 1]
    if missing:
        raise InvalidEvidence("archive missing core member(s): " + ", ".join(missing))
    return actual_sha256, found


def verify_freshness(
    *,
    repo_root: Path,
    live_dir: str,
    archive: Path,
    expected_archive_sha256: str,
    expected_commit: str,
) -> dict:
    """Return deterministic CURRENT/STALE/INVALID evidence for one package."""
    base = {
        "schema": SCHEMA,
        "verdict": "INVALID",
        "expected_commit": expected_commit,
        "expected_archive_sha256": expected_archive_sha256,
        "core_paths": list(CORE_PATHS),
        "files": [],
        "stale_paths": [],
        "problems": [],
    }
    try:
        repo_root = Path(repo_root)
        archive = Path(archive)
        if repo_root.is_symlink() or not repo_root.is_dir():
            raise InvalidEvidence("repo root must be an existing non-symlink directory")
        if not _is_hex(expected_commit, 40):
            raise InvalidEvidence("expected commit must be lowercase 40-hex")
        live_rel = _safe_relative_path(live_dir)
        head = _git(repo_root, "rev-parse", "HEAD")
        if head != expected_commit:
            raise InvalidEvidence(f"checkout HEAD drift: expected {expected_commit}, got {head}")
        base["commit"] = head

        actual_archive_sha256, package = _read_archive_core(archive, expected_archive_sha256)
        base["archive_sha256"] = actual_archive_sha256

        stale: list[str] = []
        records = []
        for name in CORE_PATHS:
            repo_rel = live_rel / name
            live = _read_live_file(repo_root, repo_rel)
            live_blob = _git_blob(live)
            tracked_blob = _git(repo_root, "rev-parse", f"HEAD:{repo_rel.as_posix()}")
            if not _is_hex(tracked_blob, 40) or tracked_blob != live_blob:
                raise InvalidEvidence(f"live file is not byte-identical to HEAD: {repo_rel.as_posix()}")
            packed = package[name]
            package_blob = _git_blob(packed)
            same = live == packed
            if not same:
                stale.append(name)
            records.append(
                {
                    "path": name,
                    "same": same,
                    "live": {
                        "bytes": len(live),
                        "git_blob": live_blob,
                        "sha256": _sha256(live),
                    },
                    "package": {
                        "bytes": len(packed),
                        "git_blob": package_blob,
                        "sha256": _sha256(packed),
                    },
                }
            )
        base["files"] = records
        base["stale_paths"] = stale
        base["verdict"] = "STALE" if stale else "CURRENT"
        return base
    except InvalidEvidence as exc:
        base["problems"] = [str(exc)]
        return base


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo-root", required=True, type=Path)
    p.add_argument(
        "--live-dir",
        default="revenue/kaggriculture/cloud-execution-lab",
        help="repository-relative directory containing the live production core",
    )
    p.add_argument("--archive", required=True, type=Path)
    p.add_argument("--expected-archive-sha256", required=True)
    p.add_argument("--expected-commit", required=True)
    return p


def main(argv: Iterable[str] | None = None) -> int:
    ns = _parser().parse_args(argv)
    report = verify_freshness(
        repo_root=ns.repo_root,
        live_dir=ns.live_dir,
        archive=ns.archive,
        expected_archive_sha256=ns.expected_archive_sha256,
        expected_commit=ns.expected_commit,
    )
    print(json.dumps(report, sort_keys=True, separators=(",", ":")))
    return {"CURRENT": 0, "STALE": 1, "INVALID": 2}[report["verdict"]]


if __name__ == "__main__":
    raise SystemExit(main())
