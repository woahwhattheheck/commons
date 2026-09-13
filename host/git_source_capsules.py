"""Exact committed-tree Git source capsules for Commons context packets."""

from __future__ import annotations

import hashlib
import re
import subprocess
from pathlib import Path
from typing import Any, Sequence

HEX40 = re.compile(r"[0-9a-f]{40}")
ORDINARY_BLOB_MODES = {"100644", "100755"}
MAX_SOURCE_PATHS = 32
MAX_FILE_BYTES_CEILING = 1_048_576


class GitSourceError(ValueError):
    pass


def _run(repo: Path, args: Sequence[str], *, input_bytes: bytes | None = None) -> bytes:
    try:
        proc = subprocess.run(
            ["git", "-C", str(repo), *args],
            input=input_bytes,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
    except OSError as exc:
        raise GitSourceError(f"git unavailable: {exc}") from exc
    if proc.returncode != 0:
        detail = proc.stderr.decode("utf-8", "replace").strip()
        raise GitSourceError(f"git command failed: {' '.join(args)}: {detail[:240]}")
    return proc.stdout


def _canonical_path(raw: str) -> str:
    if not isinstance(raw, str):
        raise GitSourceError("source path must be a string")
    if not raw or raw != raw.strip() or len(raw) > 512:
        raise GitSourceError("source path must be 1..512 canonical characters")
    if raw.startswith("/") or "\\" in raw or "\x00" in raw or raw.startswith(":"):
        raise GitSourceError(f"unsafe source path: {raw!r}")
    if any(ch in raw for ch in "*?[]"):
        raise GitSourceError(f"pathspec metacharacters are not allowed: {raw!r}")
    pieces = raw.split("/")
    if any(piece in ("", ".", "..") for piece in pieces):
        raise GitSourceError(f"non-canonical source path: {raw!r}")
    if any(ord(ch) < 32 or ord(ch) == 127 for ch in raw):
        raise GitSourceError(f"control character in source path: {raw!r}")
    return raw


def _object_type(repo: Path, oid: str) -> str:
    return _run(repo, ["cat-file", "-t", oid]).decode("ascii", "strict").strip()


def _commit_tree(repo: Path, commit: str) -> str:
    raw = _run(repo, ["cat-file", "-p", commit])
    for line in raw.split(b"\n"):
        if line.startswith(b"tree "):
            try:
                tree = line[5:].decode("ascii", "strict")
            except UnicodeDecodeError as exc:
                raise GitSourceError("commit has malformed tree header") from exc
            if HEX40.fullmatch(tree):
                return tree
            break
    raise GitSourceError("commit has no canonical 40-hex tree")


def _observed_main(repo: Path) -> str | None:
    try:
        raw = _run(repo, ["rev-parse", "--verify", "refs/heads/main"]).decode("ascii", "strict").strip()
    except GitSourceError:
        return None
    return raw if HEX40.fullmatch(raw) else None


def _tree_entry(repo: Path, commit: str, path: str) -> tuple[str, str, str]:
    raw = _run(repo, ["ls-tree", "-z", "--full-tree", commit, "--", path])
    rows = [row for row in raw.split(b"\x00") if row]
    if len(rows) != 1:
        raise GitSourceError(f"source path must resolve to exactly one committed entry: {path}")
    try:
        meta, returned = rows[0].split(b"\t", 1)
        mode_b, typ_b, oid_b = meta.split(b" ", 2)
        mode = mode_b.decode("ascii", "strict")
        typ = typ_b.decode("ascii", "strict")
        oid = oid_b.decode("ascii", "strict")
        returned_path = returned.decode("utf-8", "strict")
    except (ValueError, UnicodeDecodeError) as exc:
        raise GitSourceError(f"malformed ls-tree result for {path}") from exc
    if returned_path != path:
        raise GitSourceError(f"source path resolved ambiguously: requested {path!r}, got {returned_path!r}")
    if typ != "blob" or mode not in ORDINARY_BLOB_MODES or not HEX40.fullmatch(oid):
        raise GitSourceError(f"source path is not an ordinary committed blob: {path} mode={mode} type={typ}")
    return mode, typ, oid


def _blob(repo: Path, oid: str, expected_size: int, collect_limit: int) -> tuple[str, bytes | None]:
    try:
        proc = subprocess.Popen(
            ["git", "-C", str(repo), "cat-file", "blob", oid],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except OSError as exc:
        raise GitSourceError(f"git unavailable: {exc}") from exc
    if proc.stdout is None:
        proc.kill()
        raise GitSourceError("git cat-file stdout unavailable")
    hasher = hashlib.sha256()
    collected = bytearray() if expected_size <= collect_limit else None
    seen = 0
    while True:
        chunk = proc.stdout.read(65536)
        if not chunk:
            break
        seen += len(chunk)
        hasher.update(chunk)
        if collected is not None:
            collected.extend(chunk)
    if proc.stdout is not None:
        proc.stdout.close()
    stderr = proc.stderr.read() if proc.stderr is not None else b""
    if proc.stderr is not None:
        proc.stderr.close()
    code = proc.wait()
    if code != 0:
        raise GitSourceError(f"git cat-file blob failed: {stderr.decode('utf-8', 'replace')[:240]}")
    if seen != expected_size:
        raise GitSourceError(f"blob size changed while reading {oid}: expected {expected_size}, got {seen}")
    return hasher.hexdigest(), bytes(collected) if collected is not None else None


def _text_status(raw: bytes | None, *, oversized: bool) -> tuple[str | None, str | None]:
    if oversized:
        return None, "FILE_TOO_LARGE"
    if raw is None:
        raise GitSourceError("blob bytes unavailable below collection limit")
    try:
        text = raw.decode("utf-8", "strict")
    except UnicodeDecodeError:
        return None, "NON_UTF8"
    if any((ord(ch) < 32 and ch not in "\n\r\t") or ord(ch) == 127 for ch in text):
        return None, "NON_TEXT_CONTROL"
    return text, None


def collect_git_source(
    repository: str | Path,
    commit: str,
    paths: Sequence[str],
    *,
    max_file_bytes: int = 16_384,
) -> dict[str, Any]:
    """Read only exact committed Git objects for explicitly requested paths."""
    repo = Path(repository)
    if not repo.is_dir():
        raise GitSourceError(f"repository path is not a directory: {repo}")
    if not isinstance(commit, str) or not HEX40.fullmatch(commit):
        raise GitSourceError("source commit must be exact lowercase 40-hex")
    if type(max_file_bytes) is not int or not (1 <= max_file_bytes <= MAX_FILE_BYTES_CEILING):
        raise GitSourceError(f"max_file_bytes must be 1..{MAX_FILE_BYTES_CEILING}")
    if isinstance(paths, (str, bytes)):
        raise GitSourceError("source paths must be a sequence of explicit paths")
    canonical_paths = sorted({_canonical_path(path) for path in paths})
    if not canonical_paths:
        raise GitSourceError("at least one explicit source path is required")
    if len(canonical_paths) > MAX_SOURCE_PATHS:
        raise GitSourceError(f"source path count exceeds {MAX_SOURCE_PATHS}")
    if _object_type(repo, commit) != "commit":
        raise GitSourceError("source commit does not name a commit object")

    tree_sha = _commit_tree(repo, commit)
    observed_main = _observed_main(repo)
    capsules: list[dict[str, Any]] = []
    for path in canonical_paths:
        mode, _, blob_sha = _tree_entry(repo, commit, path)
        size_text = _run(repo, ["cat-file", "-s", blob_sha]).decode("ascii", "strict").strip()
        try:
            size = int(size_text)
        except ValueError as exc:
            raise GitSourceError(f"invalid blob size for {path}") from exc
        if size < 0:
            raise GitSourceError(f"negative blob size for {path}")
        content_sha256, raw = _blob(repo, blob_sha, size, max_file_bytes)
        text, reason = _text_status(raw, oversized=size > max_file_bytes)
        row: dict[str, Any] = {
            "path": path,
            "mode": mode,
            "blob_sha": blob_sha,
            "content_sha256": content_sha256,
            "bytes": size,
        }
        if text is None:
            row["text"] = None
            row["source_omission_reason"] = reason
        else:
            row["text"] = text
        capsules.append(row)

    return {
        "commit": commit,
        "tree_sha": tree_sha,
        "observed_main_head": observed_main,
        "source_commit_matches_observed_main": None if observed_main is None else observed_main == commit,
        "max_file_bytes": max_file_bytes,
        "requested_paths": canonical_paths,
        "capsules": capsules,
    }


def verify_git_source(bundle: Any, repository: str | Path) -> tuple[bool, str]:
    """Re-read committed objects and verify packet source metadata/text against them."""
    if not isinstance(bundle, dict):
        return False, "git-source-shape"
    commit = bundle.get("commit")
    requested = bundle.get("requested_paths")
    max_file_bytes = bundle.get("max_file_bytes")
    capsules = bundle.get("capsules")
    if not isinstance(requested, list) or not isinstance(capsules, list):
        return False, "git-source-shape"
    try:
        expected = collect_git_source(repository, commit, requested, max_file_bytes=max_file_bytes)
    except (GitSourceError, TypeError):
        return False, "git-source-read"
    for key in ("commit", "tree_sha", "max_file_bytes", "requested_paths"):
        if bundle.get(key) != expected.get(key):
            return False, f"git-source-{key.replace('_', '-')}"
    # observed main is drift metadata, never source authority; it may legitimately move later.
    actual_by_path = {row["path"]: row for row in expected["capsules"]}
    if len(actual_by_path) != len(capsules):
        return False, "git-source-capsule-count"
    for packet_row in capsules:
        if not isinstance(packet_row, dict):
            return False, "git-source-capsule-shape"
        path = packet_row.get("path")
        actual = actual_by_path.get(path)
        if actual is None:
            return False, "git-source-path"
        for key in ("mode", "blob_sha", "content_sha256", "bytes"):
            if packet_row.get(key) != actual.get(key):
                return False, f"git-source-{key.replace('_', '-')}"
        if packet_row.get("text_included") is True:
            if "text" not in packet_row or packet_row.get("text") != actual.get("text") or actual.get("text") is None:
                return False, "git-source-text"
        elif packet_row.get("text_included") is False:
            reason = packet_row.get("omission_reason")
            if reason not in {"PACKET_BUDGET", actual.get("source_omission_reason")}:
                return False, "git-source-omission"
        else:
            return False, "git-source-inclusion-flag"
    return True, "ok"
