#!/usr/bin/env python3
"""Fail-closed package-vs-checkout freshness gate for TITAN V4 native execution.

This module does not build, mutate, or extract a package. It authenticates an
already-built tar archive, binds the live files to an exact Git commit, derives
the canonical package source map from the exact publisher contract, and compares
every published source-mapped member against that checkout.
"""
from __future__ import annotations

import argparse
import ast
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
CANONICAL_LIVE_DIR = "revenue/kaggriculture/cloud-execution-lab"
PUBLISHER = "build_integrated.py"
SOURCE_MANIFEST = "SOURCE.json"
MAX_ARCHIVE_BYTES = 32 * 1024 * 1024
MAX_EXTRACTED_BYTES = 64 * 1024 * 1024
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


def _safe_archive_path(value: str) -> str:
    if not isinstance(value, str) or not value or "\\" in value:
        raise InvalidEvidence("archive member path must be a normalized relative POSIX path")
    raw_parts = value.split("/")
    if any(part in ("", ".", "..") for part in raw_parts):
        raise InvalidEvidence(f"unsafe archive member path: {value!r}")
    path = PurePosixPath(value)
    if path.is_absolute() or path.as_posix() != value:
        raise InvalidEvidence(f"unsafe archive member path: {value!r}")
    return value


def _repo_relative_source(live_rel: PurePosixPath, value: str) -> PurePosixPath:
    if not isinstance(value, str) or not value or "\\" in value:
        raise InvalidEvidence("source_path must be a non-empty repository-relative POSIX path")
    raw_parts = value.split("/")
    if any(part in ("", ".") for part in raw_parts):
        raise InvalidEvidence(f"source_path is not normalized: {value!r}")
    if PurePosixPath(value).is_absolute():
        raise InvalidEvidence(f"source_path must be relative: {value!r}")
    parts = list(live_rel.parts)
    for part in raw_parts:
        if part == "..":
            if not parts:
                raise InvalidEvidence(f"source_path escapes repository root: {value!r}")
            parts.pop()
        else:
            parts.append(part)
    if not parts:
        raise InvalidEvidence(f"source_path resolves to repository root: {value!r}")
    return PurePosixPath(*parts)


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
    if before.st_size > MAX_CORE_MEMBER_BYTES:
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


def _pairs_no_dupes(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise InvalidEvidence(f"duplicate JSON object key: {key!r}")
        out[key] = value
    return out


def _reject_constant(value: str):
    raise InvalidEvidence(f"non-finite JSON constant forbidden: {value}")


def _strict_json(raw: bytes, *, label: str):
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise InvalidEvidence(f"{label} is not UTF-8") from exc
    try:
        return json.loads(
            text,
            object_pairs_hook=_pairs_no_dupes,
            parse_constant=_reject_constant,
        )
    except InvalidEvidence:
        raise
    except json.JSONDecodeError as exc:
        raise InvalidEvidence(f"{label} is not valid JSON: {exc}") from exc


def _validate_publisher_ast(runtime_node: ast.AST, source_node: ast.FunctionDef) -> None:
    """Keep selective publisher-map evaluation read-only and structurally narrow."""
    forbidden = (
        ast.Import,
        ast.ImportFrom,
        ast.With,
        ast.AsyncWith,
        ast.Try,
        ast.Raise,
        ast.Delete,
        ast.Global,
        ast.Nonlocal,
        ast.Lambda,
        ast.Yield,
        ast.YieldFrom,
        ast.Await,
        ast.NamedExpr,
    )
    for node in ast.walk(runtime_node):
        if isinstance(node, forbidden) or isinstance(node, (ast.Call, ast.Attribute)):
            raise InvalidEvidence("publisher RUNTIME declaration contains executable side effects")

    allowed_methods = {"rglob", "is_file", "relative_to"}
    for node in ast.walk(source_node):
        if isinstance(node, forbidden):
            raise InvalidEvidence(
                f"publisher source_files() contains forbidden syntax: {type(node).__name__}"
            )
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name) and func.id == "str":
                if node.keywords:
                    raise InvalidEvidence("publisher source_files() str() call may not use keywords")
                continue
            if isinstance(func, ast.Attribute) and func.attr in allowed_methods:
                continue
            label = func.id if isinstance(func, ast.Name) else getattr(func, "attr", type(func).__name__)
            raise InvalidEvidence(f"publisher source_files() contains unsafe call: {label}")
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            if any(isinstance(target, ast.Attribute) for target in targets):
                raise InvalidEvidence("publisher source_files() may not assign through attributes")
        if isinstance(node, (ast.AugAssign, ast.NamedExpr)):
            raise InvalidEvidence(
                f"publisher source_files() contains unsupported assignment: {type(node).__name__}"
            )


