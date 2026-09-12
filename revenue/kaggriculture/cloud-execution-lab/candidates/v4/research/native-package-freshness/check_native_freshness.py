#!/usr/bin/env python3
"""Fail-closed package-vs-checkout freshness gate for TITAN V4 native execution.

This module does not build, mutate, or extract a package. It authenticates an
already-built tar archive, binds the live publisher and every source file to an
exact Git commit, snapshots the canonical publisher's source_files() closure,
and compares the archive to that full closure.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import posixpath
from pathlib import Path, PurePosixPath
import stat
import subprocess
import tarfile
from typing import Iterable, Mapping

SCHEMA = "titan.v4.native_freshness.v2"
PUBLISHER_PATH = "build_integrated.py"
SOURCE_MANIFEST_MEMBER = "SOURCE.json"
MAX_ARCHIVE_BYTES = 32 * 1024 * 1024
MAX_SOURCE_MEMBER_BYTES = 4 * 1024 * 1024
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


def _safe_relative_path(value: str, *, label: str = "path") -> PurePosixPath:
    if not isinstance(value, str) or not value or "\\" in value:
        raise InvalidEvidence(f"{label} must be a non-empty POSIX relative path")
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in ("", ".", "..") for part in path.parts):
        raise InvalidEvidence(f"{label} must be normalized and repository-relative")
    return path


def _normalize_source_path(live_rel: PurePosixPath, source: str) -> PurePosixPath:
    if not isinstance(source, str) or not source or "\\" in source:
        raise InvalidEvidence("publisher source path must be a non-empty POSIX path")
    raw = PurePosixPath(source)
    if raw.is_absolute():
        raise InvalidEvidence("publisher source path may not be absolute")
    normalized = posixpath.normpath(f"{live_rel.as_posix()}/{source}")
    if normalized in ("", ".", "..") or normalized.startswith("../"):
        raise InvalidEvidence("publisher source path escapes repository root")
    return _safe_relative_path(normalized, label="publisher source path")


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
        raise InvalidEvidence(f"live source member is not a regular file: {relative.as_posix()}")
    if before.st_size > MAX_SOURCE_MEMBER_BYTES:
        raise InvalidEvidence(f"live source member exceeds size bound: {relative.as_posix()}")
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


def _tracked_live_file(
    repo_root: Path,
    relative: PurePosixPath,
    expected_commit: str,
) -> tuple[bytes, str]:
    live = _read_live_file(repo_root, relative)
    live_blob = _git_blob(live)
    tracked_blob = _git(repo_root, "rev-parse", f"{expected_commit}:{relative.as_posix()}")
    if not _is_hex(tracked_blob, 40) or tracked_blob != live_blob:
        raise InvalidEvidence(
            f"live file is not byte-identical to expected commit: {relative.as_posix()}"
        )
    return live, live_blob


def _publisher_source_mapping(
    repo_root: Path,
    live_rel: PurePosixPath,
    expected_commit: str,
) -> tuple[dict[str, tuple[str, PurePosixPath]], str]:
    """Snapshot and execute only the exact-commit canonical source_files() mapping."""
    publisher_rel = live_rel / PUBLISHER_PATH
    publisher, publisher_blob = _tracked_live_file(repo_root, publisher_rel, expected_commit)
    try:
        text = publisher.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise InvalidEvidence("canonical publisher is not UTF-8 Python source") from exc

    namespace = {
        "__file__": str(repo_root / Path(*publisher_rel.parts)),
        "__name__": "_titan_native_freshness_publisher_snapshot",
    }
    try:
        exec(compile(text, namespace["__file__"], "exec"), namespace)
        source_files = namespace.get("source_files")
        if not callable(source_files):
            raise InvalidEvidence("canonical publisher does not expose callable source_files()")
        raw_mapping = source_files()
    except InvalidEvidence:
        raise
    except Exception as exc:
        raise InvalidEvidence(f"canonical publisher source_files() failed: {exc}") from exc

    if not isinstance(raw_mapping, Mapping) or not raw_mapping:
        raise InvalidEvidence("canonical publisher source_files() must return a non-empty mapping")
    if len(raw_mapping) + 1 > MAX_TAR_MEMBERS:
        raise InvalidEvidence("canonical publisher source mapping exceeds archive member bound")

    mapping: dict[str, tuple[str, PurePosixPath]] = {}
    for archive_name, source in raw_mapping.items():
        archive_path = _safe_relative_path(archive_name, label="archive member")
        canonical_name = archive_path.as_posix()
        if canonical_name == SOURCE_MANIFEST_MEMBER:
            raise InvalidEvidence("publisher source mapping may not own generated SOURCE.json")
        if canonical_name in mapping:
            raise InvalidEvidence(f"duplicate canonical archive member: {canonical_name}")
        source_rel = _normalize_source_path(live_rel, source)
        mapping[canonical_name] = (source, source_rel)
    return dict(sorted(mapping.items())), publisher_blob


def _read_archive_members(
    archive: Path,
    expected_sha256: str,
    wanted_members: Iterable[str],
) -> tuple[str, dict[str, bytes]]:
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

    wanted = set(wanted_members)
    found: dict[str, bytes] = {}
    counts = {name: 0 for name in wanted}
    try:
        with tarfile.open(fileobj=io.BytesIO(raw), mode="r:*") as tf:
            for index, member in enumerate(tf, start=1):
                if index > MAX_TAR_MEMBERS:
                    raise InvalidEvidence("archive member count exceeds accepted bound")
                name = member.name
                try:
                    canonical = _safe_relative_path(name, label="archive member").as_posix()
                except InvalidEvidence as exc:
                    raise InvalidEvidence(f"unsafe archive member: {name!r}") from exc
                if canonical not in wanted:
                    raise InvalidEvidence(f"unexpected archive member: {canonical}")
                counts[canonical] += 1
                if counts[canonical] > 1:
                    raise InvalidEvidence(f"duplicate archive source member: {canonical}")
                if not member.isfile():
                    raise InvalidEvidence(
                        f"archive source member is not a regular file: {canonical}"
                    )
                if member.size < 0 or member.size > MAX_SOURCE_MEMBER_BYTES:
                    raise InvalidEvidence(f"archive source member exceeds size bound: {canonical}")
                stream = tf.extractfile(member)
                if stream is None:
                    raise InvalidEvidence(f"archive source member is unreadable: {canonical}")
                data = stream.read(MAX_SOURCE_MEMBER_BYTES + 1)
                if len(data) != member.size or len(data) > MAX_SOURCE_MEMBER_BYTES:
                    raise InvalidEvidence(f"archive source member size mismatch: {canonical}")
                found[canonical] = data
    except InvalidEvidence:
        raise
    except (tarfile.TarError, OSError, EOFError) as exc:
        raise InvalidEvidence("archive is not a readable tar package") from exc

    missing = [name for name in sorted(wanted) if counts[name] != 1]
    if missing:
        raise InvalidEvidence("archive missing source member(s): " + ", ".join(missing))
    return actual_sha256, found


def _strict_json_object(data: bytes, label: str) -> dict:
    def no_constant(value: str):
        raise InvalidEvidence(f"{label} contains non-finite JSON constant: {value}")

    def unique_object(pairs):
        out = {}
        for key, value in pairs:
            if key in out:
                raise InvalidEvidence(f"{label} contains duplicate key: {key}")
            out[key] = value
        return out

    try:
        parsed = json.loads(
            data.decode("utf-8"),
            parse_constant=no_constant,
            object_pairs_hook=unique_object,
        )
    except InvalidEvidence:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise InvalidEvidence(f"{label} is not strict UTF-8 JSON") from exc
    if not isinstance(parsed, dict):
        raise InvalidEvidence(f"{label} must be a JSON object")
    return parsed


def _validate_source_manifest(
    data: bytes,
    mapping: Mapping[str, tuple[str, PurePosixPath]],
    package: Mapping[str, bytes],
) -> dict:
    manifest = _strict_json_object(data, SOURCE_MANIFEST_MEMBER)
    runtime = manifest.get("runtime")
    if not isinstance(runtime, dict):
        raise InvalidEvidence("SOURCE.json runtime must be an object")
    expected_names = set(mapping)
    actual_names = set(runtime)
    if actual_names != expected_names:
        missing = sorted(expected_names - actual_names)
        extra = sorted(actual_names - expected_names)
        raise InvalidEvidence(
            f"SOURCE.json runtime source-set mismatch: missing={missing}, extra={extra}"
        )

    for name, (declared_source, _source_rel) in mapping.items():
        row = runtime[name]
        if not isinstance(row, dict):
            raise InvalidEvidence(f"SOURCE.json runtime row must be an object: {name}")
        if row.get("source_path") != declared_source:
            raise InvalidEvidence(f"SOURCE.json source_path mismatch: {name}")
        packed = package[name]
        expected_hash = _sha256(packed)
        expected_bytes = len(packed)
        if row.get("sha256") != expected_hash or row.get("bytes") != expected_bytes:
            raise InvalidEvidence(f"SOURCE.json member identity mismatch: {name}")
    return manifest


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
        "publisher_path": PUBLISHER_PATH,
        "tracked_members": [],
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
        live_rel = _safe_relative_path(live_dir, label="live directory")
        head = _git(repo_root, "rev-parse", "HEAD")
        if head != expected_commit:
            raise InvalidEvidence(f"checkout HEAD drift: expected {expected_commit}, got {head}")
        base["commit"] = head

        mapping, publisher_blob = _publisher_source_mapping(
            repo_root, live_rel, expected_commit
        )
        base["publisher_git_blob"] = publisher_blob
        base["tracked_members"] = list(mapping)

        wanted = list(mapping) + [SOURCE_MANIFEST_MEMBER]
        actual_archive_sha256, package = _read_archive_members(
            archive, expected_archive_sha256, wanted
        )
        base["archive_sha256"] = actual_archive_sha256
        _validate_source_manifest(package[SOURCE_MANIFEST_MEMBER], mapping, package)

        stale: list[str] = []
        records = []
        source_cache: dict[PurePosixPath, tuple[bytes, str]] = {}
        for name, (declared_source, repo_rel) in mapping.items():
            if repo_rel not in source_cache:
                source_cache[repo_rel] = _tracked_live_file(
                    repo_root, repo_rel, expected_commit
                )
            live, live_blob = source_cache[repo_rel]
            packed = package[name]
            package_blob = _git_blob(packed)
            same = live == packed
            if not same:
                stale.append(name)
            records.append(
                {
                    "path": name,
                    "source_path": declared_source,
                    "repo_path": repo_rel.as_posix(),
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
        default="revenue/kaggriculture/cloud-execution-lab",
        help="repository-relative canonical publisher/runtime directory",
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
