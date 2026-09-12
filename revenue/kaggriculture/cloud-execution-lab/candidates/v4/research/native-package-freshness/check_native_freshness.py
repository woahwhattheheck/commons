#!/usr/bin/env python3
"""Fail-closed package-vs-checkout freshness gate for TITAN V4 native execution.

This module does not build, mutate, extract, publish, or promote a package. It
authenticates an already-built tar archive, binds the canonical live production
root to an exact Git commit, consumes the package's SOURCE.json runtime manifest,
and compares every declared package member to its exact tracked source byte.
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
from typing import Any, Iterable

SCHEMA = "titan.v4.native_freshness.v2"
CANONICAL_LIVE_DIR = "revenue/kaggriculture/cloud-execution-lab"
SOURCE_MEMBER = "SOURCE.json"
CORE_PATHS = (
    "main.py",
    "titan_runtime.py",
    "scheduler.py",
    "frozen_selected.py",
    "TITAN-CONFIG.json",
)
MAX_ARCHIVE_BYTES = 32 * 1024 * 1024
MAX_MEMBER_BYTES = 4 * 1024 * 1024
MAX_TAR_MEMBERS = 4096
_HEX = frozenset("0123456789abcdef")


class InvalidEvidence(ValueError):
    """Raised when inputs cannot support a freshness claim."""


def _is_hex(value: Any, length: int) -> bool:
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


def _safe_member_path(value: Any) -> PurePosixPath:
    if not isinstance(value, str) or not value or "\\" in value:
        raise InvalidEvidence("archive member names must be non-empty normalized POSIX paths")
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in ("", ".", "..") for part in path.parts):
        raise InvalidEvidence(f"unsafe archive member path: {value!r}")
    if path.as_posix() != value:
        raise InvalidEvidence(f"non-normalized archive member path: {value!r}")
    return path


def _canonical_live_dir(value: Any) -> PurePosixPath:
    if value != CANONICAL_LIVE_DIR:
        raise InvalidEvidence(
            f"live directory must be canonical {CANONICAL_LIVE_DIR!r}; got {value!r}"
        )
    return PurePosixPath(CANONICAL_LIVE_DIR)


def _source_repo_path(live_rel: PurePosixPath, value: Any) -> PurePosixPath:
    if not isinstance(value, str) or not value or "\\" in value:
        raise InvalidEvidence("SOURCE runtime source_path must be a non-empty POSIX path")
    source = PurePosixPath(value)
    if source.is_absolute():
        raise InvalidEvidence(f"absolute SOURCE source_path forbidden: {value!r}")
    parts = list(live_rel.parts)
    for part in source.parts:
        if part in ("", "."):
            raise InvalidEvidence(f"non-normalized SOURCE source_path: {value!r}")
        if part == "..":
            if not parts:
                raise InvalidEvidence(f"SOURCE source_path escapes repository: {value!r}")
            parts.pop()
        else:
            parts.append(part)
    if not parts:
        raise InvalidEvidence(f"SOURCE source_path resolves to repository root: {value!r}")
    result = PurePosixPath(*parts)
    if result.as_posix().startswith("../"):
        raise InvalidEvidence(f"SOURCE source_path escapes repository: {value!r}")
    return result


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
        raise InvalidEvidence(f"live member is not a regular file: {relative.as_posix()}")
    if before.st_size < 0 or before.st_size > MAX_MEMBER_BYTES:
        raise InvalidEvidence(f"live member exceeds size bound: {relative.as_posix()}")
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


def _strict_json_object(raw: bytes) -> dict[str, Any]:
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise InvalidEvidence("SOURCE.json is not valid UTF-8") from exc

    def reject_constant(value: str):
        raise InvalidEvidence(f"SOURCE.json non-finite constant forbidden: {value}")

    def reject_duplicates(pairs):
        out = {}
        for key, value in pairs:
            if key in out:
                raise InvalidEvidence(f"SOURCE.json duplicate key forbidden: {key!r}")
            out[key] = value
        return out

    try:
        parsed = json.loads(
            text,
            parse_constant=reject_constant,
            object_pairs_hook=reject_duplicates,
        )
    except InvalidEvidence:
        raise
    except (json.JSONDecodeError, TypeError, ValueError) as exc:
        raise InvalidEvidence("SOURCE.json is not strict JSON") from exc
    if not isinstance(parsed, dict):
        raise InvalidEvidence("SOURCE.json top level must be an object")
    return parsed


def _read_archive(archive: Path, expected_sha256: str) -> tuple[str, dict[str, bytes]]:
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

    found: dict[str, bytes] = {}
    try:
        with tarfile.open(fileobj=io.BytesIO(raw), mode="r:*") as tf:
            for index, member in enumerate(tf, start=1):
                if index > MAX_TAR_MEMBERS:
                    raise InvalidEvidence("archive member count exceeds accepted bound")
                name = _safe_member_path(member.name).as_posix()
                if name in found:
                    raise InvalidEvidence(f"duplicate archive member: {name}")
                if not member.isfile():
                    raise InvalidEvidence(f"archive member is not a regular file: {name}")
                if member.size < 0 or member.size > MAX_MEMBER_BYTES:
                    raise InvalidEvidence(f"archive member exceeds size bound: {name}")
                stream = tf.extractfile(member)
                if stream is None:
                    raise InvalidEvidence(f"archive member is unreadable: {name}")
                data = stream.read(MAX_MEMBER_BYTES + 1)
                if len(data) != member.size or len(data) > MAX_MEMBER_BYTES:
                    raise InvalidEvidence(f"archive member size mismatch: {name}")
                found[name] = data
    except InvalidEvidence:
        raise
    except (tarfile.TarError, OSError, EOFError) as exc:
        raise InvalidEvidence("archive is not a readable tar package") from exc
    if SOURCE_MEMBER not in found:
        raise InvalidEvidence(f"archive missing required {SOURCE_MEMBER}")
    return actual_sha256, found


def _validate_runtime_manifest(
    source: dict[str, Any], package: dict[str, bytes], live_rel: PurePosixPath
) -> list[tuple[str, PurePosixPath, dict[str, Any]]]:
    runtime = source.get("runtime")
    if not isinstance(runtime, dict) or not runtime:
        raise InvalidEvidence("SOURCE.json runtime must be a non-empty object")

    expected_members = {SOURCE_MEMBER}
    rows: list[tuple[str, PurePosixPath, dict[str, Any]]] = []
    core_seen = set()
    for member_name, receipt in runtime.items():
        member = _safe_member_path(member_name).as_posix()
        if member == SOURCE_MEMBER:
            raise InvalidEvidence("SOURCE.json runtime may not self-declare SOURCE.json")
        if member in expected_members:
            raise InvalidEvidence(f"duplicate SOURCE runtime member: {member}")
        expected_members.add(member)
        if not isinstance(receipt, dict):
            raise InvalidEvidence(f"SOURCE runtime receipt must be an object: {member}")
        size = receipt.get("bytes")
        digest = receipt.get("sha256")
        source_path = receipt.get("source_path")
        if type(size) is not int or size < 0 or size > MAX_MEMBER_BYTES:
            raise InvalidEvidence(f"invalid SOURCE runtime bytes: {member}")
        if not _is_hex(digest, 64):
            raise InvalidEvidence(f"invalid SOURCE runtime sha256: {member}")
        repo_rel = _source_repo_path(live_rel, source_path)
        packed = package.get(member)
        if packed is None:
            raise InvalidEvidence(f"archive missing SOURCE runtime member: {member}")
        if len(packed) != size or _sha256(packed) != digest:
            raise InvalidEvidence(f"SOURCE runtime receipt mismatch: {member}")
        rows.append((member, repo_rel, receipt))
        if member in CORE_PATHS:
            core_seen.add(member)
            if source_path != member:
                raise InvalidEvidence(f"canonical core source_path mismatch: {member}")

    extras = sorted(set(package) - expected_members)
    missing = sorted(expected_members - set(package))
    if extras or missing:
        details = []
        if missing:
            details.append("missing=" + ",".join(missing))
        if extras:
            details.append("extra=" + ",".join(extras))
        raise InvalidEvidence("archive/SOURCE runtime member-set mismatch: " + " ".join(details))
    absent_core = [name for name in CORE_PATHS if name not in core_seen]
    if absent_core:
        raise InvalidEvidence("SOURCE runtime missing canonical core member(s): " + ", ".join(absent_core))
    return rows


def verify_freshness(
    *,
    repo_root: Path,
    live_dir: str = CANONICAL_LIVE_DIR,
    archive: Path,
    expected_archive_sha256: str,
    expected_commit: str,
) -> dict[str, Any]:
    """Return deterministic CURRENT/STALE/INVALID evidence for one package."""
    base: dict[str, Any] = {
        "schema": SCHEMA,
        "verdict": "INVALID",
        "expected_commit": expected_commit,
        "expected_archive_sha256": expected_archive_sha256,
        "live_dir": CANONICAL_LIVE_DIR,
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
        live_rel = _canonical_live_dir(live_dir)
        head = _git(repo_root, "rev-parse", "HEAD")
        if head != expected_commit:
            raise InvalidEvidence(f"checkout HEAD drift: expected {expected_commit}, got {head}")
        base["commit"] = head

        actual_archive_sha256, package = _read_archive(archive, expected_archive_sha256)
        base["archive_sha256"] = actual_archive_sha256
        source = _strict_json_object(package[SOURCE_MEMBER])
        manifest_rows = _validate_runtime_manifest(source, package, live_rel)
        base["runtime_members"] = len(manifest_rows)
        base["source_sha256"] = _sha256(package[SOURCE_MEMBER])

        # Bind every manifest-resolved source identity to the immutable expected
        # commit before reading live bytes. Never resolve through moving HEAD.
        tracked_blobs: dict[PurePosixPath, str] = {}
        for _member, repo_rel, _receipt in manifest_rows:
            if repo_rel in tracked_blobs:
                continue
            tracked_blob = _git(
                repo_root,
                "rev-parse",
                f"{expected_commit}:{repo_rel.as_posix()}",
            )
            if not _is_hex(tracked_blob, 40):
                raise InvalidEvidence(
                    f"tracked source identity is not a Git blob id: {repo_rel.as_posix()}"
                )
            tracked_blobs[repo_rel] = tracked_blob

        stale: list[str] = []
        records = []
        live_cache: dict[PurePosixPath, tuple[bytes, str]] = {}
        for member, repo_rel, _receipt in manifest_rows:
            cached = live_cache.get(repo_rel)
            if cached is None:
                live = _read_live_file(repo_root, repo_rel)
                live_blob = _git_blob(live)
                if tracked_blobs[repo_rel] != live_blob:
                    raise InvalidEvidence(
                        f"live file is not byte-identical to expected commit: {repo_rel.as_posix()}"
                    )
                cached = (live, live_blob)
                live_cache[repo_rel] = cached
            live, live_blob = cached
            packed = package[member]
            same = live == packed
            if not same:
                stale.append(member)
            records.append(
                {
                    "path": member,
                    "source_path": repo_rel.as_posix(),
                    "same": same,
                    "live": {
                        "bytes": len(live),
                        "git_blob": live_blob,
                        "sha256": _sha256(live),
                    },
                    "package": {
                        "bytes": len(packed),
                        "git_blob": _git_blob(packed),
                        "sha256": _sha256(packed),
                    },
                }
            )
        final_head = _git(repo_root, "rev-parse", "HEAD")
        if final_head != expected_commit:
            raise InvalidEvidence(
                f"checkout HEAD changed during verification: expected {expected_commit}, got {final_head}"
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
        default=CANONICAL_LIVE_DIR,
        help=f"must be the canonical production directory: {CANONICAL_LIVE_DIR}",
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
    print(json.dumps(report, sort_keys=True, separators=(",", ":"), allow_nan=False))
    return {"CURRENT": 0, "STALE": 1, "INVALID": 2}[report["verdict"]]


if __name__ == "__main__":
    raise SystemExit(main())