def _publisher_source_map(
    repo_root: Path,
    live_rel: PurePosixPath,
    expected_commit: str,
) -> dict[str, str]:
    """Derive source_files() from the exact tracked publisher without executing its module body."""
    publisher_rel = live_rel / PUBLISHER
    source = _read_live_file(repo_root, publisher_rel)
    live_blob = _git_blob(source)
    tracked_blob = _git(
        repo_root,
        "rev-parse",
        f"{expected_commit}:{publisher_rel.as_posix()}",
    )
    if not _is_hex(tracked_blob, 40) or tracked_blob != live_blob:
        raise InvalidEvidence(
            f"publisher is not byte-identical to expected commit: {publisher_rel.as_posix()}"
        )
    try:
        tree = ast.parse(source, filename=publisher_rel.as_posix())
    except SyntaxError as exc:
        raise InvalidEvidence(f"publisher source does not parse: {exc}") from exc

    runtime_nodes = [
        node
        for node in tree.body
        if isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == "RUNTIME" for target in node.targets)
    ]
    source_nodes = [
        node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == "source_files"
    ]
    if len(runtime_nodes) != 1 or len(source_nodes) != 1 or isinstance(source_nodes[0], ast.AsyncFunctionDef):
        raise InvalidEvidence("publisher must expose one top-level RUNTIME assignment and source_files()")
    if source_nodes[0].decorator_list:
        raise InvalidEvidence("publisher source_files() must not be decorated")
    _validate_publisher_ast(runtime_nodes[0], source_nodes[0])

    module = ast.Module(body=[runtime_nodes[0], source_nodes[0]], type_ignores=[])
    ast.fix_missing_locations(module)
    env = {
        "__builtins__": {"str": str},
        "Path": Path,
        "ROOT": repo_root / Path(*live_rel.parts),
    }
    try:
        exec(compile(module, publisher_rel.as_posix(), "exec"), env, env)
        mapping = env["source_files"]()
    except Exception as exc:
        raise InvalidEvidence(
            f"publisher source map derivation failed: {type(exc).__name__}: {exc}"
        ) from exc
    if type(mapping) is not dict or not mapping:
        raise InvalidEvidence("publisher source_files() must return a non-empty object")

    normalized: dict[str, str] = {}
    for member, source_path in mapping.items():
        member = _safe_archive_path(member)
        if member == SOURCE_MANIFEST:
            raise InvalidEvidence("publisher source map may not claim SOURCE.json")
        if not isinstance(source_path, str):
            raise InvalidEvidence(f"publisher source_path for {member!r} must be text")
        _repo_relative_source(live_rel, source_path)
        if member in normalized:
            raise InvalidEvidence(f"publisher source map duplicates member: {member}")
        normalized[member] = source_path
    missing = [name for name in CORE_PATHS if name not in normalized]
    if missing:
        raise InvalidEvidence("publisher source map missing core member(s): " + ", ".join(missing))
    return normalized


def _read_archive_core(
    archive: Path,
    expected_sha256: str,
) -> tuple[str, dict[str, bytes], dict[str, str]]:
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
    total_extracted = 0
    try:
        with tarfile.open(fileobj=io.BytesIO(raw), mode="r:*") as tf:
            for index, member in enumerate(tf, start=1):
                if index > MAX_TAR_MEMBERS:
                    raise InvalidEvidence("archive member count exceeds accepted bound")
                name = _safe_archive_path(member.name)
                if name in found:
                    raise InvalidEvidence(f"duplicate archive member: {name}")
                if not member.isfile():
                    raise InvalidEvidence(f"archive member is not a regular file: {name}")
                if member.size < 0 or member.size > MAX_CORE_MEMBER_BYTES:
                    raise InvalidEvidence(f"archive member exceeds size bound: {name}")
                total_extracted += member.size
                if total_extracted > MAX_EXTRACTED_BYTES:
                    raise InvalidEvidence("archive uncompressed size exceeds accepted bound")
                stream = tf.extractfile(member)
                if stream is None:
                    raise InvalidEvidence(f"archive member is unreadable: {name}")
                data = stream.read(MAX_CORE_MEMBER_BYTES + 1)
                if len(data) != member.size or len(data) > MAX_CORE_MEMBER_BYTES:
                    raise InvalidEvidence(f"archive member size mismatch: {name}")
                found[name] = data
    except InvalidEvidence:
        raise
    except (tarfile.TarError, OSError, EOFError) as exc:
        raise InvalidEvidence("archive is not a readable tar package") from exc

    source_raw = found.get(SOURCE_MANIFEST)
    if source_raw is None:
        raise InvalidEvidence("archive missing SOURCE.json")
    manifest = _strict_json(source_raw, label=SOURCE_MANIFEST)
    if type(manifest) is not dict:
        raise InvalidEvidence("SOURCE.json must contain an object")
    runtime = manifest.get("runtime")
    if type(runtime) is not dict or not runtime:
        raise InvalidEvidence("SOURCE.json runtime must be a non-empty object")

    source_map: dict[str, str] = {}
    for name, row in runtime.items():
        name = _safe_archive_path(name)
        if name == SOURCE_MANIFEST:
            raise InvalidEvidence("SOURCE.json runtime may not claim SOURCE.json")
        if type(row) is not dict:
            raise InvalidEvidence(f"SOURCE.json runtime row for {name!r} must be an object")
        source_path = row.get("source_path")
        expected_member_sha = row.get("sha256")
        expected_member_bytes = row.get("bytes")
        if not isinstance(source_path, str) or not source_path:
            raise InvalidEvidence(f"SOURCE.json runtime row for {name!r} lacks source_path")
        if not _is_hex(expected_member_sha, 64):
            raise InvalidEvidence(f"SOURCE.json runtime row for {name!r} has invalid sha256")
        if type(expected_member_bytes) is not int or expected_member_bytes < 0:
            raise InvalidEvidence(f"SOURCE.json runtime row for {name!r} has invalid bytes")
        if expected_member_bytes > MAX_CORE_MEMBER_BYTES:
            raise InvalidEvidence(f"SOURCE.json runtime row for {name!r} exceeds size bound")
        data = found.get(name)
        if data is None:
            raise InvalidEvidence(f"archive missing source-mapped member: {name}")
        if len(data) != expected_member_bytes or _sha256(data) != expected_member_sha:
            raise InvalidEvidence(f"archive member disagrees with SOURCE.json: {name}")
        source_map[name] = source_path

    missing = [name for name in CORE_PATHS if name not in source_map]
    if missing:
        raise InvalidEvidence("SOURCE.json missing core member(s): " + ", ".join(missing))
    expected_members = set(source_map) | {SOURCE_MANIFEST}
    actual_members = set(found)
    if actual_members != expected_members:
        undeclared = sorted(actual_members - expected_members)
        missing_mapped = sorted(expected_members - actual_members)
        detail = []
        if undeclared:
            detail.append("undeclared=" + ",".join(undeclared))
        if missing_mapped:
            detail.append("missing=" + ",".join(missing_mapped))
        raise InvalidEvidence("archive member set disagrees with SOURCE.json: " + "; ".join(detail))
    return actual_sha256, {name: found[name] for name in source_map}, source_map


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
        "coverage": "canonical_publisher_source_map",
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
        if live_dir != CANONICAL_LIVE_DIR:
            raise InvalidEvidence(
                f"live directory must be canonical: {CANONICAL_LIVE_DIR}"
            )
        live_rel = _safe_relative_path(live_dir)
        head = _git(repo_root, "rev-parse", "HEAD")
        if head != expected_commit:
            raise InvalidEvidence(f"checkout HEAD drift: expected {expected_commit}, got {head}")
        base["commit"] = head

        publisher_map = _publisher_source_map(repo_root, live_rel, expected_commit)
        actual_archive_sha256, package, source_map = _read_archive_core(
            archive, expected_archive_sha256
        )
        base["archive_sha256"] = actual_archive_sha256
        if source_map != publisher_map:
            package_only = sorted(set(source_map) - set(publisher_map))
            publisher_only = sorted(set(publisher_map) - set(source_map))
            remapped = sorted(
                name
                for name in set(source_map) & set(publisher_map)
                if source_map[name] != publisher_map[name]
            )
            detail = []
            if package_only:
                detail.append("package_only=" + ",".join(package_only))
            if publisher_only:
                detail.append("publisher_only=" + ",".join(publisher_only))
            if remapped:
                detail.append("remapped=" + ",".join(remapped))
            raise InvalidEvidence(
                "SOURCE.json runtime does not match canonical publisher source map"
                + (": " + "; ".join(detail) if detail else "")
            )

        stale: list[str] = []
        records = []
        live_cache: dict[str, tuple[bytes, str, str]] = {}
        for name in sorted(source_map):
            repo_rel = _repo_relative_source(live_rel, source_map[name])
            repo_key = repo_rel.as_posix()
            cached = live_cache.get(repo_key)
            if cached is None:
                live = _read_live_file(repo_root, repo_rel)
                live_blob = _git_blob(live)
                tracked_blob = _git(
                    repo_root,
                    "rev-parse",
                    f"{expected_commit}:{repo_key}",
                )
                if not _is_hex(tracked_blob, 40) or tracked_blob != live_blob:
                    raise InvalidEvidence(
                        f"live file is not byte-identical to expected commit: {repo_key}"
                    )
                live_cache[repo_key] = (live, live_blob, tracked_blob)
            else:
                live, live_blob, tracked_blob = cached
            packed = package[name]
            package_blob = _git_blob(packed)
            same = live == packed
            if not same:
                stale.append(name)
            records.append(
                {
                    "path": name,
                    "source_path": source_map[name],
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

        final_publisher_map = _publisher_source_map(repo_root, live_rel, expected_commit)
        if final_publisher_map != publisher_map:
            raise InvalidEvidence("canonical publisher source map changed during verification")
        for repo_key, (_, _, tracked_blob) in live_cache.items():
            live_final = _read_live_file(repo_root, PurePosixPath(repo_key))
            if _git_blob(live_final) != tracked_blob:
                raise InvalidEvidence(f"live file changed during verification: {repo_key}")

        final_head = _git(repo_root, "rev-parse", "HEAD")
        if final_head != expected_commit:
            raise InvalidEvidence(
                f"checkout HEAD changed during verification: expected {expected_commit}, got {final_head}"
            )

        base["publisher_members"] = len(source_map)
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
